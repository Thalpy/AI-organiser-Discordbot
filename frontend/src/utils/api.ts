// API utility functions and configuration

import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';

// API configuration
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000/api';
const WS_BASE_URL = process.env.REACT_APP_WS_BASE_URL || 'ws://localhost:8000/ws';

// Create axios instance with default configuration
const createApiClient = (): AxiosInstance => {
  const client = axios.create({
    baseURL: API_BASE_URL,
    timeout: 10000,
    headers: {
      'Content-Type': 'application/json',
    },
  });

  // Request interceptor to add auth token
  client.interceptors.request.use(
    (config) => {
      const token = localStorage.getItem('taskbot_auth_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    },
    (error) => {
      return Promise.reject(error);
    }
  );

  // Response interceptor for error handling
  client.interceptors.response.use(
    (response: AxiosResponse) => {
      return response;
    },
    (error) => {
      if (error.response?.status === 401) {
        // Token expired or invalid
        localStorage.removeItem('taskbot_auth_token');
        window.location.href = '/login';
      }
      return Promise.reject(error);
    }
  );

  return client;
};

// Export configured API client
export const apiClient = createApiClient();

// API endpoint helpers
export const endpoints = {
  // Authentication
  auth: {
    login: '/auth/token',
    profile: '/users/me',
    refresh: '/auth/refresh',
  },
  
  // Tasks
  tasks: {
    list: '/tasks',
    create: '/tasks',
    get: (id: number) => `/tasks/${id}`,
    update: (id: number) => `/tasks/${id}`,
    delete: (id: number) => `/tasks/${id}`,
    assign: (id: number) => `/tasks/${id}/assign`,
    progress: (id: number) => `/tasks/${id}/progress`,
    messages: (id: number) => `/tasks/${id}/messages`,
    collaborative: '/tasks/collaborative',
  },
  
  // Users
  users: {
    list: '/users',
    get: (id: string) => `/users/${id}`,
    preferences: '/users/me/preferences',
    notifications: '/users/me/notifications',
  },
  
  // Analytics
  analytics: {
    user: '/analytics',
    team: '/analytics/team',
    recommendations: '/analytics/recommendations',
    export: '/analytics/export',
    goals: '/analytics/goals',
    goal: (id: number) => `/analytics/goals/${id}`,
  },
  
  // Notifications
  notifications: {
    taskAssignment: '/notifications/task-assignment',
    taskUpdate: '/notifications/task-update',
    reminder: '/notifications/reminder',
    preferences: '/notifications/preferences',
  },
};

// WebSocket URL helper
export const getWebSocketUrl = (userId: string): string => {
  return `${WS_BASE_URL}/${userId}`;
};

// API response types
export interface ApiResponse<T = any> {
  data: T;
  message?: string;
  success: boolean;
}

export interface PaginatedResponse<T = any> {
  items: T[];
  total: number;
  page: number;
  limit: number;
  pages: number;
}

// Error handling utilities
export class ApiError extends Error {
  constructor(
    message: string,
    public status?: number,
    public code?: string,
    public details?: any
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export const handleApiError = (error: any): ApiError => {
  if (error.response) {
    // Server responded with error status
    const { status, data } = error.response;
    return new ApiError(
      data.detail || data.message || 'An error occurred',
      status,
      data.code,
      data
    );
  } else if (error.request) {
    // Request was made but no response received
    return new ApiError('Network error - please check your connection');
  } else {
    // Something else happened
    return new ApiError(error.message || 'An unexpected error occurred');
  }
};

// Request helpers
export const makeRequest = async <T = any>(
  config: AxiosRequestConfig
): Promise<T> => {
  try {
    const response = await apiClient(config);
    return response.data;
  } catch (error) {
    throw handleApiError(error);
  }
};

// Common request methods
export const api = {
  get: <T = any>(url: string, config?: AxiosRequestConfig): Promise<T> =>
    makeRequest({ method: 'GET', url, ...config }),
    
  post: <T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> =>
    makeRequest({ method: 'POST', url, data, ...config }),
    
  put: <T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> =>
    makeRequest({ method: 'PUT', url, data, ...config }),
    
  patch: <T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> =>
    makeRequest({ method: 'PATCH', url, data, ...config }),
    
  delete: <T = any>(url: string, config?: AxiosRequestConfig): Promise<T> =>
    makeRequest({ method: 'DELETE', url, ...config }),
};

export default api;