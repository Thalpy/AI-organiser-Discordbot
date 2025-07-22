// Task detail page with collaboration messaging

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Paper,
  Button,
  Grid,
  Chip,
  Avatar,
  AvatarGroup,
  LinearProgress,
  Divider,
  IconButton,
  Menu,
  MenuItem,
  Alert,
  CircularProgress,
  Card,
  CardContent,
  Stack,
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  MoreVert as MoreVertIcon,
  AccessTime as TimeIcon,
  Person as PersonIcon,
  Flag as FlagIcon,
  CheckCircle as CheckCircleIcon,
  Cancel as CancelIcon,
  Pending as PendingIcon,
  PlayArrow as PlayArrowIcon,
  Group as GroupIcon,
  LocationOn as LocationIcon,
  CalendarToday as CalendarIcon,
} from '@mui/icons-material';

import { useGetTaskQuery, useUpdateTaskMutation, useDeleteTaskMutation } from '../../store/api/taskApi';
import { TaskStatus, TaskPriority } from '../../types';
import { formatDistanceToNow, format } from 'date-fns';

import TaskMessages from '../../components/Tasks/TaskMessages';
import EditTaskDialog from '../../components/Tasks/EditTaskDialog';
import ConfirmDialog from '../../components/UI/ConfirmDialog';

