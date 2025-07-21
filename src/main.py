"""
FastAPI web application for Discord Task Management Bot
Provides REST API and WebSocket endpoints for the web interface
"""

import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from pydantic import BaseModel

from utils.logging_config import get_logger, get_user_action_logger

from .auth import AuthService, get_current_user
from .database import close_database, initialize_database
from .models import (
    AnalyticsResponse,
    ErrorResponse,
    TaskAssignRequest,
    TaskCreateRequest,
    TaskListResponse,
    TaskMessageRequest,
    TaskResponse,
    TaskUpdateRequest,
)
from .services import get_task_service, get_template_service
from .websocket import WebSocketManager

logger = get_logger(__name__)
user_logger = get_user_action_logger()

# Security
security = HTTPBearer()

# WebSocket manager
websocket_manager = WebSocketManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Discord Task Management Bot API")
    
    # Initialize database
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'user': os.getenv('DB_USER', 'taskbot'),
        'password': os.getenv('DB_PASSWORD', 'changeme'),
        'database': os.getenv('DB_NAME', 'taskdb')
    }
    
    redis_config = {
        'host': os.getenv('REDIS_HOST', 'localhost'),
        'port': int(os.getenv('REDIS_PORT', 6379)),
        'password': os.getenv('REDIS_PASSWORD')
    }
    
    await initialize_database(db_config, redis_config)
    
    # Initialize services
    await get_task_service()
    await get_template_service()
    
    logger.info("API startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down API")
    await close_database()
    logger.info("API shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Discord Task Management Bot API",
    description="REST API for collaborative task management with Discord integration",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(','),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0"
    }


