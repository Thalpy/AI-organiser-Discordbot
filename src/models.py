"""
Data models for the Discord Task Management Bot
Defines Pydantic models for data validation and serialization
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


class TaskStatus(str, Enum):
    """Task status enumeration"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    """Task priority enumeration"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class AssignmentStatus(str, Enum):
    """Task assignment status enumeration"""
    ASSIGNED = "assigned"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    COMPLETED = "completed"


class MessageType(str, Enum):
    """Task message type enumeration"""
    COMMENT = "comment"
    STATUS_UPDATE = "status_update"
    SYSTEM = "system"


class NotificationChannel(str, Enum):
    """Notification channel enumeration"""
    DISCORD = "discord"
    EMAIL = "email"
    WEB_PUSH = "web_push"


class Task(BaseModel):
    """Task data model"""
    id: Optional[int] = None
    description: str = Field(..., min_length=1, max_length=500)
    created_by_user_id: str
    assigned_users: List[str] = []
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    due_time: Optional[datetime] = None
    duration_minutes: int = Field(default=15, ge=1, le=1440)
    location: Optional[str] = Field(None, max_length=200)
    is_collaborative: bool = False
    completion_percentage: int = Field(default=0, ge=0, le=100)
    collaboration_notes: Optional[str] = None
    template_id: Optional[int] = None
    recurring_task_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @validator('assigned_users')
    def validate_assigned_users(cls, v):
        """Validate assigned users list"""
        if len(v) > 10:  # Reasonable limit
            raise ValueError('Cannot assign more than 10 users to a task')
        return v


class TaskAssignment(BaseModel):
    """Task assignment data model"""
    id: Optional[int] = None
    task_id: int
    assigned_user_id: str
    assigned_by_user_id: str
    status: AssignmentStatus = AssignmentStatus.ASSIGNED
    completion_notes: Optional[str] = None
    assigned_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class TaskMessage(BaseModel):
    """Task collaboration message data model"""
    id: Optional[int] = None
    task_id: int
    user_id: str
    message: str = Field(..., min_length=1, max_length=1000)
    message_type: MessageType = MessageType.COMMENT
    created_at: Optional[datetime] = None
    edited_at: Optional[datetime] = None
    parent_message_id: Optional[int] = None





class TaskTemplate(BaseModel):
    """Task template data model"""
    id: Optional[int] = None
    created_by_user_id: str
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    default_duration_minutes: int = Field(default=15, ge=1, le=1440)
    default_priority: TaskPriority = TaskPriority.NORMAL
    template_data: Dict[str, Any] = {}
    is_shared: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class RecurringTask(BaseModel):
    """Recurring task configuration data model"""
    id: Optional[int] = None
    template_id: int
    user_id: str
    recurrence_pattern: Dict[str, Any]  # Cron-like pattern
    next_creation_date: Optional[datetime] = None
    is_active: bool = True
    created_at: Optional[datetime] = None


class UserPreferences(BaseModel):
    """User preferences data model"""
    user_id: str
    work_start: str = "09:00"
    work_end: str = "17:00"
    lunch_duration_minutes: int = Field(default=30, ge=0, le=120)
    time_zone: str = "UTC"
    lunch_window_start: str = "12:00"
    lunch_window_end: str = "14:00"

    @validator('work_start', 'work_end', 'lunch_window_start', 'lunch_window_end')
    def validate_time_format(cls, v):
        """Validate time format (HH:MM)"""
        try:
            parts = v.split(':')
            if len(parts) != 2:
                raise ValueError('Time must be in HH:MM format')
            hour, minute = map(int, parts)
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError('Invalid time values')
            return v
        except (ValueError, AttributeError):
            raise ValueError('Time must be in HH:MM format')


class NotificationPreferences(BaseModel):
    """Notification preferences data model"""
    user_id: str
    task_reminders: bool = True
    overdue_alerts: bool = True
    daily_summaries: bool = True
    email_notifications: bool = False
    web_push_notifications: bool = True
    reminder_minutes: int = Field(default=15, ge=1, le=60)
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    email_address: Optional[str] = None

    @validator('email_address')
    def validate_email(cls, v):
        """Basic email validation"""
        if v and '@' not in v:
            raise ValueError('Invalid email address')
        return v


