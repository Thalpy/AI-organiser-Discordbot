# Time Utilities for Discord Task Management Bot
# Timezone handling, date/time parsing, and scheduling helpers

import datetime
import pytz
from typing import Optional, List, Tuple, Dict
from dateutil import parser
import logging

logger = logging.getLogger(__name__)

class TimeZoneManager:
    """Handle timezone operations and conversions"""
    
    # Common timezones for easy selection
    COMMON_TIMEZONES = [
        'UTC', 'GMT',
        'US/Eastern', 'US/Central', 'US/Mountain', 'US/Pacific',
        'Europe/London', 'Europe/Paris', 'Europe/Berlin', 'Europe/Rome',
        'Asia/Tokyo', 'Asia/Shanghai', 'Asia/Kolkata', 'Asia/Dubai',
        'Australia/Sydney', 'Australia/Melbourne'
    ]
    
    @staticmethod
    def get_user_timezone(timezone_str: str) -> pytz.BaseTzInfo:
        """Get timezone object from string, with fallback to UTC"""
        try:
            return pytz.timezone(timezone_str)
        except pytz.exceptions.UnknownTimeZoneError:
            logger.warning(f"Unknown timezone: {timezone_str}, falling back to UTC")
            return pytz.UTC
    
    @staticmethod
    def convert_to_user_timezone(dt: datetime.datetime, user_timezone: str) -> datetime.datetime:
        """Convert datetime to user's timezone"""
        if dt.tzinfo is None:
            # Assume UTC if no timezone info
            dt = pytz.UTC.localize(dt)
        
        user_tz = TimeZoneManager.get_user_timezone(user_timezone)
        return dt.astimezone(user_tz)
    
    @staticmethod
    def convert_to_utc(dt: datetime.datetime, user_timezone: str) -> datetime.datetime:
        """Convert user's local time to UTC"""
        if dt.tzinfo is None:
            user_tz = TimeZoneManager.get_user_timezone(user_timezone)
            dt = user_tz.localize(dt)
        
        return dt.astimezone(pytz.UTC)
    
    @staticmethod
    def get_current_time_in_timezone(timezone_str: str) -> datetime.datetime:
        """Get current time in specified timezone"""
        user_tz = TimeZoneManager.get_user_timezone(timezone_str)
        return datetime.datetime.now(user_tz)

class DateTimeParser:
    """Parse various date/time formats from user input"""
    
    @staticmethod
    def parse_time(time_str: str) -> Optional[datetime.time]:
        """Parse time string in HH:MM format"""
        try:
            return datetime.datetime.strptime(time_str.strip(), '%H:%M').time()
        except ValueError:
            try:
                # Try with AM/PM
                return datetime.datetime.strptime(time_str.strip(), '%I:%M %p').time()
            except ValueError:
                return None
    
    @staticmethod
    def parse_date(date_str: str) -> Optional[datetime.date]:
        """Parse date string in various formats"""
        formats = ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%m-%d-%Y', '%d-%m-%Y']
        
        for fmt in formats:
            try:
                return datetime.datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue
        
        # Try using dateutil parser as fallback
        try:
            return parser.parse(date_str.strip()).date()
        except:
            return None
    
    @staticmethod
    def parse_datetime(datetime_str: str, user_timezone: str = 'UTC') -> Optional[datetime.datetime]:
        """Parse datetime string with timezone awareness"""
        try:
            # Try standard format first
            dt = datetime.datetime.strptime(datetime_str.strip(), '%Y-%m-%d %H:%M')
            user_tz = TimeZoneManager.get_user_timezone(user_timezone)
            return user_tz.localize(dt)
        except ValueError:
            pass
        
        # Try MM/DD HH:MM format (common in task creation)
        try:
            current_year = datetime.datetime.now().year
            dt = datetime.datetime.strptime(f"{current_year}/{datetime_str.strip()}", '%Y/%m/%d %H:%M')
            user_tz = TimeZoneManager.get_user_timezone(user_timezone)
            return user_tz.localize(dt)
        except ValueError:
            pass
        
        # Try dateutil parser as fallback
        try:
            dt = parser.parse(datetime_str.strip())
            if dt.tzinfo is None:
                user_tz = TimeZoneManager.get_user_timezone(user_timezone)
                dt = user_tz.localize(dt)
            return dt
        except:
            return None
    
    @staticmethod
    def parse_schedule_input(input_str: str, user_timezone: str = 'UTC') -> Optional[datetime.datetime]:
        """Parse flexible schedule input (MM/DD HH:MM, today HH:MM, tomorrow HH:MM, etc.)"""
        input_str = input_str.strip().lower()
        
        if not input_str:
            return None
        
        now = TimeZoneManager.get_current_time_in_timezone(user_timezone)
        
        # Handle relative dates
        if input_str.startswith('today '):
            time_part = input_str[6:]
            time_obj = DateTimeParser.parse_time(time_part)
            if time_obj:
                return now.replace(hour=time_obj.hour, minute=time_obj.minute, second=0, microsecond=0)
        
        elif input_str.startswith('tomorrow '):
            time_part = input_str[9:]
            time_obj = DateTimeParser.parse_time(time_part)
            if time_obj:
                tomorrow = now + datetime.timedelta(days=1)
                return tomorrow.replace(hour=time_obj.hour, minute=time_obj.minute, second=0, microsecond=0)
        
        # Handle MM/DD HH:MM format
        elif '/' in input_str and ':' in input_str:
            try:
                current_year = now.year
                dt = datetime.datetime.strptime(f"{current_year}/{input_str}", '%Y/%m/%d %H:%M')
                user_tz = TimeZoneManager.get_user_timezone(user_timezone)
                return user_tz.localize(dt)
            except ValueError:
                pass
        
        # Fallback to general datetime parsing
        return DateTimeParser.parse_datetime(input_str, user_timezone)

