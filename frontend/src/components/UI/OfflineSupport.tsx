// Offline support component with cached data and pending actions

import React, { useEffect, useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  IconButton,
  Chip,
  Alert,
  AlertTitle,
  Collapse,
  LinearProgress,
} from '@mui/material';
import {
  CloudOff as CloudOffIcon,
  CloudQueue as CloudQueueIcon,
  Sync as SyncIcon,
  Delete as DeleteIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
} from '@mui/icons-material';

import { useAppSelector, useAppDispatch } from '../../store/hooks';
import { useWebSocket } from '../../hooks/useWebSocket';
import { selectUser } from '../../store/slices/authSlice';
import {
  clearPendingActions,
  removePendingAction,
  showSuccessNotification,
  showErrorNotification,
} from '../../store/slices/uiSlice';
import { storage } from '../../utils/helpers';
import { STORAGE_KEYS } from '../../utils/constants';
import { api } from '../../utils/api';

interface PendingAction {
  id: string;
  type: string;
  data: any;
  timestamp: number;
  retryCount: number;
  error?: string;
}

interface OfflineSupportProps {
  show?: boolean;
}

const OfflineSupport: React.FC<OfflineSupportProps> = ({ show = true }) => {
  const dispatch = useAppDispatch();
  const user = useAppSelector(selectUser);
  const [pendingActions, setPendingActions] = useState<PendingAction[]>([]);
  const [isExpanded, setIsExpanded] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncProgress, setSyncProgress] = useState(0);

  const { isConnected, isOnline } = useWebSocket(user?.id);

  // Load pending actions from storage
  useEffect(() => {
    const loadPendingActions = () => {
      const stored = storage.get(STORAGE_KEYS.OFFLINE_ACTIONS, []);
      setPendingActions(stored);
    };

    loadPendingActions();
    
    // Reload when storage changes (from other tabs)
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === STORAGE_KEYS.OFFLINE_ACTIONS) {
        loadPendingActions();
      }
    };

    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, []);

  // Auto-sync when connection is restored
  useEffect(() => {
    if (isConnected && isOnline && pendingActions.length > 0) {
      handleSyncPendingActions();
    }
  }, [isConnected, isOnline, pendingActions.length]);

  const handleSyncPendingActions = async () => {
    if (isSyncing || pendingActions.length === 0) return;

    setIsSyncing(true);
    setSyncProgress(0);

    const totalActions = pendingActions.length;
    let completedActions = 0;
    let successCount = 0;
    let failedActions: PendingAction[] = [];

    for (const action of pendingActions) {
      try {
        await executeAction(action);
        successCount++;
        
        // Remove from storage
        const updatedActions = pendingActions.filter(a => a.id !== action.id);
        storage.set(STORAGE_KEYS.OFFLINE_ACTIONS, updatedActions);
        
        dispatch(removePendingAction(action.id));
      } catch (error) {
        console.error('Failed to sync action:', error);
        
        // Increment retry count
        const updatedAction = {
          ...action,
          retryCount: action.retryCount + 1,
          error: error instanceof Error ? error.message : 'Unknown error',
        };
        
        // Keep failed actions with retry limit
        if (updatedAction.retryCount < 3) {
          failedActions.push(updatedAction);
        }
      }

      completedActions++;
      setSyncProgress((completedActions / totalActions) * 100);
    }

    // Update storage with failed actions
    storage.set(STORAGE_KEYS.OFFLINE_ACTIONS, failedActions);
    setPendingActions(failedActions);

    setIsSyncing(false);
    setSyncProgress(0);

    // Show sync results
    if (successCount > 0) {
      dispatch(showSuccessNotification({
        title: 'Sync Complete',
        message: `Successfully synced ${successCount} offline actions`,
      }));
    }

    if (failedActions.length > 0) {
      dispatch(showErrorNotification({
        title: 'Sync Incomplete',
        message: `${failedActions.length} actions failed to sync and will be retried`,
      }));
    }
  };

  const executeAction = async (action: PendingAction): Promise<void> => {
    switch (action.type) {
      case 'create_task':
        await api.post('/tasks', action.data);
        break;
      case 'update_task':
        await api.put(`/tasks/${action.data.id}`, action.data);
        break;
      case 'delete_task':
        await api.delete(`/tasks/${action.data.id}`);
        break;
      case 'send_message':
        await api.post(`/tasks/${action.data.taskId}/messages`, action.data);
        break;
      case 'update_task_status':
        await api.put(`/tasks/${action.data.id}/status`, { status: action.data.status });
        break;
      default:
        throw new Error(`Unknown action type: ${action.type}`);
    }
  };

  const handleRemoveAction = (actionId: string) => {
    const updatedActions = pendingActions.filter(a => a.id !== actionId);
    setPendingActions(updatedActions);
    storage.set(STORAGE_KEYS.OFFLINE_ACTIONS, updatedActions);
    dispatch(removePendingAction(actionId));
  };

  const handleClearAllActions = () => {
    setPendingActions([]);
    storage.remove(STORAGE_KEYS.OFFLINE_ACTIONS);
    dispatch(clearPendingActions());
  };

  const getActionDescription = (action: PendingAction): string => {
    switch (action.type) {
      case 'create_task':
        return `Create task: ${action.data.title || 'Untitled'}`;
      case 'update_task':
        return `Update task: ${action.data.title || `Task #${action.data.id}`}`;
      case 'delete_task':
        return `Delete task #${action.data.id}`;
      case 'send_message':
        return `Send message in task #${action.data.taskId}`;
      case 'update_task_status':
        return `Update task #${action.data.id} status to ${action.data.status}`;
      default:
        return `Unknown action: ${action.type}`;
    }
  };

  const getActionIcon = (action: PendingAction) => {
    if (action.error) {
      return <WarningIcon color="error" />;
    }
    return <CloudQueueIcon color="primary" />;
  };

  if (!show || (!isOnline && pendingActions.length === 0)) {
    return null;
  }

  return (
    <Box sx={{ position: 'fixed', bottom: 16, right: 16, zIndex: 1300, maxWidth: 400 }}>
      {/* Offline Status Alert */}
      {!isOnline && (
        <Alert
          severity="warning"
          icon={<CloudOffIcon />}
          sx={{ mb: 2 }}
        >
          <AlertTitle>Working Offline</AlertTitle>
          You're currently offline. Changes will be synced when connection is restored.
        </Alert>
      )}

      {/* Pending Actions */}
      {pendingActions.length > 0 && (
        <Paper elevation={6} sx={{ mb: 2 }}>
          <Box
            sx={{
              p: 2,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              cursor: 'pointer',
            }}
            onClick={() => setIsExpanded(!isExpanded)}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <CloudQueueIcon color="primary" />
              <Typography variant="subtitle2">
                {pendingActions.length} Pending Action{pendingActions.length !== 1 ? 's' : ''}
              </Typography>
              <Chip
                label={isConnected ? 'Ready to sync' : 'Waiting for connection'}
                size="small"
                color={isConnected ? 'success' : 'warning'}
                variant="outlined"
              />
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              {isConnected && !isSyncing && (
                <Button
                  size="small"
                  startIcon={<SyncIcon />}
                  onClick={(e) => {
                    e.stopPropagation();
                    handleSyncPendingActions();
                  }}
                >
                  Sync Now
                </Button>
              )}
              <IconButton size="small">
                {isExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
              </IconButton>
            </Box>
          </Box>

          {isSyncing && (
            <Box sx={{ px: 2, pb: 1 }}>
              <LinearProgress variant="determinate" value={syncProgress} />
              <Typography variant="caption" color="text.secondary">
                Syncing... {Math.round(syncProgress)}%
              </Typography>
            </Box>
          )}

          <Collapse in={isExpanded}>
            <Box sx={{ borderTop: 1, borderColor: 'divider' }}>
              <List dense>
                {pendingActions.map((action) => (
                  <ListItem
                    key={action.id}
                    sx={{
                      bgcolor: action.error ? 'error.light' : 'transparent',
                      '&:hover': { bgcolor: 'action.hover' },
                    }}
                  >
                    <ListItemIcon>{getActionIcon(action)}</ListItemIcon>
                    <ListItemText
                      primary={getActionDescription(action)}
                      secondary={
                        <Box>
                          <Typography variant="caption" color="text.secondary">
                            {new Date(action.timestamp).toLocaleString()}
                          </Typography>
                          {action.error && (
                            <Typography variant="caption" color="error" display="block">
                              Error: {action.error} (Retry {action.retryCount}/3)
                            </Typography>
                          )}
                        </Box>
                      }
                    />
                    <IconButton
                      size="small"
                      onClick={() => handleRemoveAction(action.id)}
                    >
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </ListItem>
                ))}
              </List>

              <Box sx={{ p: 2, borderTop: 1, borderColor: 'divider' }}>
                <Button
                  size="small"
                  color="error"
                  onClick={handleClearAllActions}
                  fullWidth
                >
                  Clear All Pending Actions
                </Button>
              </Box>
            </Box>
          </Collapse>
        </Paper>
      )}

      {/* Connection Restored Alert */}
      {isConnected && isOnline && pendingActions.length === 0 && (
        <Alert
          severity="success"
          icon={<CheckCircleIcon />}
          onClose={() => {}} // Auto-hide after timeout
        >
          All changes synced successfully!
        </Alert>
      )}
    </Box>
  );
};

export default OfflineSupport;