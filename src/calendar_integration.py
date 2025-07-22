"""
Enhanced Google Calendar Integration with Two-way Sync
Provides comprehensive calendar synchronization with conflict detection and resolution
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import hashlib

import httpx
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from utils.logging_config import get_logger
from src.sync_service import get_sync_service, sync_task_update
from src.discord_web_bridge import get_discord_web_bridge, BridgeMessage
from utils.database import get_database_manager

logger = get_logger(__name__)


class SyncDirection(Enum):
    """Direction of calendar synchronization"""
    TASK_TO_CALENDAR = "task_to_calendar"
    CALENDAR_TO_TASK = "calendar_to_task"
    BIDIRECTIONAL = "bidirectional"


class ConflictResolution(Enum):
    """Conflict resolution strategies"""
    TASK_WINS = "task_wins"
    CALENDAR_WINS = "calendar_wins"
    MERGE = "merge"
    ASK_USER = "ask_user"


@dataclass
class CalendarEvent:
    """Represents a Google Calendar event"""
    id: str
    summary: str
    description: Optional[str]
    start_time: datetime
    end_time: datetime
    location: Optional[str]
    attendees: List[str]
    created: datetime
    updated: datetime
    etag: str
    task_id: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API calls"""
        return {
            'id': self.id,
            'summary': self.summary,
            'description': self.description,
            'start': {'dateTime': self.start_time.isoformat()},
            'end': {'dateTime': self.end_time.isoformat()},
            'location': self.location,
            'attendees': [{'email': email} for email in self.attendees] if self.attendees else [],
            'extendedProperties': {
                'private': {
                    'task_id': str(self.task_id) if self.task_id else None
                }
            }
        }


@dataclass
class SyncConflict:
    """Represents a synchronization conflict"""
    task_id: int
    calendar_event_id: str
    task_data: Dict[str, Any]
    calendar_data: CalendarEvent
    conflict_type: str
    task_updated: datetime
    calendar_updated: datetime


