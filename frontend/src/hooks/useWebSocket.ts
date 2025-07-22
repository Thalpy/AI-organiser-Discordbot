// Enhanced WebSocket hook for real-time updates with offline support

import { useEffect, useRef, useCallback, useState } from 'react';
import { useAppDispatch, useAppSelector } from '../store/hooks';
import { 
  handleTaskUpdate, 
  addTask, 
  updateTaskStatus, 
  updateTaskProgress,
  addTaskMessage,
  updateTaskCollaborators,
  setTaskTypingUsers
} from '../store/slices/taskSlice';
import { 
  showSuccessNotification, 
  showInfoNotification, 
  showWarningNotification,
  setConnectionStatus,
  addPendingAction,
  removePendingAction
} from '../store/slices/uiSlice';
import { storage } from '../utils/helpers';
import { STORAGE_KEYS, WS_MESSAGE_TYPE } from '../utils/constants';
import type { 
  WebSocketMessage, 
  TaskUpdatedMessage, 
  TaskAssignedMessage, 
  TaskMessageMessage, 
  NotificationMessage,
  TypingIndicatorMessage,
  UserPresenceMessage,
  CollaborationMessage
} from '../types';

export const useWebSocket = (userId?: string) => {
  const dispatch = useAppDispatch();
  const ws = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;
  const pingIntervalRef = useRef<NodeJS.Timeout>();
  const [connectionState, setConnectionState] = useState<'connecting' | 'connected' | 'disconnected' | 'reconnecting'>('disconnected');
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const pendingMessages = useRef<any[]>([]);
  const subscribedTasks = useRef<Set<number>>(new Set());
  const currentRooms = useRef<Set<string>>(new Set());

  const connect = useCallback(() => {
    if (!userId || !isOnline) return;

    setConnectionState('connecting');
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/${userId}`;

    ws.current = new WebSocket(wsUrl);

    ws.current.onopen = () => {
      console.log('WebSocket connected');
      setConnectionState('connected');
      dispatch(setConnectionStatus(true));
      reconnectAttempts.current = 0;
      
      // Re-subscribe to tasks and rooms after reconnection
      resubscribeToTasks();
      rejoinRooms();
      
      // Send any pending messages
      flushPendingMessages();
      
      // Send ping to keep connection alive
      pingIntervalRef.current = setInterval(() => {
        if (ws.current?.readyState === WebSocket.OPEN) {
          ws.current.send(JSON.stringify({ type: WS_MESSAGE_TYPE.PING, timestamp: Date.now() }));
        } else {
          clearInterval(pingIntervalRef.current!);
        }
      }, 30000); // Ping every 30 seconds
    };

    ws.current.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        handleMessage(message);
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    ws.current.onclose = (event) => {
      console.log('WebSocket disconnected:', event.code, event.reason);
      setConnectionState('disconnected');
      dispatch(setConnectionStatus(false));
      
      // Clear ping interval
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
      }
      
      // Attempt to reconnect if not a normal closure and we're online
      if (event.code !== 1000 && reconnectAttempts.current < maxReconnectAttempts && isOnline) {
        setConnectionState('reconnecting');
        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
        reconnectTimeoutRef.current = setTimeout(() => {
          reconnectAttempts.current++;
          connect();
        }, delay);
      }
    };

    ws.current.onerror = (error) => {
      console.error('WebSocket error:', error);
      setConnectionState('disconnected');
      dispatch(setConnectionStatus(false));
    };
  }, [userId, isOnline]);

  const handleMessage = useCallback((message: WebSocketMessage) => {
    switch (message.type) {
      case 'connection_established':
        dispatch(showSuccessNotification({
          title: 'Connected',
          message: 'Real-time updates enabled'
        }));
        break;

      case 'task_updated':
        const taskUpdatedMsg = message as TaskUpdatedMessage;
        dispatch(handleTaskUpdate(taskUpdatedMsg.task));
        dispatch(showInfoNotification({
          title: 'Task Updated',
          message: `Task "${taskUpdatedMsg.task.description}" has been updated`,
          task_id: taskUpdatedMsg.task.id
        }));
        break;

      case 'task_assigned':
        const taskAssignedMsg = message as TaskAssignedMessage;
        dispatch(addTask(taskAssignedMsg.task));
        dispatch(showInfoNotification({
          title: 'New Task Assignment',
          message: `You've been assigned to "${taskAssignedMsg.task.description}"`,
          task_id: taskAssignedMsg.task.id
        }));
        break;

      case 'task_message':
        const taskMessageMsg = message as TaskMessageMessage;
        // Task messages are handled by the task detail component
        // We just show a notification here
        dispatch(showInfoNotification({
          title: 'New Message',
          message: `New message in task collaboration`,
          task_id: taskMessageMsg.message.task_id
        }));
        break;

      case 'notification':
        const notificationMsg = message as NotificationMessage;
        const { notification } = notificationMsg;
        
        switch (notification.type) {
          case 'success':
            dispatch(showSuccessNotification({
              title: notification.title,
              message: notification.message,
              task_id: notification.task_id
            }));
            break;
          case 'warning':
            dispatch(showWarningNotification({
              title: notification.title,
              message: notification.message,
              task_id: notification.task_id
            }));
            break;
          case 'error':
            dispatch(showWarningNotification({
              title: notification.title,
              message: notification.message,
              task_id: notification.task_id
            }));
            break;
          default:
            dispatch(showInfoNotification({
              title: notification.title,
              message: notification.message,
              task_id: notification.task_id
            }));
        }
        break;

      case 'user_typing':
        // Handle typing indicators in task detail component
        break;

      case 'pong':
        // Handle ping/pong for connection health
        break;

      default:
        console.log('Unknown WebSocket message type:', message.type);
    }
  }, [dispatch]);

  const sendMessage = useCallback((message: any) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message));
    }
  }, []);

  const subscribeToTask = useCallback((taskId: number) => {
    sendMessage({ type: 'subscribe_task', task_id: taskId });
  }, [sendMessage]);

  const unsubscribeFromTask = useCallback((taskId: number) => {
    sendMessage({ type: 'unsubscribe_task', task_id: taskId });
  }, [sendMessage]);

  const sendTypingIndicator = useCallback((taskId: number) => {
    sendMessage({ type: 'typing', task_id: taskId });
  }, [sendMessage]);

  // Helper functions for reconnection and offline support
  const resubscribeToTasks = useCallback(() => {
    subscribedTasks.current.forEach(taskId => {
      sendMessage({ type: WS_MESSAGE_TYPE.SUBSCRIBE_TASK, task_id: taskId });
    });
  }, [sendMessage]);

  const rejoinRooms = useCallback(() => {
    currentRooms.current.forEach(roomId => {
      sendMessage({ type: WS_MESSAGE_TYPE.JOIN_ROOM, room_id: roomId });
    });
  }, [sendMessage]);

  const flushPendingMessages = useCallback(() => {
    while (pendingMessages.current.length > 0) {
      const message = pendingMessages.current.shift();
      if (ws.current?.readyState === WebSocket.OPEN) {
        ws.current.send(JSON.stringify(message));
      }
    }
  }, []);

  const sendMessageWithOfflineSupport = useCallback((message: any) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message));
    } else {
      // Queue message for when connection is restored
      pendingMessages.current.push(message);
      // Store in localStorage for persistence across page reloads
      const storedMessages = storage.get(STORAGE_KEYS.PENDING_MESSAGES, []);
      storedMessages.push({ ...message, timestamp: Date.now() });
      storage.set(STORAGE_KEYS.PENDING_MESSAGES, storedMessages);
    }
  }, []);

  // Enhanced collaboration features
  const joinRoom = useCallback((roomId: string) => {
    currentRooms.current.add(roomId);
    sendMessageWithOfflineSupport({ type: WS_MESSAGE_TYPE.JOIN_ROOM, room_id: roomId });
  }, [sendMessageWithOfflineSupport]);

  const leaveRoom = useCallback((roomId: string) => {
    currentRooms.current.delete(roomId);
    sendMessage({ type: WS_MESSAGE_TYPE.LEAVE_ROOM, room_id: roomId });
  }, [sendMessage]);

  const startTyping = useCallback((roomId: string) => {
    sendMessage({ type: WS_MESSAGE_TYPE.TYPING_START, room_id: roomId });
  }, [sendMessage]);

  const stopTyping = useCallback((roomId: string) => {
    sendMessage({ type: WS_MESSAGE_TYPE.TYPING_STOP, room_id: roomId });
  }, [sendMessage]);

  const updatePresence = useCallback((status: 'online' | 'away' | 'busy' | 'offline') => {
    sendMessage({ type: WS_MESSAGE_TYPE.PRESENCE_UPDATE, status });
  }, [sendMessage]);

  const sendCollaborativeEdit = useCallback((roomId: string, messageId: string, content: string) => {
    sendMessageWithOfflineSupport({
      type: WS_MESSAGE_TYPE.MESSAGE_EDIT,
      room_id: roomId,
      message_id: messageId,
      content
    });
  }, [sendMessageWithOfflineSupport]);

  // Enhanced task subscription with persistence
  const subscribeToTaskPersistent = useCallback((taskId: number) => {
    subscribedTasks.current.add(taskId);
    sendMessage({ type: WS_MESSAGE_TYPE.SUBSCRIBE_TASK, task_id: taskId });
    
    // Persist subscriptions
    const subscriptions = Array.from(subscribedTasks.current);
    storage.set(STORAGE_KEYS.TASK_SUBSCRIPTIONS, subscriptions);
  }, [sendMessage]);

  const unsubscribeFromTaskPersistent = useCallback((taskId: number) => {
    subscribedTasks.current.delete(taskId);
    sendMessage({ type: WS_MESSAGE_TYPE.UNSUBSCRIBE_TASK, task_id: taskId });
    
    // Update persisted subscriptions
    const subscriptions = Array.from(subscribedTasks.current);
    storage.set(STORAGE_KEYS.TASK_SUBSCRIPTIONS, subscriptions);
  }, [sendMessage]);

  // Online/offline event handlers
  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      if (userId && connectionState === 'disconnected') {
        connect();
      }
    };

    const handleOffline = () => {
      setIsOnline(false);
      setConnectionState('disconnected');
      dispatch(setConnectionStatus(false));
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [userId, connectionState, connect, dispatch]);

  // Load persisted data on mount
  useEffect(() => {
    if (userId) {
      // Restore task subscriptions
      const savedSubscriptions = storage.get(STORAGE_KEYS.TASK_SUBSCRIPTIONS, []);
      savedSubscriptions.forEach((taskId: number) => {
        subscribedTasks.current.add(taskId);
      });

      // Restore pending messages
      const savedMessages = storage.get(STORAGE_KEYS.PENDING_MESSAGES, []);
      pendingMessages.current = savedMessages;

      connect();
    }

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
      }
      if (ws.current) {
        ws.current.close(1000, 'Component unmounting');
      }
    };
  }, [userId, connect]);

  return {
    // Connection state
    isConnected: connectionState === 'connected',
    connectionState,
    isOnline,
    
    // Basic messaging
    sendMessage: sendMessageWithOfflineSupport,
    
    // Task subscriptions
    subscribeToTask: subscribeToTaskPersistent,
    unsubscribeFromTask: unsubscribeFromTaskPersistent,
    
    // Collaboration features
    joinRoom,
    leaveRoom,
    startTyping,
    stopTyping,
    sendCollaborativeEdit,
    
    // Presence
    updatePresence,
    
    // Legacy support
    sendTypingIndicator,
  };
};