const TaskDetailPage: React.FC = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  
  // Local state
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [menuAnchorEl, setMenuAnchorEl] = useState<null | HTMLElement>(null);
  
  // API hooks
  const { data: taskData, isLoading, error, refetch } = useGetTaskQuery(
    parseInt(taskId || '0'),
    { skip: !taskId }
  );
  const [updateTask, { isLoading: isUpdating }] = useUpdateTaskMutation();
  const [deleteTask, { isLoading: isDeleting }] = useDeleteTaskMutation();

  const task = taskData?.task;

  // Handle back navigation
  const handleBack = () => {
    navigate('/tasks');
  };

  // Handle menu
  const handleMenuClick = (event: React.MouseEvent<HTMLElement>) => {
    setMenuAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setMenuAnchorEl(null);
  };

  // Handle task status update
  const handleStatusUpdate = async (newStatus: TaskStatus) => {
    if (!task) return;
    
    try {
      await updateTask({
        id: task.id,
        status: newStatus,
      }).unwrap();
      handleMenuClose();
      refetch();
    } catch (error) {
      console.error('Failed to update task status:', error);
    }
  };

  // Handle task deletion
  const handleDelete = async () => {
    if (!task) return;
    
    try {
      await deleteTask(task.id).unwrap();
      navigate('/tasks');
    } catch (error) {
      console.error('Failed to delete task:', error);
    }
  };

  // Helper functions
  const getStatusIcon = (status: TaskStatus) => {
    switch (status) {
      case TaskStatus.COMPLETED:
        return <CheckCircleIcon fontSize=\"small\" color=\"success\" />;
      case TaskStatus.IN_PROGRESS:
        return <PlayArrowIcon fontSize=\"small\" color=\"primary\" />;
      case TaskStatus.CANCELLED:
        return <CancelIcon fontSize=\"small\" color=\"error\" />;
      case TaskStatus.PENDING:
      default:
        return <PendingIcon fontSize=\"small\" color=\"action\" />;
    }
  };

  const getPriorityColor = (priority: TaskPriority) => {
    switch (priority) {
      case TaskPriority.URGENT:
        return 'error';
      case TaskPriority.HIGH:
        return 'warning';
      case TaskPriority.LOW:
        return 'success';
      case TaskPriority.NORMAL:
      default:
        return 'primary';
    }
  };

  const getStatusColor = (status: TaskStatus) => {
    switch (status) {
      case TaskStatus.COMPLETED:
        return 'success';
      case TaskStatus.IN_PROGRESS:
        return 'primary';
      case TaskStatus.CANCELLED:
        return 'error';
      case TaskStatus.PENDING:
      default:
        return 'default';
    }
  };

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '400px' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error || !task) {
    return (
      <Box>
        <Button
          startIcon={<ArrowBackIcon />}
          onClick={handleBack}
          sx={{ mb: 2 }}
        >
          Back to Tasks
        </Button>
        <Alert severity=\"error\">
          {error ? 'Failed to load task details' : 'Task not found'}
        </Alert>
      </Box>
    );
  }

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Button
          startIcon={<ArrowBackIcon />}
          onClick={handleBack}
        >
          Back to Tasks
        </Button>
        
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            variant=\"outlined\"
            startIcon={<EditIcon />}
            onClick={() => setEditDialogOpen(true)}
          >
            Edit
          </Button>
          <IconButton onClick={handleMenuClick}>
            <MoreVertIcon />
          </IconButton>
        </Box>
      </Box>

      <Grid container spacing={3}>
        {/* Main Task Details */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3, mb: 3 }}>
            {/* Task Header */}
            <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2, mb: 3 }}>
              <Avatar 
                sx={{
                  bgcolor: task.status === TaskStatus.COMPLETED ? 'success.light' : 
                          task.status === TaskStatus.IN_PROGRESS ? 'primary.light' : 
                          'grey.300',
                  mt: 0.5
                }}
              >
                {task.is_collaborative ? <GroupIcon /> : <PersonIcon />}
              </Avatar>
              
              <Box sx={{ flexGrow: 1 }}>
                <Typography 
                  variant=\"h4\" 
                  component=\"h1\" 
                  gutterBottom
                  sx={{
                    textDecoration: task.status === TaskStatus.COMPLETED ? 'line-through' : 'none',
                    color: task.status === TaskStatus.COMPLETED ? 'text.secondary' : 'text.primary',
                  }}
                >
                  {task.description}
                </Typography>
                
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 2 }}>
                  <Chip
                    icon={getStatusIcon(task.status)}
                    label={task.status.replace('_', ' ')}
                    color={getStatusColor(task.status)}
                    variant=\"outlined\"
                  />
                  
                  {task.priority !== TaskPriority.NORMAL && (
                    <Chip 
                      icon={<FlagIcon />}
                      label={task.priority}
                      color={getPriorityColor(task.priority)}
                      variant=\"outlined\"
                    />
                  )}
                  
                  {task.is_collaborative && (
                    <Chip 
                      icon={<GroupIcon />}
                      label=\"Collaborative\"
                      color=\"primary\"
                      variant=\"outlined\"
                    />
                  )}
                </Box>
              </Box>
            </Box>

            {/* Progress Bar */}
            {task.status !== TaskStatus.COMPLETED && task.status !== TaskStatus.CANCELLED && (
              <Box sx={{ mb: 3 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant=\"body2\" color=\"text.secondary\">
                    Progress
                  </Typography>
                  <Typography variant=\"body2\" color=\"text.secondary\">
                    {task.completion_percentage}%
                  </Typography>
                </Box>
                <LinearProgress 
                  variant=\"determinate\" 
                  value={task.completion_percentage} 
                  sx={{ height: 8, borderRadius: 4 }}
                />
              </Box>
            )}

            {/* Task Details Grid */}
            <Grid container spacing={2}>
              {task.due_time && (
                <Grid item xs={12} sm={6}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <CalendarIcon fontSize=\"small\" color=\"action\" />
                    <Box>
                      <Typography variant=\"caption\" color=\"text.secondary\" display=\"block\">
                        Due Date
                      </Typography>
                      <Typography variant=\"body2\">
                        {format(new Date(task.due_time), 'PPP p')}
                      </Typography>
                      <Typography variant=\"caption\" color=\"text.secondary\">
                        ({formatDistanceToNow(new Date(task.due_time), { addSuffix: true })})
                      </Typography>
                    </Box>
                  </Box>
                </Grid>
              )}
              
              <Grid item xs={12} sm={6}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <TimeIcon fontSize=\"small\" color=\"action\" />
                  <Box>
                    <Typography variant=\"caption\" color=\"text.secondary\" display=\"block\">
                      Duration
                    </Typography>
                    <Typography variant=\"body2\">
                      {task.duration_minutes} minutes
                    </Typography>
                  </Box>
                </Box>
              </Grid>
              
              {task.location && (
                <Grid item xs={12} sm={6}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <LocationIcon fontSize=\"small\" color=\"action\" />
                    <Box>
                      <Typography variant=\"caption\" color=\"text.secondary\" display=\"block\">
                        Location
                      </Typography>
                      <Typography variant=\"body2\">
                        {task.location}
                      </Typography>
                    </Box>
                  </Box>
                </Grid>
              )}
              
              <Grid item xs={12} sm={6}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <CalendarIcon fontSize=\"small\" color=\"action\" />
                  <Box>
                    <Typography variant=\"caption\" color=\"text.secondary\" display=\"block\">
                      Created
                    </Typography>
                    <Typography variant=\"body2\">
                      {format(new Date(task.created_at), 'PPP')}
                    </Typography>
                  </Box>
                </Box>
              </Grid>
            </Grid>

            {/* Collaboration Notes */}
            {task.collaboration_notes && (
              <Box sx={{ mt: 3 }}>
                <Typography variant=\"subtitle2\" gutterBottom>
                  Collaboration Notes
                </Typography>
                <Typography variant=\"body2\" color=\"text.secondary\">
                  {task.collaboration_notes}
                </Typography>
              </Box>
            )}
          </Paper>

          {/* Task Messages/Collaboration */}
          {task.is_collaborative && (
            <TaskMessages taskId={task.id} />
          )}
        </Grid>

        {/* Sidebar */}
        <Grid item xs={12} md={4}>
          {/* Assigned Users */}
          <Card sx={{ mb: 2 }}>
            <CardContent>
              <Typography variant=\"h6\" gutterBottom>
                Assigned Users
              </Typography>
              {task.assigned_users.length > 0 ? (
                <Stack spacing={1}>
                  <AvatarGroup max={4}>
                    {task.assigned_users.map((userId, index) => (
                      <Avatar key={index} sx={{ width: 32, height: 32 }}>
                        {userId.substring(0, 2)}
                      </Avatar>
                    ))}
                  </AvatarGroup>
                  <Typography variant=\"body2\" color=\"text.secondary\">
                    {task.assigned_users.length} {task.assigned_users.length === 1 ? 'person' : 'people'} assigned
                  </Typography>
                </Stack>
              ) : (
                <Typography variant=\"body2\" color=\"text.secondary\">
                  No users assigned
                </Typography>
              )}
            </CardContent>
          </Card>

          {/* Task Actions */}
          <Card>
            <CardContent>
              <Typography variant=\"h6\" gutterBottom>
                Quick Actions
              </Typography>
              <Stack spacing={1}>
                {task.status === TaskStatus.PENDING && (
                  <Button
                    variant=\"contained\"
                    color=\"primary\"
                    onClick={() => handleStatusUpdate(TaskStatus.IN_PROGRESS)}
                    disabled={isUpdating}
                  >
                    Start Task
                  </Button>
                )}
                
                {task.status === TaskStatus.IN_PROGRESS && (
                  <Button
                    variant=\"contained\"
                    color=\"success\"
                    onClick={() => handleStatusUpdate(TaskStatus.COMPLETED)}
                    disabled={isUpdating}
                  >
                    Complete Task
                  </Button>
                )}
                
                {task.status !== TaskStatus.COMPLETED && task.status !== TaskStatus.CANCELLED && (
                  <Button
                    variant=\"outlined\"
                    color=\"error\"
                    onClick={() => handleStatusUpdate(TaskStatus.CANCELLED)}
                    disabled={isUpdating}
                  >
                    Cancel Task
                  </Button>
                )}
                
                <Button
                  variant=\"outlined\"
                  color=\"error\"
                  onClick={() => setDeleteDialogOpen(true)}
                  disabled={isDeleting}
                >
                  Delete Task
                </Button>
              </Stack>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Menu */}
      <Menu
        anchorEl={menuAnchorEl}
        open={Boolean(menuAnchorEl)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={() => setEditDialogOpen(true)}>
          <EditIcon sx={{ mr: 1 }} fontSize=\"small\" />
          Edit Task
        </MenuItem>
        <MenuItem onClick={() => setDeleteDialogOpen(true)}>
          <DeleteIcon sx={{ mr: 1 }} fontSize=\"small\" />
          Delete Task
        </MenuItem>
      </Menu>

      {/* Edit Dialog */}
      <EditTaskDialog
        open={editDialogOpen}
        onClose={() => setEditDialogOpen(false)}
        task={task}
        onTaskUpdated={() => {
          setEditDialogOpen(false);
          refetch();
        }}
      />

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        open={deleteDialogOpen}
        onClose={() => setDeleteDialogOpen(false)}
        onConfirm={handleDelete}
        title=\"Delete Task\"
        message=\"Are you sure you want to delete this task? This action cannot be undone.\"
        confirmText=\"Delete\"
        confirmColor=\"error\"
        loading={isDeleting}
      />
    </Box>
  );
};

export default TaskDetailPage;