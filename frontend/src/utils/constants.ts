// Application constants and configuration

// Task-related constants
export const TASK_STATUS = {
  PENDING: 'pending',
  IN_PROGRESS: 'in_progress',
  COMPLETED: 'completed',
  CANCELLED: 'cancelled',
  ON_HOLD: 'on_hold',
} as const;

export const TASK_PRIORITY = {
  LOW: 'low',
  MEDIUM: 'medium',
  HIGH: 'high',
  URGENT: 'urgent',
} as const;

export const MESSAGE_TYPE = {
  TEXT: 'text',
  IMAGE: 'image',
  FILE: 'file',
  SYSTEM: 'system',
} as const;

// UI constants
export const THEME_MODE = {
  LIGHT: 'light',
  DARK: 'dark',
  AUTO: 'auto',
} as const;

export const NOTIFICATION_TYPE = {
  SUCCESS: 'success',
  ERROR: 'error',
  WARNING: 'warning',
  INFO: 'info',
} as const;

// Pagination constants
export const DEFAULT_PAGE_SIZE = 10;
export const PAGE_SIZE_OPTIONS = [5, 10, 25, 50, 100];

// Date/Time constants
export const DATE_FORMATS = {
  SHORT: 'MMM dd, yyyy',
  LONG: 'MMMM dd, yyyy',
  WITH_TIME: 'MMM dd, yyyy HH:mm',
  TIME_ONLY: 'HH:mm',
  ISO: "yyyy-MM-dd'T'HH:mm:ss.SSSxxx",
} as const;

// WebSocket message types
export const WS_MESSAGE_TYPE = {
  PING: 'ping',
  PONG: 'pong',
  SUBSCRIBE_TASK: 'subscribe_task',
  UNSUBSCRIBE_TASK: 'unsubscribe_task',
  TASK_UPDATE: 'task_update',
  JOIN_ROOM: 'join_room',
  LEAVE_ROOM: 'leave_room',
  TYPING_START: 'typing_start',
  TYPING_STOP: 'typing_stop',
  MESSAGE_EDIT: 'message_edit',
  PRESENCE_UPDATE: 'presence_update',
} as const;

// Analytics constants
export const ANALYTICS_TIMEFRAME = {
  DAY: 'day',
  WEEK: 'week',
  MONTH: 'month',
  QUARTER: 'quarter',
  YEAR: 'year',
} as const;

export const CHART_COLORS = {
  PRIMARY: '#5865F2',
  SECONDARY: '#57F287',
  SUCCESS: '#00C851',
  WARNING: '#FF8800',
  ERROR: '#FF4444',
  INFO: '#33B5E5',
  LIGHT: '#F8F9FA',
  DARK: '#343A40',
} as const;

// Local storage keys
export const STORAGE_KEYS = {
  AUTH_TOKEN: 'taskbot_auth_token',
  USER_PREFERENCES: 'taskbot_user_preferences',
  THEME: 'taskbot_theme',
  SIDEBAR_COLLAPSED: 'taskbot_sidebar_collapsed',
  LAST_VISITED_PAGE: 'taskbot_last_visited_page',
  PENDING_MESSAGES: 'taskbot_pending_messages',
  TASK_SUBSCRIPTIONS: 'taskbot_task_subscriptions',
  OFFLINE_ACTIONS: 'taskbot_offline_actions',
} as const;

// API configuration
export const API_CONFIG = {
  TIMEOUT: 10000,
  RETRY_ATTEMPTS: 3,
  RETRY_DELAY: 1000,
} as const;

// Validation constants
export const VALIDATION = {
  MIN_PASSWORD_LENGTH: 8,
  MAX_TASK_TITLE_LENGTH: 200,
  MAX_TASK_DESCRIPTION_LENGTH: 2000,
  MAX_MESSAGE_LENGTH: 1000,
  MAX_FILE_SIZE: 10 * 1024 * 1024, // 10MB
  ALLOWED_FILE_TYPES: [
    'image/jpeg',
    'image/png',
    'image/gif',
    'application/pdf',
    'text/plain',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  ],
} as const;

// Feature flags
export const FEATURES = {
  ANALYTICS: process.env.REACT_APP_ENABLE_ANALYTICS === 'true',
  COLLABORATION: process.env.REACT_APP_ENABLE_COLLABORATION === 'true',
  NOTIFICATIONS: process.env.REACT_APP_ENABLE_NOTIFICATIONS === 'true',
  WEBSOCKET: process.env.REACT_APP_ENABLE_WEBSOCKET === 'true',
  DEBUG_MODE: process.env.REACT_APP_DEBUG_MODE === 'true',
} as const;

// Application metadata
export const APP_INFO = {
  NAME: process.env.REACT_APP_BRAND_NAME || 'TaskBot',
  VERSION: process.env.REACT_APP_VERSION || '2.0.0',
  DESCRIPTION: 'Advanced Task Management System',
  AUTHOR: 'TaskBot Team',
  HOMEPAGE: 'https://taskbot.example.com',
  SUPPORT_EMAIL: 'support@taskbot.example.com',
} as const;

// Export type definitions for constants
export type TaskStatus = typeof TASK_STATUS[keyof typeof TASK_STATUS];
export type TaskPriority = typeof TASK_PRIORITY[keyof typeof TASK_PRIORITY];
export type MessageType = typeof MESSAGE_TYPE[keyof typeof MESSAGE_TYPE];
export type ThemeMode = typeof THEME_MODE[keyof typeof THEME_MODE];
export type NotificationType = typeof NOTIFICATION_TYPE[keyof typeof NOTIFICATION_TYPE];
export type AnalyticsTimeframe = typeof ANALYTICS_TIMEFRAME[keyof typeof ANALYTICS_TIMEFRAME];
export type WebSocketMessageType = typeof WS_MESSAGE_TYPE[keyof typeof WS_MESSAGE_TYPE];