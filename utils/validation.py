# Validation Utilities for Discord Task Management Bot
# Input validation and sanitization helpers

import re
import datetime
from typing import Optional, List, Dict, Any, Tuple
from utils.time_helpers import DateTimeParser, DurationCalculator

class InputValidator:
    """Comprehensive input validation for user data"""
    
    @staticmethod
    def validate_task_description(description: str) -> Tuple[bool, str]:
        """Validate task description"""
        if not description or not description.strip():
            return False, "Task description cannot be empty"
        
        description = description.strip()
        
        if len(description) < 3:
            return False, "Task description must be at least 3 characters long"
        
        if len(description) > 200:
            return False, "Task description must be less than 200 characters"
        
        # Check for potentially harmful content
        if any(char in description for char in ['<', '>', '@everyone', '@here']):
            return False, "Task description contains invalid characters"
        
        return True, description
    
    @staticmethod
    def validate_time_input(time_str: str) -> Tuple[bool, Optional[datetime.time], str]:
        """Validate time input and return parsed time"""
        if not time_str or not time_str.strip():
            return True, None, ""  # Optional field
        
        time_obj = DateTimeParser.parse_time(time_str.strip())
        if time_obj is None:
            return False, None, "Invalid time format. Use HH:MM (24-hour) or HH:MM AM/PM"
        
        return True, time_obj, ""
    
    @staticmethod
    def validate_date_input(date_str: str) -> Tuple[bool, Optional[datetime.date], str]:
        """Validate date input and return parsed date"""
        if not date_str or not date_str.strip():
            return True, None, ""  # Optional field
        
        date_obj = DateTimeParser.parse_date(date_str.strip())
        if date_obj is None:
            return False, None, "Invalid date format. Use YYYY-MM-DD, MM/DD/YYYY, or DD/MM/YYYY"
        
        # Check if date is not too far in the past
        if date_obj < datetime.date.today() - datetime.timedelta(days=1):
            return False, None, "Date cannot be in the past"
        
        # Check if date is not too far in the future (1 year)
        if date_obj > datetime.date.today() + datetime.timedelta(days=365):
            return False, None, "Date cannot be more than 1 year in the future"
        
        return True, date_obj, ""
    
    @staticmethod
    def validate_duration_input(duration_str: str) -> Tuple[bool, Optional[int], str]:
        """Validate duration input and return minutes"""
        if not duration_str or not duration_str.strip():
            return True, 15, ""  # Default 15 minutes
        
        duration_minutes = DurationCalculator.parse_duration_input(duration_str.strip())
        if duration_minutes is None:
            return False, None, "Invalid duration format. Use minutes (15) or time format (1h30m)"
        
        if duration_minutes < 1:
            return False, None, "Duration must be at least 1 minute"
        
        if duration_minutes > 1440:  # 24 hours
            return False, None, "Duration cannot exceed 24 hours"
        
        return True, duration_minutes, ""
    
    @staticmethod
    def validate_location_input(location_str: str) -> Tuple[bool, str, str]:
        """Validate location/URL input"""
        if not location_str or not location_str.strip():
            return True, "", ""  # Optional field
        
        location = location_str.strip()
        
        if len(location) > 100:
            return False, "", "Location must be less than 100 characters"
        
        # Basic URL validation if it looks like a URL
        if location.startswith(('http://', 'https://', 'ftp://')):
            url_pattern = re.compile(
                r'^https?://'  # http:// or https://
                r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
                r'localhost|'  # localhost...
                r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
                r'(?::\d+)?'  # optional port
                r'(?:/?|[/?]\S+)$', re.IGNORECASE)
            
            if not url_pattern.match(location):
                return False, "", "Invalid URL format"
        
        return True, location, ""
    
    @staticmethod
    def validate_timezone(timezone_str: str) -> Tuple[bool, str, str]:
        """Validate timezone string"""
        if not timezone_str or not timezone_str.strip():
            return True, "UTC", ""  # Default to UTC
        
        timezone = timezone_str.strip()
        
        # List of valid timezones (subset for validation)
        valid_timezones = [
            'UTC', 'GMT',
            'US/Eastern', 'US/Central', 'US/Mountain', 'US/Pacific',
            'America/New_York', 'America/Chicago', 'America/Denver', 'America/Los_Angeles',
            'Europe/London', 'Europe/Paris', 'Europe/Berlin', 'Europe/Rome', 'Europe/Madrid',
            'Asia/Tokyo', 'Asia/Shanghai', 'Asia/Kolkata', 'Asia/Dubai', 'Asia/Seoul',
            'Australia/Sydney', 'Australia/Melbourne', 'Australia/Perth'
        ]
        
        if timezone not in valid_timezones:
            return False, "", f"Invalid timezone. Valid options: {', '.join(valid_timezones[:10])}..."
        
        return True, timezone, ""

