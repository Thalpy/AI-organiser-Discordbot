"""Analytics API router"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body, status
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from utils.logging_config import get_logger, PerformanceMonitor
from ..auth import get_current_active_user, get_admin_user

# Import services
from src.analytics import get_analytics_service

# Setup logging
logger = get_logger(__name__)

# Create router
router = APIRouter()


# Analytics endpoints
@router.get("/")
async def get_user_analytics(
    timeframe: str = Query("week", description="Timeframe for analytics (day, week, month, quarter, year)"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Get analytics data for the current user"""
    with PerformanceMonitor("get_user_analytics"):
        try:
            # Parse dates if provided
            start_date_obj = None
            end_date_obj = None
            
            if start_date:
                start_date_obj = datetime.fromisoformat(start_date)
            
            if end_date:
                end_date_obj = datetime.fromisoformat(end_date)
            
            # Get analytics service
            analytics_service = await get_analytics_service()
            
            # Get analytics data
            analytics = await analytics_service.calculate_user_analytics(
                user_id=current_user["id"],
                timeframe=timeframe,
                start_date=start_date_obj,
                end_date=end_date_obj
            )
            
            # Get recommendations
            recommendations = await analytics_service.get_productivity_recommendations(
                user_id=current_user["id"],
                analytics_data=analytics
            )
            
            # Get chart data
            charts = {
                "productivity": await analytics_service.get_chart_data(
                    user_id=current_user["id"],
                    chart_type="productivity",
                    timeframe=timeframe
                ),
                "completion": await analytics_service.get_chart_data(
                    user_id=current_user["id"],
                    chart_type="completion",
                    timeframe=timeframe
                ),
                "priority_distribution": await analytics_service.get_chart_data(
                    user_id=current_user["id"],
                    chart_type="priority_distribution",
                    timeframe=timeframe
                ),
                "time_tracking": await analytics_service.get_chart_data(
                    user_id=current_user["id"],
                    chart_type="time_tracking",
                    timeframe=timeframe
                )
            }
            
            return {
                "analytics": analytics,
                "recommendations": recommendations,
                "charts": charts
            }
            
        except ValueError as e:
            logger.error(f"Invalid date format: {e}")
            raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in get_user_analytics: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to retrieve analytics data")


@router.get("/team")
async def get_team_analytics(
    timeframe: str = Query("week", description="Timeframe for analytics (day, week, month, quarter, year)"),
    team_id: Optional[str] = Query(None, description="Team ID (if not provided, uses all users)"),
    current_user: Dict[str, Any] = Depends(get_admin_user)  # Only admins can access team analytics
) -> Dict[str, Any]:
    """Get analytics data for a team (admin only)"""
    with PerformanceMonitor("get_team_analytics"):
        try:
            # Get analytics service
            analytics_service = await get_analytics_service()
            
            # Get team users (in a real app, this would query the database)
            team_users = ["1", "2", "3"]  # Mock user IDs
            
            # Get team analytics
            team_analytics = await analytics_service.get_team_analytics(
                team_users=team_users,
                timeframe=timeframe
            )
            
            return team_analytics
            
        except Exception as e:
            logger.error(f"Unexpected error in get_team_analytics: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to retrieve team analytics data")


@router.get("/recommendations")
async def get_recommendations(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Get productivity recommendations for the current user"""
    with PerformanceMonitor("get_recommendations"):
        try:
            # Get analytics service
            analytics_service = await get_analytics_service()
            
            # Get recommendations
            recommendations = await analytics_service.get_productivity_recommendations(
                user_id=current_user["id"]
            )
            
            # Get performance score (in a real app, this would be calculated)
            performance_score = 75  # Mock score
            
            return {
                "recommendations": recommendations,
                "performance_score": performance_score
            }
            
        except Exception as e:
            logger.error(f"Unexpected error in get_recommendations: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to retrieve recommendations")


@router.post("/export")
async def export_analytics(
    export_data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Export analytics data"""
    with PerformanceMonitor("export_analytics"):
        try:
            # In a real app, this would generate and return a file
            # For now, just return success
            return {
                "success": True,
                "format": export_data.get("format", "csv"),
                "url": f"/api/analytics/exports/sample_{export_data.get('format', 'csv')}.{export_data.get('format', 'csv')}"
            }
            
        except Exception as e:
            logger.error(f"Unexpected error in export_analytics: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to export analytics data")


@router.post("/goals")
async def create_goal(
    goal_data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Create a new productivity goal"""
    with PerformanceMonitor("create_goal"):
        try:
            # In a real app, this would create a goal in the database
            # For now, just return mock data
            return {
                "id": 1,
                "user_id": current_user["id"],
                "title": goal_data.get("title"),
                "goal_type": goal_data.get("goal_type"),
                "target_value": goal_data.get("target_value"),
                "current_value": 0,
                "period_type": goal_data.get("period_type"),
                "is_active": True,
                "created_at": datetime.now().isoformat(),
                "end_date": goal_data.get("end_date")
            }
            
        except Exception as e:
            logger.error(f"Unexpected error in create_goal: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to create goal")


@router.get("/goals")
async def get_user_goals(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Get productivity goals for the current user"""
    with PerformanceMonitor("get_user_goals"):
        try:
            # In a real app, this would query the database
            # For now, return mock data
            goals = [
                {
                    "id": 1,
                    "user_id": current_user["id"],
                    "title": "Complete 10 tasks per day",
                    "goal_type": "daily_tasks",
                    "target_value": 10,
                    "current_value": 5,
                    "period_type": "daily",
                    "is_active": True,
                    "created_at": "2023-01-01T00:00:00Z",
                    "end_date": "2023-12-31T00:00:00Z"
                },
                {
                    "id": 2,
                    "user_id": current_user["id"],
                    "title": "Achieve 90% completion rate",
                    "goal_type": "completion_rate",
                    "target_value": 90,
                    "current_value": 75,
                    "period_type": "weekly",
                    "is_active": True,
                    "created_at": "2023-01-01T00:00:00Z",
                    "end_date": "2023-12-31T00:00:00Z"
                }
            ]
            
            return {"goals": goals}
            
        except Exception as e:
            logger.error(f"Unexpected error in get_user_goals: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to retrieve goals")


@router.put("/goals/{goal_id}")
async def update_goal(
    goal_id: int = Path(..., description="The ID of the goal to update"),
    goal_data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Update a productivity goal"""
    with PerformanceMonitor("update_goal"):
        try:
            # In a real app, this would update the database
            # For now, just return the updated goal
            return {
                "id": goal_id,
                "user_id": current_user["id"],
                "title": goal_data.get("title", "Updated goal"),
                "target_value": goal_data.get("target_value", 10),
                "current_value": goal_data.get("current_value", 5),
                "is_active": goal_data.get("is_active", True),
                "updated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Unexpected error in update_goal: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to update goal")


@router.delete("/goals/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_goal(
    goal_id: int = Path(..., description="The ID of the goal to delete"),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> None:
    """Delete a productivity goal"""
    with PerformanceMonitor("delete_goal"):
        try:
            # In a real app, this would delete from the database
            # For now, just return
            pass
            
        except Exception as e:
            logger.error(f"Unexpected error in delete_goal: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to delete goal")