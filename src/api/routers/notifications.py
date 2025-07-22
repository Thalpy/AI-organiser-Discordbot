"""Notifications API router"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body, status
from typing import Dict, List, Optional, Any

from utils.logging_config import get_logger, PerformanceMonitor
from ..auth import get_current_active_user, get_admin_user

# Import services
from src.notifications import get_notification_service

# Setup logging
logger = get_logger(__name__)

# Create router
router = APIRouter()


# Notification endpoints
@router.post("/task-assignment")
async def notify_task_assignment(
    notification_data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Send task assignment notifications"""
    with PerformanceMonitor("notify_task_assignment"):
        try:
            # Get notification service
            notification_service = await get_notification_service()
            
            # Send notifications
            result = await notification_service.notify_task_assignment(
                task_id=notification_data.get("task_id"),
                assigned_users=notification_data.get("assigned_users", []),
                assigned_by=current_user["id"],
                message=notification_data.get("message")
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Unexpected error in notify_task_assignment: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to send task assignment notifications")


@router.post("/task-update")
async def notify_task_update(
    notification_data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Send task update notifications"""
    with PerformanceMonitor("notify_task_update"):
        try:
            # Get notification service
            notification_service = await get_notification_service()
            
            # Send notifications
            success = await notification_service.notify_task_update(
                task_id=notification_data.get("task_id"),
                updated_by=current_user["id"],
                update_type=notification_data.get("update_type"),
                update_data=notification_data.get("update_data", {})
            )
            
            return {"success": success}
            
        except Exception as e:
            logger.error(f"Unexpected error in notify_task_update: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to send task update notifications")


@router.post("/reminder")
async def send_reminder(
    reminder_data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Send a task reminder notification"""
    with PerformanceMonitor("send_reminder"):
        try:
            # Get notification service
            notification_service = await get_notification_service()
            
            # Send reminder
            success = await notification_service.send_reminder_notification(
                user_id=reminder_data.get("user_id", current_user["id"]),
                task_id=reminder_data.get("task_id"),
                reminder_type=reminder_data.get("reminder_type", "upcoming")
            )
            
            return {"success": success}
            
        except Exception as e:
            logger.error(f"Unexpected error in send_reminder: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to send reminder notification")


@router.post("/process-overdue")
async def process_overdue_tasks(
    current_user: Dict[str, Any] = Depends(get_admin_user)  # Only admins can trigger this
) -> Dict[str, Any]:
    """Process and send notifications for overdue tasks (admin only)"""
    with PerformanceMonitor("process_overdue_tasks"):
        try:
            # Get notification service
            notification_service = await get_notification_service()
            
            # Process overdue tasks
            result = await notification_service.notify_overdue_tasks()
            
            return result
            
        except Exception as e:
            logger.error(f"Unexpected error in process_overdue_tasks: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to process overdue tasks")


@router.post("/daily-summary/{user_id}")
async def send_daily_summary(
    user_id: str = Path(..., description="The ID of the user to send summary to"),
    current_user: Dict[str, Any] = Depends(get_admin_user)  # Only admins can trigger this
) -> Dict[str, Any]:
    """Send daily productivity summary to a user (admin only)"""
    with PerformanceMonitor("send_daily_summary"):
        try:
            # Get notification service
            notification_service = await get_notification_service()
            
            # Send daily summary
            success = await notification_service.send_daily_summary(user_id)
            
            return {"success": success}
            
        except Exception as e:
            logger.error(f"Unexpected error in send_daily_summary: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to send daily summary")


@router.get("/preferences")
async def get_notification_preferences(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Get notification preferences for the current user"""
    with PerformanceMonitor("get_notification_preferences"):
        try:
            # Get notification service
            notification_service = await get_notification_service()
            
            # Get preferences
            preferences = await notification_service._get_user_notification_preferences(current_user["id"])
            
            return preferences
            
        except Exception as e:
            logger.error(f"Unexpected error in get_notification_preferences: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to retrieve notification preferences")


@router.put("/preferences")
async def update_notification_preferences(
    preferences: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Update notification preferences for the current user"""
    with PerformanceMonitor("update_notification_preferences"):
        try:
            # In a real app, this would update the database
            # For now, just return the preferences
            return {
                "user_id": current_user["id"],
                "preferences": preferences,
                "updated_at": "2023-01-01T00:00:00Z"
            }
            
        except Exception as e:
            logger.error(f"Unexpected error in update_notification_preferences: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to update notification preferences")