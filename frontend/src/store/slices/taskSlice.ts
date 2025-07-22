// Task slice for managing task state

import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type { TaskState, Task, TaskFilters } from '../../types';

const initialState: TaskState = {
  tasks: [],
  selectedTask: null,
  loading: false,
  error: null,
  filters: {
    status: undefined,
    priority: undefined,
    assigned_to: undefined,
    created_by: undefined,
    search: undefined,
    due_date_from: undefined,
    due_date_to: undefined,
    is_collaborative: undefined,
  },
  pagination: {
    page: 1,
    per_page: 25,
    total: 0,
  },
};

const taskSlice = createSlice({
  name: 'tasks',
  initialState,
  reducers: {
    // Loading states
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.loading = action.payload;
    },
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
    },
    clearError: (state) => {
      state.error = null;
    },

    // Task management
    setTasks: (state, action: PayloadAction<Task[]>) => {
      state.tasks = action.payload;
    },
    addTask: (state, action: PayloadAction<Task>) => {
      state.tasks.unshift(action.payload);
      state.pagination.total += 1;
    },
    updateTask: (state, action: PayloadAction<Task>) => {
      const index = state.tasks.findIndex(task => task.id === action.payload.id);
      if (index !== -1) {
        state.tasks[index] = action.payload;
      }
      if (state.selectedTask?.id === action.payload.id) {
        state.selectedTask = action.payload;
      }
    },
    removeTask: (state, action: PayloadAction<number>) => {
      state.tasks = state.tasks.filter(task => task.id !== action.payload);
      if (state.selectedTask?.id === action.payload) {
        state.selectedTask = null;
      }
      state.pagination.total -= 1;
    },

    // Selected task
    setSelectedTask: (state, action: PayloadAction<Task | null>) => {
      state.selectedTask = action.payload;
    },

    // Filters
    setFilters: (state, action: PayloadAction<Partial<TaskFilters>>) => {
      state.filters = { ...state.filters, ...action.payload };
      // Reset pagination when filters change
      state.pagination.page = 1;
    },
    clearFilters: (state) => {
      state.filters = initialState.filters;
      state.pagination.page = 1;
    },
    setSearchFilter: (state, action: PayloadAction<string>) => {
      state.filters.search = action.payload;
      state.pagination.page = 1;
    },

    // Pagination
    setPagination: (state, action: PayloadAction<Partial<typeof initialState.pagination>>) => {
      state.pagination = { ...state.pagination, ...action.payload };
    },
    setPage: (state, action: PayloadAction<number>) => {
      state.pagination.page = action.payload;
    },
    setPerPage: (state, action: PayloadAction<number>) => {
      state.pagination.per_page = action.payload;
      state.pagination.page = 1; // Reset to first page
    },

    // Real-time updates
    handleTaskUpdate: (state, action: PayloadAction<Task>) => {
      const task = action.payload;
      const index = state.tasks.findIndex(t => t.id === task.id);
      
      if (index !== -1) {
        state.tasks[index] = task;
      } else {
        // Task might be new or filtered out, add it if it matches current filters
        state.tasks.unshift(task);
      }
      
      if (state.selectedTask?.id === task.id) {
        state.selectedTask = task;
      }
    },

    // Bulk operations
    updateMultipleTasks: (state, action: PayloadAction<Task[]>) => {
      action.payload.forEach(updatedTask => {
        const index = state.tasks.findIndex(task => task.id === updatedTask.id);
        if (index !== -1) {
          state.tasks[index] = updatedTask;
        }
      });
    },

    // Task status updates
    updateTaskStatus: (state, action: PayloadAction<{ id: number; status: string }>) => {
      const { id, status } = action.payload;
      const task = state.tasks.find(t => t.id === id);
      if (task) {
        task.status = status as any;
      }
      if (state.selectedTask?.id === id) {
        state.selectedTask.status = status as any;
      }
    },

    // Task progress updates
    updateTaskProgress: (state, action: PayloadAction<{ id: number; progress: number }>) => {
      const { id, progress } = action.payload;
      const task = state.tasks.find(t => t.id === id);
      if (task) {
        task.completion_percentage = progress;
      }
      if (state.selectedTask?.id === id) {
        state.selectedTask.completion_percentage = progress;
      }
    },

    // Optimistic updates for better UX
    optimisticTaskUpdate: (state, action: PayloadAction<{ id: number; changes: Partial<Task> }>) => {
      const { id, changes } = action.payload;
      const task = state.tasks.find(t => t.id === id);
      if (task) {
        Object.assign(task, changes);
      }
      if (state.selectedTask?.id === id) {
        Object.assign(state.selectedTask, changes);
      }
    },

    // Task messages and collaboration
    addTaskMessage: (state, action: PayloadAction<{ taskId: number; message: any }>) => {
      const { taskId, message } = action.payload;
      const task = state.tasks.find(t => t.id === taskId);
      if (task) {
        if (!task.messages) {
          task.messages = [];
        }
        task.messages.push(message);
      }
      if (state.selectedTask?.id === taskId) {
        if (!state.selectedTask.messages) {
          state.selectedTask.messages = [];
        }
        state.selectedTask.messages.push(message);
      }
    },

    // Collaborators management
    updateTaskCollaborators: (state, action: PayloadAction<{ taskId: number; collaborators: string[] }>) => {
      const { taskId, collaborators } = action.payload;
      const task = state.tasks.find(t => t.id === taskId);
      if (task) {
        task.assigned_users = collaborators;
      }
      if (state.selectedTask?.id === taskId) {
        state.selectedTask.assigned_users = collaborators;
      }
    },

    // Typing indicators
    setTaskTypingUsers: (state, action: PayloadAction<{ taskId: number; typingUsers: string[] }>) => {
      const { taskId, typingUsers } = action.payload;
      const task = state.tasks.find(t => t.id === taskId);
      if (task) {
        task.typingUsers = typingUsers;
      }
      if (state.selectedTask?.id === taskId) {
        state.selectedTask.typingUsers = typingUsers;
      }
    },

    // Reset state
    resetTaskState: () => initialState,
  },
});

