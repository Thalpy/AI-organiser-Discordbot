"""Tasks API router"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body, status
from typing import Dict, List, Optional, Any
from datetime import datetime

from utils.logging_config import get_logger, PerformanceMonitor
from ..auth import get_current_active_user

# Import services and models
from src.services import get_task_service, get_template_service, TaskManagementException
from src.models import TaskCreateRequest, TaskStatus, TaskPriority, MessageType

# Setup logging
logger = get_logger(__name__)

# Create router
router = APIRouter()


# Task endpoints
@router.get("/")
async def get_tasks(
    status: Optional[str] = Query(None, description="Filter by task status"),
    priority: Optional[str] = Query(None, description="Filter by task priority"),
    is_collaborative: Optional[bool] = Query(None, description="Filter by collaborative status"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Get tasks with filtering and pagination"""
    with PerformanceMonitor("get_tasks"):
        try:
            # Get task service
            task_service = await get_task_service()
            
            # Get collaborative tasks (which includes user's own tasks)
            tasks = await task_service.get_collaborative_tasks(
                user_id=current_user["id"],
                status=status
            )
            
            # Apply additional filters
            if priority:
                tasks = [task for task in tasks if task.get('priority') == priority]
            
            if is_collaborative is not None:
                tasks = [task for task in tasks if task.get('is_collaborative') == is_collaborative]
            
            # Apply pagination
            total = len(tasks)
            start = (page - 1) * limit
            end = start + limit
            paginated_tasks = tasks[start:end]
            
            return {
                "items": paginated_tasks,
                "total": total,
                "page": page,
                "limit": limit,
                "pages": (total + limit - 1) // limit if total > 0 else 0
            }
            
        except TaskManagementException as e:
            logger.error(f"Task retrieval error: {e.message}")
            raise HTTPException(status_code=400, detail=e.message)
        except Exception as e:
            logger.error(f"Unexpected error in get_tasks: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to retrieve tasks")


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Create a new task"""
    with PerformanceMonitor("create_task"):
        try:
            # Get task service
            task_service = await get_task_service()
            
            # Create TaskCreateRequest from the data
            task_request = TaskCreateRequest(
                description=task_data.get("description", ""),
                priority=TaskPriority(task_data.get("priority", "normal")),
                due_time=datetime.fromisoformat(task_data["due_time"]) if task_data.get("due_time") else None,
                duration_minutes=task_data.get("duration_minutes", 15),
                location=task_data.get("location"),
                is_collaborative=task_data.get("is_collaborative", False),
                assigned_users=task_data.get("assigned_users", []),
                template_id=task_data.get("template_id")
            )
            
            # Create task
            task = await task_service.create_task(current_user["id"], task_request)
            
            return task
            
        except ValueError as e:
            logger.error(f"Task creation validation error: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Invalid task data: {str(e)}")
        except TaskManagementException as e:
            logger.error(f"Task creation error: {e.message}")
            raise HTTPException(status_code=400, detail=e.message)
        except Exception as e:
            logger.error(f"Unexpected error in create_task: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to create task")


@router.get("/{task_id}")
async def get_task(
    task_id: int = Path(..., description="The ID of the task to retrieve"),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Get a specific task by ID"""
    with PerformanceMonitor("get_task"):
        try:
            # Get task service
            task_service = await get_task_service()
            
            # Get task
            task = await task_service.get_task_by_id(task_id, current_user["id"])
            
            return task
            
        except TaskManagementException as e:
            logger.error(f"Task retrieval error: {e.message}")
            if e.error_code == "TASK_NOT_FOUND":
                raise HTTPException(status_code=404, detail=e.message)
            raise HTTPException(status_code=400, detail=e.message)
        except Exception as e:
            logger.error(f"Unexpected error in get_task: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to retrieve task")