# Task endpoints
@app.get("/api/v1/tasks", response_model=TaskListResponse)
async def get_tasks(
    status: Optional[str] = None,
    limit: int = 25,
    offset: int = 0,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get user tasks with filtering and pagination"""
    try:
        task_service = await get_task_service()
        
        if status:
            tasks = await task_service.get_collaborative_tasks(current_user['user_id'], status)
        else:
            tasks = await task_service.get_collaborative_tasks(current_user['user_id'])
        
        # Apply pagination
        total = len(tasks)
        tasks = tasks[offset:offset + limit]
        
        user_logger.log_web_action(
            current_user['user_id'],
            'get_tasks',
            '/api/v1/tasks',
            current_user.get('ip_address')
        )
        
        return TaskListResponse(
            tasks=tasks,
            total=total,
            page=(offset // limit) + 1,
            per_page=limit
        )
        
    except Exception as e:
        logger.error(f"Failed to get tasks for user {current_user['user_id']}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tasks"
        )


@app.post("/api/v1/tasks", response_model=TaskResponse)
async def create_task(
    task_data: TaskCreateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Create a new task"""
    try:
        task_service = await get_task_service()
        task = await task_service.create_task(current_user['user_id'], task_data)
        
        # Send real-time update
        await websocket_manager.send_personal_message(
            {"type": "task_created", "task": task},
            current_user['user_id']
        )
        
        # Notify assigned users
        if task_data.assigned_users:
            for user_id in task_data.assigned_users:
                await websocket_manager.send_personal_message(
                    {"type": "task_assigned", "task": task},
                    user_id
                )
        
        user_logger.log_web_action(
            current_user['user_id'],
            'create_task',
            '/api/v1/tasks',
            current_user.get('ip_address')
        )
        
        return TaskResponse(task=task)
        
    except Exception as e:
        logger.error(f"Failed to create task: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.get("/api/v1/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get a specific task"""
    try:
        task_service = await get_task_service()
        task = await task_service.get_task_by_id(task_id, current_user['user_id'])
        messages = await task_service.get_task_messages(task_id, current_user['user_id'])
        
        return TaskResponse(task=task, messages=messages)
        
    except Exception as e:
        logger.error(f"Failed to get task {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )


@app.put("/api/v1/tasks/{task_id}")
async def update_task(
    task_id: int,
    task_data: TaskUpdateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update a task"""
    try:
        task_service = await get_task_service()
        
        # Handle different update types
        if task_data.status == "in_progress":
            success = await task_service.start_task(task_id, current_user['user_id'])
        elif task_data.status == "completed":
            success = await task_service.complete_task(
                task_id, 
                current_user['user_id'], 
                task_data.collaboration_notes
            )
        elif task_data.completion_percentage is not None:
            success = await task_service.update_task_progress(
                task_id,
                current_user['user_id'],
                task_data.completion_percentage,
                task_data.collaboration_notes
            )
        else:
            # Generic update - would need to implement in service
            success = True
        
        if success:
            # Get updated task
            task = await task_service.get_task_by_id(task_id, current_user['user_id'])
            
            # Send real-time update
            await websocket_manager.broadcast_to_task_users(
                {"type": "task_updated", "task": task},
                task_id
            )
            
            return {"success": True, "task": task}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update task"
            )
            
    except Exception as e:
        logger.error(f"Failed to update task {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.post("/api/v1/tasks/{task_id}/assign")
async def assign_task(
    task_id: int,
    assignment_data: TaskAssignRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Assign task to multiple users"""
    try:
        task_service = await get_task_service()
        success = await task_service.assign_task_to_users(
            task_id,
            assignment_data.user_ids,
            current_user['user_id'],
            assignment_data.message
        )
        
        if success:
            # Send real-time updates
            task = await task_service.get_task_by_id(task_id, current_user['user_id'])
            
            for user_id in assignment_data.user_ids:
                await websocket_manager.send_personal_message(
                    {"type": "task_assigned", "task": task},
                    user_id
                )
            
            return {
                "success": True,
                "assigned_users": assignment_data.user_ids,
                "task": task
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to assign task"
            )
            
    except Exception as e:
        logger.error(f"Failed to assign task {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.post("/api/v1/tasks/{task_id}/messages")
async def add_task_message(
    task_id: int,
    message_data: TaskMessageRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Add message to task collaboration thread"""
    try:
        task_service = await get_task_service()
        message = await task_service.add_task_message(
            task_id,
            current_user['user_id'],
            message_data.message,
            message_data.message_type.value,
            message_data.parent_message_id
        )
        
        # Send real-time update
        await websocket_manager.broadcast_to_task_users(
            {"type": "task_message", "message": message},
            task_id
        )
        
        return message
        
    except Exception as e:
        logger.error(f"Failed to add message to task {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.get("/api/v1/tasks/{task_id}/messages")
async def get_task_messages(
    task_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get messages for a task"""
    try:
        task_service = await get_task_service()
        messages = await task_service.get_task_messages(task_id, current_user['user_id'])
        
        return {"messages": messages}
        
    except Exception as e:
        logger.error(f"Failed to get messages for task {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found or access denied"
        )


# Template endpoints
@app.get("/api/v1/templates")
async def get_templates(
    include_shared: bool = True,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get user templates"""
    try:
        template_service = await get_template_service()
        templates = await template_service.get_user_templates(
            current_user['user_id'], 
            include_shared
        )
        
        return {"templates": templates}
        
    except Exception as e:
        logger.error(f"Failed to get templates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve templates"
        )


@app.post("/api/v1/templates")
async def create_template(
    template_data: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Create a task template"""
    try:
        template_service = await get_template_service()
        template_id = await template_service.create_template(
            current_user['user_id'],
            template_data
        )
        
        return {"template_id": template_id, "success": True}
        
    except Exception as e:
        logger.error(f"Failed to create template: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# Analytics endpoints
@app.get("/api/v1/analytics", response_model=AnalyticsResponse)
async def get_analytics(
    timeframe: str = "week",
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get user analytics"""
    try:
        # This would use an analytics service
        # For now, returning mock data
        analytics_data = {
            "user_id": current_user['user_id'],
            "timeframe": timeframe,
            "tasks_completed": 15,
            "total_tasks": 20,
            "completion_rate": 75.0,
            "avg_duration": 25.5,
            "performance_score": 78
        }
        
        recommendations = [
            {
                "title": "Improve Task Completion Rate",
                "description": "Focus on completing pending tasks",
                "priority": "high"
            }
        ]
        
        return AnalyticsResponse(
            analytics=analytics_data,
            recommendations=recommendations
        )
        
    except Exception as e:
        logger.error(f"Failed to get analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve analytics"
        )


# WebSocket endpoint
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for real-time updates"""
    await websocket_manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming WebSocket messages
            await websocket_manager.handle_message(data, user_id)
    except WebSocketDisconnect:
        await websocket_manager.disconnect(websocket, user_id)
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        await websocket_manager.disconnect(websocket, user_id)


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    return ErrorResponse(
        error={
            "code": exc.status_code,
            "message": exc.detail
        },
        message=exc.detail
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}")
    return ErrorResponse(
        error={
            "code": 500,
            "message": "Internal server error"
        },
        message="An unexpected error occurred"
    )


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=os.getenv("WEB_HOST", "localhost"),
        port=int(os.getenv("WEB_PORT", 8000)),
        reload=os.getenv("ENVIRONMENT") == "development",
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )