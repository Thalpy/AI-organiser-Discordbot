// Task messages component for collaboration

import React, { useState, useRef, useEffect } from 'react';
import {
  Paper,
  Typography,
  Box,
  TextField,
  Button,
  Avatar,
  List,
  ListItem,
  ListItemAvatar,
  ListItemText,
  Divider,
  IconButton,
  Menu,
  MenuItem,
  Chip,
  Alert,
  CircularProgress,
} from '@mui/material';
import {
  Send as SendIcon,
  MoreVert as MoreVertIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Reply as ReplyIcon,
} from '@mui/icons-material';
import { formatDistanceToNow } from 'date-fns';

import { 
  useGetTaskMessagesQuery, 
  useAddTaskMessageMutation, 
  useUpdateTaskMessageMutation,
  useDeleteTaskMessageMutation 
} from '../../store/api/taskApi';
import { TaskMessage } from '../../types';

interface TaskMessagesProps {
  taskId: number;
}

const TaskMessages: React.FC<TaskMessagesProps> = ({ taskId }) => {
  // Local state
  const [newMessage, setNewMessage] = useState('');
  const [editingMessage, setEditingMessage] = useState<number | null>(null);
  const [editText, setEditText] = useState('');
  const [replyingTo, setReplyingTo] = useState<number | null>(null);
  const [menuAnchorEl, setMenuAnchorEl] = useState<null | HTMLElement>(null);
  const [selectedMessage, setSelectedMessage] = useState<TaskMessage | null>(null);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  // API hooks
  const { data: messagesData, isLoading, error, refetch } = useGetTaskMessagesQuery(taskId);
  const [addMessage, { isLoading: isAdding }] = useAddTaskMessageMutation();
  const [updateMessage, { isLoading: isUpdating }] = useUpdateTaskMessageMutation();
  const [deleteMessage, { isLoading: isDeleting }] = useDeleteTaskMessageMutation();

  const messages = messagesData?.messages || [];

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Handle sending new message
  const handleSendMessage = async () => {
    if (!newMessage.trim()) return;

    try {
      await addMessage({
        taskId,
        message: newMessage,
        message_type: 'comment',
        parent_message_id: replyingTo,
      }).unwrap();
      
      setNewMessage('');
      setReplyingTo(null);
      refetch();
    } catch (error) {
      console.error('Failed to send message:', error);
    }
  };

  // Handle editing message
  const handleEditMessage = async () => {
    if (!editText.trim() || !editingMessage) return;

    try {
      await updateMessage({
        id: editingMessage,
        message: editText,
      }).unwrap();
      
      setEditingMessage(null);
      setEditText('');
      refetch();
    } catch (error) {
      console.error('Failed to update message:', error);
    }
  };

  // Handle deleting message
  const handleDeleteMessage = async (messageId: number) => {
    try {
      await deleteMessage(messageId).unwrap();
      refetch();
    } catch (error) {
      console.error('Failed to delete message:', error);
    }
  };

  // Handle menu actions
  const handleMenuClick = (event: React.MouseEvent<HTMLElement>, message: TaskMessage) => {
    setMenuAnchorEl(event.currentTarget);
    setSelectedMessage(message);
  };

  const handleMenuClose = () => {
    setMenuAnchorEl(null);
    setSelectedMessage(null);
  };

  const handleStartEdit = () => {
    if (selectedMessage) {
      setEditingMessage(selectedMessage.id);
      setEditText(selectedMessage.message);
    }
    handleMenuClose();
  };

  const handleStartReply = () => {
    if (selectedMessage) {
      setReplyingTo(selectedMessage.id);
    }
    handleMenuClose();
  };

  const handleDelete = () => {
    if (selectedMessage) {
      handleDeleteMessage(selectedMessage.id);
    }
    handleMenuClose();
  };

  // Get message type display
  const getMessageTypeChip = (messageType: string) => {
    switch (messageType) {
      case 'status_update':
        return <Chip label=\"Status Update\" size=\"small\" color=\"primary\" variant=\"outlined\" />;
      case 'system':
        return <Chip label=\"System\" size=\"small\" color=\"secondary\" variant=\"outlined\" />;
      default:
        return null;
    }
  };

  // Find parent message for replies
  const getParentMessage = (parentId: number) => {
    return messages.find(msg => msg.id === parentId);
  };

  if (isLoading) {
    return (
      <Paper sx={{ p: 3 }}>
        <Typography variant=\"h6\" gutterBottom>
          Messages
        </Typography>
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
          <CircularProgress />
        </Box>
      </Paper>
    );
  }

  if (error) {
    return (
      <Paper sx={{ p: 3 }}>
        <Typography variant=\"h6\" gutterBottom>
          Messages
        </Typography>
        <Alert severity=\"error\">
          Failed to load messages
        </Alert>
      </Paper>
    );
  }

  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant=\"h6\" gutterBottom>
        Messages ({messages.length})
      </Typography>

      {/* Messages List */}
      <Box sx={{ maxHeight: '400px', overflow: 'auto', mb: 2 }}>
        {messages.length === 0 ? (
          <Box sx={{ textAlign: 'center', py: 4 }}>
            <Typography variant=\"body2\" color=\"text.secondary\">
              No messages yet. Start the conversation!
            </Typography>
          </Box>
        ) : (
          <List sx={{ p: 0 }}>
            {messages.map((message, index) => {
              const parentMessage = message.parent_message_id ? getParentMessage(message.parent_message_id) : null;
              
              return (
                <React.Fragment key={message.id}>
                  <ListItem
                    alignItems=\"flex-start\"
                    sx={{
                      pl: message.parent_message_id ? 4 : 1,
                      borderLeft: message.parent_message_id ? '2px solid' : 'none',
                      borderLeftColor: 'primary.light',
                      ml: message.parent_message_id ? 2 : 0,
                    }}
                  >
                    <ListItemAvatar>
                      <Avatar sx={{ width: 32, height: 32 }}>
                        {message.user_id.substring(0, 2)}
                      </Avatar>
                    </ListItemAvatar>
                    
                    <ListItemText
                      primary={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                          <Typography variant=\"subtitle2\">
                            User {message.user_id.substring(0, 8)}
                          </Typography>
                          <Typography variant=\"caption\" color=\"text.secondary\">
                            {formatDistanceToNow(new Date(message.created_at), { addSuffix: true })}
                          </Typography>
                          {getMessageTypeChip(message.message_type)}
                          {message.edited_at && (
                            <Chip label=\"Edited\" size=\"small\" variant=\"outlined\" />
                          )}
                        </Box>
                      }
                      secondary={
                        <Box>
                          {/* Reply indicator */}
                          {parentMessage && (
                            <Box sx={{ 
                              bgcolor: 'grey.100', 
                              p: 1, 
                              borderRadius: 1, 
                              mb: 1,
                              borderLeft: '3px solid',
                              borderLeftColor: 'primary.main'
                            }}>
                              <Typography variant=\"caption\" color=\"text.secondary\">
                                Replying to User {parentMessage.user_id.substring(0, 8)}:
                              </Typography>
                              <Typography variant=\"body2\" sx={{ fontStyle: 'italic' }}>
                                {parentMessage.message.length > 100 
                                  ? `${parentMessage.message.substring(0, 100)}...` 
                                  : parentMessage.message}
                              </Typography>
                            </Box>
                          )}
                          
                          {/* Message content */}
                          {editingMessage === message.id ? (
                            <Box sx={{ mt: 1 }}>
                              <TextField
                                fullWidth
                                multiline
                                rows={2}
                                value={editText}
                                onChange={(e) => setEditText(e.target.value)}
                                size=\"small\"
                              />
                              <Box sx={{ mt: 1, display: 'flex', gap: 1 }}>
                                <Button
                                  size=\"small\"
                                  variant=\"contained\"
                                  onClick={handleEditMessage}
                                  disabled={isUpdating}
                                >
                                  Save
                                </Button>
                                <Button
                                  size=\"small\"
                                  onClick={() => {
                                    setEditingMessage(null);
                                    setEditText('');
                                  }}
                                >
                                  Cancel
                                </Button>
                              </Box>
                            </Box>
                          ) : (
                            <Typography variant=\"body2\" sx={{ mt: 0.5, whiteSpace: 'pre-wrap' }}>
                              {message.message}
                            </Typography>
                          )}
                        </Box>
                      }
                    />
                    
                    <IconButton
                      size=\"small\"
                      onClick={(e) => handleMenuClick(e, message)}
                    >
                      <MoreVertIcon fontSize=\"small\" />
                    </IconButton>
                  </ListItem>
                  
                  {index < messages.length - 1 && <Divider variant=\"inset\" component=\"li\" />}
                </React.Fragment>
              );
            })}
          </List>
        )}
        <div ref={messagesEndRef} />
      </Box>

      {/* Reply indicator */}
      {replyingTo && (
        <Box sx={{ mb: 2, p: 1, bgcolor: 'primary.50', borderRadius: 1 }}>
          <Typography variant=\"caption\" color=\"primary\">
            Replying to message
          </Typography>
          <Button
            size=\"small\"
            onClick={() => setReplyingTo(null)}
            sx={{ ml: 1 }}
          >
            Cancel
          </Button>
        </Box>
      )}

      {/* Message Input */}
      <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-end' }}>
        <TextField
          fullWidth
          multiline
          maxRows={4}
          placeholder=\"Type your message...\"
          value={newMessage}
          onChange={(e) => setNewMessage(e.target.value)}
          onKeyPress={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleSendMessage();
            }
          }}
          size=\"small\"
        />
        <Button
          variant=\"contained\"
          endIcon={<SendIcon />}
          onClick={handleSendMessage}
          disabled={!newMessage.trim() || isAdding}
          sx={{ minWidth: 'auto' }}
        >
          {isAdding ? <CircularProgress size={20} color=\"inherit\" /> : 'Send'}
        </Button>
      </Box>

      {/* Context Menu */}
      <Menu
        anchorEl={menuAnchorEl}
        open={Boolean(menuAnchorEl)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={handleStartReply}>
          <ReplyIcon sx={{ mr: 1 }} fontSize=\"small\" />
          Reply
        </MenuItem>
        <MenuItem onClick={handleStartEdit}>
          <EditIcon sx={{ mr: 1 }} fontSize=\"small\" />
          Edit
        </MenuItem>
        <MenuItem onClick={handleDelete} sx={{ color: 'error.main' }}>
          <DeleteIcon sx={{ mr: 1 }} fontSize=\"small\" />
          Delete
        </MenuItem>
      </Menu>
    </Paper>
  );
};

export default TaskMessages;