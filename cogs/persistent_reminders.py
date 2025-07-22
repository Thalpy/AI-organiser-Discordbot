# Enhanced Persistent Reminder System for Discord Task Management Bot
# Handles continuous reminders with multi-user support, escalation, and smart routing

from discord.ext import commands, tasks
from discord import app_commands
import discord
import datetime
from typing import Dict, Set, Optional, List, Any
import asyncio
from enum import Enum

from utils.database import TaskQueries, DatabaseManager
from utils.discord_helpers import EmbedBuilder, ErrorHandler
from utils.logging_config import get_logger, get_user_action_logger
from src.discord_web_bridge import get_discord_web_bridge, BridgeMessage
from src.sync_service import get_sync_service, sync_notification_to_discord
from src.notifications import get_notification_service
import logging

logger = get_logger(__name__)
user_logger = get_user_action_logger()


class NotificationChannel(Enum):
    """Available notification channels"""
    DISCORD_DM = "discord_dm"
    DISCORD_GUILD = "discord_guild"
    WEB_PUSH = "web_push"
    EMAIL = "email"


class EscalationLevel(Enum):
    """Escalation levels for overdue tasks"""
    NORMAL = "normal"
    URGENT = "urgent"
    CRITICAL = "critical"


class NotificationHistory:
    """Tracks notification history for analytics and debugging"""
    
    def __init__(self):
        self.history: Dict[str, List[Dict[str, Any]]] = {}
    
    def add_notification(self, user_id: str, notification_data: Dict[str, Any]):
        """Add a notification to history"""
        if user_id not in self.history:
            self.history[user_id] = []
        
        notification_record = {
            **notification_data,
            'timestamp': datetime.datetime.now().isoformat(),
            'id': f"{user_id}_{len(self.history[user_id])}"
        }
        
        self.history[user_id].append(notification_record)
        
        # Keep only last 100 notifications per user
        if len(self.history[user_id]) > 100:
            self.history[user_id] = self.history[user_id][-100:]
    
    def get_user_history(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get notification history for a user"""
        return self.history.get(user_id, [])[-limit:]
    
    def get_delivery_stats(self, user_id: str) -> Dict[str, Any]:
        """Get delivery statistics for a user"""
        user_history = self.history.get(user_id, [])
        
        if not user_history:
            return {'total': 0, 'success': 0, 'failed': 0, 'success_rate': 0}
        
        total = len(user_history)
        success = sum(1 for n in user_history if n.get('delivered', False))
        failed = total - success
        success_rate = (success / total) * 100 if total > 0 else 0
        
        return {
            'total': total,
            'success': success,
            'failed': failed,
            'success_rate': round(success_rate, 2)
        }

class PersistentReminderManager(commands.Cog):
    """Enhanced persistent reminders with multi-user support, escalation, and smart routing"""
    
    def __init__(self, bot):
        self.bot = bot
        # Track active reminders: {task_id: reminder_info}
        self.active_reminders: Dict[int, Dict] = {}
        # Track users who have been reminded: {user_id: {task_id, last_reminded}}
        self.user_reminder_state: Dict[str, Dict] = {}
        # Track collaborative task reminders: {task_id: {user_id: reminder_info}}
        self.collaborative_reminders: Dict[int, Dict[str, Dict]] = {}
        # Notification history tracker
        self.notification_history = NotificationHistory()
        # Discord-Web bridge for cross-platform notifications
        self.bridge = get_discord_web_bridge()
        self.sync_service = get_sync_service()
        
        # Start background tasks
        self.check_new_reminders.start()
        self.send_persistent_reminders.start()
        self.check_escalation_reminders.start()
        self.cleanup_old_reminders.start()
        
        logger.info("Enhanced PersistentReminderManager initialized")

    def cog_unload(self):
        self.check_new_reminders.cancel()
        self.send_persistent_reminders.cancel()
        logger.info("PersistentReminderManager unloaded")

    @tasks.loop(minutes=1)
    async def check_new_reminders(self):
        """Check for tasks that need to start sending reminders"""
        try:
            now = datetime.datetime.now()
            
            # Get all users and their reminder preferences
            query = """
                SELECT DISTINCT t.id, t.user_id, t.description, t.due_time, t.duration_minutes, t.location,
                       COALESCE(np.reminder_minutes, 15) as reminder_minutes,
                       COALESCE(np.task_reminders, true) as reminders_enabled
                FROM tasks t
                LEFT JOIN notification_preferences np ON t.user_id = np.user_id
                WHERE t.status = 'pending' 
                AND t.due_time IS NOT NULL
                AND t.due_time > %s
            """
            
            tasks = await DatabaseManager.execute_query(query, (now,), fetch_all=True)
            
            for task in tasks:
                task_id = task['id']
                user_id = task['user_id']
                reminder_minutes = task['reminder_minutes']
                
                # Skip if reminders disabled
                if not task['reminders_enabled']:
                    continue
                
                # Skip if already in active reminders
                if task_id in self.active_reminders:
                    continue
                
                # Check if it's time to start reminding
                reminder_time = task['due_time'] - datetime.timedelta(minutes=reminder_minutes)
                
                if now >= reminder_time:
                    # Start persistent reminding
                    await self.start_persistent_reminder(task)
                    
        except Exception as e:
            logger.error(f"Error checking new reminders: {e}")

    @tasks.loop(minutes=2)  # Send reminders every 2 minutes
    async def send_persistent_reminders(self):
        """Send reminders for all active reminder tasks"""
        try:
            current_time = datetime.datetime.now()
            
            for task_id, reminder_info in list(self.active_reminders.items()):
                try:
                    # Check if task is still pending
                    task = await TaskQueries.get_task_by_id(task_id, reminder_info['user_id'])
                    
                    if not task or task['status'] != 'pending':
                        # Task was started, completed, or deleted - stop reminding
                        await self.stop_persistent_reminder(task_id, "Task status changed")
                        continue
                    
                    # Check if task time has passed
                    if current_time > task['due_time']:
                        # Task is overdue - send overdue reminder instead
                        await self.send_overdue_reminder(task)
                        await self.stop_persistent_reminder(task_id, "Task overdue")
                        continue
                    
                    # Send the persistent reminder
                    await self.send_reminder_message(task, reminder_info)
                    
                    # Update last reminded time
                    reminder_info['last_reminded'] = current_time
                    reminder_info['reminder_count'] += 1
                    
                    # Log the reminder
                    user_logger.log_task_action(
                        reminder_info['user_id'], 
                        "persistent_reminder_sent", 
                        task_id,
                        f"Count: {reminder_info['reminder_count']}"
                    )
                    
                except Exception as e:
                    logger.error(f"Error sending persistent reminder for task {task_id}: {e}")
                    
        except Exception as e:
            logger.error(f"Error in persistent reminder loop: {e}")

    async def start_persistent_reminder(self, task: Dict):
        """Start persistent reminding for a task"""
        task_id = task['id']
        user_id = task['user_id']
        
        logger.info(f"Starting persistent reminder for task {task_id} (user {user_id})")
        
        # Add to active reminders
        self.active_reminders[task_id] = {
            'user_id': user_id,
            'task': task,
            'started_at': datetime.datetime.now(),
            'last_reminded': None,
            'reminder_count': 0
        }
        
        # Initialize user reminder state
        if user_id not in self.user_reminder_state:
            self.user_reminder_state[user_id] = {}
        
        self.user_reminder_state[user_id][task_id] = {
            'active': True,
            'started_at': datetime.datetime.now()
        }
        
        # Send initial reminder immediately
        await self.send_reminder_message(task, self.active_reminders[task_id])
        
        user_logger.log_task_action(user_id, "persistent_reminder_started", task_id)

    async def stop_persistent_reminder(self, task_id: int, reason: str = "Manual stop"):
        """Stop persistent reminding for a task"""
        if task_id in self.active_reminders:
            reminder_info = self.active_reminders[task_id]
            user_id = reminder_info['user_id']
            
            logger.info(f"Stopping persistent reminder for task {task_id}: {reason}")
            
            # Remove from active reminders
            del self.active_reminders[task_id]
            
            # Update user reminder state
            if user_id in self.user_reminder_state and task_id in self.user_reminder_state[user_id]:
                self.user_reminder_state[user_id][task_id]['active'] = False
                self.user_reminder_state[user_id][task_id]['stopped_at'] = datetime.datetime.now()
                self.user_reminder_state[user_id][task_id]['stop_reason'] = reason
            
            user_logger.log_task_action(user_id, "persistent_reminder_stopped", task_id, reason)

    async def send_reminder_message(self, task: Dict, reminder_info: Dict):
        """Send a persistent reminder message to the user"""
        try:
            user = await self.bot.fetch_user(int(task['user_id']))
            if not user:
                logger.warning(f"Could not fetch user {task['user_id']} for reminder")
                return

            now = datetime.datetime.now()
            time_until = task['due_time'] - now
            minutes_until = int(time_until.total_seconds() / 60)
            
            # Create reminder embed with urgency indicators
            if minutes_until <= 5:
                color = discord.Color.red()
                urgency = "🚨 URGENT"
            elif minutes_until <= 10:
                color = discord.Color.orange()
                urgency = "⚠️ SOON"
            else:
                color = discord.Color.yellow()
                urgency = "⏰ REMINDER"
            
            embed = EmbedBuilder.create_embed(
                title=f"{urgency} - Task Starting Soon!",
                description=f"**{task['description']}** starts in {minutes_until} minutes",
                color=color,
                fields=[
                    ("📅 Scheduled Time", task['due_time'].strftime('%H:%M'), True),
                    ("⏱️ Duration", f"{task.get('duration_minutes', 15)} minutes", True),
                    ("🔔 Reminder #", str(reminder_info['reminder_count'] + 1), True)
                ]
            )
            
            if task.get('location'):
                embed.add_field(name="📍 Location", value=task['location'], inline=False)
            
            # Add action buttons
            view = ReminderActionView(task['id'], task['user_id'])
            
            embed.set_footer(text="Use the buttons below or type /start to begin the task")
            
            await user.send(embed=embed, view=view)
            
            logger.debug(f"Sent persistent reminder #{reminder_info['reminder_count'] + 1} to user {task['user_id']}")
            
        except discord.Forbidden:
            logger.warning(f"Cannot send DM to user {task['user_id']} - DMs disabled")
            await self.stop_persistent_reminder(task['id'], "DMs disabled")
        except Exception as e:
            logger.error(f"Error sending reminder message: {e}")

    async def send_overdue_reminder(self, task: Dict):
        """Send an overdue task reminder"""
        try:
            user = await self.bot.fetch_user(int(task['user_id']))
            if not user:
                return

            now = datetime.datetime.now()
            overdue_duration = now - task['due_time']
            overdue_minutes = int(overdue_duration.total_seconds() / 60)
            
            embed = EmbedBuilder.create_embed(
                title="🚨 OVERDUE TASK",
                description=f"**{task['description']}** was scheduled {overdue_minutes} minutes ago!",
                color=discord.Color.red(),
                fields=[
                    ("📅 Was Scheduled", task['due_time'].strftime('%H:%M'), True),
                    ("⏰ Overdue By", f"{overdue_minutes} minutes", True),
                    ("⏱️ Duration", f"{task.get('duration_minutes', 15)} minutes", True)
                ]
            )
            
            view = ReminderActionView(task['id'], task['user_id'], is_overdue=True)
            embed.set_footer(text="Start now or reschedule this task")
            
            await user.send(embed=embed, view=view)
            
        except Exception as e:
            logger.error(f"Error sending overdue reminder: {e}")

    @tasks.loop(minutes=5)
    async def check_escalation_reminders(self):
        """Check for tasks that need escalation notifications"""
        try:
            current_time = datetime.datetime.now()
            
            # Check for overdue collaborative tasks that need escalation
            for task_id, user_reminders in list(self.collaborative_reminders.items()):
                try:
                    # Get task details
                    first_user_id = next(iter(user_reminders.keys()))
                    task = await TaskQueries.get_task_by_id(task_id, first_user_id)
                    
                    if not task or task['status'] != 'pending':
                        # Clean up if task is no longer pending
                        del self.collaborative_reminders[task_id]
                        continue
                    
                    # Check if task is overdue
                    if current_time > task['due_time']:
                        overdue_minutes = int((current_time - task['due_time']).total_seconds() / 60)
                        
                        # Determine escalation level
                        if overdue_minutes >= 60:  # 1 hour overdue
                            escalation_level = EscalationLevel.CRITICAL
                        elif overdue_minutes >= 30:  # 30 minutes overdue
                            escalation_level = EscalationLevel.URGENT
                        else:
                            escalation_level = EscalationLevel.NORMAL
                        
                        # Send escalation notifications
                        await self.send_escalation_notifications(task, escalation_level, overdue_minutes)
                        
                except Exception as e:
                    logger.error(f"Error checking escalation for task {task_id}: {e}")
                    
        except Exception as e:
            logger.error(f"Error in escalation reminder loop: {e}")
    
    @tasks.loop(hours=1)
    async def cleanup_old_reminders(self):
        """Clean up old reminder data and history"""
        try:
            cutoff_time = datetime.datetime.now() - datetime.timedelta(days=7)
            
            # Clean up old user reminder states
            for user_id in list(self.user_reminder_state.keys()):
                user_state = self.user_reminder_state[user_id]
                
                # Remove old inactive reminders
                for task_id in list(user_state.keys()):
                    reminder_state = user_state[task_id]
                    if (not reminder_state.get('active', False) and 
                        reminder_state.get('stopped_at') and
                        datetime.datetime.fromisoformat(reminder_state['stopped_at']) < cutoff_time):
                        del user_state[task_id]
                
                # Remove empty user states
                if not user_state:
                    del self.user_reminder_state[user_id]
            
            # Clean up old collaborative reminders
            for task_id in list(self.collaborative_reminders.keys()):
                # Check if task still exists and is relevant
                try:
                    first_user_id = next(iter(self.collaborative_reminders[task_id].keys()))
                    task = await TaskQueries.get_task_by_id(task_id, first_user_id)
                    
                    if not task or task['status'] in ['completed', 'cancelled']:
                        del self.collaborative_reminders[task_id]
                        
                except Exception:
                    # If we can't check the task, remove the reminder
                    del self.collaborative_reminders[task_id]
            
            logger.info("Completed cleanup of old reminder data")
            
        except Exception as e:
            logger.error(f"Error in cleanup loop: {e}")
    
    @check_new_reminders.before_loop
    @send_persistent_reminders.before_loop
    @check_escalation_reminders.before_loop
    @cleanup_old_reminders.before_loop
    async def before_reminder_loops(self):
        await self.bot.wait_until_ready()

    async def send_escalation_notifications(self, task: Dict, escalation_level: EscalationLevel, overdue_minutes: int):
        """Send escalation notifications for overdue collaborative tasks"""
        try:
            task_id = task['id']
            
            # Get all assigned users for the task
            assigned_users = task.get('assigned_users', [])
            if not assigned_users:
                return
            
            # Determine escalation message based on level
            escalation_messages = {
                EscalationLevel.NORMAL: "⚠️ Task is overdue",
                EscalationLevel.URGENT: "🚨 Task is significantly overdue",
                EscalationLevel.CRITICAL: "🔥 Task is critically overdue"
            }
            
            escalation_colors = {
                EscalationLevel.NORMAL: discord.Color.orange(),
                EscalationLevel.URGENT: discord.Color.red(),
                EscalationLevel.CRITICAL: discord.Color.dark_red()
            }
            
            # Send notifications to all assigned users
            for user_id in assigned_users:
                try:
                    await self.send_smart_notification(
                        user_id,
                        {
                            'type': 'task_escalation',
                            'title': escalation_messages[escalation_level],
                            'message': f"Task '{task['description']}' is {overdue_minutes} minutes overdue",
                            'task_id': task_id,
                            'escalation_level': escalation_level.value,
                            'overdue_minutes': overdue_minutes
                        },
                        escalation_level
                    )
                    
                except Exception as e:
                    logger.error(f"Failed to send escalation notification to user {user_id}: {e}")
            
            # Also notify task creator if not in assigned users
            creator_id = task.get('created_by_user_id')
            if creator_id and creator_id not in assigned_users:
                try:
                    await self.send_smart_notification(
                        creator_id,
                        {
                            'type': 'task_escalation_creator',
                            'title': f"Your task is overdue ({escalation_level.value})",
                            'message': f"Task '{task['description']}' you created is {overdue_minutes} minutes overdue",
                            'task_id': task_id,
                            'escalation_level': escalation_level.value,
                            'overdue_minutes': overdue_minutes
                        },
                        escalation_level
                    )
                    
                except Exception as e:
                    logger.error(f"Failed to send escalation notification to creator {creator_id}: {e}")
            
            logger.info(f"Sent {escalation_level.value} escalation notifications for task {task_id}")
            
        except Exception as e:
            logger.error(f"Error sending escalation notifications: {e}")
    
    async def send_smart_notification(self, user_id: str, notification_data: Dict[str, Any], 
                                    escalation_level: EscalationLevel = EscalationLevel.NORMAL):
        """Send notification using smart routing based on user preferences and escalation level"""
        try:
            # Get user notification preferences
            user_prefs = await self.get_user_notification_preferences(user_id)
            
            # Determine which channels to use based on escalation level
            channels_to_use = self.determine_notification_channels(user_prefs, escalation_level)
            
            notification_sent = False
            
            # Try each channel in order of preference
            for channel in channels_to_use:
                try:
                    success = await self.send_notification_via_channel(
                        user_id, notification_data, channel
                    )
                    
                    if success:
                        notification_sent = True
                        # For normal notifications, one successful delivery is enough
                        if escalation_level == EscalationLevel.NORMAL:
                            break
                        # For urgent/critical, continue to send via multiple channels
                    
                except Exception as e:
                    logger.error(f"Failed to send notification via {channel.value}: {e}")
                    continue
            
            # Record notification in history
            self.notification_history.add_notification(user_id, {
                **notification_data,
                'channels_attempted': [c.value for c in channels_to_use],
                'delivered': notification_sent,
                'escalation_level': escalation_level.value
            })
            
            return notification_sent
            
        except Exception as e:
            logger.error(f"Error in smart notification routing: {e}")
            return False
    
    async def get_user_notification_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user's notification preferences from database"""
        try:
            query = """
                SELECT discord_dm, discord_guild, web_push, email, 
                       quiet_hours_start, quiet_hours_end, timezone
                FROM notification_preferences 
                WHERE user_id = %s
            """
            
            result = await DatabaseManager.execute_query(query, (user_id,), fetch_one=True)
            
            if result:
                return dict(result)
            else:
                # Return default preferences
                return {
                    'discord_dm': True,
                    'discord_guild': False,
                    'web_push': True,
                    'email': False,
                    'quiet_hours_start': None,
                    'quiet_hours_end': None,
                    'timezone': 'UTC'
                }
                
        except Exception as e:
            logger.error(f"Error getting user notification preferences: {e}")
            # Return safe defaults
            return {
                'discord_dm': True,
                'discord_guild': False,
                'web_push': False,
                'email': False
            }
    
    def determine_notification_channels(self, user_prefs: Dict[str, Any], 
                                     escalation_level: EscalationLevel) -> List[NotificationChannel]:
        """Determine which notification channels to use based on preferences and escalation"""
        channels = []
        
        # Check if we're in quiet hours
        in_quiet_hours = self.is_in_quiet_hours(user_prefs)
        
        # For critical escalations, override quiet hours
        if escalation_level == EscalationLevel.CRITICAL:
            in_quiet_hours = False
        
        # Discord DM (highest priority for urgent notifications)
        if user_prefs.get('discord_dm', True) and not in_quiet_hours:
            channels.append(NotificationChannel.DISCORD_DM)
        
        # Web push notifications
        if user_prefs.get('web_push', True):
            channels.append(NotificationChannel.WEB_PUSH)
        
        # Email for urgent/critical escalations
        if (user_prefs.get('email', False) and 
            escalation_level in [EscalationLevel.URGENT, EscalationLevel.CRITICAL]):
            channels.append(NotificationChannel.EMAIL)
        
        # Discord guild notifications (lowest priority)
        if user_prefs.get('discord_guild', False) and not in_quiet_hours:
            channels.append(NotificationChannel.DISCORD_GUILD)
        
        # Ensure at least one channel for critical notifications
        if not channels and escalation_level == EscalationLevel.CRITICAL:
            channels.append(NotificationChannel.DISCORD_DM)
        
        return channels
    
    def is_in_quiet_hours(self, user_prefs: Dict[str, Any]) -> bool:
        """Check if current time is within user's quiet hours"""
        try:
            quiet_start = user_prefs.get('quiet_hours_start')
            quiet_end = user_prefs.get('quiet_hours_end')
            
            if not quiet_start or not quiet_end:
                return False
            
            # For simplicity, assume UTC time
            # In production, you'd use the user's timezone
            current_time = datetime.datetime.now().time()
            
            # Handle quiet hours that span midnight
            if quiet_start <= quiet_end:
                return quiet_start <= current_time <= quiet_end
            else:
                return current_time >= quiet_start or current_time <= quiet_end
                
        except Exception as e:
            logger.error(f"Error checking quiet hours: {e}")
            return False
    
    async def send_notification_via_channel(self, user_id: str, notification_data: Dict[str, Any], 
                                          channel: NotificationChannel) -> bool:
        """Send notification via specific channel"""
        try:
            if channel == NotificationChannel.DISCORD_DM:
                return await self.send_discord_dm_notification(user_id, notification_data)
            
            elif channel == NotificationChannel.WEB_PUSH:
                return await self.send_web_push_notification(user_id, notification_data)
            
            elif channel == NotificationChannel.EMAIL:
                return await self.send_email_notification(user_id, notification_data)
            
            elif channel == NotificationChannel.DISCORD_GUILD:
                return await self.send_discord_guild_notification(user_id, notification_data)
            
            return False
            
        except Exception as e:
            logger.error(f"Error sending notification via {channel.value}: {e}")
            return False
    
    async def send_discord_dm_notification(self, user_id: str, notification_data: Dict[str, Any]) -> bool:
        """Send notification via Discord DM"""
        try:
            user = await self.bot.fetch_user(int(user_id))
            if not user:
                return False
            
            # Create embed based on notification type
            embed = self.create_notification_embed(notification_data)
            await user.send(embed=embed)
            
            return True
            
        except discord.Forbidden:
            logger.warning(f"Cannot send DM to user {user_id} - DMs disabled")
            return False
        except Exception as e:
            logger.error(f"Error sending Discord DM notification: {e}")
            return False
    
    async def send_web_push_notification(self, user_id: str, notification_data: Dict[str, Any]) -> bool:
        """Send notification via web push (through bridge)"""
        try:
            # Send through Discord-Web bridge
            await sync_notification_to_discord(notification_data, user_id)
            return True
            
        except Exception as e:
            logger.error(f"Error sending web push notification: {e}")
            return False
    
    async def send_email_notification(self, user_id: str, notification_data: Dict[str, Any]) -> bool:
        """Send notification via email"""
        try:
            # Get notification service and send email
            notification_service = await get_notification_service()
            success = await notification_service.send_email_notification(user_id, notification_data)
            return success
            
        except Exception as e:
            logger.error(f"Error sending email notification: {e}")
            return False
    
    async def send_discord_guild_notification(self, user_id: str, notification_data: Dict[str, Any]) -> bool:
        """Send notification in Discord guild channel"""
        try:
            # This would require guild-specific configuration
            # For now, just log that it would be sent
            logger.info(f"Would send guild notification for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending Discord guild notification: {e}")
            return False
    
    def create_notification_embed(self, notification_data: Dict[str, Any]) -> discord.Embed:
        """Create Discord embed for notification"""
        notification_type = notification_data.get('type', 'general')
        title = notification_data.get('title', 'Notification')
        message = notification_data.get('message', '')
        
        # Color based on escalation level
        escalation_level = notification_data.get('escalation_level', 'normal')
        color_map = {
            'normal': discord.Color.blue(),
            'urgent': discord.Color.orange(),
            'critical': discord.Color.red()
        }
        
        embed = discord.Embed(
            title=title,
            description=message,
            color=color_map.get(escalation_level, discord.Color.blue()),
            timestamp=datetime.datetime.now()
        )
        
        # Add task-specific fields
        if 'task_id' in notification_data:
            embed.add_field(name="Task ID", value=str(notification_data['task_id']), inline=True)
        
        if 'overdue_minutes' in notification_data:
            embed.add_field(
                name="Overdue By", 
                value=f"{notification_data['overdue_minutes']} minutes", 
                inline=True
            )
        
        return embed
    
    @app_commands.command(name="reminder_status", description="Check your active reminders")
    async def reminder_status(self, interaction: discord.Interaction):
        """Show user their active reminders"""
        user_id = str(interaction.user.id)
        
        # Get user's active reminders
        user_reminders = [
            (task_id, info) for task_id, info in self.active_reminders.items()
            if info['user_id'] == user_id
        ]
        
        if not user_reminders:
            embed = EmbedBuilder.info_embed(
                "No Active Reminders",
                "You don't have any active task reminders right now."
            )
        else:
            embed = EmbedBuilder.create_embed(
                title="🔔 Your Active Reminders",
                description=f"You have {len(user_reminders)} active reminder(s)",
                color=EmbedBuilder.WARNING
            )
            
            for task_id, reminder_info in user_reminders:
                task = reminder_info['task']
                time_until = task['due_time'] - datetime.datetime.now()
                minutes_until = int(time_until.total_seconds() / 60)
                
                embed.add_field(
                    name=f"📋 {task['description']}",
                    value=f"Starts in {minutes_until} minutes\nReminders sent: {reminder_info['reminder_count']}",
                    inline=False
                )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="notification_history", description="View your notification delivery history")
    async def notification_history_command(self, interaction: discord.Interaction):
        """Show user their notification history and delivery stats"""
        user_id = str(interaction.user.id)
        
        # Get delivery stats
        stats = self.notification_history.get_delivery_stats(user_id)
        
        # Get recent history
        history = self.notification_history.get_user_history(user_id, limit=10)
        
        embed = EmbedBuilder.create_embed(
            title="📊 Notification History",
            description=f"Delivery statistics and recent notifications",
            color=EmbedBuilder.INFO
        )
        
        # Add stats
        embed.add_field(
            name="📈 Delivery Stats",
            value=f"Total: {stats['total']}\nSuccess: {stats['success']}\nFailed: {stats['failed']}\nSuccess Rate: {stats['success_rate']}%",
            inline=True
        )
        
        # Add recent notifications
        if history:
            recent_notifications = []
            for notification in history[-5:]:  # Last 5 notifications
                status = "✅" if notification.get('delivered', False) else "❌"
                timestamp = notification.get('timestamp', '')[:16]  # YYYY-MM-DD HH:MM
                title = notification.get('title', 'Unknown')[:30]
                recent_notifications.append(f"{status} {timestamp} - {title}")
            
            embed.add_field(
                name="📋 Recent Notifications",
                value="\n".join(recent_notifications) or "No recent notifications",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class ReminderActionView(discord.ui.View):
    """Action buttons for reminder messages"""
    
    def __init__(self, task_id: int, user_id: str, is_overdue: bool = False):
        super().__init__(timeout=300)  # 5 minute timeout
        self.task_id = task_id
        self.user_id = user_id
        self.is_overdue = is_overdue

    @discord.ui.button(label="▶️ Start Now", style=discord.ButtonStyle.success)
    async def start_task(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Start the task immediately"""
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ This is not your reminder.", ephemeral=True)
            return
        
        try:
            # Start the task
            now = datetime.datetime.now()
            success = await TaskQueries.update_task(
                self.task_id, self.user_id,
                start_time=now,
                status='in_progress',
                num_sessions=1
            )
            
            if success:
                # Stop the persistent reminder
                cog = interaction.client.get_cog("PersistentReminderManager")
                if cog:
                    await cog.stop_persistent_reminder(self.task_id, "Started via reminder button")
                
                embed = EmbedBuilder.success_embed(
                    "Task Started!",
                    f"You're now working on this task. Use `/finish` when complete."
                )
                
                # Disable all buttons
                for item in self.children:
                    item.disabled = True
                
                await interaction.response.edit_message(embed=embed, view=self)
                
                user_logger.log_task_action(self.user_id, "started_via_reminder", self.task_id)
            else:
                await interaction.response.send_message("❌ Failed to start task. Please try `/start` command.", ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error starting task via reminder: {e}")
            await ErrorHandler.handle_error(interaction, e, "Failed to start task from reminder.")

    @discord.ui.button(label="⏸️ Snooze 5min", style=discord.ButtonStyle.secondary)
    async def snooze_reminder(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Snooze the reminder for 5 minutes"""
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ This is not your reminder.", ephemeral=True)
            return
        
        try:
            # Update task due time
            new_due_time = datetime.datetime.now() + datetime.timedelta(minutes=5)
            success = await TaskQueries.update_task(
                self.task_id, self.user_id,
                due_time=new_due_time
            )
            
            if success:
                embed = EmbedBuilder.warning_embed(
                    "Reminder Snoozed",
                    f"Task rescheduled to {new_due_time.strftime('%H:%M')}. Reminders will resume closer to the new time."
                )
                
                # Disable buttons
                for item in self.children:
                    item.disabled = True
                
                await interaction.response.edit_message(embed=embed, view=self)
                
                user_logger.log_task_action(self.user_id, "snoozed_reminder", self.task_id, "5 minutes")
            else:
                await interaction.response.send_message("❌ Failed to snooze reminder.", ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error snoozing reminder: {e}")
            await ErrorHandler.handle_error(interaction, e, "Failed to snooze reminder.")

    @discord.ui.button(label="🔕 Stop Reminders", style=discord.ButtonStyle.danger)
    async def stop_reminders(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Stop all reminders for this task"""
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ This is not your reminder.", ephemeral=True)
            return
        
        try:
            # Stop the persistent reminder
            cog = interaction.client.get_cog("PersistentReminderManager")
            if cog:
                await cog.stop_persistent_reminder(self.task_id, "Stopped by user request")
            
            embed = EmbedBuilder.warning_embed(
                "Reminders Stopped",
                "No more reminders will be sent for this task. You can still start it manually with `/start`."
            )
            
            # Disable all buttons
            for item in self.children:
                item.disabled = True
            
            await interaction.response.edit_message(embed=embed, view=self)
            
            user_logger.log_task_action(self.user_id, "stopped_reminders", self.task_id)
            
        except Exception as e:
            logger.error(f"Error stopping reminders: {e}")
            await ErrorHandler.handle_error(interaction, e, "Failed to stop reminders.")

async def setup(bot):
    await bot.add_cog(PersistentReminderManager(bot))
    logger.info("PersistentReminderManager cog loaded")