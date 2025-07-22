// UI slice for managing application UI state

import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type { UIState, UINotification } from '../../types';

const initialState: UIState = {
  sidebarOpen: true,
  theme: 'light',
  notifications: [],
  loading: {},
  isConnected: false,
  pendingActions: [],
};

const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    // Sidebar
    toggleSidebar: (state) => {
      state.sidebarOpen = !state.sidebarOpen;
    },
    setSidebarOpen: (state, action: PayloadAction<boolean>) => {
      state.sidebarOpen = action.payload;
    },

    // Theme
    toggleTheme: (state) => {
      state.theme = state.theme === 'light' ? 'dark' : 'light';
      localStorage.setItem('theme', state.theme);
    },
    setTheme: (state, action: PayloadAction<'light' | 'dark'>) => {
      state.theme = action.payload;
      localStorage.setItem('theme', action.payload);
    },

    // Notifications
    addNotification: (state, action: PayloadAction<Omit<UINotification, 'id' | 'timestamp' | 'read'>>) => {
      const notification: UINotification = {
        ...action.payload,
        id: Date.now().toString(),
        timestamp: new Date().toISOString(),
        read: false,
      };
      state.notifications.unshift(notification);
      
      // Keep only the last 50 notifications
      if (state.notifications.length > 50) {
        state.notifications = state.notifications.slice(0, 50);
      }
    },
    markNotificationRead: (state, action: PayloadAction<string>) => {
      const notification = state.notifications.find(n => n.id === action.payload);
      if (notification) {
        notification.read = true;
      }
    },
    markAllNotificationsRead: (state) => {
      state.notifications.forEach(notification => {
        notification.read = true;
      });
    },
    removeNotification: (state, action: PayloadAction<string>) => {
      state.notifications = state.notifications.filter(n => n.id !== action.payload);
    },
    clearNotifications: (state) => {
      state.notifications = [];
    },

    // Loading states
    setLoading: (state, action: PayloadAction<{ key: string; loading: boolean }>) => {
      const { key, loading } = action.payload;
      if (loading) {
        state.loading[key] = true;
      } else {
        delete state.loading[key];
      }
    },
    clearLoading: (state, action: PayloadAction<string>) => {
      delete state.loading[action.payload];
    },
    clearAllLoading: (state) => {
      state.loading = {};
    },

    // Utility actions
    showSuccessNotification: (state, action: PayloadAction<{ title: string; message: string; task_id?: number }>) => {
      const notification: UINotification = {
        id: Date.now().toString(),
        type: 'success',
        title: action.payload.title,
        message: action.payload.message,
        timestamp: new Date().toISOString(),
        read: false,
        task_id: action.payload.task_id,
      };
      state.notifications.unshift(notification);
    },
    showErrorNotification: (state, action: PayloadAction<{ title: string; message: string; task_id?: number }>) => {
      const notification: UINotification = {
        id: Date.now().toString(),
        type: 'error',
        title: action.payload.title,
        message: action.payload.message,
        timestamp: new Date().toISOString(),
        read: false,
        task_id: action.payload.task_id,
      };
      state.notifications.unshift(notification);
    },
    showInfoNotification: (state, action: PayloadAction<{ title: string; message: string; task_id?: number }>) => {
      const notification: UINotification = {
        id: Date.now().toString(),
        type: 'info',
        title: action.payload.title,
        message: action.payload.message,
        timestamp: new Date().toISOString(),
        read: false,
        task_id: action.payload.task_id,
      };
      state.notifications.unshift(notification);
    },
    showWarningNotification: (state, action: PayloadAction<{ title: string; message: string; task_id?: number }>) => {
      const notification: UINotification = {
        id: Date.now().toString(),
        type: 'warning',
        title: action.payload.title,
        message: action.payload.message,
        timestamp: new Date().toISOString(),
        read: false,
        task_id: action.payload.task_id,
      };
      state.notifications.unshift(notification);
    },

    // Initialize UI state from localStorage
    initializeUI: (state) => {
      const theme = localStorage.getItem('theme') as 'light' | 'dark' | null;
      if (theme) {
        state.theme = theme;
      }
      
      const sidebarOpen = localStorage.getItem('sidebarOpen');
      if (sidebarOpen !== null) {
        state.sidebarOpen = JSON.parse(sidebarOpen);
      }
    },

    // Connection status
    setConnectionStatus: (state, action: PayloadAction<boolean>) => {
      state.isConnected = action.payload;
    },

    // Pending actions for offline support
    addPendingAction: (state, action: PayloadAction<{ id: string; action: any; timestamp: number }>) => {
      if (!state.pendingActions) {
        state.pendingActions = [];
      }
      state.pendingActions.push(action.payload);
    },
    removePendingAction: (state, action: PayloadAction<string>) => {
      if (state.pendingActions) {
        state.pendingActions = state.pendingActions.filter(a => a.id !== action.payload);
      }
    },
    clearPendingActions: (state) => {
      state.pendingActions = [];
    },

    // Reset state
    resetUIState: () => initialState,
  },
});

export const {
  toggleSidebar,
  setSidebarOpen,
  toggleTheme,
  setTheme,
  addNotification,
  markNotificationRead,
  markAllNotificationsRead,
  removeNotification,
  clearNotifications,
  setLoading,
  clearLoading,
  clearAllLoading,
  showSuccessNotification,
  showErrorNotification,
  showInfoNotification,
  showWarningNotification,
  initializeUI,
  setConnectionStatus,
  addPendingAction,
  removePendingAction,
  clearPendingActions,
  resetUIState,
} = uiSlice.actions;

export default uiSlice.reducer;

// Selectors
export const selectSidebarOpen = (state: { ui: UIState }) => state.ui.sidebarOpen;
export const selectTheme = (state: { ui: UIState }) => state.ui.theme;
export const selectNotifications = (state: { ui: UIState }) => state.ui.notifications;
export const selectUnreadNotifications = (state: { ui: UIState }) => 
  state.ui.notifications.filter(n => !n.read);
export const selectUnreadNotificationCount = (state: { ui: UIState }) => 
  state.ui.notifications.filter(n => !n.read).length;
export const selectLoading = (state: { ui: UIState }) => state.ui.loading;
export const selectIsLoading = (key: string) => (state: { ui: UIState }) => 
  Boolean(state.ui.loading[key]);

// Utility selectors
export const selectRecentNotifications = (limit: number = 10) => (state: { ui: UIState }) =>
  state.ui.notifications.slice(0, limit);

export const selectNotificationsByType = (type: UINotification['type']) => (state: { ui: UIState }) =>
  state.ui.notifications.filter(n => n.type === type);