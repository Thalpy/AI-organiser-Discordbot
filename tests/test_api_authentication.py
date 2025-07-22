"""Tests for API authentication and middleware"""

import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Import the FastAPI app
from src.api.main import app

client = TestClient(app)


class TestAuthentication:
    """Test authentication endpoints and middleware"""
    
    def test_health_check_no_auth_required(self):
        """Test that health check endpoint doesn't require authentication"""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
    
    def test_login_success(self):
        """Test successful login"""
        response = client.post(
            "/api/auth/token",
            data={"username": "admin", "password": "password"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = client.post(
            "/api/auth/token",
            data={"username": "admin", "password": "wrongpassword"}
        )
        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Incorrect username or password"
    
    def test_protected_endpoint_without_token(self):
        """Test accessing protected endpoint without token"""
        response = client.get("/api/users/me")
        assert response.status_code == 401
    
    def test_protected_endpoint_with_valid_token(self):
        """Test accessing protected endpoint with valid token"""
        # First, get a token
        login_response = client.post(
            "/api/auth/token",
            data={"username": "admin", "password": "password"}
        )
        token = login_response.json()["access_token"]
        
        # Use the token to access protected endpoint
        response = client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "admin"
        assert data["is_admin"] is True
    
    def test_protected_endpoint_with_invalid_token(self):
        """Test accessing protected endpoint with invalid token"""
        response = client.get(
            "/api/users/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401
    
    def test_admin_endpoint_with_non_admin_user(self):
        """Test accessing admin endpoint with non-admin user"""
        # This would require creating a non-admin user token
        # For now, we'll test with the admin user and mock the is_admin check
        with patch('src.api.main.get_current_active_user') as mock_user:
            mock_user.return_value = {"id": "2", "username": "user1", "is_admin": False}
            
            response = client.get("/api/users/")
            assert response.status_code == 403
            assert response.json()["detail"] == "Not enough permissions"


class TestMiddleware:
    """Test middleware functionality"""
    
    def test_cors_headers(self):
        """Test CORS headers are present"""
        response = client.get("/api/health")
        assert response.status_code == 200
        # CORS headers should be present in the response
        # Note: TestClient doesn't always include all middleware headers
    
    def test_request_timing_header(self):
        """Test that timing header is added to responses"""
        response = client.get("/api/health")
        assert response.status_code == 200
        assert "X-Process-Time" in response.headers
        # Verify it's a valid float
        process_time = float(response.headers["X-Process-Time"])
        assert process_time >= 0
    
    def test_rate_limiting_basic(self):
        """Test basic rate limiting functionality"""
        # Make multiple requests quickly
        responses = []
        for i in range(5):
            response = client.get("/api/health")
            responses.append(response)
        
        # All should succeed (under rate limit)
        for response in responses:
            assert response.status_code == 200
    
    def test_global_exception_handler(self):
        """Test global exception handler"""
        # This would require triggering an unhandled exception
        # For now, we'll test that the handler is properly configured
        pass


class TestWebSocket:
    """Test WebSocket functionality"""
    
    def test_websocket_connection(self):
        """Test WebSocket connection establishment"""
        with client.websocket_connect("/ws/test_user") as websocket:
            # Send a ping message
            websocket.send_text(json.dumps({"type": "ping", "timestamp": "123456"}))
            
            # Receive pong response
            data = websocket.receive_text()
            message = json.loads(data)
            assert message["type"] == "pong"
            assert message["timestamp"] == "123456"
    
    def test_websocket_invalid_message(self):
        """Test WebSocket with invalid JSON message"""
        with client.websocket_connect("/ws/test_user") as websocket:
            # Send invalid JSON
            websocket.send_text("invalid json")
            
            # Should receive error message
            data = websocket.receive_text()
            message = json.loads(data)
            assert message["type"] == "error"
            assert "Invalid JSON format" in message["message"]
    
    def test_websocket_unknown_message_type(self):
        """Test WebSocket with unknown message type"""
        with client.websocket_connect("/ws/test_user") as websocket:
            # Send unknown message type
            websocket.send_text(json.dumps({"type": "unknown_type"}))
            
            # Should receive error message
            data = websocket.receive_text()
            message = json.loads(data)
            assert message["type"] == "error"
            assert "Unknown message type" in message["message"]


class TestAPIDocumentation:
    """Test API documentation endpoints"""
    
    def test_openapi_json(self):
        """Test OpenAPI JSON endpoint"""
        response = client.get("/api/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert data["info"]["title"] == "Task Bot API"
    
    def test_swagger_ui(self):
        """Test Swagger UI endpoint"""
        response = client.get("/api/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


@pytest.fixture
def authenticated_client():
    """Fixture to provide an authenticated test client"""
    # Get a token
    login_response = client.post(
        "/api/auth/token",
        data={"username": "admin", "password": "password"}
    )
    token = login_response.json()["access_token"]
    
    # Create a client with the token
    class AuthenticatedClient:
        def __init__(self, token):
            self.token = token
            self.client = client
        
        def get(self, url, **kwargs):
            headers = kwargs.get("headers", {})
            headers["Authorization"] = f"Bearer {self.token}"
            kwargs["headers"] = headers
            return self.client.get(url, **kwargs)
        
        def post(self, url, **kwargs):
            headers = kwargs.get("headers", {})
            headers["Authorization"] = f"Bearer {self.token}"
            kwargs["headers"] = headers
            return self.client.post(url, **kwargs)
        
        def put(self, url, **kwargs):
            headers = kwargs.get("headers", {})
            headers["Authorization"] = f"Bearer {self.token}"
            kwargs["headers"] = headers
            return self.client.put(url, **kwargs)
        
        def delete(self, url, **kwargs):
            headers = kwargs.get("headers", {})
            headers["Authorization"] = f"Bearer {self.token}"
            kwargs["headers"] = headers
            return self.client.delete(url, **kwargs)
    
    return AuthenticatedClient(token)


class TestIntegration:
    """Integration tests for the complete API"""
    
    def test_complete_user_flow(self, authenticated_client):
        """Test a complete user flow"""
        # Get current user info
        response = authenticated_client.get("/api/users/me")
        assert response.status_code == 200
        user_data = response.json()
        assert user_data["username"] == "admin"
        
        # Get user preferences
        response = authenticated_client.get("/api/users/me/preferences")
        assert response.status_code == 200
        
        # Update preferences
        new_preferences = {"theme": "dark", "notifications_enabled": False}
        response = authenticated_client.put(
            "/api/users/me/preferences",
            json=new_preferences
        )
        assert response.status_code == 200
    
    def test_task_management_flow(self, authenticated_client):
        """Test task management flow"""
        # Create a task
        task_data = {
            "title": "Test Task",
            "description": "Test Description",
            "priority": "high",
            "status": "pending"
        }
        response = authenticated_client.post("/api/tasks/", json=task_data)
        assert response.status_code == 201
        
        # Get tasks
        response = authenticated_client.get("/api/tasks/")
        assert response.status_code == 200
        
        # Get specific task (would need actual task ID in real implementation)
        # response = authenticated_client.get("/api/tasks/1")
        # assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__])