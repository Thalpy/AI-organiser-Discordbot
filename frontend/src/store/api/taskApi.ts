// RTK Query API for task management

import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';
import type {
  Task,
  TaskCreateRequest,
  TaskUpdateRequest,
  TaskAssignRequest,
  TaskMessageRequest,
  TaskResponse,
  TaskListResponse,
  TaskMessage,
  TaskFilters,
  PaginationParams,
} from '../../types';
import type { RootState } from '../index';

export const taskApi = createApi({
  reducerPath: 'taskApi',
  baseQuery: fetchBaseQuery({
    baseUrl: '/api/v1/',
    prepareHeaders: (headers, { getState }) => {
      const token = (getState() as RootState).auth.token;
      if (token) {
        headers.set('authorization', `Bearer ${token}`);
      }
      return headers;
    },
  }),
  tagTypes: ['Task', 'TaskMessage', 'Template'],
  endpoints: (builder) => ({
    // Task CRUD operations
    getTasks: builder.query<TaskListResponse, TaskFilters & PaginationParams>({
      query: (params) => ({
        url: 'tasks',
        params: {
          ...params,
          // Convert undefined values to avoid sending them
          ...Object.fromEntries(
            Object.entries(params).filter(([_, value]) => value !== undefined)
          ),
        },
      }),
      providesTags: (result) =>
        result
          ? [
              ...result.tasks.map(({ id }) => ({ type: 'Task' as const, id })),
              { type: 'Task', id: 'LIST' },
            ]
          : [{ type: 'Task', id: 'LIST' }],
    }),

    getTask: builder.query<TaskResponse, number>({
      query: (id) => `tasks/${id}`,
      providesTags: (result, error, id) => [{ type: 'Task', id }],
    }),

    createTask: builder.mutation<TaskResponse, TaskCreateRequest>({
      query: (task) => ({
        url: 'tasks',
        method: 'POST',
        body: task,
      }),
      invalidatesTags: [{ type: 'Task', id: 'LIST' }],
    }),

    updateTask: builder.mutation<
      { success: boolean; task: Task },
      { id: number; data: TaskUpdateRequest }
    >({
      query: ({ id, data }) => ({
        url: `tasks/${id}`,
        method: 'PUT',
        body: data,
      }),
      invalidatesTags: (result, error, { id }) => [
        { type: 'Task', id },
        { type: 'Task', id: 'LIST' },
      ],
    }),

    deleteTask: builder.mutation<{ success: boolean }, number>({
      query: (id) => ({
        url: `tasks/${id}`,
        method: 'DELETE',
      }),
      invalidatesTags: (result, error, id) => [
        { type: 'Task', id },
        { type: 'Task', id: 'LIST' },
      ],
    }),

    // Task assignment
    assignTask: builder.mutation<
      { success: boolean; assigned_users: string[]; task: Task },
      { id: number; data: TaskAssignRequest }
    >({
      query: ({ id, data }) => ({
        url: `tasks/${id}/assign`,
        method: 'POST',
        body: data,
      }),
      invalidatesTags: (result, error, { id }) => [
        { type: 'Task', id },
        { type: 'Task', id: 'LIST' },
      ],
    }),

    // Task messages
    getTaskMessages: builder.query<{ messages: TaskMessage[] }, number>({
      query: (taskId) => `tasks/${taskId}/messages`,
      providesTags: (result, error, taskId) => [
        { type: 'TaskMessage', id: taskId },
      ],
    }),

    addTaskMessage: builder.mutation<
      TaskMessage,
      { taskId: number; data: TaskMessageRequest }
    >({
      query: ({ taskId, data }) => ({
        url: `tasks/${taskId}/messages`,
        method: 'POST',
        body: data,
      }),
      invalidatesTags: (result, error, { taskId }) => [
        { type: 'TaskMessage', id: taskId },
        { type: 'Task', id: taskId },
      ],
    }),

    updateTaskMessage: builder.mutation<
      TaskMessage,
      { id: number; message: string }
    >({
      query: ({ id, message }) => ({
        url: `messages/${id}`,
        method: 'PUT',
        body: { message },
      }),
      invalidatesTags: ['TaskMessage'],
    }),

    deleteTaskMessage: builder.mutation<{ success: boolean }, number>({
      query: (id) => ({
        url: `messages/${id}`,
        method: 'DELETE',
      }),
      invalidatesTags: ['TaskMessage'],
    }),

    // Task templates
    getTemplates: builder.query<
      { templates: any[] },
      { include_shared?: boolean }
    >({
      query: (params) => ({
        url: 'templates',
        params,
      }),
      providesTags: [{ type: 'Template', id: 'LIST' }],
    }),

    createTemplate: builder.mutation<
      { template_id: number; success: boolean },
      any
    >({
      query: (template) => ({
        url: 'templates',
        method: 'POST',
        body: template,
      }),
      invalidatesTags: [{ type: 'Template', id: 'LIST' }],
    }),

    // Task actions
    startTask: builder.mutation<{ success: boolean; task: Task }, number>({
      query: (id) => ({
        url: `tasks/${id}`,
        method: 'PUT',
        body: { status: 'in_progress' },
      }),
      invalidatesTags: (result, error, id) => [
        { type: 'Task', id },
        { type: 'Task', id: 'LIST' },
      ],
    }),

    completeTask: builder.mutation<
      { success: boolean; task: Task },
      { id: number; notes?: string }
    >({
      query: ({ id, notes }) => ({
        url: `tasks/${id}`,
        method: 'PUT',
        body: {
          status: 'completed',
          collaboration_notes: notes,
        },
      }),
      invalidatesTags: (result, error, { id }) => [
        { type: 'Task', id },
        { type: 'Task', id: 'LIST' },
      ],
    }),

    updateTaskProgress: builder.mutation<
      { success: boolean; task: Task },
      { id: number; progress: number; notes?: string }
    >({
      query: ({ id, progress, notes }) => ({
        url: `tasks/${id}`,
        method: 'PUT',
        body: {
          completion_percentage: progress,
          collaboration_notes: notes,
        },
      }),
      invalidatesTags: (result, error, { id }) => [
        { type: 'Task', id },
        { type: 'Task', id: 'LIST' },
      ],
    }),
  }),
});

export const {
  useGetTasksQuery,
  useGetTaskQuery,
  useCreateTaskMutation,
  useUpdateTaskMutation,
  useDeleteTaskMutation,
  useAssignTaskMutation,
  useGetTaskMessagesQuery,
  useAddTaskMessageMutation,
  useUpdateTaskMessageMutation,
  useDeleteTaskMessageMutation,
  useGetTemplatesQuery,
  useCreateTemplateMutation,
  useStartTaskMutation,
  useCompleteTaskMutation,
  useUpdateTaskProgressMutation,
} = taskApi;