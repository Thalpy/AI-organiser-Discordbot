// Real-time collaboration component for task messaging

import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Avatar,
  Chip,
  List,
  ListItem,
  ListItemAvatar,
  ListItemText,
  Divider,
  IconButton,
  Menu,
  MenuItem,
  Badge,
} from '@mui/material';
import {
  Send as SendIcon,
  MoreVert as MoreVertIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Reply as ReplyIcon,
} from '@mui/icons-material';
import { formatDistanceToNow } from 'date-fns';

import { useAppSelector, useAppDispatch } from '../../store/hooks';
import { useWebSocket } from '../../hooks/useWebSocket';
import { selectUser } from '../../store/slices/authSlice';
import { addTaskMessage } from '../../store/slices/taskSlice';
import { showSuccessNotification } from '../../store/slices/uiSlice';
import { api, endpoints } from '../../utils/api';
import { truncateText } from '../../utils/helpers';

interface TaskCollaborationProps {
  taskId: number;
  messages?: any[];
  collaborators?: string[];
  isCollaborative?: boolean;
}

interface TypingIndicatorProps {
  typingUsers: string[];
  currentUserId: string;
}

const TypingIndicator: React.FC<TypingIndicatorProps> = ({ typingUsers, currentUserId }) => {
  const otherTypingUsers = typingUsers.filter(userId => userId !== currentUserId);
  
  if (otherTypingUsers.length === 0) return null;

  const getTypingText = () => {
    if (otherTypingUsers.length === 1) {
      return `${otherTypingUsers[0]} is typing...`;
    } else if (otherTypingUsers.length === 2) {
      return `${otherTypingUsers[0]} and ${otherTypingUsers[1]} are typing...`;
    } else {
      return `${otherTypingUsers.length} people are typing...`;
    }
  };

  return (
    <Box sx={{ p: 1, fontStyle: 'italic', color: 'text.secondary', fontSize: '0.875rem' }}>
      {getTypingText()}
    </Box>
  );
};

