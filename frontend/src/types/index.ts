// Type definitions for Discord Task Management Bot frontend

export interface User {
  id: string;
  username: string;
  discriminator: string;
  avatar?: string;
  email?: string;
}

export interface Task {
  id: number;
  description: string;
  created_by_user_id: string;
  assigned_users: string[];
  status: TaskStatus;
  priority: TaskPriority;
  due_time?: string;
  duration_minutes: number;
  location?: string;
  is_collaborative: boolean;
  completion_percentage: number;
  collaboration_notes?: string;
  template_id?: number;
  recurring_task_id?: number;
  created_at: string;
  updated_at: string;
}

export enum TaskStatus {
  PENDING = 'pending',
  IN_PROGRESS = 'in_progress',
  COMPLETED = 'completed',
  CANCELLED = 'cancelled',
}

export enum TaskPriority {
  LOW = 'low',
  NORMAL = 'normal',
  HIGH = 'high',
  URGENT = 'urgent',
}

export interface TaskAssignment {
  id: number;
  task_id: number;
  assigned_user_id: string;
  assigned_by_user_id: string;
  status: AssignmentStatus;
  completion_notes?: string;
  assigned_at: string;
  completed_at?: string;
}

export enum AssignmentStatus {
  ASSIGNED = 'assigned',
  ACCEPTED = 'accepted',
  DECLINED = 'declined',
  COMPLETED = 'completed',
}

export interface TaskMessage {
  id: number;
  task_id: number;
  user_id: string;
  message: string;
  message_type: MessageType;
  created_at: string;
  edited_at?: string;
  parent_message_id?: number;
}

export enum MessageType {
  COMMENT = 'comment',
  STATUS_UPDATE = 'status_update',
  SYSTEM = 'system',
}

export interface TaskTemplate {
  id: number;
  created_by_user_id: string;
  name: string;
  description?: string;
  default_duration_minutes: number;
  default_priority: TaskPriority;
  template_data: Record<string, any>;
  is_shared: boolean;
  created_at: string;
  updated_at: string;
}

export interface UserPreferences {
  user_id: string;
  work_start: string;
  work_end: string;
  lunch_duration_minutes: number;
  time_zone: string;
  lunch_window_start: string;
  lunch_window_end: string;
}

export interface NotificationPreferences {
  user_id: string;
  task_reminders: boolean;
  overdue_alerts: boolean;
  daily_summaries: boolean;
  email_notifications: boolean;
  web_push_notifications: boolean;
  reminder_minutes: number;
  quiet_hours_start?: string;
  quiet_hours_end?: string;
  email_address?: string;
}

export interface AnalyticsData {
  user_id: string;
  timeframe: string;
  tasks_completed: number;
  total_tasks: number;
  completion_rate: number;
  avg_duration: number;
  on_time_starts: number;
  on_time_finishes: number;
  avg_delay: number;
  total_time: number;
  best_day: string;
  peak_hour: number;
  current_streak: number;
  priority_completion: number;
  performance_score: number;
  goals?: Goal[];
}

export interface ProductivityGoal {
  id: number;
  user_id: string;
  goal_type: string;
  target_value: number;
  current_value: number;
  period_type: string;
  start_date: string;
  end_date?: string;
  is_active: boolean;
  created_at: string;
}

// API Request/Response types
export interface TaskCreateRequest {
  description: string;
  assigned_users?: string[];
  priority?: TaskPriority;
  due_time?: string;
  duration_minutes?: number;
  location?: string;
  is_collaborative?: boolean;
  template_id?: number;
}

export interface TaskUpdateRequest {
  id?: number;
  description?: string;
  status?: TaskStatus;
  priority?: TaskPriority;
  due_time?: string;
  duration_minutes?: number;
  location?: string;
  completion_percentage?: number;
  collaboration_notes?: string;
  assigned_users?: string[];
  is_collaborative?: boolean;
}

export interface TaskAssignRequest {
  user_ids: string[];
  message?: string;
}

export interface TaskMessageRequest {
  message: string;
  message_type?: MessageType;
  parent_message_id?: number;
}

export interface AddTaskMessageRequest {
  taskId: number;
  message: string;
  message_type?: string;
  parent_message_id?: number;
}

export interface UpdateTaskMessageRequest {
  id: number;
  message: string;
}

export interface TaskResponse {
  task: Task;
  assignments?: TaskAssignment[];
  messages?: TaskMessage[];
}

