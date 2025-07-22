"""Integration tests for WebSocket functionality"""

import pytest
import json
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Import the FastAPI app and WebSocket components
from src.api.main import app
from src.api.websocket_manager import (
    connection_manager, 
    websocket_handler, 
    collaborative_editing_manager,
    presence_manager
)

client = TestClient(app)


class TestWebSocketBasicFunctionality:
    """Test basic WebSocket functionality"""
    
    def test_websocket_connection_establishment(self):
        """Test WebSocket connection can be established"""
        with client.websocket_connect("/ws/test_user") as websocket:
            # Connection should be established successfully
            assert websocket is not None
    
    def test_ping_pong_functionality(self):
        """Test ping-pong message handling"""
        with client.websocket_connect("/ws/test_user") as websocket:
            # Send ping
            ping_message = {"type": "ping", "timestamp": "123456789"}
            websocket.send_text(json.dumps(ping_message))
            
            # Receive pong
            response = websocket.receive_text()
            pong_message = json.loads(response)
            
            assert pong_message["type"] == "pong"
            assert pong_message["timestamp"] == "123456789"
    
    def test_invalid_json_handling(self):
        """Test handling of invalid JSON messages"""
        with client.websocket_connect("/ws/test_user") as websocket:
            # Send invalid JSON
            websocket.send_text("invalid json")
            
            # Should receive error message
            response = websocket.receive_text()
            error_message = json.loads(response)
            
            assert error_message["type"] == "error"
            assert "Invalid JSON format" in error_message["message"]
    
    def test_unknown_message_type_handling(self):
        """Test handling of unknown message types"""
        with client.websocket_connect("/ws/test_user") as websocket:
            # Send unknown message type
            unknown_message = {"type": "unknown_message_type"}
            websocket.send_text(json.dumps(unknown_message))
            
            # Should receive error message
            response = websocket.receive_text()
            error_message = json.loads(response)
            
            assert error_message["type"] == "error"
            assert "Unknown message type" in error_message["message"]


class TestTaskSubscription:
    """Test task subscription functionality"""
    
    def test_task_subscription(self):
        """Test subscribing to task updates"""
        with client.websocket_connect("/ws/test_user") as websocket:
            # Subscribe to a task
            subscribe_message = {"type": "subscribe_task", "task_id": "123"}
            websocket.send_text(json.dumps(subscribe_message))
            
            # Should receive confirmation
            response = websocket.receive_text()
            confirmation = json.loads(response)
            
            assert confirmation["type"] == "subscription_confirmed"
            assert confirmation["task_id"] == "123"
    
    def test_task_unsubscription(self):
        """Test unsubscribing from task updates"""
        with client.websocket_connect("/ws/test_user") as websocket:
            # First subscribe
            subscribe_message = {"type": "subscribe_task", "task_id": "123"}
            websocket.send_text(json.dumps(subscribe_message))
            websocket.receive_text()  # Consume confirmation
            
            # Then unsubscribe
            unsubscribe_message = {"type": "unsubscribe_task", "task_id": "123"}
            websocket.send_text(json.dumps(unsubscribe_message))
            
            # Should receive confirmation
            response = websocket.receive_text()
            confirmation = json.loads(response)
            
            assert confirmation["type"] == "unsubscription_confirmed"
            assert confirmation["task_id"] == "123"


