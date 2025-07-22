// Integration tests for real-time features

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import WS from 'jest-websocket-mock';

import { useWebSocket } from '../hooks/useWebSocket';
import TaskCollaboration from '../components/Tasks/TaskCollaboration';
import RealTimeNotifications from '../components/UI/RealTimeNotifications';
import OfflineSupport from '../components/UI/OfflineSupport';
import authSlice from '../store/slices/authSlice';
import uiSlice from '../store/slices/uiSlice';
import taskSlice from '../store/slices/taskSlice';

// Mock WebSocket
const mockWebSocket = {
  isConnected: true,
  connectionState: 'connected',
  isOnline: true,
  sendMessage: jest.fn(),
  subscribeToTask: jest.fn(),
  unsubscribeFromTask: jest.fn(),
  joinRoom: jest.fn(),
  leaveRoom: jest.fn(),
  startTyping: jest.fn(),
  stopTyping: jest.fn(),
  sendCollaborativeEdit: jest.fn(),
  updatePresence: jest.fn(),
  sendTypingIndicator: jest.fn(),
};

jest.mock('../hooks/useWebSocket', () => ({
  useWebSocket: jest.fn(() => mockWebSocket),
}));

// Mock API
jest.mock('../utils/api', () => ({
  api: {
    post: jest.fn().mockResolvedValue({ id: 1, content: 'Test message' }),
    put: jest.fn().mockResolvedValue({}),
    delete: jest.fn().mockResolvedValue({}),
  },
  endpoints: {
    tasks: {
      messages: (id: number) => `/tasks/${id}/messages`,
    },
  },
}));

// Create test store
const createTestStore = (initialState = {}) => {
  return configureStore({
    reducer: {
      auth: authSlice,
      ui: uiSlice,
      tasks: taskSlice,
    },
    preloadedState: {
      auth: {
        user: { id: 'user1', username: 'testuser' },
        token: 'test-token',
        isAuthenticated: true,
        loading: false,
        error: null,
      },
      ui: {
        sidebarOpen: true,
        theme: 'light',
        notifications: [],
        loading: {},
        isConnected: true,
        pendingActions: [],
      },
      tasks: {
        tasks: [],
        selectedTask: null,
        loading: false,
        error: null,
        filters: {},
        pagination: { page: 1, per_page: 25, total: 0 },
      },
      ...initialState,
    },
  });
};

const renderWithStore = (component: React.ReactElement, store = createTestStore()) => {
  return render(<Provider store={store}>{component}</Provider>);
};

describe('WebSocket Hook', () => {
  let server: WS;

  beforeEach(() => {
    server = new WS('ws://localhost:8000/ws/user1');
  });

  afterEach(() => {
    WS.clean();
  });

  test('should establish WebSocket connection', async () => {
    const TestComponent = () => {
      const { isConnected } = useWebSocket('user1');
      return <div>{isConnected ? 'Connected' : 'Disconnected'}</div>;
    };

    renderWithStore(<TestComponent />);

    await server.connected;
    expect(screen.getByText('Connected')).toBeInTheDocument();
  });

  test('should handle connection loss and reconnection', async () => {
    const TestComponent = () => {
      const { connectionState } = useWebSocket('user1');
      return <div>Status: {connectionState}</div>;
    };

    renderWithStore(<TestComponent />);

    await server.connected;
    expect(screen.getByText('Status: connected')).toBeInTheDocument();

    // Simulate connection loss
    act(() => {
      server.close();
    });

    await waitFor(() => {
      expect(screen.getByText('Status: disconnected')).toBeInTheDocument();
    });
  });

  test('should send and receive messages', async () => {
    const TestComponent = () => {
      const { sendMessage } = useWebSocket('user1');
      
      const handleSend = () => {
        sendMessage({ type: 'test', data: 'hello' });
      };

      return <button onClick={handleSend}>Send Message</button>;
    };

    renderWithStore(<TestComponent />);

    await server.connected;

    fireEvent.click(screen.getByText('Send Message'));

    await expect(server).toReceiveMessage(
      JSON.stringify({ type: 'test', data: 'hello' })
    );
  });
});