class ScheduleCalculator:
    """Calculate scheduling conflicts and optimal times"""
    
    @staticmethod
    def find_schedule_conflicts(new_start: datetime.datetime, new_duration: int, 
                              existing_tasks: List[Dict]) -> List[Dict]:
        """Find tasks that conflict with a new scheduled task"""
        new_end = new_start + datetime.timedelta(minutes=new_duration)
        conflicts = []
        
        for task in existing_tasks:
            if not task.get('due_time') or not task.get('duration_minutes'):
                continue
            
            task_start = task['due_time']
            task_end = task_start + datetime.timedelta(minutes=task['duration_minutes'])
            
            # Check for overlap
            if (new_start < task_end and new_end > task_start):
                conflicts.append(task)
        
        return conflicts
    
    @staticmethod
    def find_available_slots(date: datetime.date, duration_minutes: int, 
                           work_start: datetime.time, work_end: datetime.time,
                           existing_tasks: List[Dict], user_timezone: str = 'UTC') -> List[datetime.datetime]:
        """Find available time slots for a task on a given date"""
        user_tz = TimeZoneManager.get_user_timezone(user_timezone)
        
        # Create datetime objects for work hours
        work_start_dt = user_tz.localize(datetime.datetime.combine(date, work_start))
        work_end_dt = user_tz.localize(datetime.datetime.combine(date, work_end))
        
        # Get existing tasks for the day
        day_tasks = []
        for task in existing_tasks:
            if (task.get('due_time') and 
                task['due_time'].date() == date and 
                task.get('duration_minutes')):
                day_tasks.append(task)
        
        # Sort tasks by start time
        day_tasks.sort(key=lambda x: x['due_time'])
        
        available_slots = []
        current_time = work_start_dt
        
        for task in day_tasks:
            task_start = task['due_time']
            
            # Check if there's a gap before this task
            if current_time + datetime.timedelta(minutes=duration_minutes) <= task_start:
                available_slots.append(current_time)
            
            # Move current time to after this task
            task_end = task_start + datetime.timedelta(minutes=task['duration_minutes'])
            current_time = max(current_time, task_end)
        
        # Check if there's time after the last task
        if current_time + datetime.timedelta(minutes=duration_minutes) <= work_end_dt:
            available_slots.append(current_time)
        
        return available_slots
    
    @staticmethod
    def calculate_optimal_schedule(tasks: List[Dict], work_start: datetime.time, 
                                 work_end: datetime.time, lunch_start: datetime.time,
                                 lunch_duration: int, user_timezone: str = 'UTC') -> List[Dict]:
        """Calculate optimal schedule for a list of tasks"""
        # This is a simplified scheduling algorithm
        # In a real implementation, you might want to use more sophisticated algorithms
        
        scheduled_tasks = []
        current_date = datetime.date.today()
        user_tz = TimeZoneManager.get_user_timezone(user_timezone)
        
        # Sort tasks by priority and deadline
        sorted_tasks = sorted(tasks, key=lambda x: (
            not x.get('priority', False),  # Priority tasks first
            x.get('deadline') or datetime.datetime.max.replace(tzinfo=user_tz),  # Then by deadline
            x.get('id', 0)  # Finally by ID for consistency
        ))
        
        current_time = user_tz.localize(datetime.datetime.combine(current_date, work_start))
        work_end_dt = user_tz.localize(datetime.datetime.combine(current_date, work_end))
        lunch_start_dt = user_tz.localize(datetime.datetime.combine(current_date, lunch_start))
        lunch_end_dt = lunch_start_dt + datetime.timedelta(minutes=lunch_duration)
        
        for task in sorted_tasks:
            duration = task.get('duration_minutes', 15)
            task_end = current_time + datetime.timedelta(minutes=duration)
            
            # Check if task fits before lunch
            if task_end <= lunch_start_dt:
                scheduled_task = task.copy()
                scheduled_task['scheduled_time'] = current_time
                scheduled_tasks.append(scheduled_task)
                current_time = task_end
            
            # Check if we need to skip lunch
            elif current_time < lunch_start_dt < task_end:
                current_time = lunch_end_dt
                task_end = current_time + datetime.timedelta(minutes=duration)
                
                if task_end <= work_end_dt:
                    scheduled_task = task.copy()
                    scheduled_task['scheduled_time'] = current_time
                    scheduled_tasks.append(scheduled_task)
                    current_time = task_end
                else:
                    # Move to next day
                    current_date += datetime.timedelta(days=1)
                    current_time = user_tz.localize(datetime.datetime.combine(current_date, work_start))
                    work_end_dt = user_tz.localize(datetime.datetime.combine(current_date, work_end))
                    lunch_start_dt = user_tz.localize(datetime.datetime.combine(current_date, lunch_start))
                    lunch_end_dt = lunch_start_dt + datetime.timedelta(minutes=lunch_duration)
                    
                    scheduled_task = task.copy()
                    scheduled_task['scheduled_time'] = current_time
                    scheduled_tasks.append(scheduled_task)
                    current_time += datetime.timedelta(minutes=duration)
            
            # Task fits after current time
            elif task_end <= work_end_dt:
                scheduled_task = task.copy()
                scheduled_task['scheduled_time'] = current_time
                scheduled_tasks.append(scheduled_task)
                current_time = task_end
            
            else:
                # Move to next day
                current_date += datetime.timedelta(days=1)
                current_time = user_tz.localize(datetime.datetime.combine(current_date, work_start))
                work_end_dt = user_tz.localize(datetime.datetime.combine(current_date, work_end))
                lunch_start_dt = user_tz.localize(datetime.datetime.combine(current_date, lunch_start))
                lunch_end_dt = lunch_start_dt + datetime.timedelta(minutes=lunch_duration)
                
                scheduled_task = task.copy()
                scheduled_task['scheduled_time'] = current_time
                scheduled_tasks.append(scheduled_task)
                current_time += datetime.timedelta(minutes=duration)
        
        return scheduled_tasks