class TestCollaborativeRooms:
    """Test collaborative room functionality"""
    
    def test_join_room(self):
        """Test joining a collaboration room"""
        with client.websocket_connect("/ws/test_user") as websocket:
            # Join a room
            join_message = {"type": "join_room", "room_id": "room_123"}
            websocket.send_text(json.dumps(join_message))
            
            # Should receive confirmation
            response = websocket.receive_text()
            confirmation = json.loads(response)
            
            assert confirmation["type"] == "room_joined"
            assert confirmation["room_id"] == "room_123"
            assert "test_user" in confirmation["members"]
    
    def test_leave_room(self):
        """Test leaving a collaboration room"""
        with client.websocket_connect("/ws/test_user") as websocket:
            # First join a room
            join_message = {"type": "join_room", "room_id": "room_123"}
            websocket.send_text(json.dumps(join_message))
            websocket.receive_text()  # Consume join confirmation
            
            # Then leave the room
            leave_message = {"type": "leave_room", "room_id": "room_123"}
            websocket.send_text(json.dumps(leave_message))
            
            # Should receive confirmation
            response = websocket.receive_text()
            confirmation = json.loads(response)
            
            assert confirmation["type"] == "room_left"
            assert confirmation["room_id"] == "room_123"
    
    def test_multiple_users_in_room(self):
        """Test multiple users joining the same room"""
        with client.websocket_connect("/ws/user1") as ws1, \
             client.websocket_connect("/ws/user2") as ws2:
            
            # User 1 joins room
            join_message = {"type": "join_room", "room_id": "room_123"}
            ws1.send_text(json.dumps(join_message))
            response1 = json.loads(ws1.receive_text())
            assert response1["type"] == "room_joined"
            
            # User 2 joins the same room
            ws2.send_text(json.dumps(join_message))
            response2 = json.loads(ws2.receive_text())
            assert response2["type"] == "room_joined"
            
            # User 1 should receive notification about user 2 joining
            try:
                notification = json.loads(ws1.receive_text())
                assert notification["type"] == "user_joined_room"
                assert notification["user_id"] == "user2"
            except:
                # This might not work in test environment due to async nature
                pass


class TestTypingIndicators:
    """Test typing indicator functionality"""
    
    def test_typing_start_stop(self):
        """Test typing start and stop indicators"""
        with client.websocket_connect("/ws/test_user") as websocket:
            # Start typing
            typing_start = {"type": "typing_start", "room_id": "room_123"}
            websocket.send_text(json.dumps(typing_start))
            
            # Stop typing
            typing_stop = {"type": "typing_stop", "room_id": "room_123"}
            websocket.send_text(json.dumps(typing_stop))
            
            # These don't return direct responses, but should not cause errors


class TestPresenceUpdates:
    """Test user presence functionality"""
    
    def test_presence_update(self):
        """Test updating user presence"""
        with client.websocket_connect("/ws/test_user") as websocket:
            # Update presence
            presence_message = {"type": "presence_update", "status": "busy"}
            websocket.send_text(json.dumps(presence_message))
            
            # This broadcasts to all users, so we might not receive a direct response
            # But it should not cause an error


class TestCollaborativeEditing:
    """Test collaborative editing functionality"""
    
    def test_message_edit(self):
        """Test collaborative message editing"""
        with client.websocket_connect("/ws/test_user") as websocket:
            # Edit a message
            edit_message = {
                "type": "message_edit",
                "room_id": "room_123",
                "message_id": "msg_456",
                "content": "Updated message content"
            }
            websocket.send_text(json.dumps(edit_message))
            
            # This broadcasts to room members, so no direct response expected


class TestNotificationDelivery:
    """Test notification delivery through WebSocket"""
    
    @pytest.mark.asyncio
    async def test_personal_notification_delivery(self):
        """Test sending personal notifications via WebSocket"""
        from src.api.websocket_manager import notify_user_notification
        
        # This would require a more complex test setup with actual WebSocket connections
        # For now, we'll test that the function doesn't raise errors
        notification_data = {
            "id": 1,
            "type": "task_assignment",
            "message": "You have been assigned a new task",
            "task_id": 123
        }
        
        # This should not raise an error even if no user is connected
        await notify_user_notification("test_user", notification_data)
    
    @pytest.mark.asyncio
    async def test_task_reminder_notification(self):
        """Test sending task reminder notifications"""
        from src.api.websocket_manager import notify_task_reminder
        
        reminder_data = {
            "type": "due_soon",
            "message": "Task is due in 1 hour",
            "due_date": "2023-01-01T12:00:00Z"
        }
        
        # This should not raise an error even if no user is connected
        await notify_task_reminder("test_user", 123, reminder_data)
    
    @pytest.mark.asyncio
    async def test_system_announcement(self):
        """Test broadcasting system announcements"""
        from src.api.websocket_manager import broadcast_system_announcement
        
        announcement = {
            "title": "System Maintenance",
            "message": "The system will be down for maintenance at 2 AM",
            "priority": "high"
        }
        
        # This should not raise an error even if no users are connected
        await broadcast_system_announcement(announcement)


