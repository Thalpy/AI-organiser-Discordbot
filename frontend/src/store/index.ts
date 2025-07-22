// Redux store configuration with RTK Query

import { configureStore } from '@reduxjs/toolkit';
import { setupListeners } from '@reduxjs/toolkit/query';

import { taskApi } from './api/taskApi';
import { authApi } from './api/authApi';
import { analyticsApi } from './api/analyticsApi';
import authSlice from './slices/authSlice';
import uiSlice from './slices/uiSlice';
import taskSlice from './slices/taskSlice';

export const store = configureStore({
  reducer: {
    // API slices
    [taskApi.reducerPath]: taskApi.reducer,
    [authApi.reducerPath]: authApi.reducer,
    [analyticsApi.reducerPath]: analyticsApi.reducer,
    
    // Regular slices
    auth: authSlice,
    ui: uiSlice,
    tasks: taskSlice,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: [
          // Ignore these action types
          'persist/PERSIST',
          'persist/REHYDRATE',
        ],
        ignoredPaths: ['register'],
      },
    }).concat(
      taskApi.middleware,
      authApi.middleware,
      analyticsApi.middleware
    ),
  devTools: process.env.NODE_ENV !== 'production',
});

// Enable listener behavior for the store
setupListeners(store.dispatch);

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

// Export hooks
export { useAppDispatch, useAppSelector } from './hooks';