const TaskCollaboration: React.FC<TaskCollaborationProps> = ({
  taskId,
  messages = [],
  collaborators = [],
  isCollaborative = false,
}) => {
  const dispatch = useAppDispatch();
  const user = useAppSelector(selectUser);
  const [newMessage, setNewMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [typingUsers, setTypingUsers] = useState<string[]>([]);
  const [editingMessage, setEditingMessage] = useState<string | null>(null);
  const [editContent, setEditContent] = useState('');
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [selectedMessage, setSelectedMessage] = useState<any>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const typingTimeoutRef = useRef<NodeJS.Timeout>();

  const {
    isConnected,
    joinRoom,
    leaveRoom,
    startTyping,
    stopTyping,
    sendCollaborativeEdit,
  } = useWebSocket(user?.id);

  // Join collaboration room on mount
  useEffect(() => {
    if (isCollaborative && isConnected) {
      joinRoom(`task_${taskId}`);
    }

    return () => {
      if (isCollaborative) {
        leaveRoom(`task_${taskId}`);
      }
    };
  }, [taskId, isCollaborative, isConnected, joinRoom, leaveRoom]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Handle typing indicators
  const handleTypingStart = () => {
    if (!isTyping && isCollaborative) {
      setIsTyping(true);
      startTyping(`task_${taskId}`);
    }

    // Reset typing timeout
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }

    typingTimeoutRef.current = setTimeout(() => {
      handleTypingStop();
    }, 3000);
  };

  const handleTypingStop = () => {
    if (isTyping && isCollaborative) {
      setIsTyping(false);
      stopTyping(`task_${taskId}`);
    }

    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }
  };

  const handleSendMessage = async () => {
    if (!newMessage.trim() || !user) return;

    try {
      const messageData = {
        message: newMessage.trim(),
        message_type: 'text',
      };

      // Send to API
      const response = await api.post(endpoints.tasks.messages(taskId), messageData);
      
      // Add to local state
      dispatch(addTaskMessage({ taskId, message: response }));
      
      // Clear input
      setNewMessage('');
      handleTypingStop();
      
      dispatch(showSuccessNotification({
        title: 'Message Sent',
        message: 'Your message has been sent successfully',
      }));
    } catch (error) {
      console.error('Failed to send message:', error);
    }
  };

  const handleEditMessage = async (messageId: string, content: string) => {
    if (!content.trim()) return;

    try {
      if (isCollaborative) {
        // Send collaborative edit
        sendCollaborativeEdit(`task_${taskId}`, messageId, content);
      }

      // Update via API
      await api.put(`/tasks/${taskId}/messages/${messageId}`, { content });
      
      setEditingMessage(null);
      setEditContent('');
      
      dispatch(showSuccessNotification({
        title: 'Message Updated',
        message: 'Your message has been updated successfully',
      }));
    } catch (error) {
      console.error('Failed to edit message:', error);
    }
  };

  const handleDeleteMessage = async (messageId: string) => {
    try {
      await api.delete(`/tasks/${taskId}/messages/${messageId}`);
      
      dispatch(showSuccessNotification({
        title: 'Message Deleted',
        message: 'Message has been deleted successfully',
      }));
    } catch (error) {
      console.error('Failed to delete message:', error);
    }
  };

  const handleMenuClick = (event: React.MouseEvent<HTMLElement>, message: any) => {
    setAnchorEl(event.currentTarget);
    setSelectedMessage(message);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
    setSelectedMessage(null);
  };

  const startEditing = (message: any) => {
    setEditingMessage(message.id);
    setEditContent(message.content);
    handleMenuClose();
  };

  const cancelEditing = () => {
    setEditingMessage(null);
    setEditContent('');
  };

  if (!isCollaborative) {
    return (
      <Box sx={{ p: 2, textAlign: 'center' }}>
        <Typography variant="body2" color="text.secondary">
          Enable collaboration to start messaging with team members
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Collaborators */}
      {collaborators.length > 0 && (
        <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
          <Typography variant="subtitle2" gutterBottom>
            Collaborators ({collaborators.length})
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            {collaborators.map((collaborator) => (
              <Chip
                key={collaborator}
                label={collaborator}
                size="small"
                avatar={<Avatar sx={{ width: 24, height: 24 }}>{collaborator[0]?.toUpperCase()}</Avatar>}
              />
            ))}
          </Box>
        </Box>
      )}

      {/* Messages */}
      <Box sx={{ flex: 1, overflow: 'auto', p: 1 }}>
        <List>
          {messages.map((message, index) => (
            <React.Fragment key={message.id}>
              <ListItem
                alignItems="flex-start"
                sx={{
                  '&:hover .message-actions': {
                    opacity: 1,
                  },
                }}
              >
                <ListItemAvatar>
                  <Badge
                    color="success"
                    variant="dot"
                    invisible={!isConnected}
                  >
                    <Avatar sx={{ width: 32, height: 32 }}>
                      {message.user_name?.[0]?.toUpperCase() || 'U'}
                    </Avatar>
                  </Badge>
                </ListItemAvatar>
                
                <ListItemText
                  primary={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography variant="subtitle2">
                        {message.user_name || 'Unknown User'}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {formatDistanceToNow(new Date(message.created_at), { addSuffix: true })}
                      </Typography>
                      {message.edited_at && (
                        <Chip label="edited" size="small" variant="outlined" />
                      )}
                    </Box>
                  }
                  secondary={
                    editingMessage === message.id ? (
                      <Box sx={{ mt: 1 }}>
                        <TextField
                          fullWidth
                          multiline
                          rows={2}
                          value={editContent}
                          onChange={(e) => setEditContent(e.target.value)}
                          variant="outlined"
                          size="small"
                        />
                        <Box sx={{ mt: 1, display: 'flex', gap: 1 }}>
                          <Button
                            size="small"
                            variant="contained"
                            onClick={() => handleEditMessage(message.id, editContent)}
                          >
                            Save
                          </Button>
                          <Button size="small" onClick={cancelEditing}>
                            Cancel
                          </Button>
                        </Box>
                      </Box>
                    ) : (
                      <Typography variant="body2" sx={{ mt: 0.5, whiteSpace: 'pre-wrap' }}>
                        {message.content}
                      </Typography>
                    )
                  }
                />
                
                {message.user_id === user?.id && (
                  <Box className="message-actions" sx={{ opacity: 0, transition: 'opacity 0.2s' }}>
                    <IconButton
                      size="small"
                      onClick={(e) => handleMenuClick(e, message)}
                    >
                      <MoreVertIcon fontSize="small" />
                    </IconButton>
                  </Box>
                )}
              </ListItem>
              
              {index < messages.length - 1 && <Divider variant="inset" component="li" />}
            </React.Fragment>
          ))}
        </List>
        
        {/* Typing Indicator */}
        <TypingIndicator typingUsers={typingUsers} currentUserId={user?.id || ''} />
        
        <div ref={messagesEndRef} />
      </Box>

      {/* Message Input */}
      <Paper sx={{ p: 2, borderTop: 1, borderColor: 'divider' }}>
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-end' }}>
          <TextField
            fullWidth
            multiline
            maxRows={4}
            placeholder="Type a message..."
            value={newMessage}
            onChange={(e) => {
              setNewMessage(e.target.value);
              handleTypingStart();
            }}
            onKeyPress={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSendMessage();
              }
            }}
            variant="outlined"
            size="small"
            disabled={!isConnected}
          />
          <Button
            variant="contained"
            onClick={handleSendMessage}
            disabled={!newMessage.trim() || !isConnected}
            sx={{ minWidth: 'auto', px: 2 }}
          >
            <SendIcon />
          </Button>
        </Box>
        
        {!isConnected && (
          <Typography variant="caption" color="error" sx={{ mt: 1, display: 'block' }}>
            Disconnected - Messages will be sent when connection is restored
          </Typography>
        )}
      </Paper>

      {/* Message Actions Menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={() => startEditing(selectedMessage)}>
          <EditIcon fontSize="small" sx={{ mr: 1 }} />
          Edit
        </MenuItem>
        <MenuItem onClick={() => handleDeleteMessage(selectedMessage?.id)}>
          <DeleteIcon fontSize="small" sx={{ mr: 1 }} />
          Delete
        </MenuItem>
      </Menu>
    </Box>
  );
};

export default TaskCollaboration;