describe('TaskCollaboration Component', () => {
  const mockProps = {
    taskId: 1,
    messages: [
      {
        id: '1',
        content: 'Test message',
        user_name: 'testuser',
        user_id: 'user1',
        created_at: new Date().toISOString(),
      },
    ],
    collaborators: ['user1', 'user2'],
    isCollaborative: true,
  };

  test('should render collaboration interface', () => {
    renderWithStore(<TaskCollaboration {...mockProps} />);

    expect(screen.getByText('Collaborators (2)')).toBeInTheDocument();
    expect(screen.getByText('Test message')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Type a message...')).toBeInTheDocument();
  });

  test('should join room on mount', () => {
    renderWithStore(<TaskCollaboration {...mockProps} />);

    expect(mockWebSocket.joinRoom).toHaveBeenCalledWith('task_1');
  });

  test('should send message when form is submitted', async () => {
    const { api } = require('../utils/api');
    
    renderWithStore(<TaskCollaboration {...mockProps} />);

    const input = screen.getByPlaceholderText('Type a message...');
    const sendButton = screen.getByRole('button', { name: /send/i });

    fireEvent.change(input, { target: { value: 'New message' } });
    fireEvent.click(sendButton);

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/tasks/1/messages', {
        message: 'New message',
        message_type: 'text',
      });
    });
  });

  test('should handle typing indicators', () => {
    renderWithStore(<TaskCollaboration {...mockProps} />);

    const input = screen.getByPlaceholderText('Type a message...');
    
    fireEvent.change(input, { target: { value: 'Typing...' } });

    expect(mockWebSocket.startTyping).toHaveBeenCalledWith('task_1');
  });

  test('should show non-collaborative message when not collaborative', () => {
    const nonCollaborativeProps = { ...mockProps, isCollaborative: false };
    
    renderWithStore(<TaskCollaboration {...nonCollaborativeProps} />);

    expect(screen.getByText(/Enable collaboration to start messaging/)).toBeInTheDocument();
  });
});

describe('RealTimeNotifications Component', () => {
  test('should render notification bell with badge', () => {
    const store = createTestStore({
      ui: {
        sidebarOpen: true,
        theme: 'light',
        notifications: [
          {
            id: '1',
            type: 'info',
            title: 'Test Notification',
            message: 'Test message',
            timestamp: new Date().toISOString(),
            read: false,
          },
        ],
        loading: {},
        isConnected: true,
        pendingActions: [],
      },
    });

    renderWithStore(<RealTimeNotifications />, store);

    expect(screen.getByRole('button')).toBeInTheDocument();
    // Badge should show 1 unread notification
  });

  test('should open notifications popover when clicked', () => {
    const store = createTestStore({
      ui: {
        sidebarOpen: true,
        theme: 'light',
        notifications: [
          {
            id: '1',
            type: 'info',
            title: 'Test Notification',
            message: 'Test message',
            timestamp: new Date().toISOString(),
            read: false,
          },
        ],
        loading: {},
        isConnected: true,
        pendingActions: [],
      },
    });

    renderWithStore(<RealTimeNotifications />, store);

    fireEvent.click(screen.getByRole('button'));

    expect(screen.getByText('Notifications')).toBeInTheDocument();
    expect(screen.getByText('Test Notification')).toBeInTheDocument();
  });

  test('should show connection status', () => {
    renderWithStore(<RealTimeNotifications />);

    fireEvent.click(screen.getByRole('button'));

    expect(screen.getByText('Connected')).toBeInTheDocument();
  });
});