export interface TaskListResponse {
  tasks: Task[];
  total: number;
  page: number;
  per_page: number;
}

export interface AnalyticsResponse {
  analytics: AnalyticsData;
  recommendations: Recommendation[];
  charts: Record<string, any>;
}

export interface Recommendation {
  title: string;
  description: string;
  priority: 'low' | 'medium' | 'high';
  action?: string;
}

// WebSocket message types
export interface WebSocketMessage {
  type: string;
  data?: any;
  timestamp?: string;
}

export interface TaskUpdatedMessage extends WebSocketMessage {
  type: 'task_updated';
  task: Task;
}

export interface TaskAssignedMessage extends WebSocketMessage {
  type: 'task_assigned';
  task: Task;
  assigned_by: string;
}

export interface TaskMessageMessage extends WebSocketMessage {
  type: 'task_message';
  message: TaskMessage;
}

export interface NotificationMessage extends WebSocketMessage {
  type: 'notification';
  notification: {
    title: string;
    message: string;
    type: 'info' | 'success' | 'warning' | 'error';
    task_id?: number;
  };
}

// UI State types
export interface AuthState {
  isAuthenticated: boolean;
  user: User | null;
  token: string | null;
  loading: boolean;
  error: string | null;
}

export interface TaskState {
  tasks: Task[];
  selectedTask: Task | null;
  loading: boolean;
  error: string | null;
  filters: TaskFilters;
  pagination: {
    page: number;
    per_page: number;
    total: number;
  };
}

export interface TaskFilters {
  status?: TaskStatus;
  priority?: TaskPriority;
  assigned_to?: string;
  created_by?: string;
  search?: string;
  due_date_from?: string;
  due_date_to?: string;
  is_collaborative?: boolean;
}

export interface UIState {
  sidebarOpen: boolean;
  theme: 'light' | 'dark';
  notifications: UINotification[];
  loading: Record<string, boolean>;
}

export interface UINotification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
  task_id?: number;
}

// Form types
export interface LoginForm {
  email: string;
  password: string;
}

export interface TaskForm {
  description: string;
  assigned_users: string[];
  priority: TaskPriority;
  due_time?: Date;
  duration_minutes: number;
  location?: string;
  is_collaborative: boolean;
}

export interface MessageForm {
  message: string;
  message_type: MessageType;
  parent_message_id?: number;
}

// API Error types
export interface APIError {
  error: {
    code: number | string;
    message: string;
  };
  message: string;
  details?: Record<string, any>;
}

// Chart data types
export interface ChartData {
  labels: string[];
  datasets: ChartDataset[];
}

export interface ChartDataset {
  label: string;
  data: number[];
  backgroundColor?: string | string[];
  borderColor?: string | string[];
  borderWidth?: number;
  fill?: boolean;
}

// Analytics types
export type AnalyticsTimeframe = 'day' | 'week' | 'month' | 'quarter' | 'year';

export interface AnalyticsQuery {
  timeframe: AnalyticsTimeframe;
  start_date: string;
  end_date: string;
  user_id?: string;
}

export interface ProductivityChartData {
  date: string;
  completed_tasks: number;
  total_tasks: number;
  completion_rate: number;
  avg_duration: number;
  performance_score: number;
}

export interface TaskCompletionData {
  status: string;
  count: number;
  percentage: number;
}

export interface PriorityDistributionData {
  priority: string;
  count: number;
  percentage: number;
  completion_rate: number;
}

export interface TimeTrackingData {
  hour: number;
  tasks_completed: number;
  avg_duration: number;
  efficiency_score: number;
}

export interface Goal {
  id: number;
  title: string;
  target_value: number;
  current_value: number;
  period_type: 'daily' | 'weekly' | 'monthly';
  goal_type: 'completion_rate' | 'daily_tasks' | 'time_management';
  is_active: boolean;
  end_date?: string;
}

export interface RecommendationData {
  id: string;
  type: 'productivity' | 'time_management' | 'goal_setting' | 'efficiency';
  title: string;
  description: string;
  impact: 'high' | 'medium' | 'low';
  effort: 'high' | 'medium' | 'low';
  category: string;
  actionable_steps?: string[];
  estimated_improvement?: number;
}

// Utility types
export type LoadingState = 'idle' | 'loading' | 'succeeded' | 'failed';

export interface PaginationParams {
  page?: number;
  per_page?: number;
  offset?: number;
  limit?: number;
}

export interface SortParams {
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}