class TaskValidator:
    """Specialized validation for task-related operations"""
    
    @staticmethod
    def validate_task_creation_data(data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any], List[str]]:
        """Validate all data for task creation"""
        errors = []
        validated_data = {}
        
        # Validate description (required)
        if 'description' not in data:
            errors.append("Task description is required")
        else:
            valid, desc, error = InputValidator.validate_task_description(data['description'])
            if valid:
                validated_data['description'] = desc
            else:
                errors.append(error)
        
        # Validate duration
        if 'duration' in data:
            valid, duration, error = InputValidator.validate_duration_input(data['duration'])
            if valid:
                validated_data['duration_minutes'] = duration
            elif error:
                errors.append(error)
        
        # Validate location
        if 'location' in data:
            valid, location, error = InputValidator.validate_location_input(data['location'])
            if valid:
                validated_data['location'] = location
            elif error:
                errors.append(error)
        
        # Validate schedule date and time
        if 'schedule_date' in data and 'schedule_time' in data:
            date_valid, date_obj, date_error = InputValidator.validate_date_input(data['schedule_date'])
            time_valid, time_obj, time_error = InputValidator.validate_time_input(data['schedule_time'])
            
            if not date_valid:
                errors.append(date_error)
            if not time_valid:
                errors.append(time_error)
            
            if date_valid and time_valid and date_obj and time_obj:
                validated_data['schedule_date'] = date_obj
                validated_data['schedule_time'] = time_obj
                
                # Create due_time for easier querying
                due_datetime = datetime.datetime.combine(date_obj, time_obj)
                validated_data['due_time'] = due_datetime
        
        # Validate deadline
        if 'deadline' in data and data['deadline']:
            try:
                deadline = datetime.datetime.strptime(data['deadline'], '%Y-%m-%d %H:%M')
                if deadline < datetime.datetime.now():
                    errors.append("Deadline cannot be in the past")
                else:
                    validated_data['deadline'] = deadline
            except ValueError:
                errors.append("Invalid deadline format. Use YYYY-MM-DD HH:MM")
        
        # Validate priority (boolean)
        if 'priority' in data:
            if isinstance(data['priority'], bool):
                validated_data['priority'] = data['priority']
            else:
                validated_data['priority'] = str(data['priority']).lower() in ['true', '1', 'yes', 'high']
        
        return len(errors) == 0, validated_data, errors
    
    @staticmethod
    def validate_task_update_data(data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any], List[str]]:
        """Validate data for task updates (similar to creation but all fields optional)"""
        errors = []
        validated_data = {}
        
        # Only validate fields that are present
        for field, value in data.items():
            if field == 'description' and value:
                valid, desc, error = InputValidator.validate_task_description(value)
                if valid:
                    validated_data['description'] = desc
                elif error:
                    errors.append(error)
            
            elif field == 'duration' and value:
                valid, duration, error = InputValidator.validate_duration_input(value)
                if valid:
                    validated_data['duration_minutes'] = duration
                elif error:
                    errors.append(error)
            
            elif field == 'location':
                valid, location, error = InputValidator.validate_location_input(value)
                if valid:
                    validated_data['location'] = location
                elif error:
                    errors.append(error)
            
            elif field == 'status' and value:
                if value in ['pending', 'in_progress', 'done', 'delayed']:
                    validated_data['status'] = value
                else:
                    errors.append("Invalid status. Must be: pending, in_progress, done, or delayed")
        
        return len(errors) == 0, validated_data, errors

class UserPreferencesValidator:
    """Validation for user preferences"""
    
    @staticmethod
    def validate_work_hours(start_time: str, end_time: str) -> Tuple[bool, str]:
        """Validate work hours make sense"""
        start_valid, start_obj, start_error = InputValidator.validate_time_input(start_time)
        end_valid, end_obj, end_error = InputValidator.validate_time_input(end_time)
        
        if not start_valid:
            return False, start_error
        if not end_valid:
            return False, end_error
        
        if start_obj and end_obj:
            # Convert to minutes for comparison
            start_minutes = start_obj.hour * 60 + start_obj.minute
            end_minutes = end_obj.hour * 60 + end_obj.minute
            
            if start_minutes >= end_minutes:
                return False, "Work end time must be after work start time"
            
            # Check for reasonable work hours (4-16 hours)
            work_duration = end_minutes - start_minutes
            if work_duration < 240:  # 4 hours
                return False, "Work day must be at least 4 hours"
            if work_duration > 960:  # 16 hours
                return False, "Work day cannot exceed 16 hours"
        
        return True, ""
    
    @staticmethod
    def validate_lunch_preferences(duration: str, start: str, end: str) -> Tuple[bool, str]:
        """Validate lunch preferences"""
        # Validate duration
        try:
            duration_minutes = int(duration)
            if duration_minutes < 10 or duration_minutes > 180:
                return False, "Lunch duration must be between 10 and 180 minutes"
        except ValueError:
            return False, "Invalid lunch duration format"
        
        # Validate lunch window
        start_valid, start_obj, start_error = InputValidator.validate_time_input(start)
        end_valid, end_obj, end_error = InputValidator.validate_time_input(end)
        
        if not start_valid:
            return False, start_error
        if not end_valid:
            return False, end_error
        
        if start_obj and end_obj:
            start_minutes = start_obj.hour * 60 + start_obj.minute
            end_minutes = end_obj.hour * 60 + end_obj.minute
            
            if start_minutes >= end_minutes:
                return False, "Lunch window end must be after start"
            
            window_duration = end_minutes - start_minutes
            if window_duration < duration_minutes:
                return False, "Lunch window must be longer than lunch duration"
        
        return True, ""

class SecurityValidator:
    """Security-focused validation"""
    
    @staticmethod
    def sanitize_user_input(text: str) -> str:
        """Sanitize user input to prevent injection attacks"""
        if not text:
            return ""
        
        # Remove potentially dangerous characters
        dangerous_chars = ['<', '>', '"', "'", '&', '\x00', '\r']
        sanitized = text
        
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '')
        
        # Limit length
        return sanitized[:500]
    
    @staticmethod
    def validate_user_id(user_id: str) -> bool:
        """Validate Discord user ID format"""
        if not user_id:
            return False
        
        # Discord user IDs are numeric strings of 17-19 digits
        return user_id.isdigit() and 17 <= len(user_id) <= 19
    
    @staticmethod
    def validate_guild_id(guild_id: str) -> bool:
        """Validate Discord guild ID format"""
        if not guild_id:
            return False
        
        # Discord guild IDs are numeric strings of 17-19 digits
        return guild_id.isdigit() and 17 <= len(guild_id) <= 19