"""Users API router"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body, status
from typing import Dict, List, Optional, Any

from utils.logging_config import get_logger, PerformanceMonitor
from ..auth import get_current_active_user, get_admin_user

# Setup logging
logger = get_logger(__name__)

# Create router
router = APIRouter()


# User endpoints
@router.get("/me")
async def get_current_user_info(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Get current user information"""
    return current_user


@router.get("/")
async def get_users(
    search: Optional[str] = Query(None, description="Search by username"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    current_user: Dict[str, Any] = Depends(get_admin_user)  # Only admins can list all users
) -> Dict[str, Any]:
    """Get users with filtering and pagination (admin only)"""
    with PerformanceMonitor("get_users"):
        try:
            # In a real app, this would query the database
            # For now, return mock data
            users = [
                {"id": "1", "username": "admin", "is_admin": True},
                {"id": "2", "username": "user1", "is_admin": False},
                {"id": "3", "username": "user2", "is_admin": False},
            ]
            
            # Apply search filter if provided
            if search:
                users = [u for u in users if search.lower() in u["username"].lower()]
            
            # Apply pagination
            total = len(users)
            start = (page - 1) * limit
            end = start + limit
            paginated_users = users[start:end]
            
            return {
                "items": paginated_users,
                "total": total,
                "page": page,
                "limit": limit,
                "pages": (total + limit - 1) // limit
            }
            
        except Exception as e:
            logger.error(f"Unexpected error in get_users: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to retrieve users")


@router.get("/{user_id}")
async def get_user(
    user_id: str = Path(..., description="The ID of the user to retrieve"),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Get a specific user by ID"""
    with PerformanceMonitor("get_user"):
        try:
            # Check if user is requesting their own info or is an admin
            if current_user["id"] != user_id and not current_user.get("is_admin"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not enough permissions to access this user's information"
                )
            
            # In a real app, this would query the database
            # For now, return mock data
            if user_id == "1":
                return {"id": "1", "username": "admin", "is_admin": True}
            elif user_id == "2":
                return {"id": "2", "username": "user1", "is_admin": False}
            elif user_id == "3":
                return {"id": "3", "username": "user2", "is_admin": False}
            else:
                raise HTTPException(status_code=404, detail="User not found")
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in get_user: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to retrieve user")


@router.put("/me/preferences")
async def update_user_preferences(
    preferences: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Update current user preferences"""
    with PerformanceMonitor("update_user_preferences"):
        try:
            # In a real app, this would update the database
            # For now, just return the preferences
            return {
                "user_id": current_user["id"],
                "preferences": preferences,
                "updated_at": "2023-01-01T00:00:00Z"
            }
            
        except Exception as e:
            logger.error(f"Unexpected error in update_user_preferences: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to update preferences")


@router.get("/me/preferences")
async def get_user_preferences(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Get current user preferences"""
    with PerformanceMonitor("get_user_preferences"):
        try:
            # In a real app, this would query the database
            # For now, return mock data
            return {
                "user_id": current_user["id"],
                "preferences": {
                    "theme": "light",
                    "notifications_enabled": True,
                    "email_notifications": False,
                    "task_reminders": True
                }
            }
            
        except Exception as e:
            logger.error(f"Unexpected error in get_user_preferences: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to retrieve preferences")


@router.get("/me/notifications")
async def get_user_notifications(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Get current user notifications"""
    with PerformanceMonitor("get_user_notifications"):
        try:
            # In a real app, this would query the database
            # For now, return mock data
            notifications = [
                {
                    "id": 1,
                    "type": "task_assignment",
                    "message": "You have been assigned a new task",
                    "read": False,
                    "created_at": "2023-01-01T00:00:00Z"
                },
                {
                    "id": 2,
                    "type": "task_update",
                    "message": "A task has been updated",
                    "read": True,
                    "created_at": "2023-01-02T00:00:00Z"
                }
            ]
            
            # Apply pagination
            total = len(notifications)
            start = (page - 1) * limit
            end = start + limit
            paginated_notifications = notifications[start:end]
            
            return {
                "items": paginated_notifications,
                "total": total,
                "page": page,
                "limit": limit,
                "pages": (total + limit - 1) // limit
            }
            
        except Exception as e:
            logger.error(f"Unexpected error in get_user_notifications: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to retrieve notifications")


@router.put("/me/notifications/{notification_id}/read")
async def mark_notification_as_read(
    notification_id: int = Path(..., description="The ID of the notification to mark as read"),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Mark a notification as read"""
    with PerformanceMonitor("mark_notification_as_read"):
        try:
            # In a real app, this would update the database
            # For now, just return success
            return {"success": True, "notification_id": notification_id}
            
        except Exception as e:
            logger.error(f"Unexpected error in mark_notification_as_read: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to mark notification as read")