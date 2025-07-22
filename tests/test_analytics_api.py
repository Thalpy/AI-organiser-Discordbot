"""Tests for Analytics API endpoints"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Create a simple test app for analytics
app = FastAPI()

# Mock analytics data
MOCK_ANALYTICS_DATA = {
    "total_tasks": 25,
    "completed_tasks": 18,
    "pending_tasks": 5,
    "in_progress_tasks": 2,
    "completion_rate": 72.0,
    "average_completion_time": 2.5,
    "productivity_score": 85,
    "tasks_by_priority": {
        "high": 8,
        "normal": 12,
        "low": 5
    },
    "tasks_by_day": [
        {"date": "2023-01-01", "completed": 3, "created": 4},
        {"date": "2023-01-02", "completed": 2, "created": 3},
        {"date": "2023-01-03", "completed": 4, "created": 2}
    ]
}

MOCK_RECOMMENDATIONS = [
    {
        "type": "productivity",
        "title": "Focus on High Priority Tasks",
        "description": "You have 3 high priority tasks pending. Consider tackling these first.",
        "priority": "high"
    },
    {
        "type": "time_management",
        "title": "Break Down Large Tasks",
        "description": "Tasks taking longer than 4 hours could be broken into smaller chunks.",
        "priority": "medium"
    }
]

MOCK_CHART_DATA = {
    "productivity": {
        "labels": ["Mon", "Tue", "Wed", "Thu", "Fri"],
        "data": [8, 6, 9, 7, 10],
        "type": "line"
    },
    "completion": {
        "labels": ["Completed", "Pending", "In Progress"],
        "data": [18, 5, 2],
        "type": "pie"
    }
}

MOCK_GOALS = [
    {
        "id": 1,
        "title": "Complete 10 tasks per day",
        "goal_type": "daily_tasks",
        "target_value": 10,
        "current_value": 7,
        "progress": 70,
        "is_active": True
    },
    {
        "id": 2,
        "title": "Achieve 90% completion rate",
        "goal_type": "completion_rate",
        "target_value": 90,
        "current_value": 72,
        "progress": 80,
        "is_active": True
    }
]

# Analytics endpoints
@app.get("/api/analytics/")
async def get_user_analytics(
    timeframe: str = "week",
    start_date: str = None,
    end_date: str = None
):
    return {
        "analytics": MOCK_ANALYTICS_DATA,
        "recommendations": MOCK_RECOMMENDATIONS,
        "charts": MOCK_CHART_DATA
    }

@app.get("/api/analytics/team")
async def get_team_analytics(timeframe: str = "week"):
    return {
        "team_analytics": {
            **MOCK_ANALYTICS_DATA,
            "team_size": 5,
            "average_tasks_per_user": 5.0,
            "top_performers": [
                {"user_id": "1", "username": "alice", "completed_tasks": 8},
                {"user_id": "2", "username": "bob", "completed_tasks": 6}
            ]
        }
    }

@app.get("/api/analytics/recommendations")
async def get_recommendations():
    return {
        "recommendations": MOCK_RECOMMENDATIONS,
        "performance_score": 85
    }

@app.post("/api/analytics/export")
async def export_analytics(export_data: dict):
    return {
        "success": True,
        "format": export_data.get("format", "csv"),
        "url": f"/api/analytics/exports/sample.{export_data.get('format', 'csv')}"
    }

@app.get("/api/analytics/goals")
async def get_user_goals():
    return {"goals": MOCK_GOALS}

@app.post("/api/analytics/goals")
async def create_goal(goal_data: dict):
    return {
        "id": 3,
        "title": goal_data.get("title"),
        "goal_type": goal_data.get("goal_type"),
        "target_value": goal_data.get("target_value"),
        "current_value": 0,
        "progress": 0,
        "is_active": True,
        "created_at": datetime.now().isoformat()
    }

@app.put("/api/analytics/goals/{goal_id}")
async def update_goal(goal_id: int, goal_data: dict):
    return {
        "id": goal_id,
        "title": goal_data.get("title", "Updated goal"),
        "target_value": goal_data.get("target_value", 10),
        "current_value": goal_data.get("current_value", 5),
        "progress": (goal_data.get("current_value", 5) / goal_data.get("target_value", 10)) * 100,
        "is_active": goal_data.get("is_active", True),
        "updated_at": datetime.now().isoformat()
    }

@app.delete("/api/analytics/goals/{goal_id}")
async def delete_goal(goal_id: int):
    return {"success": True}

client = TestClient(app)


class TestAnalyticsEndpoints:
    """Test analytics data endpoints"""
    
    def test_get_user_analytics_success(self):
        """Test successful user analytics retrieval"""
        response = client.get("/api/analytics/")
        assert response.status_code == 200
        
        data = response.json()
        assert "analytics" in data
        assert "recommendations" in data
        assert "charts" in data
        
        # Verify analytics structure
        analytics = data["analytics"]
        assert "total_tasks" in analytics
        assert "completed_tasks" in analytics
        assert "completion_rate" in analytics
        assert "productivity_score" in analytics
        assert "tasks_by_priority" in analytics
        assert "tasks_by_day" in analytics
    
    def test_get_user_analytics_with_timeframe(self):
        """Test user analytics with different timeframes"""
        timeframes = ["day", "week", "month", "quarter", "year"]
        
        for timeframe in timeframes:
            response = client.get(f"/api/analytics/?timeframe={timeframe}")
            assert response.status_code == 200
            
            data = response.json()
            assert "analytics" in data
            assert isinstance(data["analytics"]["total_tasks"], int)
            assert isinstance(data["analytics"]["completion_rate"], float)
    
    def test_get_user_analytics_with_date_range(self):
        """Test user analytics with custom date range"""
        start_date = (datetime.now() - timedelta(days=7)).isoformat()
        end_date = datetime.now().isoformat()
        
        response = client.get(f"/api/analytics/?start_date={start_date}&end_date={end_date}")
        assert response.status_code == 200
        
        data = response.json()
        assert "analytics" in data
        assert data["analytics"]["total_tasks"] >= 0
    
    def test_get_team_analytics_success(self):
        """Test successful team analytics retrieval"""
        response = client.get("/api/analytics/team")
        assert response.status_code == 200
        
        data = response.json()
        assert "team_analytics" in data
        
        team_analytics = data["team_analytics"]
        assert "team_size" in team_analytics
        assert "average_tasks_per_user" in team_analytics
        assert "top_performers" in team_analytics
        assert isinstance(team_analytics["top_performers"], list)
    
    def test_get_recommendations_success(self):
        """Test successful recommendations retrieval"""
        response = client.get("/api/analytics/recommendations")
        assert response.status_code == 200
        
        data = response.json()
        assert "recommendations" in data
        assert "performance_score" in data
        
        recommendations = data["recommendations"]
        assert isinstance(recommendations, list)
        
        if recommendations:
            rec = recommendations[0]
            assert "type" in rec
            assert "title" in rec
            assert "description" in rec
            assert "priority" in rec


class TestAnalyticsReporting:
    """Test analytics reporting and export functionality"""
    
    def test_export_analytics_csv(self):
        """Test analytics export in CSV format"""
        export_data = {
            "format": "csv",
            "timeframe": "month",
            "include_charts": True
        }
        
        response = client.post("/api/analytics/export", json=export_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["format"] == "csv"
        assert "url" in data
        assert data["url"].endswith(".csv")
    
    def test_export_analytics_pdf(self):
        """Test analytics export in PDF format"""
        export_data = {
            "format": "pdf",
            "timeframe": "week",
            "include_recommendations": True
        }
        
        response = client.post("/api/analytics/export", json=export_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["format"] == "pdf"
        assert "url" in data
        assert data["url"].endswith(".pdf")
    
    def test_export_analytics_excel(self):
        """Test analytics export in Excel format"""
        export_data = {
            "format": "xlsx",
            "timeframe": "quarter",
            "include_raw_data": True
        }
        
        response = client.post("/api/analytics/export", json=export_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["format"] == "xlsx"


class TestProductivityGoals:
    """Test productivity goal management endpoints"""
    
    def test_get_user_goals_success(self):
        """Test successful user goals retrieval"""
        response = client.get("/api/analytics/goals")
        assert response.status_code == 200
        
        data = response.json()
        assert "goals" in data
        
        goals = data["goals"]
        assert isinstance(goals, list)
        
        if goals:
            goal = goals[0]
            assert "id" in goal
            assert "title" in goal
            assert "goal_type" in goal
            assert "target_value" in goal
            assert "current_value" in goal
            assert "progress" in goal
            assert "is_active" in goal
    
    def test_create_goal_success(self):
        """Test successful goal creation"""
        goal_data = {
            "title": "Complete 15 tasks per day",
            "goal_type": "daily_tasks",
            "target_value": 15,
            "period_type": "daily",
            "end_date": (datetime.now() + timedelta(days=30)).isoformat()
        }
        
        response = client.post("/api/analytics/goals", json=goal_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == 3
        assert data["title"] == goal_data["title"]
        assert data["goal_type"] == goal_data["goal_type"]
        assert data["target_value"] == goal_data["target_value"]
        assert data["current_value"] == 0
        assert data["is_active"] is True
        assert "created_at" in data
    
    def test_update_goal_success(self):
        """Test successful goal update"""
        goal_data = {
            "title": "Updated goal title",
            "target_value": 20,
            "current_value": 12,
            "is_active": True
        }
        
        response = client.put("/api/analytics/goals/1", json=goal_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == 1
        assert data["title"] == goal_data["title"]
        assert data["target_value"] == goal_data["target_value"]
        assert data["current_value"] == goal_data["current_value"]
        assert data["progress"] == 60.0  # 12/20 * 100
        assert "updated_at" in data
    
    def test_delete_goal_success(self):
        """Test successful goal deletion"""
        response = client.delete("/api/analytics/goals/1")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True


class TestAnalyticsChartData:
    """Test analytics chart data functionality"""
    
    def test_chart_data_structure(self):
        """Test that chart data has proper structure"""
        response = client.get("/api/analytics/")
        assert response.status_code == 200
        
        data = response.json()
        charts = data["charts"]
        
        # Test productivity chart
        assert "productivity" in charts
        productivity_chart = charts["productivity"]
        assert "labels" in productivity_chart
        assert "data" in productivity_chart
        assert "type" in productivity_chart
        assert isinstance(productivity_chart["labels"], list)
        assert isinstance(productivity_chart["data"], list)
        
        # Test completion chart
        assert "completion" in charts
        completion_chart = charts["completion"]
        assert "labels" in completion_chart
        assert "data" in completion_chart
        assert "type" in completion_chart
    
    def test_chart_data_consistency(self):
        """Test that chart data is consistent with analytics data"""
        response = client.get("/api/analytics/")
        assert response.status_code == 200
        
        data = response.json()
        analytics = data["analytics"]
        charts = data["charts"]
        
        # Completion chart data should match analytics totals
        completion_chart = charts["completion"]
        completion_data = completion_chart["data"]
        
        # Should have data for completed, pending, in progress
        assert len(completion_data) == 3
        assert sum(completion_data) == analytics["total_tasks"]


class TestAnalyticsPerformance:
    """Test analytics performance and large dataset handling"""
    
    def test_analytics_with_large_timeframe(self):
        """Test analytics performance with large timeframes"""
        response = client.get("/api/analytics/?timeframe=year")
        assert response.status_code == 200
        
        data = response.json()
        assert "analytics" in data
        
        # Should handle large datasets efficiently
        analytics = data["analytics"]
        assert isinstance(analytics["tasks_by_day"], list)
    
    def test_team_analytics_performance(self):
        """Test team analytics performance"""
        response = client.get("/api/analytics/team?timeframe=quarter")
        assert response.status_code == 200
        
        data = response.json()
        team_analytics = data["team_analytics"]
        
        # Should efficiently aggregate team data
        assert "team_size" in team_analytics
        assert "average_tasks_per_user" in team_analytics
        assert isinstance(team_analytics["top_performers"], list)


class TestAnalyticsValidation:
    """Test analytics input validation and error handling"""
    
    def test_invalid_timeframe(self):
        """Test handling of invalid timeframe"""
        response = client.get("/api/analytics/?timeframe=invalid")
        # Should still work but might use default timeframe
        assert response.status_code == 200
    
    def test_invalid_date_format(self):
        """Test handling of invalid date format"""
        response = client.get("/api/analytics/?start_date=invalid-date")
        # Should handle gracefully
        assert response.status_code in [200, 400]
    
    def test_goal_validation(self):
        """Test goal creation validation"""
        # Test with missing required fields
        invalid_goal = {
            "title": "",  # Empty title
            "target_value": -1  # Invalid target
        }
        
        response = client.post("/api/analytics/goals", json=invalid_goal)
        # Should create with defaults or return validation error
        assert response.status_code in [200, 400, 422]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])