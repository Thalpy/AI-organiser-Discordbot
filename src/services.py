"""
Service layer for Discord Task Management Bot
Implements business logic for collaborative task management
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from utils.logging_config import get_logger, get_user_action_logger, PerformanceMonitor

from .database import get_database_manager
from .models import (
    Task,
    TaskAssignment,
    TaskCreateRequest,
    TaskMessage,
    TaskStatus,
    TaskTemplate,
    UserActivity,
)

logger = get_logger(__name__)
user_logger = get_user_action_logger()


class TaskManagementException(Exception):
    """Custom exception for task management operations"""
    
    def __init__(self, message: str, error_code: str = "TASK_ERROR", details: Dict[str, Any] = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)


class TaskService:
    """Service for collaborative task management"""
    
    def __init__(self):
        self.db = None
        self.notification_service = None
    
    async def initialize(self, notification_service=None):
        """Initialize the task service"""
        self.db = await get_database_manager()
        self.notification_service = notification_service
    
    async def create_task(self, user_id: str, task_data: TaskCreateRequest) -> Dict[str, Any]:
        """Create a new task with optional collaboration features"""
        with PerformanceMonitor("create_task"):
            try:
                # Prepare task data
                task_dict = {
                    'description': task_data.description,
                    'created_by_user_id': user_id,
                    'priority': task_data.priority.value,
                    'due_time': task_data.due_time,
                    'duration_minutes': task_data.duration_minutes,
                    'location': task_data.location,
                    'is_collaborative': task_data.is_collaborative or len(task_data.assigned_users) > 0,
                    'template_id': task_data.template_id,
                    'assigned_users': task_data.assigned_users
                }
                
                # Create the task
                task_id = await self.db.create_collaborative_task(task_dict)
                
                if not task_id:
                    raise TaskManagementException("Failed to create task", "CREATION_FAILED")
                
                # Cache the task
                await self.db.cache_set(f"task:{task_id}", task_dict, expire=3600)
                
                # Log user activity
                await self.db.log_user_activity({
                    'user_id': user_id,
                    'activity_type': 'task_created',
                    'activity_data': {'task_id': task_id, 'collaborative': task_dict['is_collaborative']},
                    'source': 'api'
                })
                
                # Send notifications for collaborative tasks
                if task_data.assigned_users and self.notification_service:
                    await self.notification_service.notify_task_assignment(
                        task_id, task_data.assigned_users, user_id
                    )
                
                # Get the complete task data
                task = await self.get_task_by_id(task_id, user_id)
                
                user_logger.log_task_action(user_id, "created", task_id, f"Collaborative: {task_dict['is_collaborative']}")
                
                return task
                
            except Exception as e:
                logger.error(f"Failed to create task for user {user_id}: {e}")
                if isinstance(e, TaskManagementException):
                    raise
                raise TaskManagementException("Task creation failed", "CREATION_ERROR")
    
    async def get_task_by_id(self, task_id: int, user_id: str) -> Dict[str, Any]:
        """Get a task by ID with user permission check"""
        with PerformanceMonitor("get_task_by_id"):
            # Check cache first
            cached_task = await self.db.cache_get(f"task:{task_id}")
            if cached_task:
                return cached_task
            
            # Get from database
            query = """
                SELECT t.*, 
                       array_agg(DISTINCT ta.assigned_user_id) FILTER (WHERE ta.assigned_user_id IS NOT NULL) as assigned_users,
                       array_agg(DISTINCT ta.status) FILTER (WHERE ta.status IS NOT NULL) as assignment_statuses
                FROM tasks t
                LEFT JOIN task_assignments ta ON t.id = ta.task_id
                WHERE t.id = $1 
                AND (t.created_by_user_id = $2 OR ta.assigned_user_id = $2 OR t.is_collaborative = true)
                GROUP BY t.id
            """
            
            result = await self.db.execute_query(query, (task_id, user_id), fetch_one=True)
            
            if not result:
                raise TaskManagementException("Task not found or access denied", "TASK_NOT_FOUND")
            
            # Cache the result
            await self.db.cache_set(f"task:{task_id}", dict(result), expire=1800)
            
            return dict(result)
    
    async def assign_task_to_users(
        self,
        task_id: int,
        user_ids: List[str],
        assigned_by: str,
        message: Optional[str] = None
    ) -> bool:
        """Assign task to multiple users"""
        with PerformanceMonitor("assign_task_to_users"):
            try:
                # Verify task exists and user has permission
                task = await self.get_task_by_id(task_id, assigned_by)
                
                if task['status'] != TaskStatus.PENDING.value:
                    raise TaskManagementException("Cannot assign completed or cancelled task", "INVALID_STATUS")
                
                # Assign users
                success = await self.db.assign_task_to_users(task_id, user_ids, assigned_by)
                
                if not success:
                    raise TaskManagementException("Failed to assign users to task", "ASSIGNMENT_FAILED")
                
                # Clear cache
                await self.db.cache_delete(f"task:{task_id}")
                
                # Add system message if provided
                if message:
                    await self.add_task_message(
                        task_id, assigned_by, f"Task assigned to users: {', '.join(user_ids)}. {message}",
                        message_type='system'
                    )
                
                # Log activity
                await self.db.log_user_activity({
                    'user_id': assigned_by,
                    'activity_type': 'task_assigned',
                    'activity_data': {'task_id': task_id, 'assigned_users': user_ids},
                    'source': 'api'
                })
                
                # Send notifications
                if self.notification_service:
                    await self.notification_service.notify_task_assignment(task_id, user_ids, assigned_by)
                
                user_logger.log_task_action(assigned_by, "assigned", task_id, f"Users: {', '.join(user_ids)}")
                
                return True
                
            except Exception as e:
                logger.error(f"Failed to assign task {task_id}: {e}")
                if isinstance(e, TaskManagementException):
                    raise
                raise TaskManagementException("Task assignment failed", "ASSIGNMENT_ERROR")
    
    async def get_collaborative_tasks(self, user_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get tasks where user is assigned or collaborating"""
        with PerformanceMonitor("get_collaborative_tasks"):
            # Check cache first
            cache_key = f"user_tasks:{user_id}:{status or 'all'}"
            cached_tasks = await self.db.cache_get(cache_key)
            if cached_tasks:
                return cached_tasks
            
            tasks = await self.db.get_collaborative_tasks(user_id)
            
            # Filter by status if provided
            if status:
                tasks = [task for task in tasks if task.get('status') == status]
            
            # Cache the results
            await self.db.cache_set(cache_key, tasks, expire=600)  # 10 minutes
            
            return tasks
    
    async def update_task_progress(
        self,
        task_id: int,
        user_id: str,
        progress: int,
        notes: Optional[str] = None
    ) -> bool:
        """Update task completion progress"""
        with PerformanceMonitor("update_task_progress"):
            try:
                # Verify user has access to task
                task = await self.get_task_by_id(task_id, user_id)
                
                if progress < 0 or progress > 100:
                    raise TaskManagementException("Progress must be between 0 and 100", "INVALID_PROGRESS")
                
                # Update progress
                success = await self.db.update_task_progress(task_id, user_id, progress, notes)
                
                if not success:
                    raise TaskManagementException("Failed to update task progress", "UPDATE_FAILED")
                
                # Clear cache
                await self.db.cache_delete(f"task:{task_id}")
                
                # Add progress message
                progress_message = f"Progress updated to {progress}%"
                if notes:
                    progress_message += f": {notes}"
                
                await self.add_task_message(task_id, user_id, progress_message, message_type='status_update')
                
                # Log activity
                await self.db.log_user_activity({
                    'user_id': user_id,
                    'activity_type': 'task_progress_updated',
                    'activity_data': {'task_id': task_id, 'progress': progress},
                    'source': 'api'
                })
                
                user_logger.log_task_action(user_id, "progress_updated", task_id, f"Progress: {progress}%")
                
                return True
                
            except Exception as e:
                logger.error(f"Failed to update task progress: {e}")
                if isinstance(e, TaskManagementException):
                    raise
                raise TaskManagementException("Progress update failed", "UPDATE_ERROR")
    
    async def add_task_message(
        self,
        task_id: int,
        user_id: str,
        message: str,
        message_type: str = 'comment',
        parent_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Add message to task collaboration thread"""
        with PerformanceMonitor("add_task_message"):
            try:
                # Verify user has access to task
                await self.get_task_by_id(task_id, user_id)
                
                # Add message
                message_data = await self.db.add_task_message(
                    task_id, user_id, message, message_type, parent_id
                )
                
                if not message_data:
                    raise TaskManagementException("Failed to add message", "MESSAGE_FAILED")
                
                # Clear task cache to refresh messages
                await self.db.cache_delete(f"task_messages:{task_id}")
                
                # Log activity
                await self.db.log_user_activity({
                    'user_id': user_id,
                    'activity_type': 'task_message_added',
                    'activity_data': {'task_id': task_id, 'message_type': message_type},
                    'source': 'api'
                })
                
                user_logger.log_task_action(user_id, "message_added", task_id, f"Type: {message_type}")
                
                return message_data
                
            except Exception as e:
                logger.error(f"Failed to add task message: {e}")
                if isinstance(e, TaskManagementException):
                    raise
                raise TaskManagementException("Message addition failed", "MESSAGE_ERROR")
    
    async def get_task_messages(self, task_id: int, user_id: str) -> List[Dict[str, Any]]:
        """Get all messages for a task"""
        with PerformanceMonitor("get_task_messages"):
            # Verify user has access to task
            await self.get_task_by_id(task_id, user_id)
            
            # Check cache first
            cache_key = f"task_messages:{task_id}"
            cached_messages = await self.db.cache_get(cache_key)
            if cached_messages:
                return cached_messages
            
            messages = await self.db.get_task_messages(task_id)
            
            # Cache the results
            await self.db.cache_set(cache_key, messages, expire=300)  # 5 minutes
            
            return messages
    
    async def start_task(self, task_id: int, user_id: str) -> bool:
        """Start working on a task"""
        with PerformanceMonitor("start_task"):
            try:
                # Get task and verify access
                task = await self.get_task_by_id(task_id, user_id)
                
                if task['status'] != TaskStatus.PENDING.value:
                    raise TaskManagementException("Task is not in pending status", "INVALID_STATUS")
                
                # Update task status
                queries = [
                    (
                        "UPDATE tasks SET status = $1, start_time = $2 WHERE id = $3",
                        (TaskStatus.IN_PROGRESS.value, datetime.now(), task_id)
                    )
                ]
                
                # Update assignment status if user is assigned
                queries.append((
                    """
                    UPDATE task_assignments 
                    SET status = $1 
                    WHERE task_id = $2 AND assigned_user_id = $3
                    """,
                    ('accepted', task_id, user_id)
                ))
                
                success = await self.db.execute_transaction(queries)
                
                if not success:
                    raise TaskManagementException("Failed to start task", "START_FAILED")
                
                # Clear cache
                await self.db.cache_delete(f"task:{task_id}")
                
                # Add system message
                await self.add_task_message(
                    task_id, user_id, "Task started", message_type='status_update'
                )
                
                # Log activity
                await self.db.log_user_activity({
                    'user_id': user_id,
                    'activity_type': 'task_started',
                    'activity_data': {'task_id': task_id},
                    'source': 'api'
                })
                
                user_logger.log_task_action(user_id, "started", task_id)
                
                return True
                
            except Exception as e:
                logger.error(f"Failed to start task {task_id}: {e}")
                if isinstance(e, TaskManagementException):
                    raise
                raise TaskManagementException("Task start failed", "START_ERROR")
    
    async def complete_task(self, task_id: int, user_id: str, notes: Optional[str] = None) -> bool:
        """Complete a task"""
        with PerformanceMonitor("complete_task"):
            try:
                # Get task and verify access
                task = await self.get_task_by_id(task_id, user_id)
                
                if task['status'] not in [TaskStatus.PENDING.value, TaskStatus.IN_PROGRESS.value]:
                    raise TaskManagementException("Task cannot be completed", "INVALID_STATUS")
                
                # Update task status
                queries = [
                    (
                        "UPDATE tasks SET status = $1, stop_time = $2, completion_percentage = 100 WHERE id = $3",
                        (TaskStatus.COMPLETED.value, datetime.now(), task_id)
                    )
                ]
                
                # Update assignment status
                queries.append((
                    """
                    UPDATE task_assignments 
                    SET status = $1, completed_at = $2, completion_notes = $3
                    WHERE task_id = $4 AND assigned_user_id = $5
                    """,
                    ('completed', datetime.now(), notes, task_id, user_id)
                ))
                
                success = await self.db.execute_transaction(queries)
                
                if not success:
                    raise TaskManagementException("Failed to complete task", "COMPLETION_FAILED")
                
                # Clear cache
                await self.db.cache_delete(f"task:{task_id}")
                
                # Add completion message
                completion_message = "Task completed"
                if notes:
                    completion_message += f": {notes}"
                
                await self.add_task_message(
                    task_id, user_id, completion_message, message_type='status_update'
                )
                
                # Log activity
                await self.db.log_user_activity({
                    'user_id': user_id,
                    'activity_type': 'task_completed',
                    'activity_data': {'task_id': task_id},
                    'source': 'api'
                })
                
                user_logger.log_task_action(user_id, "completed", task_id)
                
                return True
                
            except Exception as e:
                logger.error(f"Failed to complete task {task_id}: {e}")
                if isinstance(e, TaskManagementException):
                    raise
                raise TaskManagementException("Task completion failed", "COMPLETION_ERROR")


class TemplateService:
    """Service for task template management"""
    
    def __init__(self):
        self.db = None
    
    async def initialize(self):
        """Initialize the template service"""
        self.db = await get_database_manager()
    
    async def create_template(self, user_id: str, template_data: Dict[str, Any]) -> int:
        """Create a new task template"""
        with PerformanceMonitor("create_template"):
            try:
                template_data['created_by_user_id'] = user_id
                template_id = await self.db.create_task_template(template_data)
                
                if not template_id:
                    raise TaskManagementException("Failed to create template", "TEMPLATE_CREATION_FAILED")
                
                # Log activity
                await self.db.log_user_activity({
                    'user_id': user_id,
                    'activity_type': 'template_created',
                    'activity_data': {'template_id': template_id, 'name': template_data['name']},
                    'source': 'api'
                })
                
                user_logger.log_task_action(user_id, "template_created", template_id, template_data['name'])
                
                return template_id
                
            except Exception as e:
                logger.error(f"Failed to create template: {e}")
                if isinstance(e, TaskManagementException):
                    raise
                raise TaskManagementException("Template creation failed", "TEMPLATE_ERROR")
    
    async def get_user_templates(self, user_id: str, include_shared: bool = True) -> List[Dict[str, Any]]:
        """Get templates available to a user"""
        with PerformanceMonitor("get_user_templates"):
            # Check cache first
            cache_key = f"user_templates:{user_id}:{include_shared}"
            cached_templates = await self.db.cache_get(cache_key)
            if cached_templates:
                return cached_templates
            
            templates = await self.db.get_user_templates(user_id, include_shared)
            
            # Cache the results
            await self.db.cache_set(cache_key, templates, expire=1800)  # 30 minutes
            
            return templates


# Global service instances
task_service: Optional[TaskService] = None
template_service: Optional[TemplateService] = None


async def get_task_service() -> TaskService:
    """Get the global task service instance"""
    global task_service
    if task_service is None:
        task_service = TaskService()
        await task_service.initialize()
    return task_service


async def get_template_service() -> TemplateService:
    """Get the global template service instance"""
    global template_service
    if template_service is None:
        template_service = TemplateService()
        await template_service.initialize()
    return template_service