class UserSession(BaseModel):
    """User session data model"""
    id: Optional[int] = None
    user_id: str
    session_token: str
    discord_token: Optional[str] = None
    expires_at: datetime
    created_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class APIKey(BaseModel):
    """API key data model"""
    id: Optional[int] = None
    user_id: str
    key_name: str = Field(..., min_length=1, max_length=100)
    api_key_hash: str
    permissions: List[str] = []
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_active: bool = True
    created_at: Optional[datetime] = None


class ProductivityGoal(BaseModel):
    """Productivity goal data model"""
    id: Optional[int] = None
    user_id: str
    goal_type: str = Field(..., regex=r'^(completion_rate|daily_tasks|time_management)$')
    target_value: float = Field(..., ge=0)
    current_value: float = Field(default=0, ge=0)
    period_type: str = Field(default='weekly', regex=r'^(daily|weekly|monthly)$')
    start_date: datetime
    end_date: Optional[datetime] = None
    is_active: bool = True
    created_at: Optional[datetime] = None


class UserActivity(BaseModel):
    """User activity log data model"""
    id: Optional[int] = None
    user_id: str
    activity_type: str = Field(..., min_length=1, max_length=50)
    activity_data: Dict[str, Any] = {}
    source: str = Field(..., regex=r'^(discord|web|api)$')
    ip_address: Optional[str] = None
    created_at: Optional[datetime] = None


class AnalyticsData(BaseModel):
    """Analytics data model"""
    user_id: str
    timeframe: str
    tasks_completed: int = 0
    total_tasks: int = 0
    completion_rate: float = 0.0
    avg_duration: float = 0.0
    on_time_starts: float = 0.0
    on_time_finishes: float = 0.0
    avg_delay: float = 0.0
    total_time: float = 0.0
    best_day: str = "Monday"
    peak_hour: int = 9
    current_streak: int = 0
    priority_completion: float = 0.0
    performance_score: int = 0


# Request/Response models for API
class TaskCreateRequest(BaseModel):
    """Request model for task creation"""
    description: str = Field(..., min_length=1, max_length=500)
    assigned_users: List[str] = []
    priority: TaskPriority = TaskPriority.NORMAL
    due_time: Optional[datetime] = None
    duration_minutes: int = Field(default=15, ge=1, le=1440)
    location: Optional[str] = Field(None, max_length=200)
    is_collaborative: bool = False
    template_id: Optional[int] = None


class TaskUpdateRequest(BaseModel):
    """Request model for task updates"""
    description: Optional[str] = Field(None, min_length=1, max_length=500)
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    due_time: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(None, ge=1, le=1440)
    location: Optional[str] = Field(None, max_length=200)
    completion_percentage: Optional[int] = Field(None, ge=0, le=100)
    collaboration_notes: Optional[str] = None


class TaskAssignRequest(BaseModel):
    """Request model for task assignment"""
    user_ids: List[str] = Field(..., min_items=1, max_items=10)
    message: Optional[str] = Field(None, max_length=500)


class TaskMessageRequest(BaseModel):
    """Request model for task messages"""
    message: str = Field(..., min_length=1, max_length=1000)
    message_type: MessageType = MessageType.COMMENT
    parent_message_id: Optional[int] = None


class TaskResponse(BaseModel):
    """Response model for task data"""
    task: Task
    assignments: List[TaskAssignment] = []
    messages: List[TaskMessage] = []


class TaskListResponse(BaseModel):
    """Response model for task lists"""
    tasks: List[Task]
    total: int
    page: int = 1
    per_page: int = 25


class AnalyticsResponse(BaseModel):
    """Response model for analytics data"""
    analytics: AnalyticsData
    recommendations: List[Dict[str, Any]] = []
    charts: Dict[str, Any] = {}


class ErrorResponse(BaseModel):
    """Error response model"""
    error: Dict[str, Any]
    message: str
    details: Optional[Dict[str, Any]] = None