class GoogleCalendarService:
    """Enhanced Google Calendar service with two-way sync"""
    
    def __init__(self):
        self.credentials_cache: Dict[str, Credentials] = {}
        self.sync_service = get_sync_service()
        self.bridge = get_discord_web_bridge()
        self.db = None
        
        # Load OAuth configuration
        self.client_config = self._load_client_config()
        
        # Sync settings
        self.sync_enabled_users: Dict[str, bool] = {}
        self.last_sync_times: Dict[str, datetime] = {}
        self.conflict_queue: List[SyncConflict] = []
    
    async def initialize(self):
        """Initialize the calendar service"""
        self.db = await get_database_manager()
        await self._load_user_sync_settings()
        logger.info("Google Calendar service initialized")
    
    def _load_client_config(self) -> Dict[str, Any]:
        """Load OAuth client configuration"""
        credentials_file = "credentials/client_secret.json"
        
        if not os.path.exists(credentials_file):
            logger.error(f"Missing {credentials_file}. Calendar integration disabled.")
            return {}
        
        try:
            with open(credentials_file) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load calendar credentials: {e}")
            return {}
    
    async def _load_user_sync_settings(self):
        """Load user sync settings from database"""
        try:
            query = """
                SELECT user_id, calendar_sync_enabled, last_calendar_sync
                FROM user_preferences
                WHERE calendar_sync_enabled = true
            """
            
            results = await self.db.execute_query(query, fetch_all=True)
            
            for row in results:
                user_id = row['user_id']
                self.sync_enabled_users[user_id] = row['calendar_sync_enabled']
                if row['last_calendar_sync']:
                    self.last_sync_times[user_id] = row['last_calendar_sync']
            
            logger.info(f"Loaded sync settings for {len(self.sync_enabled_users)} users")
            
        except Exception as e:
            logger.error(f"Failed to load user sync settings: {e}")
    
    async def get_oauth_flow(self, user_id: str) -> Flow:
        """Create OAuth flow for user authentication"""
        if not self.client_config:
            raise ValueError("Calendar OAuth not configured")
        
        flow = Flow.from_client_config(
            self.client_config,
            scopes=[
                'https://www.googleapis.com/auth/calendar.events',
                'https://www.googleapis.com/auth/calendar.readonly'
            ]
        )
        
        # Set redirect URI (should match your web server)
        flow.redirect_uri = self.client_config['web']['redirect_uris'][0]
        
        return flow
    
    async def get_authorization_url(self, user_id: str) -> str:
        """Get authorization URL for OAuth flow"""
        try:
            flow = await self.get_oauth_flow(user_id)
            
            auth_url, _ = flow.authorization_url(
                access_type='offline',
                prompt='consent',
                state=user_id
            )
            
            return auth_url
            
        except Exception as e:
            logger.error(f"Failed to generate authorization URL: {e}")
            raise
    
    async def handle_oauth_callback(self, user_id: str, authorization_code: str) -> bool:
        """Handle OAuth callback and store credentials"""
        try:
            flow = await self.get_oauth_flow(user_id)
            flow.fetch_token(code=authorization_code)
            
            credentials = flow.credentials
            
            # Store credentials securely
            await self._store_user_credentials(user_id, credentials)
            
            # Enable sync for this user
            await self._update_user_sync_settings(user_id, True)
            
            logger.info(f"OAuth setup completed for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"OAuth callback failed for user {user_id}: {e}")
            return False
    
    async def _store_user_credentials(self, user_id: str, credentials: Credentials):
        """Store user credentials securely in database"""
        try:
            # In production, encrypt these credentials
            credentials_data = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes
            }
            
            query = """
                INSERT INTO user_calendar_credentials (user_id, credentials_data, created_at, updated_at)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id) 
                DO UPDATE SET 
                    credentials_data = EXCLUDED.credentials_data,
                    updated_at = EXCLUDED.updated_at
            """
            
            now = datetime.now()
            await self.db.execute_query(
                query, 
                (user_id, json.dumps(credentials_data), now, now)
            )
            
            # Cache credentials
            self.credentials_cache[user_id] = credentials
            
        except Exception as e:
            logger.error(f"Failed to store credentials for user {user_id}: {e}")
            raise
    
    async def _get_user_credentials(self, user_id: str) -> Optional[Credentials]:
        """Get user credentials from cache or database"""
        # Check cache first
        if user_id in self.credentials_cache:
            credentials = self.credentials_cache[user_id]
            
            # Refresh if expired
            if credentials.expired and credentials.refresh_token:
                try:
                    credentials.refresh(Request())
                    await self._store_user_credentials(user_id, credentials)
                except Exception as e:
                    logger.error(f"Failed to refresh credentials for user {user_id}: {e}")
                    return None
            
            return credentials
        
        # Load from database
        try:
            query = "SELECT credentials_data FROM user_calendar_credentials WHERE user_id = %s"
            result = await self.db.execute_query(query, (user_id,), fetch_one=True)
            
            if not result:
                return None
            
            credentials_data = json.loads(result['credentials_data'])
            credentials = Credentials(**credentials_data)
            
            # Cache and return
            self.credentials_cache[user_id] = credentials
            return credentials
            
        except Exception as e:
            logger.error(f"Failed to load credentials for user {user_id}: {e}")
            return None
    
    async def _update_user_sync_settings(self, user_id: str, enabled: bool):
        """Update user sync settings"""
        try:
            query = """
                INSERT INTO user_preferences (user_id, calendar_sync_enabled, updated_at)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id)
                DO UPDATE SET 
                    calendar_sync_enabled = EXCLUDED.calendar_sync_enabled,
                    updated_at = EXCLUDED.updated_at
            """
            
            await self.db.execute_query(query, (user_id, enabled, datetime.now()))
            self.sync_enabled_users[user_id] = enabled
            
        except Exception as e:
            logger.error(f"Failed to update sync settings for user {user_id}: {e}")
    
    async def get_calendar_service(self, user_id: str):
        """Get authenticated Google Calendar service for user"""
        credentials = await self._get_user_credentials(user_id)
        if not credentials:
            raise ValueError(f"No valid credentials for user {user_id}")
        
        return build('calendar', 'v3', credentials=credentials)
    
    async def sync_task_to_calendar(self, user_id: str, task_data: Dict[str, Any]) -> Optional[str]:
        """Sync a task to Google Calendar"""
        try:
            if not self.sync_enabled_users.get(user_id, False):
                return None
            
            service = await self.get_calendar_service(user_id)
            
            # Check if task already has a calendar event
            existing_event_id = await self._get_task_calendar_event_id(task_data['id'])
            
            # Create calendar event from task
            event_data = self._task_to_calendar_event(task_data)
            
            if existing_event_id:
                # Update existing event
                try:
                    event = service.events().update(
                        calendarId='primary',
                        eventId=existing_event_id,
                        body=event_data
                    ).execute()
                    
                    logger.info(f"Updated calendar event {existing_event_id} for task {task_data['id']}")
                    return event['id']
                    
                except HttpError as e:
                    if e.resp.status == 404:
                        # Event was deleted, create new one
                        existing_event_id = None
                    else:
                        raise
            
            if not existing_event_id:
                # Create new event
                event = service.events().insert(
                    calendarId='primary',
                    body=event_data
                ).execute()
                
                # Store the association
                await self._store_task_calendar_association(task_data['id'], event['id'])
                
                logger.info(f"Created calendar event {event['id']} for task {task_data['id']}")
                return event['id']
            
        except Exception as e:
            logger.error(f"Failed to sync task {task_data['id']} to calendar: {e}")
            return None
    
    async def sync_calendar_to_task(self, user_id: str, event: CalendarEvent) -> Optional[int]:
        """Sync a calendar event to task system"""
        try:
            if not self.sync_enabled_users.get(user_id, False):
                return None
            
            # Check if event is already linked to a task
            if event.task_id:
                # Update existing task
                task_data = self._calendar_event_to_task(event, user_id)
                task_data['id'] = event.task_id
                
                # Update task in database
                await self._update_task_from_calendar(task_data)
                
                # Sync to Discord/Web
                await sync_task_update(task_data, user_id, 'calendar')
                
                logger.info(f"Updated task {event.task_id} from calendar event {event.id}")
                return event.task_id
            else:
                # Create new task
                task_data = self._calendar_event_to_task(event, user_id)
                
                # Create task in database
                task_id = await self._create_task_from_calendar(task_data)
                
                if task_id:
                    # Update event to link to task
                    await self._update_calendar_event_task_link(user_id, event.id, task_id)
                    
                    # Sync to Discord/Web
                    task_data['id'] = task_id
                    await sync_task_update(task_data, user_id, 'calendar')
                    
                    logger.info(f"Created task {task_id} from calendar event {event.id}")
                    return task_id
            
        except Exception as e:
            logger.error(f"Failed to sync calendar event {event.id} to task: {e}")
            return None
    
    def _task_to_calendar_event(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert task data to Google Calendar event format"""
        start_time = task_data.get('due_time') or datetime.now()
        duration = timedelta(minutes=task_data.get('duration_minutes', 30))
        end_time = start_time + duration
        
        event = {
            'summary': task_data['description'],
            'description': f"Task from TaskBot\nTask ID: {task_data['id']}",
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'UTC',
            },
            'extendedProperties': {
                'private': {
                    'task_id': str(task_data['id']),
                    'source': 'taskbot'
                }
            }
        }
        
        if task_data.get('location'):
            event['location'] = task_data['location']
        
        return event
    
    def _calendar_event_to_task(self, event: CalendarEvent, user_id: str) -> Dict[str, Any]:
        """Convert calendar event to task data"""
        return {
            'user_id': user_id,
            'description': event.summary,
            'due_time': event.start_time,
            'duration_minutes': int((event.end_time - event.start_time).total_seconds() / 60),
            'location': event.location,
            'status': 'pending',
            'priority': 'normal',
            'is_collaborative': False,
            'calendar_event_id': event.id
        }
    
    async def _get_task_calendar_event_id(self, task_id: int) -> Optional[str]:
        """Get calendar event ID associated with task"""
        try:
            query = "SELECT calendar_event_id FROM task_calendar_sync WHERE task_id = %s"
            result = await self.db.execute_query(query, (task_id,), fetch_one=True)
            return result['calendar_event_id'] if result else None
        except Exception as e:
            logger.error(f"Failed to get calendar event ID for task {task_id}: {e}")
            return None
    
    async def _store_task_calendar_association(self, task_id: int, event_id: str):
        """Store task-calendar event association"""
        try:
            query = """
                INSERT INTO task_calendar_sync (task_id, calendar_event_id, created_at)
                VALUES (%s, %s, %s)
                ON CONFLICT (task_id) 
                DO UPDATE SET 
                    calendar_event_id = EXCLUDED.calendar_event_id,
                    updated_at = %s
            """
            
            now = datetime.now()
            await self.db.execute_query(query, (task_id, event_id, now, now))
            
        except Exception as e:
            logger.error(f"Failed to store task-calendar association: {e}")
    
    async def _update_task_from_calendar(self, task_data: Dict[str, Any]):
        """Update existing task from calendar data"""
        try:
            query = """
                UPDATE tasks 
                SET description = %s, due_time = %s, duration_minutes = %s, 
                    location = %s, updated_at = %s
                WHERE id = %s
            """
            
            await self.db.execute_query(
                query,
                (
                    task_data['description'],
                    task_data['due_time'],
                    task_data['duration_minutes'],
                    task_data['location'],
                    datetime.now(),
                    task_data['id']
                )
            )
            
        except Exception as e:
            logger.error(f"Failed to update task from calendar: {e}")
    
    async def _create_task_from_calendar(self, task_data: Dict[str, Any]) -> Optional[int]:
        """Create new task from calendar data"""
        try:
            query = """
                INSERT INTO tasks (user_id, description, due_time, duration_minutes, 
                                 location, status, priority, is_collaborative, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """
            
            result = await self.db.execute_query(
                query,
                (
                    task_data['user_id'],
                    task_data['description'],
                    task_data['due_time'],
                    task_data['duration_minutes'],
                    task_data['location'],
                    task_data['status'],
                    task_data['priority'],
                    task_data['is_collaborative'],
                    datetime.now()
                ),
                fetch_one=True
            )
            
            return result['id'] if result else None
            
        except Exception as e:
            logger.error(f"Failed to create task from calendar: {e}")
            return None
    
    async def _update_calendar_event_task_link(self, user_id: str, event_id: str, task_id: int):
        """Update calendar event to link to task"""
        try:
            service = await self.get_calendar_service(user_id)
            
            # Get current event
            event = service.events().get(calendarId='primary', eventId=event_id).execute()
            
            # Update extended properties
            if 'extendedProperties' not in event:
                event['extendedProperties'] = {'private': {}}
            elif 'private' not in event['extendedProperties']:
                event['extendedProperties']['private'] = {}
            
            event['extendedProperties']['private']['task_id'] = str(task_id)
            event['extendedProperties']['private']['source'] = 'taskbot'
            
            # Update event
            service.events().update(
                calendarId='primary',
                eventId=event_id,
                body=event
            ).execute()
            
        except Exception as e:
            logger.error(f"Failed to update calendar event task link: {e}")
    
    async def detect_conflicts(self, user_id: str) -> List[SyncConflict]:
        """Detect synchronization conflicts between tasks and calendar events"""
        conflicts = []
        
        try:
            # Get tasks with calendar events
            query = """
                SELECT t.*, tcs.calendar_event_id
                FROM tasks t
                JOIN task_calendar_sync tcs ON t.id = tcs.task_id
                WHERE t.user_id = %s
            """
            
            tasks = await self.db.execute_query(query, (user_id,), fetch_all=True)
            
            if not tasks:
                return conflicts
            
            # Get calendar events
            service = await self.get_calendar_service(user_id)
            calendar_events = await self._get_user_calendar_events(service)
            
            # Check for conflicts
            for task in tasks:
                calendar_event = next(
                    (e for e in calendar_events if e.id == task['calendar_event_id']), 
                    None
                )
                
                if calendar_event:
                    conflict = self._check_for_conflict(task, calendar_event)
                    if conflict:
                        conflicts.append(conflict)
            
        except Exception as e:
            logger.error(f"Failed to detect conflicts for user {user_id}: {e}")
        
        return conflicts
    
    def _check_for_conflict(self, task_data: Dict[str, Any], calendar_event: CalendarEvent) -> Optional[SyncConflict]:
        """Check if there's a conflict between task and calendar event"""
        # Compare key fields
        conflicts = []
        
        # Title/description conflict
        if task_data['description'] != calendar_event.summary:
            conflicts.append('title')
        
        # Time conflict
        if task_data['due_time'] != calendar_event.start_time:
            conflicts.append('time')
        
        # Duration conflict
        task_duration = timedelta(minutes=task_data.get('duration_minutes', 30))
        calendar_duration = calendar_event.end_time - calendar_event.start_time
        if abs((task_duration - calendar_duration).total_seconds()) > 300:  # 5 minute tolerance
            conflicts.append('duration')
        
        # Location conflict
        if task_data.get('location') != calendar_event.location:
            conflicts.append('location')
        
        if conflicts:
            return SyncConflict(
                task_id=task_data['id'],
                calendar_event_id=calendar_event.id,
                task_data=task_data,
                calendar_data=calendar_event,
                conflict_type=','.join(conflicts),
                task_updated=task_data.get('updated_at', datetime.now()),
                calendar_updated=calendar_event.updated
            )
        
        return None
    
    async def _get_user_calendar_events(self, service, days_ahead: int = 30) -> List[CalendarEvent]:
        """Get user's calendar events"""
        try:
            now = datetime.now()
            time_min = now.isoformat() + 'Z'
            time_max = (now + timedelta(days=days_ahead)).isoformat() + 'Z'
            
            events_result = service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            calendar_events = []
            for event in events:
                try:
                    calendar_event = self._parse_calendar_event(event)
                    if calendar_event:
                        calendar_events.append(calendar_event)
                except Exception as e:
                    logger.error(f"Failed to parse calendar event: {e}")
                    continue
            
            return calendar_events
            
        except Exception as e:
            logger.error(f"Failed to get calendar events: {e}")
            return []
    
    def _parse_calendar_event(self, event_data: Dict[str, Any]) -> Optional[CalendarEvent]:
        """Parse Google Calendar event data"""
        try:
            # Parse start and end times
            start = event_data.get('start', {})
            end = event_data.get('end', {})
            
            start_time = self._parse_datetime(start.get('dateTime') or start.get('date'))
            end_time = self._parse_datetime(end.get('dateTime') or end.get('date'))
            
            if not start_time or not end_time:
                return None
            
            # Extract task ID if present
            task_id = None
            extended_props = event_data.get('extendedProperties', {}).get('private', {})
            if extended_props.get('task_id'):
                try:
                    task_id = int(extended_props['task_id'])
                except ValueError:
                    pass
            
            # Extract attendees
            attendees = []
            for attendee in event_data.get('attendees', []):
                if attendee.get('email'):
                    attendees.append(attendee['email'])
            
            return CalendarEvent(
                id=event_data['id'],
                summary=event_data.get('summary', 'Untitled Event'),
                description=event_data.get('description'),
                start_time=start_time,
                end_time=end_time,
                location=event_data.get('location'),
                attendees=attendees,
                created=self._parse_datetime(event_data.get('created')),
                updated=self._parse_datetime(event_data.get('updated')),
                etag=event_data.get('etag', ''),
                task_id=task_id
            )
            
        except Exception as e:
            logger.error(f"Failed to parse calendar event: {e}")
            return None
    
    def _parse_datetime(self, dt_string: Optional[str]) -> Optional[datetime]:
        """Parse datetime string from Google Calendar"""
        if not dt_string:
            return None
        
        try:
            # Handle different datetime formats
            if 'T' in dt_string:
                # Full datetime
                if dt_string.endswith('Z'):
                    return datetime.fromisoformat(dt_string[:-1])
                else:
                    return datetime.fromisoformat(dt_string.split('+')[0].split('-')[0])
            else:
                # Date only
                return datetime.fromisoformat(dt_string + 'T00:00:00')
        except Exception as e:
            logger.error(f"Failed to parse datetime {dt_string}: {e}")
            return None
    
    async def resolve_conflict(self, conflict: SyncConflict, resolution: ConflictResolution) -> bool:
        """Resolve a synchronization conflict"""
        try:
            if resolution == ConflictResolution.TASK_WINS:
                # Update calendar event with task data
                await self.sync_task_to_calendar(
                    conflict.task_data['user_id'], 
                    conflict.task_data
                )
                
            elif resolution == ConflictResolution.CALENDAR_WINS:
                # Update task with calendar data
                await self.sync_calendar_to_task(
                    conflict.task_data['user_id'], 
                    conflict.calendar_data
                )
                
            elif resolution == ConflictResolution.MERGE:
                # Merge data (task wins for some fields, calendar for others)
                merged_data = self._merge_conflict_data(conflict)
                
                # Update both task and calendar
                await self.sync_task_to_calendar(
                    conflict.task_data['user_id'], 
                    merged_data
                )
                await self._update_task_from_calendar(merged_data)
            
            logger.info(f"Resolved conflict for task {conflict.task_id} using {resolution.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to resolve conflict: {e}")
            return False
    
    def _merge_conflict_data(self, conflict: SyncConflict) -> Dict[str, Any]:
        """Merge conflicting data using predefined rules"""
        merged = conflict.task_data.copy()
        
        # Use most recent update for each field
        if conflict.calendar_updated > conflict.task_updated:
            # Calendar is more recent, use calendar data for time-sensitive fields
            merged['due_time'] = conflict.calendar_data.start_time
            merged['duration_minutes'] = int(
                (conflict.calendar_data.end_time - conflict.calendar_data.start_time).total_seconds() / 60
            )
            if conflict.calendar_data.location:
                merged['location'] = conflict.calendar_data.location
        
        return merged


# Global calendar service instance
_calendar_service_instance: Optional[GoogleCalendarService] = None


async def get_calendar_service() -> GoogleCalendarService:
    """Get the global calendar service instance"""
    global _calendar_service_instance
    if _calendar_service_instance is None:
        _calendar_service_instance = GoogleCalendarService()
        await _calendar_service_instance.initialize()
    return _calendar_service_instance


# Convenience functions for common operations
async def sync_task_to_calendar(user_id: str, task_data: Dict[str, Any]) -> Optional[str]:
    """Convenience function to sync task to calendar"""
    service = await get_calendar_service()
    return await service.sync_task_to_calendar(user_id, task_data)


async def sync_calendar_to_tasks(user_id: str) -> List[int]:
    """Convenience function to sync calendar events to tasks"""
    service = await get_calendar_service()
    
    try:
        calendar_service = await service.get_calendar_service(user_id)
        events = await service._get_user_calendar_events(calendar_service)
        
        synced_tasks = []
        for event in events:
            task_id = await service.sync_calendar_to_task(user_id, event)
            if task_id:
                synced_tasks.append(task_id)
        
        return synced_tasks
        
    except Exception as e:
        logger.error(f"Failed to sync calendar to tasks for user {user_id}: {e}")
        return []


async def detect_and_resolve_conflicts(user_id: str, auto_resolve: bool = False) -> List[SyncConflict]:
    """Detect and optionally auto-resolve conflicts"""
    service = await get_calendar_service()
    conflicts = await service.detect_conflicts(user_id)
    
    if auto_resolve and conflicts:
        for conflict in conflicts:
            # Use merge strategy for auto-resolution
            await service.resolve_conflict(conflict, ConflictResolution.MERGE)
    
        return conflicts
    
    def _merge_conflict_data(self, conflict: SyncConflict) -> Dict[str, Any]:
        """Merge conflicting data using predefined rules"""
        # This is a simple merge strategy - in production you might want more sophisticated logic
        merged = conflict.task_data.copy()
        
        # Use calendar data for time-related fields if calendar is newer
        if conflict.calendar_data.updated > conflict.task_updated:
            merged['due_time'] = conflict.calendar_data.start_time
            merged['duration_minutes'] = int(
                (conflict.calendar_data.end_time - conflict.calendar_data.start_time).total_seconds() / 60
            )
            
        # Use task data for description if task is newer
        if conflict.task_updated > conflict.calendar_data.updated:
            merged['description'] = conflict.task_data['description']
        else:
            merged['description'] = conflict.calendar_data.summary
            
        # Always prefer calendar location if present
        if conflict.calendar_data.location:
            merged['location'] = conflict.calendar_data.location
            
        return merged
    
    async def perform_full_sync(self, user_id: str, direction: SyncDirection = SyncDirection.BIDIRECTIONAL) -> Dict[str, Any]:
        """Perform a full synchronization between tasks and calendar"""
        try:
            if not self.sync_enabled_users.get(user_id, False):
                return {"error": "Sync not enabled for user"}
            
            sync_stats = {
                "tasks_synced_to_calendar": 0,
                "calendar_events_synced_to_tasks": 0,
                "conflicts_detected": 0,
                "conflicts_resolved": 0,
                "errors": []
            }
            
            # Get user's tasks
            tasks = await self._get_user_tasks_for_sync(user_id)
            
            # Get user's calendar events
            service = await self.get_calendar_service(user_id)
            calendar_events = await self._get_user_calendar_events(service)
            
            # Sync tasks to calendar
            if direction in [SyncDirection.TASK_TO_CALENDAR, SyncDirection.BIDIRECTIONAL]:
                for task in tasks:
                    try:
                        event_id = await self.sync_task_to_calendar(user_id, task)
                        if event_id:
                            sync_stats["tasks_synced_to_calendar"] += 1
                    except Exception as e:
                        sync_stats["errors"].append(f"Task {task['id']}: {str(e)}")
            
            # Sync calendar events to tasks
            if direction in [SyncDirection.CALENDAR_TO_TASK, SyncDirection.BIDIRECTIONAL]:
                for event in calendar_events:
                    try:
                        # Only sync events that don't already have a task ID or are from external sources
                        if not event.task_id or not await self._task_exists(event.task_id):
                            task_id = await self.sync_calendar_to_task(user_id, event)
                            if task_id:
                                sync_stats["calendar_events_synced_to_tasks"] += 1
                    except Exception as e:
                        sync_stats["errors"].append(f"Event {event.id}: {str(e)}")
            
            # Detect and resolve conflicts
            conflicts = await self.detect_conflicts(user_id)
            sync_stats["conflicts_detected"] = len(conflicts)
            
            # Auto-resolve conflicts based on user preferences
            user_conflict_resolution = await self._get_user_conflict_resolution_preference(user_id)
            
            for conflict in conflicts:
                try:
                    if await self.resolve_conflict(conflict, user_conflict_resolution):
                        sync_stats["conflicts_resolved"] += 1
                except Exception as e:
                    sync_stats["errors"].append(f"Conflict resolution: {str(e)}")
            
            # Update last sync time
            await self._update_last_sync_time(user_id)
            
            logger.info(f"Full sync completed for user {user_id}: {sync_stats}")
            return sync_stats
            
        except Exception as e:
            logger.error(f"Full sync failed for user {user_id}: {e}")
            return {"error": str(e)}
    
    async def _get_user_tasks_for_sync(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user tasks that should be synced to calendar"""
        try:
            query = """
                SELECT * FROM tasks 
                WHERE user_id = %s 
                AND status != 'completed' 
                AND due_time IS NOT NULL
                AND due_time > NOW()
                ORDER BY due_time ASC
            """
            
            return await self.db.execute_query(query, (user_id,), fetch_all=True)
            
        except Exception as e:
            logger.error(f"Failed to get user tasks for sync: {e}")
            return []
    
    async def _task_exists(self, task_id: int) -> bool:
        """Check if a task exists in the database"""
        try:
            query = "SELECT 1 FROM tasks WHERE id = %s"
            result = await self.db.execute_query(query, (task_id,), fetch_one=True)
            return result is not None
        except Exception as e:
            logger.error(f"Failed to check if task exists: {e}")
            return False
    
    async def _get_user_conflict_resolution_preference(self, user_id: str) -> ConflictResolution:
        """Get user's preferred conflict resolution strategy"""
        try:
            query = "SELECT calendar_conflict_resolution FROM user_preferences WHERE user_id = %s"
            result = await self.db.execute_query(query, (user_id,), fetch_one=True)
            
            if result and result['calendar_conflict_resolution']:
                return ConflictResolution(result['calendar_conflict_resolution'])
            
            # Default to asking user
            return ConflictResolution.ASK_USER
            
        except Exception as e:
            logger.error(f"Failed to get conflict resolution preference: {e}")
            return ConflictResolution.ASK_USER
    
    async def _update_last_sync_time(self, user_id: str):
        """Update the last sync time for a user"""
        try:
            query = """
                UPDATE user_preferences 
                SET last_calendar_sync = %s, updated_at = %s
                WHERE user_id = %s
            """
            
            now = datetime.now()
            await self.db.execute_query(query, (now, now, user_id))
            self.last_sync_times[user_id] = now
            
        except Exception as e:
            logger.error(f"Failed to update last sync time: {e}")
    
    async def schedule_automatic_sync(self, user_id: str, interval_minutes: int = 15):
        """Schedule automatic synchronization for a user"""
        try:
            # In a production system, this would use a task queue like Celery
            # For now, we'll use asyncio to schedule periodic syncs
            
            async def sync_loop():
                while self.sync_enabled_users.get(user_id, False):
                    try:
                        await self.perform_full_sync(user_id)
                        await asyncio.sleep(interval_minutes * 60)
                    except Exception as e:
                        logger.error(f"Automatic sync failed for user {user_id}: {e}")
                        await asyncio.sleep(300)  # Wait 5 minutes before retrying
            
            # Start the sync loop in the background
            asyncio.create_task(sync_loop())
            
            logger.info(f"Scheduled automatic sync for user {user_id} every {interval_minutes} minutes")
            
        except Exception as e:
            logger.error(f"Failed to schedule automatic sync: {e}")
    
    async def handle_calendar_webhook(self, user_id: str, webhook_data: Dict[str, Any]):
        """Handle webhook notifications from Google Calendar"""
        try:
            # Google Calendar sends webhook notifications when events change
            # This allows for real-time synchronization
            
            resource_id = webhook_data.get('resourceId')
            resource_state = webhook_data.get('resourceState')
            
            if resource_state in ['exists', 'sync']:
                # Calendar event was created or updated
                await self.perform_full_sync(user_id, SyncDirection.CALENDAR_TO_TASK)
                
                logger.info(f"Processed calendar webhook for user {user_id}: {resource_state}")
                
        except Exception as e:
            logger.error(f"Failed to handle calendar webhook: {e}")
    
    async def get_sync_status(self, user_id: str) -> Dict[str, Any]:
        """Get synchronization status for a user"""
        try:
            # Check if sync is enabled
            sync_enabled = self.sync_enabled_users.get(user_id, False)
            
            # Get last sync time
            last_sync = self.last_sync_times.get(user_id)
            
            # Get pending conflicts
            conflicts = await self.detect_conflicts(user_id)
            
            # Get sync statistics
            stats = await self._get_sync_statistics(user_id)
            
            return {
                "sync_enabled": sync_enabled,
                "last_sync": last_sync.isoformat() if last_sync else None,
                "pending_conflicts": len(conflicts),
                "conflicts": [
                    {
                        "task_id": c.task_id,
                        "event_id": c.calendar_event_id,
                        "conflict_type": c.conflict_type,
                        "task_updated": c.task_updated.isoformat(),
                        "calendar_updated": c.calendar_updated.isoformat()
                    }
                    for c in conflicts
                ],
                "statistics": stats
            }
            
        except Exception as e:
            logger.error(f"Failed to get sync status: {e}")
            return {"error": str(e)}
    
    async def _get_sync_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get synchronization statistics for a user"""
        try:
            # Get counts of synced items
            query = """
                SELECT 
                    COUNT(*) as total_tasks,
                    COUNT(tcs.calendar_event_id) as synced_tasks
                FROM tasks t
                LEFT JOIN task_calendar_sync tcs ON t.id = tcs.task_id
                WHERE t.user_id = %s
            """
            
            result = await self.db.execute_query(query, (user_id,), fetch_one=True)
            
            return {
                "total_tasks": result['total_tasks'] if result else 0,
                "synced_tasks": result['synced_tasks'] if result else 0,
                "sync_coverage": (result['synced_tasks'] / result['total_tasks'] * 100) if result and result['total_tasks'] > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get sync statistics: {e}")
            return {}
    
    async def disable_sync(self, user_id: str) -> bool:
        """Disable calendar synchronization for a user"""
        try:
            await self._update_user_sync_settings(user_id, False)
            
            # Remove from cache
            if user_id in self.credentials_cache:
                del self.credentials_cache[user_id]
            
            if user_id in self.sync_enabled_users:
                del self.sync_enabled_users[user_id]
            
            if user_id in self.last_sync_times:
                del self.last_sync_times[user_id]
            
            logger.info(f"Disabled calendar sync for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to disable sync for user {user_id}: {e}")
            return False


# Singleton instance
_calendar_service = None


async def get_calendar_service() -> GoogleCalendarService:
    """Get the calendar service instance"""
    global _calendar_service
    if _calendar_service is None:
        _calendar_service = GoogleCalendarService()
        await _calendar_service.initialize()
    return _calendar_service