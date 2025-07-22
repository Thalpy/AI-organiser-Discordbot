import { useState, useCallback } from 'react';
import { api } from '../utils/api';

interface CalendarSyncStatus {
  sync_enabled: boolean;
  last_sync: string | null;
  pending_conflicts: number;
  conflicts: CalendarConflict[];
  statistics: {
    total_tasks: number;
    synced_tasks: number;
    sync_coverage: number;
  };
}

interface CalendarConflict {
  task_id: number;
  calendar_event_id: string;
  conflict_type: string;
  task_updated: string;
  calendar_updated: string;
  task_data: {
    title: string;
    due_time: string | null;
    location: string | null;
  };
  calendar_data: {
    title: string;
    start_time: string;
    end_time: string;
    location: string | null;
  };
}

interface CalendarEvent {
  id: string;
  title: string;
  description: string | null;
  start_time: string;
  end_time: string;
  location: string | null;
  attendees: string[];
  task_id: number | null;
  created: string | null;
  updated: string | null;
}

interface SyncResult {
  tasks_synced_to_calendar: number;
  calendar_events_synced_to_tasks: number;
  conflicts_detected: number;
  conflicts_resolved: number;
  errors: string[];
}

export const useCalendarIntegration = () => {
  const [syncStatus, setSyncStatus] = useState<CalendarSyncStatus | null>(null);
  const [conflicts, setConflicts] = useState<CalendarConflict[]>([]);
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleError = (err: any) => {
    const message = err.response?.data?.detail || err.message || 'An unexpected error occurred';
    setError(message);
    console.error('Calendar integration error:', err);
  };

  const refreshStatus = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await api.get('/calendar/status');
      setSyncStatus(response.data.data);
    } catch (err) {
      handleError(err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const setupCalendar = useCallback(async (): Promise<string> => {
    setError(null);
    
    try {
      const response = await api.get('/calendar/auth-url');
      return response.data.auth_url;
    } catch (err) {
      handleError(err);
      throw err;
    }
  }, []);

  const handleOAuthCallback = useCallback(async (code: string) => {
    setError(null);
    
    try {
      await api.post('/calendar/oauth-callback', { code });
      await refreshStatus();
      return true;
    } catch (err) {
      handleError(err);
      return false;
    }
  }, [refreshStatus]);

  const triggerSync = useCallback(async (direction: 'bidirectional' | 'task_to_calendar' | 'calendar_to_task' = 'bidirectional'): Promise<SyncResult> => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await api.post('/calendar/sync', { direction });
      return response.data.sync_result;
    } catch (err) {
      handleError(err);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const getConflicts = useCallback(async () => {
    setError(null);
    
    try {
      const response = await api.get('/calendar/conflicts');
      setConflicts(response.data.conflicts);
      return response.data.conflicts;
    } catch (err) {
      handleError(err);
      return [];
    }
  }, []);

  const resolveConflict = useCallback(async (taskId: number, resolution: string) => {
    setError(null);
    
    try {
      await api.post('/calendar/resolve-conflict', {
        task_id: taskId,
        resolution
      });
      
      // Refresh conflicts after resolution
      await getConflicts();
    } catch (err) {
      handleError(err);
      throw err;
    }
  }, [getConflicts]);

  const getEvents = useCallback(async (daysAhead: number = 30) => {
    setError(null);
    
    try {
      const response = await api.get(`/calendar/events?days_ahead=${daysAhead}`);
      setEvents(response.data.events);
      return response.data.events;
    } catch (err) {
      handleError(err);
      return [];
    }
  }, []);

  const disableSync = useCallback(async () => {
    setError(null);
    
    try {
      await api.post('/calendar/disable');
      setSyncStatus(null);
      setConflicts([]);
      setEvents([]);
    } catch (err) {
      handleError(err);
      throw err;
    }
  }, []);

  const scheduleAutoSync = useCallback(async (intervalMinutes: number) => {
    setError(null);
    
    try {
      await api.post('/calendar/schedule-auto-sync', {
        interval_minutes: intervalMinutes
      });
    } catch (err) {
      handleError(err);
      throw err;
    }
  }, []);

  const handleWebhook = useCallback(async (webhookData: any) => {
    setError(null);
    
    try {
      await api.post('/calendar/webhook', webhookData);
      // Refresh status after webhook processing
      await refreshStatus();
    } catch (err) {
      handleError(err);
      throw err;
    }
  }, [refreshStatus]);

  return {
    // State
    syncStatus,
    conflicts,
    events,
    isLoading,
    error,
    
    // Actions
    setupCalendar,
    handleOAuthCallback,
    triggerSync,
    getConflicts,
    resolveConflict,
    getEvents,
    disableSync,
    scheduleAutoSync,
    handleWebhook,
    refreshStatus,
    
    // Utilities
    clearError: () => setError(null),
  };
};