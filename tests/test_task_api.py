"""Tests for Task Management API endpoints"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

# Import the FastAPI app
from src.api.main import app
from src.services import TaskManagementException
from src.models import TaskStatus, TaskPriority

client = TestClient(app)


@pytest.fixture
def mock_task_service():
    """Mock task service for testing"""
    service = AsyncMock()
    return service


@pytest.fixture
def mock_template_service():
    """Mock template service for testing"""
    service = AsyncMock()
    return service


@pytest.fixture
def authenticated_headers():
    """Get authentication headers for testing"""
    # First, get a token
    login_response = client.post(
        "/api/auth/token",
        data={"username": "admin", "password": "password"}
    )
    token = login_response.json()["access_token"]
    
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_task_data():
    """Sample task data for testing"""
    return {
        "description": "Test task description",
        "priority": "high",
        "due_time": (datetime.now() + timedelta(days=1)).isoformat(),
        "duration_minutes": 30,
        "location": "Test location",
        "is_collaborative": True,
        "assigned_users": ["user1", "user2"]
    }


@pytest.fixture
def sample_task_response():
    """Sample task response for testing"""
    return {
        "id": 1,
        "description": "Test task description",
        "created_by_user_id": "1",
        "assigned_users": ["user1", "user2"],
        "status": "pending",
        "priority": "high",
        "due_time": (datetime.now() + timedelta(days=1)).isoformat(),
        "duration_minutes": 30,
        "location": "Test location",
        "is_collaborative": True,
        "completion_percentage": 0,
        "created_at": datetime.now().isoformat()
    }


class TestTaskEndpoints:
    """Test task CRUD endpoints"""
    
    @patch('src.api.routers.tasks.get_task_service')
    def test_get_tasks_success(self, mock_get_service, authenticated_headers, mock_task_service):
        """Test successful task retrieval"""
        # Setup mock
        mock_get_service.return_value = mock_task_service
        mock_task_service.get_collaborative_tasks.return_value = [
            {"id": 1, "description": "Task 1", "priority": "high"},
            {"id": 2, "description": "Task 2", "priority": "normal"}
        ]
        
        # Make request
        response = client.get("/api/tasks/", headers=authenticated_headers)
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "limit" in data
        assert len(data["items"]) == 2
        
        # Verify service was called correctly
        mock_task_service.get_collaborative_tasks.assert_called_once()
    
    @patch('src.api.routers.tasks.get_task_service')
    def test_get_tasks_with_filters(self, mock_get_service, authenticated_headers, mock_task_service):
        """Test task retrieval with filters"""
        # Setup mock
        mock_get_service.return_value = mock_task_service
        mock_task_service.get_collaborative_tasks.return_value = [
            {"id": 1, "description": "Task 1", "priority": "high", "is_collaborative": True},
            {"id": 2, "description": "Task 2", "priority": "normal", "is_collaborative": False}
        ]
        
        # Make request with filters
        response = client.get(
            "/api/tasks/?priority=high&is_collaborative=true&page=1&limit=5",
            headers=authenticated_headers
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["priority"] == "high"
        assert data["items"][0]["is_collaborative"] is True
    
    @patch('src.api.routers.tasks.get_task_service')
    def test_create_task_success(self, mock_get_service, authenticated_headers, mock_task_service, sample_task_data, sample_task_response):
        """Test successful task creation"""
        # Setup mock
        mock_get_service.return_value = mock_task_service
        mock_task_service.create_task.return_value = sample_task_response
        
        # Make request
        response = client.post("/api/tasks/", json=sample_task_data, headers=authenticated_headers)
        
        # Assertions
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == 1
        assert data["description"] == "Test task description"
        assert data["priority"] == "high"
        
        # Verify service was called correctly
        mock_task_service.create_task.assert_called_once()
        call_args = mock_task_service.create_task.call_args
        assert call_args[0][0] == "1"  # user_id
        assert call_args[0][1].description == "Test task description"
    
    @patch('src.api.routers.tasks.get_task_service')
    def test_create_task_validation_error(self, mock_get_service, authenticated_headers, mock_task_service):
        """Test task creation with validation error"""
        # Setup mock
        mock_get_service.return_value = mock_task_service
        
        # Make request with invalid data
        invalid_data = {"description": ""}  # Empty description should fail
        response = client.post("/api/tasks/", json=invalid_data, headers=authenticated_headers)
        
        # Assertions
        assert response.status_code == 400
        assert "Invalid task data" in response.json()["detail"]
    
    @patch('src.api.routers.tasks.get_task_service')
    def test_create_task_service_error(self, mock_get_service, authenticated_headers, mock_task_service, sample_task_data):
        """Test task creation with service error"""
        # Setup mock
        mock_get_service.return_value = mock_task_service
        mock_task_service.create_task.side_effect = TaskManagementException("Creation failed", "CREATION_ERROR")
        
        # Make request
        response = client.post("/api/tasks/", json=sample_task_data, headers=authenticated_headers)
        
        # Assertions
        assert response.status_code == 400
        assert response.json()["detail"] == "Creation failed"
    
    @patch('src.api.routers.tasks.get_task_service')
    def test_get_task_by_id_success(self, mock_get_service, authenticated_headers, mock_task_service, sample_task_response):
        """Test successful task retrieval by ID"""
        # Setup mock
        mock_get_service.return_value = mock_task_service
        mock_task_service.get_task_by_id.return_value = sample_task_response
        
        # Make request
        response = client.get("/api/tasks/1", headers=authenticated_headers)
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["description"] == "Test task description"
        
        # Verify service was called correctly
        mock_task_service.get_task_by_id.assert_called_once_with(1, "1")
    
    @patch('src.api.routers.tasks.get_task_service')
    def test_get_task_by_id_not_found(self, mock_get_service, authenticated_headers, mock_task_service):
        """Test task retrieval by ID when task not found"""
        # Setup mock
        mock_get_service.return_value = mock_task_service
        mock_task_service.get_task_by_id.side_effect = TaskManagementException("Task not found", "TASK_NOT_FOUND")
        
        # Make request
        response = client.get("/api/tasks/999", headers=authenticated_headers)
        
        # Assertions
        assert response.status_code == 404
        assert response.json()["detail"] == "Task not found"
    
    @patch('src.api.routers.tasks.get_task_service')
    def test_update_task_progress_success(self, mock_get_service, authenticated_headers, mock_task_service, sample_task_response):
        """Test successful task progress update"""
        # Setup mock
        mock_get_service.return_value = mock_task_service
        mock_task_service.update_task_progress.return_value = True
        mock_task_service.get_task_by_id.return_value = sample_task_response
        
        # Make request
        progress_data = {"progress": 50, "notes": "Half way done"}
        response = client.put("/api/tasks/1", json=progress_data, headers=authenticated_headers)
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        
        # Verify service was called correctly
        mock_task_service.update_task_progress.assert_called_once_with(
            task_id=1,
            user_id="1",
            progress=50,
            notes="Half way done"
        )
    
    @patch('src.api.routers.tasks.get_task_service')
    def test_delete_task_success(self, mock_get_service, authenticated_headers, mock_task_service, sample_task_response):
        """Test successful task deletion"""
        # Setup mock
        mock_get_service.return_value = mock_task_service
        mock_task_service.get_task_by_id.return_value = sample_task_response
        
        # Make request
        response = client.delete("/api/tasks/1", headers=authenticated_headers)
        
        # Assertions
        assert response.status_code == 204
        
        # Verify service was called correctly
        mock_task_service.get_task_by_id.assert_called_once_with(1, "1")
    
    @patch('src.api.routers.tasks.get_task_service')
    def test_delete_task_unauthorized(self, mock_get_service, authenticated_headers, mock_task_service):
        """Test task deletion when user is not authorized"""
        # Setup mock - task created by different user
        unauthorized_task = {
            "id": 1,
            "created_by_user_id": "other_user",
            "assigned_users": []
        }
        mock_get_service.return_value = mock_task_service
        mock_task_service.get_task_by_id.return_value = unauthorized_task
        
        # Make request
        response = client.delete("/api/tasks/1", headers=authenticated_headers)
        
        # Assertions
        assert response.status_code == 403
        assert "Not authorized" in response.json()["detail"]


class TestTaskCollaborationEndpoints:
    """Test task collaboration endpoints"""
    
    @patch('src.api.routers.tasks.get_task_service')
    def test_assign_task_success(self, mock_get_service, authenticated_headers, mock_task_service):
        """Test successful task assignment"""
        # Setup mock
        mock_get_service.return_value = mock_task_service
        mock_task_service.assign_task_to_users.return_value = True
        
        # Make request
        assignment_data = {
            "user_ids": ["user1", "user2"],
            "message": "Please work on this task"
        }
        response = client.post("/api/tasks/1/assign", json=assignment_data, headers=authenticated_headers)
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["assigned_users"] == ["user1", "user2"]
        
        # Verify service was called correctly
        mock_task_service.assign_task_to_users.assert_called_once_with(
            task_id=1,
            user_ids=["user1", "user2"],
            assigned_by="1",
            message="Please work on this task"
        )
    
    @patch('src.api.routers.tasks.get_task_service')
    def test_update_task_progress_endpoint(self, mock_get_service, authenticated_headers, mock_task_service):
        """Test task progress update endpoint"""
        # Setup mock
        mock_get_service.return_value = mock_task_service
        mock_task_service.update_task_progress.return_value = True
        
        # Make request
        progress_data = {"progress": 75, "notes": "Almost done"}
        response = client.post("/api/tasks/1/progress", json=progress_data, headers=authenticated_headers)
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["task_id"] == 1
        
        # Verify service was called correctly
        mock_task_service.update_task_progress.assert_called_once_with(
            task_id=1,
            user_id="1",
            progress=75,
            notes="Almost done"
        )
    
    @patch('src.api.routers.tasks.get_task_service')
    def test_start_task_success(self, mock_get_service, authenticated_headers, mock_task_service):
        """Test successful task start"""
        # Setup mock
        mock_get_service.return_value = mock_task_service
        mock_task_service.start_task.return_value = True
        
        # Make request
        response = client.post("/api/tasks/1/start", headers=authenticated_headers)
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["task_id"] == 1
        
        # Verify service was called correctly
        mock_task_service.start_task.assert_called_once_with(1, "1")
    
    @patch('src.api.routers.tasks.get_task_service')
    def test_complete_task_success(self, mock_get_service, authenticated_headers, mock_task_service):
        """Test successful task completion"""
        # Setup mock
        mock_get_service.return_value = mock_task_service
        mock_task_service.complete_task.return_value = True
        
        # Make request
        completion_data = {"notes": "Task completed successfully"}
        response = client.post("/api/tasks/1/complete", json=completion_data, headers=authenticated_headers)
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["task_id"] == 1
        
        # Verify service was called correctly
        mock_task_service.complete_task.assert_called_once_with(1, "1", notes="Task completed successfully")


class TestTaskMessagingEndpoints:
    """Test task messaging endpoints"""
    
    @patch('src.api.routers.tasks.get_task_service')
    def test_get_task_messages_success(self, mock_get_service, authenticated_headers, mock_task_service):
        """Test successful task messages retrieval"""
        # Setup mock
        mock_get_service.return_value = mock_task_service
        mock_messages = [
            {"id": 1, "message": "First message", "user_id": "1", "message_type": "comment"},
            {"id": 2, "message": "Second message", "user_id": "2", "message_type": "status_update"}
        ]
        mock_task_service.get_task_messages.return_value = mock_messages
        
        # Make request
        response = client.get("/api/tasks/1/messages", headers=authenticated_headers)
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert "messages" in data
        assert len(data["messages"]) == 2
        assert data["messages"][0]["message"] == "First message"
        
        # Verify service was called correctly
        mock_task_service.get_task_messages.assert_called_once_with(1, "1")
    
    @patch('src.api.routers.tasks.get_task_service')
    def test_add_task_message_success(self, mock_get_service, authenticated_headers, mock_task_service):
        """Test successful task message addition"""
        # Setup mock
        mock_get_service.return_value = mock_task_service
        mock_message_response = {
            "id": 1,
            "task_id": 1,
            "user_id": "1",
            "message": "Test message",
            "message_type": "comment",
            "created_at": datetime.now().isoformat()
        }
        mock_task_service.add_task_message.return_value = mock_message_response
        
        # Make request
        message_data = {
            "message": "Test message",
            "message_type": "comment",
            "parent_message_id": None
        }
        response = client.post("/api/tasks/1/messages", json=message_data, headers=authenticated_headers)
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Test message"
        assert data["message_type"] == "comment"
        
        # Verify service was called correctly
        mock_task_service.add_task_message.assert_called_once_with(
            task_id=1,
            user_id="1",
            message="Test message",
            message_type="comment",
            parent_id=None
        )


class TestTaskTemplateEndpoints:
    """Test task template endpoints"""
    
    @patch('src.api.routers.tasks.get_template_service')
    def test_get_task_templates_success(self, mock_get_service, authenticated_headers, mock_template_service):
        """Test successful task templates retrieval"""
        # Setup mock
        mock_get_service.return_value = mock_template_service
        mock_templates = [
            {"id": 1, "name": "Template 1", "description": "First template"},
            {"id": 2, "name": "Template 2", "description": "Second template"}
        ]
        mock_template_service.get_user_templates.return_value = mock_templates
        
        # Make request
        response = client.get("/api/tasks/templates/", headers=authenticated_headers)
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        assert len(data["templates"]) == 2
        assert data["templates"][0]["name"] == "Template 1"
        
        # Verify service was called correctly
        mock_template_service.get_user_templates.assert_called_once_with("1", include_shared=True)
    
    @patch('src.api.routers.tasks.get_template_service')
    def test_create_task_template_success(self, mock_get_service, authenticated_headers, mock_template_service):
        """Test successful task template creation"""
        # Setup mock
        mock_get_service.return_value = mock_template_service
        mock_template_service.create_template.return_value = 1
        
        # Make request
        template_data = {
            "name": "New Template",
            "description": "Template description",
            "default_priority": "normal",
            "default_duration": 30
        }
        response = client.post("/api/tasks/templates/", json=template_data, headers=authenticated_headers)
        
        # Assertions
        assert response.status_code == 201
        data = response.json()
        assert data["template_id"] == 1
        assert data["success"] is True
        
        # Verify service was called correctly
        mock_template_service.create_template.assert_called_once_with("1", template_data)


class TestCollaborativeTasksEndpoint:
    """Test collaborative tasks endpoint"""
    
    @patch('src.api.routers.tasks.get_task_service')
    def test_get_collaborative_tasks_success(self, mock_get_service, authenticated_headers, mock_task_service):
        """Test successful collaborative tasks retrieval"""
        # Setup mock
        mock_get_service.return_value = mock_task_service
        mock_tasks = [
            {"id": 1, "description": "Collaborative task 1", "is_collaborative": True},
            {"id": 2, "description": "Collaborative task 2", "is_collaborative": True}
        ]
        mock_task_service.get_collaborative_tasks.return_value = mock_tasks
        
        # Make request
        response = client.get("/api/tasks/collaborative/", headers=authenticated_headers)
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) == 2
        assert data["total"] == 2
        
        # Verify service was called correctly
        mock_task_service.get_collaborative_tasks.assert_called_once_with(
            user_id="1",
            status=None
        )


class TestErrorHandling:
    """Test error handling scenarios"""
    
    def test_unauthorized_access(self):
        """Test accessing endpoints without authentication"""
        response = client.get("/api/tasks/")
        assert response.status_code == 401
    
    @patch('src.api.routers.tasks.get_task_service')
    def test_service_exception_handling(self, mock_get_service, authenticated_headers, mock_task_service):
        """Test handling of service exceptions"""
        # Setup mock to raise exception
        mock_get_service.return_value = mock_task_service
        mock_task_service.get_collaborative_tasks.side_effect = TaskManagementException("Service error", "SERVICE_ERROR")
        
        # Make request
        response = client.get("/api/tasks/", headers=authenticated_headers)
        
        # Assertions
        assert response.status_code == 400
        assert response.json()["detail"] == "Service error"
    
    @patch('src.api.routers.tasks.get_task_service')
    def test_unexpected_exception_handling(self, mock_get_service, authenticated_headers, mock_task_service):
        """Test handling of unexpected exceptions"""
        # Setup mock to raise unexpected exception
        mock_get_service.return_value = mock_task_service
        mock_task_service.get_collaborative_tasks.side_effect = Exception("Unexpected error")
        
        # Make request
        response = client.get("/api/tasks/", headers=authenticated_headers)
        
        # Assertions
        assert response.status_code == 500
        assert "Failed to retrieve tasks" in response.json()["detail"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])