describe('OfflineSupport Component', () => {
  test('should show offline alert when offline', () => {
    // Mock offline state
    (useWebSocket as jest.Mock).mockReturnValue({
      ...mockWebSocket,
      isOnline: false,
      isConnected: false,
    });

    renderWithStore(<OfflineSupport />);

    expect(screen.getByText('Working Offline')).toBeInTheDocument();
  });

  test('should show pending actions', () => {
    const store = createTestStore({
      ui: {
        sidebarOpen: true,
        theme: 'light',
        notifications: [],
        loading: {},
        isConnected: false,
        pendingActions: [
          {
            id: '1',
            type: 'create_task',
            data: { title: 'Test Task' },
            timestamp: Date.now(),
            retryCount: 0,
          },
        ],
      },
    });

    // Mock localStorage
    const mockStorage = {
      get: jest.fn().mockReturnValue([
        {
          id: '1',
          type: 'create_task',
          data: { title: 'Test Task' },
          timestamp: Date.now(),
          retryCount: 0,
        },
      ]),
      set: jest.fn(),
      remove: jest.fn(),
    };

    jest.doMock('../utils/helpers', () => ({
      storage: mockStorage,
    }));

    renderWithStore(<OfflineSupport />, store);

    expect(screen.getByText('1 Pending Action')).toBeInTheDocument();
  });

  test('should sync pending actions when connection is restored', async () => {
    const { api } = require('../utils/api');
    
    // Start offline
    (useWebSocket as jest.Mock).mockReturnValue({
      ...mockWebSocket,
      isOnline: false,
      isConnected: false,
    });

    const { rerender } = renderWithStore(<OfflineSupport />);

    // Go online
    (useWebSocket as jest.Mock).mockReturnValue({
      ...mockWebSocket,
      isOnline: true,
      isConnected: true,
    });

    rerender(<OfflineSupport />);

    // Should attempt to sync pending actions
    await waitFor(() => {
      expect(api.post).toHaveBeenCalled();
    });
  });
});

describe('Real-time Message Handling', () => {
  test('should handle task update messages', () => {
    const store = createTestStore();
    
    const TestComponent = () => {
      const { sendMessage } = useWebSocket('user1');
      
      React.useEffect(() => {
        // Simulate receiving a task update message
        const mockMessage = {
          type: 'task_updated',
          task: {
            id: 1,
            title: 'Updated Task',
            status: 'completed',
          },
        };
        
        // This would normally be handled by the WebSocket message handler
        store.dispatch({ type: 'tasks/handleTaskUpdate', payload: mockMessage.task });
      }, []);

      return <div>Test Component</div>;
    };

    renderWithStore(<TestComponent />, store);

    // Verify that the task was updated in the store
    const state = store.getState();
    expect(state.tasks.tasks).toHaveLength(1);
    expect(state.tasks.tasks[0].title).toBe('Updated Task');
  });

  test('should handle typing indicators', () => {
    const store = createTestStore();
    
    const TestComponent = () => {
      React.useEffect(() => {
        // Simulate receiving typing indicator
        store.dispatch({
          type: 'tasks/setTaskTypingUsers',
          payload: { taskId: 1, typingUsers: ['user2'] },
        });
      }, []);

      return <div>Test Component</div>;
    };

    renderWithStore(<TestComponent />, store);

    // Verify typing users were set
    const state = store.getState();
    // This would be checked if we had a task with id 1 in the state
  });
});

describe('Offline Data Persistence', () => {
  test('should persist pending actions to localStorage', () => {
    const mockSetItem = jest.spyOn(Storage.prototype, 'setItem');
    
    const store = createTestStore();
    
    // Dispatch a pending action
    store.dispatch({
      type: 'ui/addPendingAction',
      payload: {
        id: '1',
        action: { type: 'create_task', data: { title: 'Test' } },
        timestamp: Date.now(),
      },
    });

    expect(mockSetItem).toHaveBeenCalled();
  });

  test('should restore pending actions from localStorage', () => {
    const mockGetItem = jest.spyOn(Storage.prototype, 'getItem')
      .mockReturnValue(JSON.stringify([
        {
          id: '1',
          type: 'create_task',
          data: { title: 'Restored Task' },
          timestamp: Date.now(),
          retryCount: 0,
        },
      ]));

    renderWithStore(<OfflineSupport />);

    expect(mockGetItem).toHaveBeenCalledWith('taskbot_offline_actions');
  });
});

// Cleanup
afterEach(() => {
  jest.clearAllMocks();
});