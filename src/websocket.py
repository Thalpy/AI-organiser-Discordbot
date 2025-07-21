"""
WebSocket manager for real-time updates in Discord Task Management Bot
Handles WebSocket connections, message broadcasting, and real-time synchronization
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import WebSocket, WebSocketDisconnect

from utils.logging_config import get_logger

from .database import get_database_manager

logger = get_logger(__name__)


class WebSocketManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self):
        # Active connections: {user_id: [WebSocket, ...]}
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # Task subscriptions: {task_id: [user_id, ...]}
        self.task_subscriptions: Dict[int, List[str]] = {}
        self.db = None
    
    async def initialize(self):
        """Initialize the WebSocket manager"""
        self.db = await get_database_manager()
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        
        self.active_connections[user_id].append(websocket)
        
        logger.info(f"WebSocket connected for user {user_id}")
        
        # Send connection confirmation
        await self.send_personal_message(
            {
                "type": "connection_established",
                "user_id": user_id,
                "timestamp": str(datetime.now())
            },
            user_id
        )
    
    async def disconnect(self, websocket: WebSocket, user_id: str):
        """Handle WebSocket disconnection"""
        if user_id in self.active_connections:
            try:
                self.active_connections[user_id].remove(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
            except ValueError:
                pass  # WebSocket not in list
        
        # Remove from task subscriptions
        for task_id, subscribers in self.task_subscriptions.items():
            if user_id in subscribers:
                subscribers.remove(user_id)
        
        logger.info(f"WebSocket disconnected for user {user_id}")
    
    async def send_personal_message(self, message: Dict[str, Any], user_id: str):
        """Send message to a specific user"""
        if user_id in self.active_connections:
            disconnected_sockets = []
            
            for websocket in self.active_connections[user_id]:
                try:
                    await websocket.send_text(json.dumps(message))
                except Exception as e:
                    logger.error(f"Failed to send message to user {user_id}: {e}")
                    disconnected_sockets.append(websocket)
            
            # Clean up disconnected sockets
            for socket in disconnected_sockets:
                try:
                    self.active_connections[user_id].remove(socket)
                except ValueError:
                    pass
            
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
    
    async def broadcast_to_users(self, message: Dict[str, Any], user_ids: List[str]):
        """Broadcast message to multiple users"""
        for user_id in user_ids:
            await self.send_personal_message(message, user_id)
    
    async def broadcast_to_all(self, message: Dict[str, Any]):
        """Broadcast message to all connected users"""
        user_ids = list(self.active_connections.keys())
        await self.broadcast_to_users(message, user_ids)
    
    async def subscribe_to_task(self, user_id: str, task_id: int):
        """Subscribe user to task updates"""
        if task_id not in self.task_subscriptions:
            self.task_subscriptions[task_id] = []
        
        if user_id not in self.task_subscriptions[task_id]:
            self.task_subscriptions[task_id].append(user_id)
        
        logger.debug(f"User {user_id} subscribed to task {task_id}")
    
    async def unsubscribe_from_task(self, user_id: str, task_id: int):
        """Unsubscribe user from task updates"""
        if task_id in self.task_subscriptions:
            try:
                self.task_subscriptions[task_id].remove(user_id)
                if not self.task_subscriptions[task_id]:
                    del self.task_subscriptions[task_id]
            except ValueError:
                pass
        
        logger.debug(f"User {user_id} unsubscribed from task {task_id}")
    
    async def broadcast_to_task_users(self, message: Dict[str, Any], task_id: int):
        """Broadcast message to all users subscribed to a task"""
        if task_id in self.task_subscriptions:
            await self.broadcast_to_users(message, self.task_subscriptions[task_id])
        
        # Also send to task creator and assigned users
        if self.db:
            try:
                # Get task details to find relevant users
                query = """
                    SELECT t.created_by_user_id,
                           array_agg(DISTINCT ta.assigned_user_id) FILTER (WHERE ta.assigned_user_id IS NOT NULL) as assigned_users
                    FROM tasks t
                    LEFT JOIN task_assignments ta ON t.id = ta.task_id
                    WHERE t.id = $1
                    GROUP BY t.id, t.created_by_user_id
                """
                
                result = await self.db.execute_query(query, (task_id,), fetch_one=True)
                
                if result:
                    relevant_users = [result['created_by_user_id']]
                    if result['assigned_users']:
                        relevant_users.extend(result['assigned_users'])
                    
                    # Remove duplicates
                    relevant_users = list(set(relevant_users))
                    
                    await self.broadcast_to_users(message, relevant_users)
                    
            except Exception as e:
                logger.error(f"Failed to get task users for broadcasting: {e}")
    
    async def handle_message(self, data: str, user_id: str):
        """Handle incoming WebSocket message"""
        try:
            message = json.loads(data)
            message_type = message.get("type")
            
            if message_type == "subscribe_task":
                task_id = message.get("task_id")
                if task_id:
                    await self.subscribe_to_task(user_id, task_id)
                    await self.send_personal_message(
                        {"type": "subscribed", "task_id": task_id},
                        user_id
                    )
            
            elif message_type == "unsubscribe_task":
                task_id = message.get("task_id")
                if task_id:
                    await self.unsubscribe_from_task(user_id, task_id)
                    await self.send_personal_message(
                        {"type": "unsubscribed", "task_id": task_id},
                        user_id
                    )
            
            elif message_type == "ping":
                await self.send_personal_message(
                    {"type": "pong", "timestamp": str(datetime.now())},
                    user_id
                )
            
            elif message_type == "typing":
                # Handle typing indicators for task messages
                task_id = message.get("task_id")
                if task_id:
                    typing_message = {
                        "type": "user_typing",
                        "task_id": task_id,
                        "user_id": user_id,
                        "timestamp": str(datetime.now())
                    }
                    await self.broadcast_to_task_users(typing_message, task_id)
            
            else:
                logger.warning(f"Unknown WebSocket message type: {message_type}")
                
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in WebSocket message from user {user_id}")
            await self.send_personal_message(
                {"type": "error", "message": "Invalid JSON format"},
                user_id
            )
        except Exception as e:
            logger.error(f"Error handling WebSocket message from user {user_id}: {e}")
            await self.send_personal_message(
                {"type": "error", "message": "Message processing failed"},
                user_id
            )
    
    async def send_notification(self, user_id: str, notification: Dict[str, Any]):
        """Send a notification through WebSocket"""
        message = {
            "type": "notification",
            "notification": notification,
            "timestamp": str(datetime.now())
        }
        
        await self.send_personal_message(message, user_id)
    
    async def send_task_update(self, task_data: Dict[str, Any]):
        """Send task update to relevant users"""
        task_id = task_data.get("id")
        if not task_id:
            return
        
        message = {
            "type": "task_updated",
            "task": task_data,
            "timestamp": str(datetime.now())
        }
        
        await self.broadcast_to_task_users(message, task_id)
    
    async def send_task_assignment(self, task_data: Dict[str, Any], assigned_users: List[str]):
        """Send task assignment notification"""
        message = {
            "type": "task_assigned",
            "task": task_data,
            "timestamp": str(datetime.now())
        }
        
        await self.broadcast_to_users(message, assigned_users)
    
    async def send_task_message(self, message_data: Dict[str, Any]):
        """Send new task message to relevant users"""
        task_id = message_data.get("task_id")
        if not task_id:
            return
        
        message = {
            "type": "task_message",
            "message": message_data,
            "timestamp": str(datetime.now())
        }
        
        await self.broadcast_to_task_users(message, task_id)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get WebSocket connection statistics"""
        total_connections = sum(len(sockets) for sockets in self.active_connections.values())
        
        return {
            "total_users": len(self.active_connections),
            "total_connections": total_connections,
            "task_subscriptions": len(self.task_subscriptions),
            "active_users": list(self.active_connections.keys())
        }


# Global WebSocket manager instance
websocket_manager: Optional[WebSocketManager] = None


def get_websocket_manager() -> WebSocketManager:
    """Get the global WebSocket manager instance"""
    global websocket_manager
    if websocket_manager is None:
        websocket_manager = WebSocketManager()
    return websocket_manager