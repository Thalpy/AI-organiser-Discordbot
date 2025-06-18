# Notification Utilities for Discord Task Management Bot
# Helper functions for notification system

import datetime
import pytz
from typing import Optional, Dict
import psycopg2
from psycopg2.extras import RealDictCursor
from config import DB_CONFIG

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

class NotificationUtils:
    @staticmethod
    def is_quiet_hours(user_id: str) -> bool:
        """Check if current time is within user's quiet hours"""
        try:
            with get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT quiet_hours_start, quiet_hours_end, time_zone
                        FROM notification_preferences np
                        LEFT JOIN user_preferences up ON np.user_id = up.user_id
                        WHERE np.user_id = %s
                    """, (user_id,))
                    prefs = cur.fetchone()
            
            if not prefs or not prefs['quiet_hours_start'] or not prefs['quiet_hours_end']:
                return False
            
            # Get user's timezone
            user_tz = pytz.timezone(prefs.get('time_zone', 'UTC'))
            now = datetime.datetime.now(user_tz).time()
            
            start_time = prefs['quiet_hours_start']
            end_time = prefs['quiet_hours_end']
            
            # Handle overnight quiet hours (e.g., 22:00 to 08:00)
            if start_time > end_time:
                return now >= start_time or now <= end_time
            else:
                return start_time <= now <= end_time
                
        except Exception as e:
            print(f"Error checking quiet hours for user {user_id}: {e}")
            return False

    @staticmethod
    def get_user_notification_prefs(user_id: str) -> Dict:
        """Get user's notification preferences with defaults"""
        try:
            with get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT * FROM notification_preferences WHERE user_id = %s
                    """, (user_id,))
                    prefs = cur.fetchone()
            
            if prefs:
                return dict(prefs)
            else:
                # Return defaults
                return {
                    'task_reminders': True,
                    'overdue_alerts': True,
                    'daily_summaries': True,
                    'reminder_minutes': 15,
                    'quiet_hours_start': None,
                    'quiet_hours_end': None
                }
                
        except Exception as e:
            print(f"Error getting notification preferences for user {user_id}: {e}")
            return {
                'task_reminders': True,
                'overdue_alerts': True,
                'daily_summaries': True,
                'reminder_minutes': 15,
                'quiet_hours_start': None,
                'quiet_hours_end': None
            }

    @staticmethod
    def log_notification(user_id: str, notification_type: str, task_id: Optional[int] = None, 
                        delivery_status: str = 'sent', error_message: Optional[str] = None):
        """Log notification delivery for debugging and analytics"""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO notification_log (user_id, notification_type, task_id, delivery_status, error_message)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (user_id, notification_type, task_id, delivery_status, error_message))
                    conn.commit()
        except Exception as e:
            print(f"Error logging notification: {e}")

    @staticmethod
    def should_send_notification(user_id: str, notification_type: str) -> bool:
        """Check if we should send a notification based on user preferences and quiet hours"""
        # Check quiet hours
        if NotificationUtils.is_quiet_hours(user_id):
            return False
        
        # Check user preferences
        prefs = NotificationUtils.get_user_notification_prefs(user_id)
        
        if notification_type == 'task_reminder':
            return prefs.get('task_reminders', True)
        elif notification_type == 'overdue_alert':
            return prefs.get('overdue_alerts', True)
        elif notification_type == 'daily_summary':
            return prefs.get('daily_summaries', True)
        
        return True

    @staticmethod
    def get_reminder_time_offset(user_id: str) -> int:
        """Get user's preferred reminder time in minutes"""
        prefs = NotificationUtils.get_user_notification_prefs(user_id)
        return prefs.get('reminder_minutes', 15)

    @staticmethod
    def format_task_time(task_time: datetime.datetime, user_id: str) -> str:
        """Format task time according to user's timezone"""
        try:
            with get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT time_zone FROM user_preferences WHERE user_id = %s
                    """, (user_id,))
                    result = cur.fetchone()
            
            if result and result['time_zone']:
                user_tz = pytz.timezone(result['time_zone'])
                if task_time.tzinfo is None:
                    task_time = pytz.UTC.localize(task_time)
                local_time = task_time.astimezone(user_tz)
                return local_time.strftime('%H:%M')
            else:
                return task_time.strftime('%H:%M')
                
        except Exception as e:
            print(f"Error formatting time for user {user_id}: {e}")
            return task_time.strftime('%H:%M')

    @staticmethod
    def create_notification_embed(title: str, description: str, color: int, 
                                 fields: Optional[list] = None, footer: Optional[str] = None) -> dict:
        """Create a standardized notification embed"""
        embed_data = {
            'title': title,
            'description': description,
            'color': color,
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        if fields:
            embed_data['fields'] = fields
            
        if footer:
            embed_data['footer'] = {'text': footer}
            
        return embed_data