// Real-time notifications component with WebSocket integration

import React, { useState, useEffect } from 'react';
import {
  Snackbar,
  Alert,
  AlertTitle,
  Box,
  IconButton,
  Badge,
  Popover,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Typography,
  Button,
  Divider,
  Chip,
} from '@mui/material';
import {
  Notifications as NotificationsIcon,
  Close as CloseIcon,
  Task as TaskIcon,
  Assignment as AssignmentIcon,
  Message as MessageIcon,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
  Info as InfoIcon,
  WifiOff as WifiOffIcon,
  Wifi as WifiIcon,
} from '@mui/icons-material';
import { formatDistanceToNow } from 'date-fns';

import { useAppSelector, useAppDispatch } from '../../store/hooks';
import { useWebSocket } from '../../hooks/useWebSocket';
import {
  selectNotifications,
  selectUnreadNotificationCount,
  markNotificationRead,
  markAllNotificationsRead,
  removeNotification,
} from '../../store/slices/uiSlice';
import { selectUser } from '../../store/slices/authSlice';
import { truncateText } from '../../utils/helpers';

interface NotificationItemProps {
  notification: any;
  onRead: (id: string) => void;
  onRemove: (id: string) => void;
}

const NotificationItem: React.FC<NotificationItemProps> = ({ notification, onRead, onRemove }) => {
  const getIcon = () => {
    switch (notification.type) {
      case 'task_assignment':
        return <AssignmentIcon color="primary" />;
      case 'task_update':
        return <TaskIcon color="info" />;
      case 'task_message':
        return <MessageIcon color="secondary" />;
      case 'success':
        return <CheckCircleIcon color="success" />;
      case 'warning':
        return <WarningIcon color="warning" />;
      case 'error':
        return <WarningIcon color="error" />;
      default:
        return <InfoIcon color="info" />;
    }
  };

  const getColor = () => {
    switch (notification.type) {
      case 'success':
        return 'success';
      case 'warning':
        return 'warning';
      case 'error':
        return 'error';
      default:
        return 'info';
    }
  };

  return (
    <ListItem
      sx={{
        bgcolor: notification.read ? 'transparent' : 'action.hover',
        borderRadius: 1,
        mb: 1,
      }}
    >
      <ListItemIcon>{getIcon()}</ListItemIcon>
      <ListItemText
        primary={
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: notification.read ? 'normal' : 'bold' }}>
              {notification.title}
            </Typography>
            {!notification.read && (
              <Chip label="New" size="small" color={getColor() as any} variant="outlined" />
            )}
          </Box>
        }
        secondary={
          <Box>
            <Typography variant="body2" color="text.secondary">
              {truncateText(notification.message, 100)}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {formatDistanceToNow(new Date(notification.timestamp), { addSuffix: true })}
            </Typography>
          </Box>
        }
      />
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
        {!notification.read && (
          <Button size="small" onClick={() => onRead(notification.id)}>
            Mark Read
          </Button>
        )}
        <Button size="small" color="error" onClick={() => onRemove(notification.id)}>
          Remove
        </Button>
      </Box>
    </ListItem>
  );
};

