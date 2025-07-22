"""Tests for calendar API endpoints"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

# We need to create a test app
from src.api.routers.calendar import router
from fastapi import FastAPI

app = FastAPI()
app.include_router(router, prefix="/api/calendar")

# Mock the dependencies
def mock_get_current_active_user():
    return {"id": "test_user", "username": "test_user"}

# Override the dependency
from src.api.routers.calendar import get_current_active_user
app.dependency_overrides[get_current_active_user] = mock_get_current_active_user


class TestCalendarAPI:
    """Test cases for calendar API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    def test_get_calendar_sync_status(self, client):
        """Test getting calendar sync status"""
        with patch('src.api.routers.calendar.get_calendar_service') as mock_service:
            mock_calendar_service = AsyncMock()
            mock_calendar_service.get_sync_status.return_value = {
                "sync_enabled": True,
                "last_sync": "2024-01-01T10:00:00",
                "pending_conflicts": 0,
                "statistics": {
                    "total_tasks": 10,
                    "synced_tasks": 8,
                    "sync_coverage": 80.0
                }
            }
            mock_service.return_value = mock_calendar_service
            
            response = client.get("/api/calendar/status")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "data" in data
            assert data["data"]["sync_enabled"] is True
    
    def test_get_calendar_auth_url(self, client):
        """Test getting calendar auth URL"""
        with patch('src.api.routers.calendar.get_calendar_service') as mock_service:
            mock_calendar_service = AsyncMock()
            mock_calendar_service.get_authorization_url.return_value = "https://accounts.google.com/oauth/authorize"
            mock_service.return_value = mock_calendar_service
            
            response = client.get("/api/calendar/auth-url")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "auth_url" in data
            assert data["auth_url"].startswith("https://accounts.google.com")
    
    def test_handle_oauth_callback(self, client):
        """Test handling OAuth callback"""
        with patch('src.api.routers.calendar.get_calendar_service') as mock_service:
            mock_calendar_service = AsyncMock()
            mock_calendar_service.handle_oauth_callback.return_value = True
            mock_service.return_value = mock_calendar_service
            
            response = client.post("/api/calendar/oauth-callback", json={
                "code": "test_auth_code"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "message" in data
    
    def test_trigger_calendar_sync(self, client):
        """Test triggering calendar sync"""
        with patch('src.api.routers.calendar.get_calendar_service') as mock_service:
            mock_calendar_service = AsyncMock()
            mock_calendar_service.perform_full_sync.return_value = {
                "tasks_synced_to_calendar": 5,
                "calendar_events_synced_to_tasks": 3,
                "conflicts_detected": 1,
                "conflicts_resolved": 1,
                "errors": []
            }
            mock_service.return_value = mock_calendar_service
            
            response = client.post("/api/calendar/sync", json={
                "direction": "bidirectional"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "sync_result" in data
            assert data["sync_result"]["tasks_synced_to_calendar"] == 5
    
    def test_get_calendar_conflicts(self, client):
        """Test getting calendar conflicts"""
        with patch('src.api.routers.calendar.get_calendar_service') as mock_service:
            mock_calendar_service = AsyncMock()
            mock_conflict = type('MockConflict', (), {
                'task_id': 1,
                'calendar_event_id': 'event_1',
                'conflict_type': 'title,time',
                'task_updated': '2024-01-01T10:00:00',
                'calendar_updated': '2024-01-01T11:00:00',
                'task_data': {'description': 'Task Title', 'due_time': '2024-01-01T10:00:00', 'location': None},
                'calendar_data': type('CalendarData', (), {
                    'summary': 'Calendar Title',
                    'start_time': '2024-01-01T11:00:00',
                    'end_time': '2024-01-01T12:00:00',
                    'location': None
                })()
            })()
            
            mock_calendar_service.detect_conflicts.return_value = [mock_conflict]
            mock_service.return_value = mock_calendar_service
            
            response = client.get("/api/calendar/conflicts")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "conflicts" in data
            assert len(data["conflicts"]) == 1
            assert data["conflicts"][0]["task_id"] == 1
    
    def test_resolve_calendar_conflict(self, client):
        """Test resolving calendar conflict"""
        with patch('src.api.routers.calendar.get_calendar_service') as mock_service:
            mock_calendar_service = AsyncMock()
            
            # Mock conflict for resolution
            mock_conflict = type('MockConflict', (), {
                'task_id': 1,
                'calendar_event_id': 'event_1'
            })()
            
            mock_calendar_service.detect_conflicts.return_value = [mock_conflict]
            mock_calendar_service.resolve_conflict.return_value = True
            mock_service.return_value = mock_calendar_service
            
            response = client.post("/api/calendar/resolve-conflict", json={
                "task_id": 1,
                "resolution": "task_wins"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "message" in data
    
    def test_disable_calendar_sync(self, client):
        """Test disabling calendar sync"""
        with patch('src.api.routers.calendar.get_calendar_service') as mock_service:
            mock_calendar_service = AsyncMock()
            mock_calendar_service.disable_sync.return_value = True
            mock_service.return_value = mock_calendar_service
            
            response = client.post("/api/calendar/disable")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "message" in data
    
    def test_get_calendar_events(self, client):
        """Test getting calendar events"""
        with patch('src.api.routers.calendar.get_calendar_service') as mock_service:
            mock_calendar_service = AsyncMock()
            mock_calendar_service.get_calendar_service.return_value = AsyncMock()
            
            mock_event = type('MockEvent', (), {
                'id': 'event_1',
                'summary': 'Test Event',
                'description': 'Test Description',
                'start_time': '2024-01-01T10:00:00',
                'end_time': '2024-01-01T11:00:00',
                'location': 'Test Location',
                'attendees': ['test@example.com'],
                'task_id': 1,
                'created': '2024-01-01T09:00:00',
                'updated': '2024-01-01T09:30:00'
            })()
            
            mock_calendar_service._get_user_calendar_events.return_value = [mock_event]
            mock_service.return_value = mock_calendar_service
            
            response = client.get("/api/calendar/events?days_ahead=30")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "events" in data
            assert len(data["events"]) == 1
            assert data["events"][0]["id"] == "event_1"


if __name__ == "__main__":
    pytest.main([__file__])