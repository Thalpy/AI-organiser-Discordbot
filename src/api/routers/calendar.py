"""Calendar integration API router"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body, status
from typing import Dict, List, Optional, Any
from datetime import datetime

from utils.logging_config import get_logger, PerformanceMonitor
from ..main import get_current_active_user

# Import services
from src.calendar_integration import get_calendar_service, SyncDirection, ConflictResolution

# Setup logging
logger = get_logger(__name__)

# Create router
router = APIRouter()


@router.get("/status")
async def get_calendar_sync_status(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Get calendar synchronization status for the current user"""
    with PerformanceMonitor("get_calendar_sync_status"):
        try:
            calendar_service = await get_calendar_service()
            status = await calendar_service.get_sync_status(current_user["id"])
            
            return {
                "success": True,
                "data": status
            }
            
        except Exception as e:
            logger.error(f"Failed to get calendar sync status: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve calendar sync status")


@router.get("/auth-url")
async def get_calendar_auth_url(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Get Google Calendar OAuth authorization URL"""
    with PerformanceMonitor("get_calendar_auth_url"):
        try:
            calendar_service = await get_calendar_service()
            auth_url = await calendar_service.get_authorization_url(current_user["id"])
            
            return {
                "success": True,
                "auth_url": auth_url
            }
            
        except Exception as e:
            logger.error(f"Failed to generate calendar auth URL: {e}")
            raise HTTPException(status_code=500, detail="Failed to generate authorization URL")


@router.post("/oauth-callback")
async def handle_calendar_oauth_callback(
    callback_data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Handle Google Calendar OAuth callback"""
    with PerformanceMonitor("handle_calendar_oauth_callback"):
        try:
            authorization_code = callback_data.get("code")
            if not authorization_code:
                raise HTTPException(status_code=400, detail="Authorization code is required")
            
            calendar_service = await get_calendar_service()
            success = await calendar_service.handle_oauth_callback(
                user_id=current_user["id"],
                authorization_code=authorization_code
            )
            
            if success:
                return {
                    "success": True,
                    "message": "Calendar integration setup successfully"
                }
            else:
                raise HTTPException(status_code=400, detail="Failed to setup calendar integration")
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to handle OAuth callback: {e}")
            raise HTTPException(status_code=500, detail="Failed to process OAuth callback")


@router.post("/sync")
async def trigger_calendar_sync(
    sync_data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Trigger manual calendar synchronization"""
    with PerformanceMonitor("trigger_calendar_sync"):
        try:
            calendar_service = await get_calendar_service()
            
            # Parse sync direction
            direction_str = sync_data.get("direction", "bidirectional")
            try:
                direction = SyncDirection(direction_str)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid sync direction: {direction_str}")
            
            # Perform sync
            sync_result = await calendar_service.perform_full_sync(
                user_id=current_user["id"],
                direction=direction
            )
            
            if "error" in sync_result:
                raise HTTPException(status_code=400, detail=sync_result["error"])
            
            return {
                "success": True,
                "sync_result": sync_result
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to trigger calendar sync: {e}")
            raise HTTPException(status_code=500, detail="Failed to trigger synchronization")


@router.get("/conflicts")
async def get_calendar_conflicts(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Get calendar synchronization conflicts"""
    with PerformanceMonitor("get_calendar_conflicts"):
        try:
            calendar_service = await get_calendar_service()
            conflicts = await calendar_service.detect_conflicts(current_user["id"])
            
            # Convert conflicts to serializable format
            conflict_data = []
            for conflict in conflicts:
                conflict_data.append({
                    "task_id": conflict.task_id,
                    "calendar_event_id": conflict.calendar_event_id,
                    "conflict_type": conflict.conflict_type,
                    "task_updated": conflict.task_updated.isoformat(),
                    "calendar_updated": conflict.calendar_updated.isoformat(),
                    "task_data": {
                        "title": conflict.task_data.get("description", ""),
                        "due_time": conflict.task_data.get("due_time").isoformat() if conflict.task_data.get("due_time") else None,
                        "location": conflict.task_data.get("location")
                    },
                    "calendar_data": {
                        "title": conflict.calendar_data.summary,
                        "start_time": conflict.calendar_data.start_time.isoformat(),
                        "end_time": conflict.calendar_data.end_time.isoformat(),
                        "location": conflict.calendar_data.location
                    }
                })
            
            return {
                "success": True,
                "conflicts": conflict_data,
                "count": len(conflict_data)
            }
            
        except Exception as e:
            logger.error(f"Failed to get calendar conflicts: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve conflicts")


@router.post("/resolve-conflict")
async def resolve_calendar_conflict(
    conflict_data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Resolve a calendar synchronization conflict"""
    with PerformanceMonitor("resolve_calendar_conflict"):
        try:
            calendar_service = await get_calendar_service()
            
            # Get conflict details
            task_id = conflict_data.get("task_id")
            resolution_str = conflict_data.get("resolution")
            
            if not task_id or not resolution_str:
                raise HTTPException(status_code=400, detail="Task ID and resolution are required")
            
            # Parse resolution
            try:
                resolution = ConflictResolution(resolution_str)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid resolution: {resolution_str}")
            
            # Find the conflict
            conflicts = await calendar_service.detect_conflicts(current_user["id"])
            conflict = next((c for c in conflicts if c.task_id == task_id), None)
            
            if not conflict:
                raise HTTPException(status_code=404, detail="Conflict not found")
            
            # Resolve the conflict
            success = await calendar_service.resolve_conflict(conflict, resolution)
            
            if success:
                return {
                    "success": True,
                    "message": f"Conflict resolved using {resolution.value} strategy"
                }
            else:
                raise HTTPException(status_code=500, detail="Failed to resolve conflict")
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to resolve calendar conflict: {e}")
            raise HTTPException(status_code=500, detail="Failed to resolve conflict")


@router.post("/webhook")
async def handle_calendar_webhook(
    webhook_data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Handle Google Calendar webhook notifications"""
    with PerformanceMonitor("handle_calendar_webhook"):
        try:
            calendar_service = await get_calendar_service()
            
            await calendar_service.handle_calendar_webhook(
                user_id=current_user["id"],
                webhook_data=webhook_data
            )
            
            return {
                "success": True,
                "message": "Webhook processed successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to handle calendar webhook: {e}")
            raise HTTPException(status_code=500, detail="Failed to process webhook")


@router.post("/disable")
async def disable_calendar_sync(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Disable calendar synchronization for the current user"""
    with PerformanceMonitor("disable_calendar_sync"):
        try:
            calendar_service = await get_calendar_service()
            success = await calendar_service.disable_sync(current_user["id"])
            
            if success:
                return {
                    "success": True,
                    "message": "Calendar synchronization disabled"
                }
            else:
                raise HTTPException(status_code=500, detail="Failed to disable calendar sync")
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to disable calendar sync: {e}")
            raise HTTPException(status_code=500, detail="Failed to disable calendar synchronization")


@router.get("/events")
async def get_calendar_events(
    days_ahead: int = Query(30, ge=1, le=365, description="Number of days ahead to fetch events"),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Get user's calendar events"""
    with PerformanceMonitor("get_calendar_events"):
        try:
            calendar_service = await get_calendar_service()
            
            # Get calendar service for user
            service = await calendar_service.get_calendar_service(current_user["id"])
            
            # Get calendar events
            events = await calendar_service._get_user_calendar_events(service, days_ahead)
            
            # Convert to serializable format
            event_data = []
            for event in events:
                event_data.append({
                    "id": event.id,
                    "title": event.summary,
                    "description": event.description,
                    "start_time": event.start_time.isoformat(),
                    "end_time": event.end_time.isoformat(),
                    "location": event.location,
                    "attendees": event.attendees,
                    "task_id": event.task_id,
                    "created": event.created.isoformat() if event.created else None,
                    "updated": event.updated.isoformat() if event.updated else None
                })
            
            return {
                "success": True,
                "events": event_data,
                "count": len(event_data)
            }
            
        except Exception as e:
            logger.error(f"Failed to get calendar events: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve calendar events")


@router.post("/schedule-auto-sync")
async def schedule_automatic_sync(
    sync_settings: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Schedule automatic calendar synchronization"""
    with PerformanceMonitor("schedule_automatic_sync"):
        try:
            calendar_service = await get_calendar_service()
            
            interval_minutes = sync_settings.get("interval_minutes", 15)
            
            # Validate interval
            if not (5 <= interval_minutes <= 1440):  # 5 minutes to 24 hours
                raise HTTPException(status_code=400, detail="Interval must be between 5 and 1440 minutes")
            
            await calendar_service.schedule_automatic_sync(
                user_id=current_user["id"],
                interval_minutes=interval_minutes
            )
            
            return {
                "success": True,
                "message": f"Automatic sync scheduled every {interval_minutes} minutes"
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to schedule automatic sync: {e}")
            raise HTTPException(status_code=500, detail="Failed to schedule automatic synchronization")