// RTK Query API for authentication

import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';
import type { User, UserPreferences, NotificationPreferences } from '../../types';

interface LoginRequest {
  email: string;
  password: string;
}

interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

interface RefreshTokenRequest {
  refresh_token: string;
}

export const authApi = createApi({
  reducerPath: 'authApi',
  baseQuery: fetchBaseQuery({
    baseUrl: '/api/v1/auth/',
  }),
  tagTypes: ['User', 'Preferences'],
  endpoints: (builder) => ({
    // Authentication
    login: builder.mutation<LoginResponse, LoginRequest>({
      query: (credentials) => ({
        url: 'login',
        method: 'POST',
        body: credentials,
      }),
    }),

    logout: builder.mutation<{ success: boolean }, void>({
      query: () => ({
        url: 'logout',
        method: 'POST',
      }),
    }),

    refreshToken: builder.mutation<LoginResponse, RefreshTokenRequest>({
      query: (data) => ({
        url: 'refresh',
        method: 'POST',
        body: data,
      }),
    }),

    // Discord OAuth
    discordAuth: builder.mutation<LoginResponse, { code: string; state?: string }>({
      query: (data) => ({
        url: 'discord/callback',
        method: 'POST',
        body: data,
      }),
    }),

    getDiscordAuthUrl: builder.query<{ auth_url: string }, void>({
      query: () => 'discord/auth-url',
    }),

    // User profile
    getProfile: builder.query<User, void>({
      query: () => 'profile',
      providesTags: ['User'],
    }),

    updateProfile: builder.mutation<User, Partial<User>>({
      query: (data) => ({
        url: 'profile',
        method: 'PUT',
        body: data,
      }),
      invalidatesTags: ['User'],
    }),

    // User preferences
    getUserPreferences: builder.query<UserPreferences, void>({
      query: () => 'preferences',
      providesTags: ['Preferences'],
    }),

    updateUserPreferences: builder.mutation<UserPreferences, Partial<UserPreferences>>({
      query: (data) => ({
        url: 'preferences',
        method: 'PUT',
        body: data,
      }),
      invalidatesTags: ['Preferences'],
    }),

    // Notification preferences
    getNotificationPreferences: builder.query<NotificationPreferences, void>({
      query: () => 'notification-preferences',
      providesTags: ['Preferences'],
    }),

    updateNotificationPreferences: builder.mutation<
      NotificationPreferences,
      Partial<NotificationPreferences>
    >({
      query: (data) => ({
        url: 'notification-preferences',
        method: 'PUT',
        body: data,
      }),
      invalidatesTags: ['Preferences'],
    }),

    // API Keys
    getApiKeys: builder.query<{ api_keys: any[] }, void>({
      query: () => 'api-keys',
    }),

    createApiKey: builder.mutation<
      { api_key: string; success: boolean },
      { name: string; permissions: string[]; expires_at?: string }
    >({
      query: (data) => ({
        url: 'api-keys',
        method: 'POST',
        body: data,
      }),
    }),

    revokeApiKey: builder.mutation<{ success: boolean }, number>({
      query: (keyId) => ({
        url: `api-keys/${keyId}`,
        method: 'DELETE',
      }),
    }),
  }),
});

export const {
  useLoginMutation,
  useLogoutMutation,
  useRefreshTokenMutation,
  useDiscordAuthMutation,
  useGetDiscordAuthUrlQuery,
  useGetProfileQuery,
  useUpdateProfileMutation,
  useGetUserPreferencesQuery,
  useUpdateUserPreferencesMutation,
  useGetNotificationPreferencesQuery,
  useUpdateNotificationPreferencesMutation,
  useGetApiKeysQuery,
  useCreateApiKeyMutation,
  useRevokeApiKeyMutation,
} = authApi;