class DurationCalculator:
    """Calculate and format durations"""
    
    @staticmethod
    def parse_duration_input(duration_str: str) -> Optional[int]:
        """Parse duration input in various formats (15, 1h, 30m, 1h30m)"""
        duration_str = duration_str.strip().lower()
        
        if not duration_str:
            return None
        
        # Just a number (assume minutes)
        if duration_str.isdigit():
            return int(duration_str)
        
        # Parse formats like 1h, 30m, 1h30m
        total_minutes = 0
        
        # Extract hours
        if 'h' in duration_str:
            try:
                hours_part = duration_str.split('h')[0]
                total_minutes += int(hours_part) * 60
                duration_str = duration_str.split('h', 1)[1]
            except (ValueError, IndexError):
                return None
        
        # Extract minutes
        if 'm' in duration_str:
            try:
                minutes_part = duration_str.split('m')[0]
                if minutes_part:  # Could be empty if format was just "1h"
                    total_minutes += int(minutes_part)
            except (ValueError, IndexError):
                return None
        elif duration_str and not 'h' in duration_str:
            # No 'h' or 'm', treat as minutes
            try:
                total_minutes = int(duration_str)
            except ValueError:
                return None
        
        return total_minutes if total_minutes > 0 else None
    
    @staticmethod
    def format_duration(minutes: int) -> str:
        """Format duration in human-readable format"""
        if minutes < 60:
            return f"{minutes}m"
        elif minutes % 60 == 0:
            return f"{minutes // 60}h"
        else:
            hours = minutes // 60
            mins = minutes % 60
            return f"{hours}h{mins}m"
    
    @staticmethod
    def calculate_work_time_between(start: datetime.datetime, end: datetime.datetime,
                                  work_start: datetime.time, work_end: datetime.time,
                                  exclude_weekends: bool = True) -> int:
        """Calculate work time in minutes between two datetimes"""
        if start >= end:
            return 0
        
        total_minutes = 0
        current_date = start.date()
        end_date = end.date()
        
        while current_date <= end_date:
            # Skip weekends if requested
            if exclude_weekends and current_date.weekday() >= 5:
                current_date += datetime.timedelta(days=1)
                continue
            
            # Calculate work hours for this day
            day_start = max(start, datetime.datetime.combine(current_date, work_start))
            day_end = min(end, datetime.datetime.combine(current_date, work_end))
            
            if day_start < day_end:
                day_minutes = int((day_end - day_start).total_seconds() / 60)
                total_minutes += day_minutes
            
            current_date += datetime.timedelta(days=1)
        
        return total_minutes