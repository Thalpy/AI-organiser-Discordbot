import React, { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../UI/Card';
import { Button } from '../UI/Button';
import { Badge } from '../UI/Badge';
import { Alert, AlertDescription } from '../UI/Alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../UI/Tabs';
import { Progress } from '../UI/Progress';
import {
  Calendar,
  Settings,
  Sync,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Clock,
  BarChart3,
  Webhook,
} from 'lucide-react';
import { useCalendarIntegration } from '../../hooks/useCalendarIntegration';
import { CalendarConflictResolver } from './CalendarConflictResolver';
import { CalendarSyncSettings } from './CalendarSyncSettings';
import { CalendarEventsList } from './CalendarEventsList';

interface CalendarIntegrationProps {
  className?: string;
}

export const CalendarIntegration: React.FC<CalendarIntegrationProps> = ({
  className = '',
}) => {
  const {
    syncStatus,
    conflicts,
    events,
    isLoading,
    error,
    setupCalendar,
    triggerSync,
    resolveConflict,
    disableSync,
    refreshStatus,
  } = useCalendarIntegration();

  const [activeTab, setActiveTab] = useState('status');
  const [syncDirection, setSyncDirection] = useState<'bidirectional' | 'task_to_calendar' | 'calendar_to_task'>('bidirectional');

  useEffect(() => {
    refreshStatus();
  }, [refreshStatus]);

  const handleSetupCalendar = async () => {
    try {
      const authUrl = await setupCalendar();
      // Open in new window for OAuth flow
      window.open(authUrl, 'calendar-auth', 'width=600,height=600');
    } catch (err) {
      console.error('Failed to setup calendar:', err);
    }
  };

  const handleSync = async () => {
    try {
      await triggerSync(syncDirection);
      await refreshStatus();
    } catch (err) {
      console.error('Failed to sync calendar:', err);
    }
  };

  const handleDisableSync = async () => {
    if (window.confirm('Are you sure you want to disable calendar synchronization?')) {
      try {
        await disableSync();
        await refreshStatus();
      } catch (err) {
        console.error('Failed to disable sync:', err);
      }
    }
  };

  const getSyncStatusBadge = () => {
    if (!syncStatus) return null;

    if (syncStatus.sync_enabled) {
      return (
        <Badge variant="success" className="flex items-center gap-1">
          <CheckCircle className="h-3 w-3" />
          Enabled
        </Badge>
      );
    } else {
      return (
        <Badge variant="secondary" className="flex items-center gap-1">
          <XCircle className="h-3 w-3" />
          Disabled
        </Badge>
      );
    }
  };

  const formatLastSync = (lastSync: string | null) => {
    if (!lastSync) return 'Never';
    
    const date = new Date(lastSync);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / (1000 * 60));
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} minutes ago`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)} hours ago`;
    return date.toLocaleDateString();
  };

  if (isLoading) {
    return (
      <Card className={className}>
        <CardContent className="flex items-center justify-center py-8">
          <div className="flex items-center gap-2">
            <Sync className="h-4 w-4 animate-spin" />
            Loading calendar integration...
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {error && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Calendar className="h-5 w-5" />
              <CardTitle>Google Calendar Integration</CardTitle>
            </div>
            {getSyncStatusBadge()}
          </div>
          <CardDescription>
            Synchronize your tasks with Google Calendar for better time management
          </CardDescription>
        </CardHeader>
      </Card>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="status">Status</TabsTrigger>
          <TabsTrigger value="conflicts">
            Conflicts
            {conflicts && conflicts.length > 0 && (
              <Badge variant="destructive" className="ml-2">
                {conflicts.length}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="events">Events</TabsTrigger>
          <TabsTrigger value="settings">Settings</TabsTrigger>
        </TabsList>

        <TabsContent value="status" className="space-y-4">
          {!syncStatus?.sync_enabled ? (
            <Card>
              <CardContent className="pt-6">
                <div className="text-center space-y-4">
                  <Calendar className="h-12 w-12 mx-auto text-muted-foreground" />
                  <div>
                    <h3 className="text-lg font-semibold">Calendar Not Connected</h3>
                    <p className="text-muted-foreground">
                      Connect your Google Calendar to automatically sync your tasks
                    </p>
                  </div>
                  <Button onClick={handleSetupCalendar} className="flex items-center gap-2">
                    <Calendar className="h-4 w-4" />
                    Connect Google Calendar
                  </Button>
                </div>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium">Sync Status</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">Last Sync</span>
                      <span className="text-sm font-medium">
                        {formatLastSync(syncStatus.last_sync)}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">Pending Conflicts</span>
                      <Badge variant={syncStatus.pending_conflicts > 0 ? "destructive" : "secondary"}>
                        {syncStatus.pending_conflicts}
                      </Badge>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium">Statistics</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">Total Tasks</span>
                      <span className="text-sm font-medium">
                        {syncStatus.statistics?.total_tasks || 0}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">Synced Tasks</span>
                      <span className="text-sm font-medium">
                        {syncStatus.statistics?.synced_tasks || 0}
                      </span>
                    </div>
                    <div className="space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-muted-foreground">Sync Coverage</span>
                        <span className="text-sm font-medium">
                          {syncStatus.statistics?.sync_coverage?.toFixed(1) || 0}%
                        </span>
                      </div>
                      <Progress 
                        value={syncStatus.statistics?.sync_coverage || 0} 
                        className="h-2"
                      />
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          {syncStatus?.sync_enabled && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium">Manual Sync</CardTitle>
                <CardDescription>
                  Trigger a manual synchronization between tasks and calendar
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-4">
                  <select
                    value={syncDirection}
                    onChange={(e) => setSyncDirection(e.target.value as any)}
                    className="flex h-9 w-[180px] rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  >
                    <option value="bidirectional">Both Directions</option>
                    <option value="task_to_calendar">Tasks → Calendar</option>
                    <option value="calendar_to_task">Calendar → Tasks</option>
                  </select>
                  <Button onClick={handleSync} className="flex items-center gap-2">
                    <Sync className="h-4 w-4" />
                    Sync Now
                  </Button>
                  <Button 
                    variant="outline" 
                    onClick={handleDisableSync}
                    className="flex items-center gap-2"
                  >
                    <XCircle className="h-4 w-4" />
                    Disable Sync
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="conflicts">
          <CalendarConflictResolver
            conflicts={conflicts || []}
            onResolveConflict={resolveConflict}
            onRefresh={refreshStatus}
          />
        </TabsContent>

        <TabsContent value="events">
          <CalendarEventsList events={events || []} />
        </TabsContent>

        <TabsContent value="settings">
          <CalendarSyncSettings
            syncStatus={syncStatus}
            onSettingsChange={refreshStatus}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
};