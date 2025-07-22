"""
Enhanced notification service with multi-channel support
Handles Discord, email, and web push notifications with escalation logic
"""

import asyncio
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from typing import Any, Dict, List, Optional, Set
from enum import Enum
import json

from utils.logging_config import get_logger, get_user_action_logger, PerformanceMonitor

from .database import get_database_manager
from .models import NotificationChannel, NotificationPreferences
from .websocket import get_websocket_manager

logger = get_logger(__name__)
user_logger = get_user_action_logger()


class NotificationPriority(str, Enum):
    """Notification priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationStatus(str, Enum):
    """Notification delivery status"""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    ESCALATED = "escalated"


class NotificationException(Exception):
    """Custom exception for notification operations"""
    
    def __init__(self, message: str, channel: str = None, error_code: str = "NOTIFICATION_ERROR"):
        self.message = message
        self.channel = channel
        self.error_code = error_code
        super().__init__(message)


class NotificationService:
    """Enhanced notification service with multi-channel support"""
    
    def __init__(self):
        self.db = None
        self.websocket_manager = None
        self.discord_bot = None
        self.email_config = {}
        self.web_push_config = {}
        self.escalation_rules = {}
        self.quiet_hours_cache = {}
    
    async def initialize(self, discord_bot=None, email_config=None, web_push_config=None):
        """Initialize the notification service"""
        self.db = await get_database_manager()
        self.websocket_manager = get_websocket_manager()
        self.discord_bot = discord_bot
        self.email_config = email_config or {}
        self.web_push_config = web_push_config or {}
        
        # Load escalation rules
        await self._load_escalation_rules()
    
    async def notify_task_assignment(
        self,
        task_id: int,
        assigned_users: List[str],
        assigned_by: str,
        message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send notifications for task assignments to multiple users"""
        with PerformanceMonitor("notify_task_assignment"):
            try:
                # Get task details
                task = await self._get_task_details(task_id)
                if not task:
                    raise NotificationException(f"Task {task_id} not found", error_code="TASK_NOT_FOUND")
                
                # Get assigner details
                assigner = await self._get_user_details(assigned_by)
                
                notification_results = {}
                
                # Send notifications to each assigned user
                for user_id in assigned_users:
                    try:
                        # Get user preferences
                        preferences = await self._get_user_notification_preferences(user_id)
                        
                        # Check quiet hours
                        if await self._is_quiet_hours(user_id, preferences):
                            # Schedule for later delivery
                            await self._schedule_notification(
                                user_id, "task_assignment", task_id, 
                                {"task": task, "assigned_by": assigner, "message": message}
                            )
                            notification_results[user_id] = {"status": "scheduled", "channels": []}
                            continue
                        
                        # Send through enabled channels
                        channels_used = []
                        
                        # Discord notification
                        if preferences.get('discord_notifications', True):
                            discord_result = await self._send_discord_notification(
                                user_id, "task_assignment", {
                                    "task": task,
                                    "assigned_by": assigner,
                                    "message": message
                                }
                            )
                            if discord_result:
                                channels_used.append("discord")
                        
                        # Email notification
                        if preferences.get('email_notifications', False) and preferences.get('email_address'):
                            email_result = await self._send_email_notification(
                                preferences['email_address'], "task_assignment", {
                                    "task": task,
                                    "assigned_by": assigner,
                                    "message": message
                                }
                            )
                            if email_result:
                                channels_used.append("email")
                        
                        # Web push notification
                        if preferences.get('web_push_notifications', True):
                            web_push_result = await self._send_web_push_notification(
                                user_id, "task_assignment", {
                                    "task": task,
                                    "assigned_by": assigner,
                                    "message": message
                                }
                            )
                            if web_push_result:
                                channels_used.append("web_push")
                        
                        notification_results[user_id] = {
                            "status": "sent" if channels_used else "failed",
                            "channels": channels_used
                        }
                        
                        # Log notification activity
                        await self._log_notification_activity(
                            user_id, "task_assignment", task_id, channels_used
                        )
                        
                    except Exception as e:
                        logger.error(f"Failed to notify user {user_id} about task assignment: {e}")
                        notification_results[user_id] = {"status": "failed", "error": str(e)}
                
                # Log user action
                user_logger.log_task_action(
                    assigned_by, "task_assigned", task_id, 
                    f"Notified {len(assigned_users)} users"
                )
                
                return {
                    "task_id": task_id,
                    "notification_results": notification_results,
                    "total_users": len(assigned_users),
                    "successful_notifications": len([r for r in notification_results.values() if r["status"] == "sent"])
                }
                
            except Exception as e:
                logger.error(f"Failed to send task assignment notifications: {e}")
                raise NotificationException("Task assignment notification failed", error_code="ASSIGNMENT_NOTIFICATION_FAILED")
    
    async def notify_task_update(
        self,
        task_id: int,
        updated_by: str,
        update_type: str,
        update_data: Dict[str, Any]
    ) -> bool:
        """Send notifications for task updates"""
        with PerformanceMonitor("notify_task_update"):
            try:
                # Get task and involved users
                task = await self._get_task_details(task_id)
                if not task:
                    return False
                
                # Get all users involved with the task
                involved_users = set()
                involved_users.add(task['created_by_user_id'])
                involved_users.update(task.get('assigned_users', []))
                
                # Remove the user who made the update
                involved_users.discard(updated_by)
                
                if not involved_users:
                    return True
                
                # Send notifications
                for user_id in involved_users:
                    try:
                        preferences = await self._get_user_notification_preferences(user_id)
                        
                        # Check if user wants task update notifications
                        if not preferences.get('task_updates', True):
                            continue
                        
                        # Send through preferred channels
                        await self._send_multi_channel_notification(
                            user_id, "task_update", {
                                "task": task,
                                "updated_by": updated_by,
                                "update_type": update_type,
                                "update_data": update_data
                            }, preferences
                        )
                        
                    except Exception as e:
                        logger.error(f"Failed to notify user {user_id} about task update: {e}")
                
                return True
                
            except Exception as e:
                logger.error(f"Failed to send task update notifications: {e}")
                return False
    
    async def notify_overdue_tasks(self) -> Dict[str, Any]:
        """Send escalation notifications for overdue tasks"""
        with PerformanceMonitor("notify_overdue_tasks"):
            try:
                # Get overdue tasks
                overdue_tasks = await self._get_overdue_tasks()
                
                notification_results = {
                    "total_overdue_tasks": len(overdue_tasks),
                    "notifications_sent": 0,
                    "escalations_triggered": 0,
                    "failed_notifications": 0
                }
                
                for task in overdue_tasks:
                    try:
                        # Check if task has already been escalated recently
                        last_escalation = await self._get_last_escalation(task['id'])
                        
                        # Determine escalation level based on how overdue the task is
                        overdue_hours = (datetime.now() - task['due_time']).total_seconds() / 3600
                        escalation_level = self._calculate_escalation_level(overdue_hours)
                        
                        # Get users to notify (assigned users + creator)
                        users_to_notify = set()
                        users_to_notify.add(task['created_by_user_id'])
                        users_to_notify.update(task.get('assigned_users', []))
                        
                        # Send escalation notifications
                        for user_id in users_to_notify:
                            success = await self._send_escalation_notification(
                                user_id, task, escalation_level, overdue_hours
                            )
                            
                            if success:
                                notification_results["notifications_sent"] += 1
                            else:
                                notification_results["failed_notifications"] += 1
                        
                        # Record escalation
                        await self._record_escalation(task['id'], escalation_level)
                        notification_results["escalations_triggered"] += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to process overdue task {task['id']}: {e}")
                        notification_results["failed_notifications"] += 1
                
                return notification_results
                
            except Exception as e:
                logger.error(f"Failed to process overdue task notifications: {e}")
                raise NotificationException("Overdue task notification processing failed")
    
    async def send_daily_summary(self, user_id: str) -> bool:
        """Send daily productivity summary to user"""
        with PerformanceMonitor("send_daily_summary"):
            try:
                # Get user preferences
                preferences = await self._get_user_notification_preferences(user_id)
                
                if not preferences.get('daily_summaries', True):
                    return True  # User doesn't want summaries
                
                # Get daily summary data
                summary_data = await self._generate_daily_summary(user_id)
                
                # Send through preferred channels
                return await self._send_multi_channel_notification(
                    user_id, "daily_summary", summary_data, preferences
                )
                
            except Exception as e:
                logger.error(f"Failed to send daily summary to user {user_id}: {e}")
                return False
    
    async def send_reminder_notification(
        self,
        user_id: str,
        task_id: int,
        reminder_type: str = "upcoming"
    ) -> bool:
        """Send task reminder notification"""
        with PerformanceMonitor("send_reminder_notification"):
            try:
                # Get task details
                task = await self._get_task_details(task_id)
                if not task:
                    return False
                
                # Get user preferences
                preferences = await self._get_user_notification_preferences(user_id)
                
                if not preferences.get('task_reminders', True):
                    return True  # User doesn't want reminders
                
                # Check quiet hours
                if await self._is_quiet_hours(user_id, preferences):
                    return True  # Skip during quiet hours
                
                # Send reminder
                return await self._send_multi_channel_notification(
                    user_id, "task_reminder", {
                        "task": task,
                        "reminder_type": reminder_type
                    }, preferences
                )
                
            except Exception as e:
                logger.error(f"Failed to send reminder for task {task_id} to user {user_id}: {e}")
                return False
    
    # Private helper methods
    
    async def _send_multi_channel_notification(
        self,
        user_id: str,
        notification_type: str,
        data: Dict[str, Any],
        preferences: Dict[str, Any]
    ) -> bool:
        """Send notification through multiple channels based on preferences"""
        channels_used = []
        
        try:
            # Discord notification
            if preferences.get('discord_notifications', True):
                if await self._send_discord_notification(user_id, notification_type, data):
                    channels_used.append("discord")
            
            # Email notification
            if preferences.get('email_notifications', False) and preferences.get('email_address'):
                if await self._send_email_notification(preferences['email_address'], notification_type, data):
                    channels_used.append("email")
            
            # Web push notification
            if preferences.get('web_push_notifications', True):
                if await self._send_web_push_notification(user_id, notification_type, data):
                    channels_used.append("web_push")
            
            # Log notification activity
            await self._log_notification_activity(user_id, notification_type, data.get('task', {}).get('id'), channels_used)
            
            return len(channels_used) > 0
            
        except Exception as e:
            logger.error(f"Failed to send multi-channel notification: {e}")
            return False
    
    async def _send_discord_notification(
        self,
        user_id: str,
        notification_type: str,
        data: Dict[str, Any]
    ) -> bool:
        """Send Discord notification"""
        try:
            if not self.discord_bot:
                return False
            
            # Get Discord user
            try:
                discord_user = await self.discord_bot.fetch_user(int(user_id))
                if not discord_user:
                    return False
            except:
                return False
            
            # Create notification message based on type
            embed = await self._create_discord_embed(notification_type, data)
            
            # Send DM
            await discord_user.send(embed=embed)
            return True
            
        except Exception as e:
            logger.error(f"Failed to send Discord notification to {user_id}: {e}")
            return False
    
    async def _send_email_notification(
        self,
        email_address: str,
        notification_type: str,
        data: Dict[str, Any]
    ) -> bool:
        """Send email notification"""
        try:
            if not self.email_config.get('smtp_server'):
                return False
            
            # Create email content
            subject, body = await self._create_email_content(notification_type, data)
            
            # Create message
            msg = MimeMultipart()
            msg['From'] = self.email_config['from_address']
            msg['To'] = email_address
            msg['Subject'] = subject
            
            msg.attach(MimeText(body, 'html'))
            
            # Send email
            with smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port']) as server:
                if self.email_config.get('use_tls'):
                    server.starttls()
                
                if self.email_config.get('username'):
                    server.login(self.email_config['username'], self.email_config['password'])
                
                server.send_message(msg)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email notification to {email_address}: {e}")
            return False
    
    async def _send_web_push_notification(
        self,
        user_id: str,
        notification_type: str,
        data: Dict[str, Any]
    ) -> bool:
        """Send web push notification through WebSocket"""
        try:
            # Create notification payload
            notification_payload = {
                "type": "notification",
                "notification_type": notification_type,
                "data": data,
                "timestamp": datetime.now().isoformat()
            }
            
            # Send through WebSocket
            return await self.websocket_manager.send_notification(user_id, notification_payload)
            
        except Exception as e:
            logger.error(f"Failed to send web push notification to {user_id}: {e}")
            return False
    
    async def _is_quiet_hours(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """Check if current time is within user's quiet hours"""
        try:
            quiet_start = preferences.get('quiet_hours_start')
            quiet_end = preferences.get('quiet_hours_end')
            
            if not quiet_start or not quiet_end:
                return False
            
            # Parse time strings and check current time
            from datetime import time
            current_time = datetime.now().time()
            
            start_time = datetime.strptime(quiet_start, '%H:%M').time()
            end_time = datetime.strptime(quiet_end, '%H:%M').time()
            
            if start_time <= end_time:
                return start_time <= current_time <= end_time
            else:  # Quiet hours span midnight
                return current_time >= start_time or current_time <= end_time
            
        except Exception as e:
            logger.error(f"Failed to check quiet hours for user {user_id}: {e}")
            return False
    
    async def _get_user_notification_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user's notification preferences"""
        # Check cache first
        cache_key = f"notification_prefs:{user_id}"
        cached_prefs = await self.db.cache_get(cache_key)
        if cached_prefs:
            return cached_prefs
        
        # Get from database
        query = """
            SELECT * FROM notification_preferences
            WHERE user_id = $1
        """
        
        result = await self.db.execute_query(query, (user_id,), fetch_one=True)
        
        if result:
            prefs = dict(result)
        else:
            # Default preferences
            prefs = {
                'user_id': user_id,
                'task_reminders': True,
                'overdue_alerts': True,
                'daily_summaries': True,
                'email_notifications': False,
                'web_push_notifications': True,
                'discord_notifications': True,
                'reminder_minutes': 15,
                'quiet_hours_start': None,
                'quiet_hours_end': None,
                'email_address': None
            }
        
        # Cache the preferences
        await self.db.cache_set(cache_key, prefs, expire=1800)  # 30 minutes
        
        return prefs
    
    async def _get_task_details(self, task_id: int) -> Optional[Dict[str, Any]]:
        """Get task details for notifications"""
        query = """
            SELECT t.*, 
                   array_agg(DISTINCT ta.assigned_user_id) FILTER (WHERE ta.assigned_user_id IS NOT NULL) as assigned_users
            FROM tasks t
            LEFT JOIN task_assignments ta ON t.id = ta.task_id
            WHERE t.id = $1
            GROUP BY t.id
        """
        
        result = await self.db.execute_query(query, (task_id,), fetch_one=True)
        return dict(result) if result else None
    
    async def _get_user_details(self, user_id: str) -> Dict[str, Any]:
        """Get user details for notifications"""
        # This would typically fetch from a users table or Discord API
        return {
            'id': user_id,
            'username': f'User {user_id[:8]}',
            'display_name': f'User {user_id[:8]}'
        }
    
    async def _create_discord_embed(self, notification_type: str, data: Dict[str, Any]):
        """Create Discord embed for notification"""
        # This would create appropriate Discord embeds based on notification type
        # Implementation would depend on discord.py library
        pass
    
    async def _create_email_content(self, notification_type: str, data: Dict[str, Any]) -> tuple:
        """Create email subject and body for notification"""
        # Implementation for email content creation
        subject = f"Task Notification - {notification_type}"
        body = f"<html><body><h2>{notification_type}</h2><p>Task details...</p></body></html>"
        return subject, body
    
    async def _log_notification_activity(
        self,
        user_id: str,
        notification_type: str,
        task_id: Optional[int],
        channels: List[str]
    ):
        """Log notification activity"""
        await self.db.log_user_activity({
            'user_id': user_id,
            'activity_type': 'notification_sent',
            'activity_data': {
                'notification_type': notification_type,
                'task_id': task_id,
                'channels': channels
            },
            'source': 'notification_service'
        })
    
    async def _schedule_notification(
        self,
        user_id: str,
        notification_type: str,
        task_id: int,
        data: Dict[str, Any]
    ):
        """Schedule notification for later delivery"""
        # Implementation for scheduling notifications
        pass
    
    async def _get_overdue_tasks(self) -> List[Dict[str, Any]]:
        """Get all overdue tasks"""
        query = """
            SELECT t.*, 
                   array_agg(DISTINCT ta.assigned_user_id) FILTER (WHERE ta.assigned_user_id IS NOT NULL) as assigned_users
            FROM tasks t
            LEFT JOIN task_assignments ta ON t.id = ta.task_id
            WHERE t.due_time < NOW() 
            AND t.status NOT IN ('completed', 'cancelled')
            GROUP BY t.id
            ORDER BY t.due_time
        """
        
        return await self.db.execute_query(query)
    
    async def _send_escalation_notification(
        self,
        user_id: str,
        task: Dict[str, Any],
        escalation_level: int,
        overdue_hours: float
    ) -> bool:
        """Send escalation notification for overdue task"""
        try:
            preferences = await self._get_user_notification_preferences(user_id)
            
            if not preferences.get('overdue_alerts', True):
                return True  # User doesn't want overdue alerts
            
            return await self._send_multi_channel_notification(
                user_id, "task_overdue", {
                    "task": task,
                    "escalation_level": escalation_level,
                    "overdue_hours": overdue_hours
                }, preferences
            )
            
        except Exception as e:
            logger.error(f"Failed to send escalation notification: {e}")
            return False
    
    def _calculate_escalation_level(self, overdue_hours: float) -> int:
        """Calculate escalation level based on how overdue a task is"""
        if overdue_hours < 2:
            return 1  # Low escalation
        elif overdue_hours < 8:
            return 2  # Medium escalation
        elif overdue_hours < 24:
            return 3  # High escalation
        else:
            return 4  # Critical escalation
    
    async def _get_last_escalation(self, task_id: int) -> Optional[datetime]:
        """Get the last escalation time for a task"""
        # Implementation for tracking escalation history
        return None
    
    async def _record_escalation(self, task_id: int, escalation_level: int):
        """Record escalation in database"""
        # Implementation for recording escalation history
        pass
    
    async def _generate_daily_summary(self, user_id: str) -> Dict[str, Any]:
        """Generate daily productivity summary for user"""
        # Implementation for daily summary generation
        return {
            "user_id": user_id,
            "date": datetime.now().date().isoformat(),
            "tasks_completed": 0,
            "tasks_pending": 0,
            "productivity_score": 0
        }
    
    async def _load_escalation_rules(self):
        """Load escalation rules from configuration"""
        self.escalation_rules = {
            "default": {
                "levels": [
                    {"hours": 2, "channels": ["discord"]},
                    {"hours": 8, "channels": ["discord", "web_push"]},
                    {"hours": 24, "channels": ["discord", "web_push", "email"]},
                    {"hours": 48, "channels": ["discord", "web_push", "email"]}
                ]
            }
        }


# Global service instance
notification_service: Optional[NotificationService] = None


async def get_notification_service() -> NotificationService:
    """Get the global notification service instance"""
    global notification_service
    if notification_service is None:
        notification_service = NotificationService()
        await notification_service.initialize()
    return notification_service