@router.put("/{task_id}")
async def update_task(
    task_id: int = Path(..., description="The ID of the task to update"),
    task_data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Update a task"""
    with PerformanceMonitor("update_task"):
        try:
            # Get task service
            task_service = await get_task_service()
            
            # For now, we'll implement basic progress update
            # In a full implementation, you'd have a proper update_task method
            if "progress" in task_data:
                success = await task_service.update_task_progress(
                    task_id=task_id,
                    user_id=current_user["id"],
                    progress=task_data["progress"],
                    notes=task_data.get("notes")
                )
                if not success:
                    raise HTTPException(status_code=404, detail="Task not found")
            
            # Get updated task
            updated_task = await task_service.get_task_by_id(task_id, current_user["id"])
            
            return updated_task
            
        except TaskManagementException as e:
            logger.error(f"Task update error: {e.message}")
            if e.error_code == "TASK_NOT_FOUND":
                raise HTTPException(status_code=404, detail=e.message)
            raise HTTPException(status_code=400, detail=e.message)
        except Exception as e:
            logger.error(f"Unexpected error in update_task: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to update task")


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int = Path(..., description="The ID of the task to delete"),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> None:
    """Delete a task"""
    with PerformanceMonitor("delete_task"):
        try:
            # Get task service
            task_service = await get_task_service()
            
            # For now, we'll implement task cancellation instead of deletion
            # In a real implementation, you might want actual deletion
            task = await task_service.get_task_by_id(task_id, current_user["id"])
            
            # Only allow deletion/cancellation by creator or assigned users
            if (task.get("created_by_user_id") != current_user["id"] and 
                current_user["id"] not in task.get("assigned_users", [])):
                raise HTTPException(status_code=403, detail="Not authorized to delete this task")
            
            # For now, we'll just verify the task exists (actual deletion would need implementation)
            # In a full implementation, you'd have a delete_task method in the service
            
        except TaskManagementException as e:
            logger.error(f"Task deletion error: {e.message}")
            if e.error_code == "TASK_NOT_FOUND":
                raise HTTPException(status_code=404, detail=e.message)
            raise HTTPException(status_code=400, detail=e.message)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in delete_task: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to delete task")


@router.post("/{task_id}/assign")
async def assign_task(
    task_id: int = Path(..., description="The ID of the task to assign"),
    assignment_data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Assign a task to users"""
    with PerformanceMonitor("assign_task"):
        try:
            # Get task service
            task_service = await get_task_service()
            
            user_ids = assignment_data.get("user_ids", [])
            message = assignment_data.get("message")
            
            # Assign task
            success = await task_service.assign_task_to_users(
                task_id=task_id,
                user_ids=user_ids,
                assigned_by=current_user["id"],
                message=message
            )
            
            return {"success": success, "assigned_users": user_ids}
            
        except TaskManagementException as e:
            logger.error(f"Task assignment error: {e.message}")
            raise HTTPException(status_code=400, detail=e.message)
        except Exception as e:
            logger.error(f"Unexpected error in assign_task: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to assign task")


@router.post("/{task_id}/progress")
async def update_task_progress(
    task_id: int = Path(..., description="The ID of the task to update"),
    progress_data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Update task progress"""
    with PerformanceMonitor("update_task_progress"):
        try:
            # Get task service
            task_service = await get_task_service()
            
            # Update progress
            success = await task_service.update_task_progress(
                task_id=task_id,
                user_id=current_user["id"],
                progress=progress_data.get("progress", 0),
                notes=progress_data.get("notes")
            )
            
            return {"success": success, "task_id": task_id}
            
        except TaskManagementException as e:
            logger.error(f"Task progress update error: {e.message}")
            raise HTTPException(status_code=400, detail=e.message)
        except Exception as e:
            logger.error(f"Unexpected error in update_task_progress: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to update task progress")


@router.get("/{task_id}/messages")
async def get_task_messages(
    task_id: int = Path(..., description="The ID of the task"),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Get messages for a task"""
    with PerformanceMonitor("get_task_messages"):
        try:
            # Get task service
            task_service = await get_task_service()
            
            # Get messages
            messages = await task_service.get_task_messages(task_id, current_user["id"])
            
            return {"messages": messages}
            
        except TaskManagementException as e:
            logger.error(f"Task messages retrieval error: {e.message}")
            raise HTTPException(status_code=400, detail=e.message)
        except Exception as e:
            logger.error(f"Unexpected error in get_task_messages: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to retrieve task messages")


@router.post("/{task_id}/messages")
async def add_task_message(
    task_id: int = Path(..., description="The ID of the task"),
    message_data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Add a message to a task"""
    with PerformanceMonitor("add_task_message"):
        try:
            # Get task service
            task_service = await get_task_service()
            
            # Add message
            message = await task_service.add_task_message(
                task_id=task_id,
                user_id=current_user["id"],
                message=message_data.get("message", ""),
                message_type=message_data.get("message_type", "comment"),
                parent_id=message_data.get("parent_message_id")
            )
            
            return message
            
        except TaskManagementException as e:
            logger.error(f"Task message creation error: {e.message}")
            raise HTTPException(status_code=400, detail=e.message)
        except Exception as e:
            logger.error(f"Unexpected error in add_task_message: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to add task message")


@router.post("/{task_id}/start")
async def start_task(
    task_id: int = Path(..., description="The ID of the task to start"),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Start working on a task"""
    with PerformanceMonitor("start_task"):
        try:
            # Get task service
            task_service = await get_task_service()
            
            # Start task
            success = await task_service.start_task(task_id, current_user["id"])
            
            return {"success": success, "task_id": task_id}
            
        except TaskManagementException as e:
            logger.error(f"Task start error: {e.message}")
            raise HTTPException(status_code=400, detail=e.message)
        except Exception as e:
            logger.error(f"Unexpected error in start_task: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to start task")


@router.post("/{task_id}/complete")
async def complete_task(
    task_id: int = Path(..., description="The ID of the task to complete"),
    completion_data: Dict[str, Any] = Body(default={}),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Complete a task"""
    with PerformanceMonitor("complete_task"):
        try:
            # Get task service
            task_service = await get_task_service()
            
            # Complete task
            success = await task_service.complete_task(
                task_id, 
                current_user["id"], 
                notes=completion_data.get("notes")
            )
            
            return {"success": success, "task_id": task_id}
            
        except TaskManagementException as e:
            logger.error(f"Task completion error: {e.message}")
            raise HTTPException(status_code=400, detail=e.message)
        except Exception as e:
            logger.error(f"Unexpected error in complete_task: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to complete task")


# Task Template endpoints
@router.get("/templates/")
async def get_task_templates(
    include_shared: bool = Query(True, description="Include shared templates"),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Get task templates available to the user"""
    with PerformanceMonitor("get_task_templates"):
        try:
            # Get template service
            template_service = await get_template_service()
            
            # Get templates
            templates = await template_service.get_user_templates(
                current_user["id"], 
                include_shared=include_shared
            )
            
            return {"templates": templates}
            
        except Exception as e:
            logger.error(f"Unexpected error in get_task_templates: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to retrieve task templates")


@router.post("/templates/", status_code=status.HTTP_201_CREATED)
async def create_task_template(
    template_data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Create a new task template"""
    with PerformanceMonitor("create_task_template"):
        try:
            # Get template service
            template_service = await get_template_service()
            
            # Create template
            template_id = await template_service.create_template(
                current_user["id"], 
                template_data
            )
            
            return {"template_id": template_id, "success": True}
            
        except TaskManagementException as e:
            logger.error(f"Template creation error: {e.message}")
            raise HTTPException(status_code=400, detail=e.message)
        except Exception as e:
            logger.error(f"Unexpected error in create_task_template: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to create task template")


@router.get("/collaborative/")
async def get_collaborative_tasks(
    status: Optional[str] = Query(None, description="Filter by task status"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Get collaborative tasks"""
    with PerformanceMonitor("get_collaborative_tasks"):
        try:
            # Get task service
            task_service = await get_task_service()
            
            # Get collaborative tasks
            tasks = await task_service.get_collaborative_tasks(
                user_id=current_user["id"],
                status=status
            )
            
            # Apply pagination
            total = len(tasks)
            start = (page - 1) * limit
            end = start + limit
            paginated_tasks = tasks[start:end]
            
            return {
                "items": paginated_tasks,
                "total": total,
                "page": page,
                "limit": limit,
                "pages": (total + limit - 1) // limit if total > 0 else 0
            }
            
        except TaskManagementException as e:
            logger.error(f"Collaborative tasks retrieval error: {e.message}")
            raise HTTPException(status_code=400, detail=e.message)
        except Exception as e:
            logger.error(f"Unexpected error in get_collaborative_tasks: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to retrieve collaborative tasks")