export const {
  setLoading,
  setError,
  clearError,
  setTasks,
  addTask,
  updateTask,
  removeTask,
  setSelectedTask,
  setFilters,
  clearFilters,
  setSearchFilter,
  setPagination,
  setPage,
  setPerPage,
  handleTaskUpdate,
  updateMultipleTasks,
  updateTaskStatus,
  updateTaskProgress,
  optimisticTaskUpdate,
  addTaskMessage,
  updateTaskCollaborators,
  setTaskTypingUsers,
  resetTaskState,
} = taskSlice.actions;

export default taskSlice.reducer;

// Selectors
export const selectTasks = (state: { tasks: TaskState }) => state.tasks.tasks;
export const selectSelectedTask = (state: { tasks: TaskState }) => state.tasks.selectedTask;
export const selectTaskLoading = (state: { tasks: TaskState }) => state.tasks.loading;
export const selectTaskError = (state: { tasks: TaskState }) => state.tasks.error;
export const selectTaskFilters = (state: { tasks: TaskState }) => state.tasks.filters;
export const selectTaskPagination = (state: { tasks: TaskState }) => state.tasks.pagination;

// Computed selectors
export const selectFilteredTasks = (state: { tasks: TaskState }) => {
  const { tasks, filters } = state.tasks;
  
  return tasks.filter(task => {
    if (filters.status && task.status !== filters.status) return false;
    if (filters.priority && task.priority !== filters.priority) return false;
    if (filters.assigned_to && !task.assigned_users.includes(filters.assigned_to)) return false;
    if (filters.created_by && task.created_by_user_id !== filters.created_by) return false;
    if (filters.is_collaborative !== undefined && task.is_collaborative !== filters.is_collaborative) return false;
    if (filters.search && !task.description.toLowerCase().includes(filters.search.toLowerCase())) return false;
    
    return true;
  });
};

export const selectTaskCounts = (state: { tasks: TaskState }) => {
  const tasks = state.tasks.tasks;
  
  return {
    total: tasks.length,
    pending: tasks.filter(t => t.status === 'pending').length,
    in_progress: tasks.filter(t => t.status === 'in_progress').length,
    completed: tasks.filter(t => t.status === 'completed').length,
    collaborative: tasks.filter(t => t.is_collaborative).length,
  };
};