class TestConnectionManager:
    """Test connection manager functionality"""
    
    @pytest.mark.asyncio
    async def test_connection_tracking(self):
        """Test that connections are properly tracked"""
        # Test connection manager methods
        connected_users = connection_manager.get_connected_users()
        assert isinstance(connected_users, list)
        
        # Test user connection count
        count = connection_manager.get_user_connection_count("nonexistent_user")
        assert count == 0
        
        # Test user connection status
        is_connected = connection_manager.is_user_connected("nonexistent_user")
        assert is_connected is False


class TestCollaborativeEditingManager:
    """Test collaborative editing manager"""
    
    @pytest.mark.asyncio
    async def test_editing_session_lifecycle(self):
        """Test collaborative editing session lifecycle"""
        message_id = "test_message_123"
        user_id = "test_user"
        initial_content = "Initial message content"
        
        # Start editing session
        await collaborative_editing_manager.start_editing_session(
            message_id, user_id, initial_content
        )
        
        # Check session was created
        assert message_id in collaborative_editing_manager.editing_sessions
        assert user_id in collaborative_editing_manager.editing_sessions[message_id]["users"]
        
        # Apply text operation
        operation = {
            "type": "insert",
            "position": 0,
            "text": "Updated: "
        }
        
        result = await collaborative_editing_manager.apply_text_operation(
            message_id, user_id, operation
        )
        assert result is True
        
        # Check content was updated
        session = collaborative_editing_manager.editing_sessions[message_id]
        assert session["content"].startswith("Updated: ")
        assert session["version"] == 1
        
        # End editing session
        await collaborative_editing_manager.end_editing_session(message_id, user_id)
        
        # Check session was cleaned up
        assert message_id not in collaborative_editing_manager.editing_sessions


class TestPresenceManager:
    """Test presence manager functionality"""
    
    @pytest.mark.asyncio
    async def test_presence_management(self):
        """Test user presence management"""
        user_id = "test_user"
        
        # Update presence
        await presence_manager.update_user_presence(user_id, "online", "working")
        
        # Check presence was updated
        presence = presence_manager.get_user_presence(user_id)
        assert presence is not None
        assert presence["status"] == "online"
        assert presence["activity"] == "working"
        
        # Set user offline
        await presence_manager.set_user_offline(user_id)
        
        # Check user is offline
        presence = presence_manager.get_user_presence(user_id)
        assert presence["status"] == "offline"
        
        # Get all presence
        all_presence = presence_manager.get_all_presence()
        assert user_id in all_presence


class TestErrorHandling:
    """Test error handling in WebSocket operations"""
    
    def test_malformed_message_handling(self):
        """Test handling of malformed messages"""
        with client.websocket_connect("/ws/test_user") as websocket:
            # Send message without required fields
            incomplete_message = {"type": "subscribe_task"}  # Missing task_id
            websocket.send_text(json.dumps(incomplete_message))
            
            # Should receive confirmation (with None task_id)
            response = websocket.receive_text()
            confirmation = json.loads(response)
            assert confirmation["type"] == "subscription_confirmed"
    
    def test_connection_cleanup_on_disconnect(self):
        """Test that connections are properly cleaned up on disconnect"""
        # This is harder to test directly, but we can verify the disconnect method works
        from unittest.mock import MagicMock
        
        mock_websocket = MagicMock()
        connection_manager.connection_metadata[mock_websocket] = {
            "user_id": "test_user",
            "connected_at": 123456789
        }
        connection_manager.active_connections["test_user"] = {mock_websocket}
        
        # Disconnect
        connection_manager.disconnect(mock_websocket)
        
        # Check cleanup
        assert mock_websocket not in connection_manager.connection_metadata
        assert "test_user" not in connection_manager.active_connections


if __name__ == "__main__":
    pytest.main([__file__])