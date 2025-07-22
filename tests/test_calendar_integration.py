"""Tests for enhanced Google Calendar integration"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any

from src.calendar_integration import (
    GoogleCalendarService, 
    CalendarEvent, 
    SyncConflict, 
    SyncDirection, 
    ConflictResolution,
    get_calendar_service
)


class TestGoogleCalendarService:
    """Test cases for GoogleCalendarService"""
    
    @pytest.fixture
    def calendar_service(self):
        """Create a calendar service instance for testing"""
        service = GoogleCalendarService()
        service.db = AsyncMock()
        service.sync_service = AsyncMock()
        service.bridge = AsyncMock()
        service.client_config = {
            "web": {
                "client_id": "test_client_id",
                "client_secret": "test_client_secret",
                "redirect_uris": ["http://localhost:8080/oauth2callback"]
            }
        }
        return service
    
    @pytest.fixture
    def sample_task_data(self):
        """Sample task data for testing"""
        return {
            "id": 1,
            "user_id": "test_user",
            "description": "Test Task",
            "due_time": datetime.now() + timedelta(hours=2),
            "duration_minutes": 60,
            "location": "Test Location",
            "status": "pending",
            "priority": "medium",
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
    
    @pytest.fixture
    def sample_calendar_event(self):
        """Sample calendar event for testing"""
        now = datetime.now()
        return CalendarEvent(
            id="test_event_id",
            summary="Test Event",
            description="Test Description",
            start_time=now + timedelta(hours=1),
            end_time=now + timedelta(hours=2),
            location="Test Location",
            attendees=["test@example.com"],
            created=now - timedelta(days=1),
            updated=now,
            etag="test_etag",
            task_id=1
        )
    
    @pytest.mark.asyncio
    async def test_initialization(self, calendar_service):
        """Test calendar service initialization"""
        await calendar_service.initialize()
        
        assert calendar_service.db is not None
        assert calendar_service.sync_service is not None
        assert calendar_service.bridge is not None
    
    @pytest.mark.asyncio
    async def test_get_authorization_url(self, calendar_service):
        """Test OAuth authorization URL generation"""
        user_id = "test_user"
        
        with patch('google_auth_oauthlib.flow.Flow.from_client_config') as mock_flow:
            mock_flow_instance = Mock()
            mock_flow_instance.authorization_url.return_value = ("http://test.url", "state")
            mock_flow.return_value = mock_flow_instance
            
            auth_url = await calendar_service.get_authorization_url(user_id)
            
            assert auth_url == "http://test.url"
            mock_flow_instance.authorization_url.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_oauth_callback_success(self, calendar_service):
        """Test successful OAuth callback handling"""
        user_id = "test_user"
        auth_code = "test_auth_code"
        
        with patch('google_auth_oauthlib.flow.Flow.from_client_config') as mock_flow:
            mock_flow_instance = Mock()
            mock_credentials = Mock()
            mock_flow_instance.fetch_token.return_value = None
            mock_flow_instance.credentials = mock_credentials
            mock_flow.return_value = mock_flow_instance
            
            calendar_service._store_user_credentials = AsyncMock()
            calendar_service._update_user_sync_settings = AsyncMock()
            
            result = await calendar_service.handle_oauth_callback(user_id, auth_code)
            
            assert result is True
            mock_flow_instance.fetch_token.assert_called_once_with(code=auth_code)
            calendar_service._store_user_credentials.assert_called_once_with(user_id, mock_credentials)
            calendar_service._update_user_sync_settings.assert_called_once_with(user_id, True)
    
    @pytest.mark.asyncio
    async def test_sync_task_to_calendar_new_event(self, calendar_service, sample_task_data):
        """Test syncing a task to calendar (new event)"""
        user_id = "test_user"
        calendar_service.sync_enabled_users[user_id] = True
        
        # Mock Google Calendar service
        mock_service = Mock()
        mock_events = Mock()
        mock_service.events.return_value = mock_events
        mock_events.insert.return_value.execute.return_value = {"id": "new_event_id"}
        
        calendar_service.get_calendar_service = AsyncMock(return_value=mock_service)
        calendar_service._get_task_calendar_event_id = AsyncMock(return_value=None)
        calendar_service._store_task_calendar_association = AsyncMock()
        
        event_id = await calendar_service.sync_task_to_calendar(user_id, sample_task_data)
        
        assert event_id == "new_event_id"
        mock_events.insert.assert_called_once()
        calendar_service._store_task_calendar_association.assert_called_once_with(1, "new_event_id")
    
    @pytest.mark.asyncio
    async def test_sync_task_to_calendar_update_existing(self, calendar_service, sample_task_data):
        """Test syncing a task to calendar (update existing event)"""
        user_id = "test_user"
        existing_event_id = "existing_event_id"
        calendar_service.sync_enabled_users[user_id] = True
        
        # Mock Google Calendar service
        mock_service = Mock()
        mock_events = Mock()
        mock_service.events.return_value = mock_events
        mock_events.update.return_value.execute.return_value = {"id": existing_event_id}
        
        calendar_service.get_calendar_service = AsyncMock(return_value=mock_service)
        calendar_service._get_task_calendar_event_id = AsyncMock(return_value=existing_event_id)
        
        event_id = await calendar_service.sync_task_to_calendar(user_id, sample_task_data)
        
        assert event_id == existing_event_id
        mock_events.update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_sync_calendar_to_task_new_task(self, calendar_service, sample_calendar_event):
        """Test syncing a calendar event to task system (new task)"""
        user_id = "test_user"
        calendar_service.sync_enabled_users[user_id] = True
        
        # Remove task_id to simulate new event
        sample_calendar_event.task_id = None
        
        calendar_service._create_task_from_calendar = AsyncMock(return_value=123)
        calendar_service._update_calendar_event_task_link = AsyncMock()
        calendar_service.sync_service.sync_task_update = AsyncMock()
        
        task_id = await calendar_service.sync_calendar_to_task(user_id, sample_calendar_event)
        
        assert task_id == 123
        calendar_service._create_task_from_calendar.assert_called_once()
        calendar_service._update_calendar_event_task_link.assert_called_once_with(
            user_id, sample_calendar_event.id, 123
        )
    
    @pytest.mark.asyncio
    async def test_sync_calendar_to_task_update_existing(self, calendar_service, sample_calendar_event):
        """Test syncing a calendar event to task system (update existing task)"""
        user_id = "test_user"
        calendar_service.sync_enabled_users[user_id] = True
        
        calendar_service._update_task_from_calendar = AsyncMock()
        calendar_service.sync_service.sync_task_update = AsyncMock()
        
        task_id = await calendar_service.sync_calendar_to_task(user_id, sample_calendar_event)
        
        assert task_id == sample_calendar_event.task_id
        calendar_service._update_task_from_calendar.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_detect_conflicts(self, calendar_service):
        """Test conflict detection between tasks and calendar events"""
        user_id = "test_user"
        
        # Mock database query
        task_data = {
            "id": 1,
            "description": "Task Title",
            "due_time": datetime.now(),
            "duration_minutes": 60,
            "location": "Task Location",
            "updated_at": datetime.now() - timedelta(minutes=30),
            "calendar_event_id": "event_1"
        }
        
        calendar_service.db.execute_query = AsyncMock(return_value=[task_data])
        
        # Mock calendar events
        calendar_event = CalendarEvent(
            id="event_1",
            summary="Different Title",  # Conflict!
            description="Description",
            start_time=datetime.now() + timedelta(minutes=30),  # Conflict!
            end_time=datetime.now() + timedelta(minutes=90),
            location="Different Location",  # Conflict!
            attendees=[],
            created=datetime.now() - timedelta(days=1),
            updated=datetime.now(),  # Newer than task
            etag="etag",
            task_id=1
        )
        
        calendar_service.get_calendar_service = AsyncMock()
        calendar_service._get_user_calendar_events = AsyncMock(return_value=[calendar_event])
        
        conflicts = await calendar_service.detect_conflicts(user_id)
        
        assert len(conflicts) == 1
        conflict = conflicts[0]
        assert conflict.task_id == 1
        assert conflict.calendar_event_id == "event_1"
        assert "title" in conflict.conflict_type
        assert "time" in conflict.conflict_type
        assert "location" in conflict.conflict_type
    
    @pytest.mark.asyncio
    async def test_resolve_conflict_task_wins(self, calendar_service):
        """Test conflict resolution with task wins strategy"""
        conflict = SyncConflict(
            task_id=1,
            calendar_event_id="event_1",
            task_data={"id": 1, "user_id": "test_user", "description": "Task Title"},
            calendar_data=Mock(),
            conflict_type="title,time",
            task_updated=datetime.now(),
            calendar_updated=datetime.now() - timedelta(minutes=30)
        )
        
        calendar_service.sync_task_to_calendar = AsyncMock(return_value="event_1")
        
        result = await calendar_service.resolve_conflict(conflict, ConflictResolution.TASK_WINS)
        
        assert result is True
        calendar_service.sync_task_to_calendar.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_resolve_conflict_calendar_wins(self, calendar_service):
        """Test conflict resolution with calendar wins strategy"""
        conflict = SyncConflict(
            task_id=1,
            calendar_event_id="event_1",
            task_data={"id": 1, "user_id": "test_user"},
            calendar_data=Mock(),
            conflict_type="title,time",
            task_updated=datetime.now() - timedelta(minutes=30),
            calendar_updated=datetime.now()
        )
        
        calendar_service.sync_calendar_to_task = AsyncMock(return_value=1)
        
        result = await calendar_service.resolve_conflict(conflict, ConflictResolution.CALENDAR_WINS)
        
        assert result is True
        calendar_service.sync_calendar_to_task.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_perform_full_sync(self, calendar_service):
        """Test full synchronization process"""
        user_id = "test_user"
        calendar_service.sync_enabled_users[user_id] = True
        
        # Mock tasks and events
        tasks = [{"id": 1, "description": "Task 1"}]
        events = [Mock()]
        
        calendar_service._get_user_tasks_for_sync = AsyncMock(return_value=tasks)
        calendar_service.get_calendar_service = AsyncMock()
        calendar_service._get_user_calendar_events = AsyncMock(return_value=events)
        calendar_service.sync_task_to_calendar = AsyncMock(return_value="event_1")
        calendar_service.sync_calendar_to_task = AsyncMock(return_value=1)
        calendar_service.detect_conflicts = AsyncMock(return_value=[])
        calendar_service._get_user_conflict_resolution_preference = AsyncMock(
            return_value=ConflictResolution.TASK_WINS
        )
        calendar_service._update_last_sync_time = AsyncMock()
        
        # Mock event without task_id
        events[0].task_id = None
        calendar_service._task_exists = AsyncMock(return_value=False)
        
        result = await calendar_service.perform_full_sync(user_id, SyncDirection.BIDIRECTIONAL)
        
        assert result["tasks_synced_to_calendar"] == 1
        assert result["calendar_events_synced_to_tasks"] == 1
        assert result["conflicts_detected"] == 0
        assert result["conflicts_resolved"] == 0
        assert len(result["errors"]) == 0
    
    @pytest.mark.asyncio
    async def test_get_sync_status(self, calendar_service):
        """Test getting synchronization status"""
        user_id = "test_user"
        calendar_service.sync_enabled_users[user_id] = True
        calendar_service.last_sync_times[user_id] = datetime.now()
        
        calendar_service.detect_conflicts = AsyncMock(return_value=[])
        calendar_service._get_sync_statistics = AsyncMock(return_value={
            "total_tasks": 10,
            "synced_tasks": 8,
            "sync_coverage": 80.0
        })
        
        status = await calendar_service.get_sync_status(user_id)
        
        assert status["sync_enabled"] is True
        assert status["last_sync"] is not None
        assert status["pending_conflicts"] == 0
        assert status["statistics"]["total_tasks"] == 10
        assert status["statistics"]["synced_tasks"] == 8
        assert status["statistics"]["sync_coverage"] == 80.0
    
    @pytest.mark.asyncio
    async def test_disable_sync(self, calendar_service):
        """Test disabling calendar synchronization"""
        user_id = "test_user"
        calendar_service.sync_enabled_users[user_id] = True
        calendar_service.credentials_cache[user_id] = Mock()
        calendar_service.last_sync_times[user_id] = datetime.now()
        
        calendar_service._update_user_sync_settings = AsyncMock()
        
        result = await calendar_service.disable_sync(user_id)
        
        assert result is True
        assert user_id not in calendar_service.sync_enabled_users
        assert user_id not in calendar_service.credentials_cache
        assert user_id not in calendar_service.last_sync_times
        calendar_service._update_user_sync_settings.assert_called_once_with(user_id, False)
    
    def test_task_to_calendar_event_conversion(self, calendar_service, sample_task_data):
        """Test converting task data to calendar event format"""
        event_data = calendar_service._task_to_calendar_event(sample_task_data)
        
        assert event_data["summary"] == sample_task_data["description"]
        assert "Task from TaskBot" in event_data["description"]
        assert event_data["location"] == sample_task_data["location"]
        assert event_data["extendedProperties"]["private"]["task_id"] == str(sample_task_data["id"])
    
    def test_calendar_event_to_task_conversion(self, calendar_service, sample_calendar_event):
        """Test converting calendar event to task data"""
        user_id = "test_user"
        task_data = calendar_service._calendar_event_to_task(sample_calendar_event, user_id)
        
        assert task_data["user_id"] == user_id
        assert task_data["description"] == sample_calendar_event.summary
        assert task_data["due_time"] == sample_calendar_event.start_time
        assert task_data["location"] == sample_calendar_event.location
        assert task_data["calendar_event_id"] == sample_calendar_event.id
    
    def test_parse_calendar_event(self, calendar_service):
        """Test parsing Google Calendar event data"""
        event_data = {
            "id": "test_event_id",
            "summary": "Test Event",
            "description": "Test Description",
            "start": {"dateTime": "2024-01-01T10:00:00Z"},
            "end": {"dateTime": "2024-01-01T11:00:00Z"},
            "location": "Test Location",
            "attendees": [{"email": "test@example.com"}],
            "created": "2024-01-01T09:00:00Z",
            "updated": "2024-01-01T09:30:00Z",
            "etag": "test_etag",
            "extendedProperties": {
                "private": {
                    "task_id": "123"
                }
            }
        }
        
        calendar_event = calendar_service._parse_calendar_event(event_data)
        
        assert calendar_event is not None
        assert calendar_event.id == "test_event_id"
        assert calendar_event.summary == "Test Event"
        assert calendar_event.task_id == 123
        assert calendar_event.attendees == ["test@example.com"]
    
    def test_parse_datetime(self, calendar_service):
        """Test parsing datetime strings from Google Calendar"""
        # Test full datetime with Z
        dt1 = calendar_service._parse_datetime("2024-01-01T10:00:00Z")
        assert dt1 is not None
        assert dt1.year == 2024
        assert dt1.month == 1
        assert dt1.day == 1
        assert dt1.hour == 10
        
        # Test date only
        dt2 = calendar_service._parse_datetime("2024-01-01")
        assert dt2 is not None
        assert dt2.year == 2024
        assert dt2.month == 1
        assert dt2.day == 1
        assert dt2.hour == 0
        
        # Test invalid datetime
        dt3 = calendar_service._parse_datetime("invalid")
        assert dt3 is None
    
    @pytest.mark.asyncio
    async def test_schedule_automatic_sync(self, calendar_service):
        """Test scheduling automatic synchronization"""
        user_id = "test_user"
        calendar_service.sync_enabled_users[user_id] = True
        calendar_service.perform_full_sync = AsyncMock()
        
        # Mock asyncio.create_task to avoid actually starting the loop
        with patch('asyncio.create_task') as mock_create_task:
            await calendar_service.schedule_automatic_sync(user_id, 15)
            
            mock_create_task.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_calendar_webhook(self, calendar_service):
        """Test handling calendar webhook notifications"""
        user_id = "test_user"
        webhook_data = {
            "resourceId": "test_resource",
            "resourceState": "exists"
        }
        
        calendar_service.perform_full_sync = AsyncMock()
        
        await calendar_service.handle_calendar_webhook(user_id, webhook_data)
        
        calendar_service.perform_full_sync.assert_called_once_with(
            user_id, SyncDirection.CALENDAR_TO_TASK
        )


class TestCalendarIntegrationHelpers:
    """Test helper functions and utilities"""
    
    @pytest.mark.asyncio
    async def test_get_calendar_service_singleton(self):
        """Test that get_calendar_service returns a singleton"""
        service1 = await get_calendar_service()
        service2 = await get_calendar_service()
        
        assert service1 is service2


if __name__ == "__main__":
    pytest.main([__file__])