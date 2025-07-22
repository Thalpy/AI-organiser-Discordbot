"""Mock WebSocket manager for testing"""

from typing import Dict, Any, List
from fastapi import WebSocket

class MockConnectionManager:
    """Mock connection manager"""
    
    def __init__(self):
        self.connections = {}
    
    async def connect(self, websocket: WebSocket, user_id: str, metadata: Dict[str, Any] = None):
        """Mock connect"""
        self.connections[user_id] = websocket
    
    def disconnect(self, websocket: WebSocket):
        """Mock disconnect"""
        pass
    
    def get_connected_users(self) -> List[str]:
        """Mock get connected users"""
        return list(self.connections.keys())

class MockWebSocketHandler:
    """Mock WebSocket handler"""
    
    async def handle_message(self, websocket: WebSocket, message: Dict[str, Any]):
        """Mock handle message"""
        pass

class MockPresenceManager:
    """Mock presence manager"""
    
    async def update_user_presence(self, user_id: str, status: str):
        """Mock update presence"""
        pass
    
    async def set_user_offline(self, user_id: str):
        """Mock set offline"""
        pass

# Mock instances
connection_manager = MockConnectionManager()
websocket_handler = MockWebSocketHandler()
presence_manager = MockPresenceManager()

# Mock notification functions
async def notify_task_update(task_id: int, update_data: Dict[str, Any], user_ids: List[str]):
    """Mock notify task update"""
    pass

async def notify_task_assignment(task_id: int, assigned_users: List[str], assigned_by: str):
    """Mock notify task assignment"""
    pass

async def notify_new_message(task_id: int, message_data: Dict[str, Any], user_ids: List[str]):
    """Mock notify new message"""
    pass