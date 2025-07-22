// Analytics API endpoints

import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';
import { AnalyticsData, AnalyticsTimeframe } from '../../types';

interface AnalyticsQuery {
  timeframe: AnalyticsTimeframe;
  start_date: string;
  end_date: string;
  user_id?: string;
}

interface AnalyticsResponse {
  analytics: AnalyticsData;
  recommendations: Array<{
    id: string;
    type: 'productivity' | 'time_management' | 'goal_setting' | 'efficiency';
    title: string;
    description: string;
    impact: 'high' | 'medium' | 'low';
    effort: 'high' | 'medium' | 'low';
    category: string;
    actionable_steps?: string[];
    estimated_improvement?: number;
  }>;
  charts: {
    productivity?: Array<{
      date: string;
      completed_tasks: number;
      total_tasks: number;
      completion_rate: number;
      avg_duration: number;
      performance_score: number;
    }>;
    completion?: Array<{
      status: string;
      count: number;
      percentage: number;
    }>;
    priority_distribution?: Array<{
      priority: string;
      count: number;
      percentage: number;
      completion_rate: number;
    }>;
    time_tracking?: Array<{
      hour: number;
      tasks_completed: number;
      avg_duration: number;
      efficiency_score: number;
    }>;
  };
}

interface GoalCreateRequest {
  title: string;
  goal_type: 'completion_rate' | 'daily_tasks' | 'time_management';
  target_value: number;
  period_type: 'daily' | 'weekly' | 'monthly';
  end_date?: string;
}

interface GoalUpdateRequest {
  id: number;
  title?: string;
  target_value?: number;
  current_value?: number;
  is_active?: boolean;
}

export const analyticsApi = createApi({
  reducerPath: 'analyticsApi',
  baseQuery: fetchBaseQuery({
    baseUrl: '/api/analytics',
    prepareHeaders: (headers, { getState }) => {
      // Add authentication token if available
      const token = (getState() as any).auth.token;
      if (token) {
        headers.set('authorization', `Bearer ${token}`);
      }
      return headers;
    },
  }),
  tagTypes: ['Analytics', 'Goals'],
  endpoints: (builder) => ({
    // Get analytics data
    getAnalytics: builder.query<AnalyticsResponse, AnalyticsQuery>({
      query: (params) => ({
        url: '',
        params,
      }),
      providesTags: ['Analytics'],
    }),

    // Get user goals
    getUserGoals: builder.query<{ goals: any[] }, void>({
      query: () => '/goals',
      providesTags: ['Goals'],
    }),

    // Create new goal
    createGoal: builder.mutation<{ goal: any }, GoalCreateRequest>({
      query: (goalData) => ({
        url: '/goals',
        method: 'POST',
        body: goalData,
      }),
      invalidatesTags: ['Goals'],
    }),

    // Update goal
    updateGoal: builder.mutation<{ goal: any }, GoalUpdateRequest>({
      query: ({ id, ...goalData }) => ({
        url: `/goals/${id}`,
        method: 'PUT',
        body: goalData,
      }),
      invalidatesTags: ['Goals'],
    }),

    // Delete goal
    deleteGoal: builder.mutation<void, number>({
      query: (id) => ({
        url: `/goals/${id}`,
        method: 'DELETE',
      }),
      invalidatesTags: ['Goals'],
    }),

    // Export analytics data
    exportAnalytics: builder.mutation<Blob, {
      format: 'csv' | 'pdf';
      timeframe: AnalyticsTimeframe;
      start_date: string;
      end_date: string;
    }>({
      query: (params) => ({
        url: '/export',
        method: 'POST',
        body: params,
        responseHandler: (response) => response.blob(),
      }),
    }),

    // Get productivity recommendations
    getRecommendations: builder.query<{
      recommendations: any[];
      performance_score: number;
    }, void>({
      query: () => '/recommendations',
      providesTags: ['Analytics'],
    }),

    // Update recommendation status
    updateRecommendationStatus: builder.mutation<void, {
      id: string;
      status: 'implemented' | 'dismissed' | 'remind_later';
    }>({
      query: ({ id, status }) => ({
        url: `/recommendations/${id}`,
        method: 'PUT',
        body: { status },
      }),
      invalidatesTags: ['Analytics'],
    }),
  }),
});

export const {
  useGetAnalyticsQuery,
  useGetUserGoalsQuery,
  useCreateGoalMutation,
  useUpdateGoalMutation,
  useDeleteGoalMutation,
  useExportAnalyticsMutation,
  useGetRecommendationsQuery,
  useUpdateRecommendationStatusMutation,
} = analyticsApi;