const RealTimeNotifications: React.FC = () => {
  const dispatch = useAppDispatch();
  const user = useAppSelector(selectUser);
  const notifications = useAppSelector(selectNotifications);
  const unreadCount = useAppSelector(selectUnreadNotificationCount);
  
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [activeSnackbar, setActiveSnackbar] = useState<any>(null);
  const [connectionSnackbar, setConnectionSnackbar] = useState<{
    open: boolean;
    type: 'connected' | 'disconnected';
  }>({ open: false, type: 'connected' });

  const { isConnected, connectionState } = useWebSocket(user?.id);

  // Handle connection status changes
  useEffect(() => {
    if (connectionState === 'connected') {
      setConnectionSnackbar({ open: true, type: 'connected' });
    } else if (connectionState === 'disconnected') {
      setConnectionSnackbar({ open: true, type: 'disconnected' });
    }
  }, [connectionState]);

  // Show snackbar for new notifications
  useEffect(() => {
    const latestNotification = notifications[0];
    if (latestNotification && !latestNotification.read) {
      setActiveSnackbar(latestNotification);
    }
  }, [notifications]);

  const handleNotificationClick = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleNotificationClose = () => {
    setAnchorEl(null);
  };

  const handleMarkAsRead = (id: string) => {
    dispatch(markNotificationRead(id));
  };

  const handleRemoveNotification = (id: string) => {
    dispatch(removeNotification(id));
  };

  const handleMarkAllAsRead = () => {
    dispatch(markAllNotificationsRead());
  };

  const handleSnackbarClose = () => {
    setActiveSnackbar(null);
  };

  const handleConnectionSnackbarClose = () => {
    setConnectionSnackbar({ ...connectionSnackbar, open: false });
  };

  const getSnackbarSeverity = (type: string) => {
    switch (type) {
      case 'success':
        return 'success';
      case 'warning':
        return 'warning';
      case 'error':
        return 'error';
      default:
        return 'info';
    }
  };

  const open = Boolean(anchorEl);

  return (
    <>
      {/* Notification Bell */}
      <IconButton
        color="inherit"
        onClick={handleNotificationClick}
        sx={{ mr: 1 }}
      >
        <Badge badgeContent={unreadCount} color="error">
          <NotificationsIcon />
        </Badge>
      </IconButton>

      {/* Notifications Popover */}
      <Popover
        open={open}
        anchorEl={anchorEl}
        onClose={handleNotificationClose}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'right',
        }}
        transformOrigin={{
          vertical: 'top',
          horizontal: 'right',
        }}
        PaperProps={{
          sx: { width: 400, maxHeight: 600 },
        }}
      >
        <Box sx={{ p: 2 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6">
              Notifications
              {unreadCount > 0 && (
                <Chip
                  label={`${unreadCount} new`}
                  size="small"
                  color="primary"
                  sx={{ ml: 1 }}
                />
              )}
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              {/* Connection Status */}
              <Chip
                icon={isConnected ? <WifiIcon /> : <WifiOffIcon />}
                label={isConnected ? 'Connected' : 'Offline'}
                size="small"
                color={isConnected ? 'success' : 'error'}
                variant="outlined"
              />
              <IconButton size="small" onClick={handleNotificationClose}>
                <CloseIcon />
              </IconButton>
            </Box>
          </Box>

          {unreadCount > 0 && (
            <Button
              size="small"
              onClick={handleMarkAllAsRead}
              sx={{ mb: 2 }}
            >
              Mark All as Read
            </Button>
          )}

          <Divider sx={{ mb: 2 }} />

          {notifications.length === 0 ? (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <NotificationsIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
              <Typography variant="body2" color="text.secondary">
                No notifications yet
              </Typography>
            </Box>
          ) : (
            <List sx={{ maxHeight: 400, overflow: 'auto' }}>
              {notifications.slice(0, 10).map((notification) => (
                <NotificationItem
                  key={notification.id}
                  notification={notification}
                  onRead={handleMarkAsRead}
                  onRemove={handleRemoveNotification}
                />
              ))}
              {notifications.length > 10 && (
                <ListItem>
                  <ListItemText
                    primary={
                      <Typography variant="body2" color="text.secondary" align="center">
                        {notifications.length - 10} more notifications...
                      </Typography>
                    }
                  />
                </ListItem>
              )}
            </List>
          )}
        </Box>
      </Popover>

      {/* Active Notification Snackbar */}
      <Snackbar
        open={Boolean(activeSnackbar)}
        autoHideDuration={5000}
        onClose={handleSnackbarClose}
        anchorOrigin={{ vertical: 'top', horizontal: 'right' }}
      >
        {activeSnackbar && (
          <Alert
            onClose={handleSnackbarClose}
            severity={getSnackbarSeverity(activeSnackbar.type)}
            variant="filled"
            sx={{ minWidth: 300 }}
          >
            <AlertTitle>{activeSnackbar.title}</AlertTitle>
            {truncateText(activeSnackbar.message, 100)}
          </Alert>
        )}
      </Snackbar>

      {/* Connection Status Snackbar */}
      <Snackbar
        open={connectionSnackbar.open}
        autoHideDuration={3000}
        onClose={handleConnectionSnackbarClose}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'left' }}
      >
        <Alert
          onClose={handleConnectionSnackbarClose}
          severity={connectionSnackbar.type === 'connected' ? 'success' : 'warning'}
          variant="filled"
          icon={connectionSnackbar.type === 'connected' ? <WifiIcon /> : <WifiOffIcon />}
        >
          {connectionSnackbar.type === 'connected'
            ? 'Real-time updates enabled'
            : 'Connection lost - working offline'
          }
        </Alert>
      </Snackbar>
    </>
  );
};

export default RealTimeNotifications;