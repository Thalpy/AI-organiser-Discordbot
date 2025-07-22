// Edit task dialog component

import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  FormControl,
  FormControlLabel,
  InputLabel,
  Select,
  MenuItem,
  Checkbox,
  Box,
  Typography,
  Chip,
  IconButton,
  CircularProgress,
  Alert,
  Autocomplete,
  Stack,
  Slider,
} from '@mui/material';
import { DateTimePicker } from '@mui/x-date-pickers/DateTimePicker';
import { Close as CloseIcon, Save as SaveIcon } from '@mui/icons-material';
import { useForm, Controller } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';

import { useUpdateTaskMutation } from '../../store/api/taskApi';
import { TaskPriority, TaskStatus, Task, TaskUpdateRequest } from '../../types';

interface EditTaskDialogProps {
  open: boolean;
  onClose: () => void;
  task: Task;
  onTaskUpdated: () => void;
}

// Mock user data - in a real app, this would come from an API
const mockUsers = [
  { id: '123456789', name: 'John Doe' },
  { id: '234567890', name: 'Jane Smith' },
  { id: '345678901', name: 'Bob Johnson' },
  { id: '456789012', name: 'Alice Williams' },
];

// Form validation schema
const schema = yup.object({
  description: yup.string().required('Description is required').max(500, 'Description is too long'),
  priority: yup.string().oneOf(Object.values(TaskPriority), 'Invalid priority'),
  status: yup.string().oneOf(Object.values(TaskStatus), 'Invalid status'),
  duration_minutes: yup
    .number()
    .typeError('Duration must be a number')
    .positive('Duration must be positive')
    .integer('Duration must be an integer')
    .max(1440, 'Duration cannot exceed 24 hours'),
  location: yup.string().max(200, 'Location is too long'),
  is_collaborative: yup.boolean(),
  completion_percentage: yup
    .number()
    .min(0, 'Completion percentage must be at least 0')
    .max(100, 'Completion percentage cannot exceed 100'),
  collaboration_notes: yup.string().max(1000, 'Collaboration notes are too long'),
});

const EditTaskDialog: React.FC<EditTaskDialogProps> = ({ 
  open, 
  onClose, 
  task, 
  onTaskUpdated 
}) => {
  const [selectedUsers, setSelectedUsers] = useState<{ id: string; name: string }[]>([]);
  const [dueDate, setDueDate] = useState<Date | null>(null);
  
  const [updateTask, { isLoading, error }] = useUpdateTaskMutation();

  const {
    control,
    handleSubmit,
    reset,
    formState: { errors },
    watch,
  } = useForm<TaskUpdateRequest>({
    resolver: yupResolver(schema),
    defaultValues: {
      description: task.description,
      priority: task.priority,
      status: task.status,
      duration_minutes: task.duration_minutes,
      location: task.location || '',
      is_collaborative: task.is_collaborative,
      completion_percentage: task.completion_percentage,
      collaboration_notes: task.collaboration_notes || '',
    },
  });

  const watchedStatus = watch('status');

  // Initialize form with task data
  useEffect(() => {
    if (open && task) {
      reset({
        description: task.description,
        priority: task.priority,
        status: task.status,
        duration_minutes: task.duration_minutes,
        location: task.location || '',
        is_collaborative: task.is_collaborative,
        completion_percentage: task.completion_percentage,
        collaboration_notes: task.collaboration_notes || '',
      });
      
      // Set assigned users
      const assignedUsers = mockUsers.filter(user => 
        task.assigned_users.includes(user.id)
      );
      setSelectedUsers(assignedUsers);
      
      // Set due date
      setDueDate(task.due_time ? new Date(task.due_time) : null);
    }
  }, [open, task, reset]);

  const handleClose = () => {
    reset();
    setSelectedUsers([]);
    setDueDate(null);
    onClose();
  };

  const onSubmit = async (data: TaskUpdateRequest) => {
    try {
      // Add assigned users and due date to form data
      const taskData: TaskUpdateRequest = {
        ...data,
        id: task.id,
        assigned_users: selectedUsers.map(user => user.id),
        due_time: dueDate?.toISOString(),
      };

      await updateTask(taskData).unwrap();
      handleClose();
      onTaskUpdated();
    } catch (err) {
      console.error('Failed to update task:', err);
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth=\"md\" fullWidth>
      <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        Edit Task
        <IconButton onClick={handleClose} size=\"small\">
          <CloseIcon />
        </IconButton>
      </DialogTitle>

      <form onSubmit={handleSubmit(onSubmit)}>
        <DialogContent>
          {error && (
            <Alert severity=\"error\" sx={{ mb: 2 }}>
              {(error as any)?.data?.message || 'Failed to update task'}
            </Alert>
          )}

          {/* Task Description */}
          <Controller
            name=\"description\"
            control={control}
            render={({ field }) => (
              <TextField
                {...field}
                label=\"Task Description\"
                fullWidth
                multiline
                rows={2}
                error={!!errors.description}
                helperText={errors.description?.message}
                margin=\"normal\"
                autoFocus
              />
            )}
          />

          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ mt: 2 }}>
            {/* Priority */}
            <Controller
              name=\"priority\"
              control={control}
              render={({ field }) => (
                <FormControl fullWidth error={!!errors.priority}>
                  <InputLabel>Priority</InputLabel>
                  <Select {...field} label=\"Priority\">
                    <MenuItem value={TaskPriority.LOW}>Low</MenuItem>
                    <MenuItem value={TaskPriority.NORMAL}>Normal</MenuItem>
                    <MenuItem value={TaskPriority.HIGH}>High</MenuItem>
                    <MenuItem value={TaskPriority.URGENT}>Urgent</MenuItem>
                  </Select>
                </FormControl>
              )}
            />

            {/* Status */}
            <Controller
              name=\"status\"
              control={control}
              render={({ field }) => (
                <FormControl fullWidth error={!!errors.status}>
                  <InputLabel>Status</InputLabel>
                  <Select {...field} label=\"Status\">
                    <MenuItem value={TaskStatus.PENDING}>Pending</MenuItem>
                    <MenuItem value={TaskStatus.IN_PROGRESS}>In Progress</MenuItem>
                    <MenuItem value={TaskStatus.COMPLETED}>Completed</MenuItem>
                    <MenuItem value={TaskStatus.CANCELLED}>Cancelled</MenuItem>
                  </Select>
                </FormControl>
              )}
            />

            {/* Duration */}
            <Controller
              name=\"duration_minutes\"
              control={control}
              render={({ field }) => (
                <TextField
                  {...field}
                  label=\"Duration (minutes)\"
                  type=\"number\"
                  fullWidth
                  error={!!errors.duration_minutes}
                  helperText={errors.duration_minutes?.message}
                />
              )}
            />
          </Stack>

          {/* Due Date */}
          <Box sx={{ mt: 2 }}>
            <DateTimePicker
              label=\"Due Date & Time\"
              value={dueDate}
              onChange={setDueDate}
              slotProps={{
                textField: {
                  fullWidth: true,
                  margin: 'normal',
                },
              }}
            />
          </Box>

          {/* Location */}
          <Controller
            name=\"location\"
            control={control}
            render={({ field }) => (
              <TextField
                {...field}
                label=\"Location (optional)\"
                fullWidth
                error={!!errors.location}
                helperText={errors.location?.message}
                margin=\"normal\"
              />
            )}
          />

          {/* Progress Slider */}
          {watchedStatus !== TaskStatus.COMPLETED && watchedStatus !== TaskStatus.CANCELLED && (
            <Box sx={{ mt: 2 }}>
              <Typography variant=\"subtitle2\" gutterBottom>
                Completion Progress
              </Typography>
              <Controller
                name=\"completion_percentage\"
                control={control}
                render={({ field }) => (
                  <Box sx={{ px: 1 }}>
                    <Slider
                      {...field}
                      value={field.value}
                      onChange={(_, value) => field.onChange(value)}
                      valueLabelDisplay=\"on\"
                      step={5}
                      marks
                      min={0}
                      max={100}
                      valueLabelFormat={(value) => `${value}%`}
                    />
                  </Box>
                )}
              />
            </Box>
          )}

          {/* Assigned Users */}
          <Box sx={{ mt: 2 }}>
            <Typography variant=\"subtitle2\" gutterBottom>
              Assigned Users
            </Typography>
            <Autocomplete
              multiple
              options={mockUsers}
              getOptionLabel={(option) => option.name}
              value={selectedUsers}
              onChange={(_, newValue) => setSelectedUsers(newValue)}
              renderInput={(params) => (
                <TextField
                  {...params}
                  variant=\"outlined\"
                  label=\"Assigned Users\"
                  placeholder=\"Search users\"
                  fullWidth
                />
              )}
              renderTags={(value, getTagProps) =>
                value.map((option, index) => (
                  <Chip
                    label={option.name}
                    {...getTagProps({ index })}
                    key={option.id}
                  />
                ))
              }
            />
          </Box>

          {/* Collaborative Task */}
          <Box sx={{ mt: 2 }}>
            <Controller
              name=\"is_collaborative\"
              control={control}
              render={({ field }) => (
                <FormControlLabel
                  control={
                    <Checkbox
                      {...field}
                      checked={field.value}
                    />
                  }
                  label=\"This is a collaborative task\"
                />
              )}
            />
          </Box>

          {/* Collaboration Notes */}
          <Controller
            name=\"collaboration_notes\"
            control={control}
            render={({ field }) => (
              <TextField
                {...field}
                label=\"Collaboration Notes (optional)\"
                fullWidth
                multiline
                rows={3}
                error={!!errors.collaboration_notes}
                helperText={errors.collaboration_notes?.message}
                margin=\"normal\"
                placeholder=\"Add notes about collaboration, requirements, or special instructions...\"
              />
            )}
          />
        </DialogContent>

        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={handleClose} color=\"inherit\">
            Cancel
          </Button>
          <Button
            type=\"submit\"
            variant=\"contained\"
            startIcon={isLoading ? <CircularProgress size={20} color=\"inherit\" /> : <SaveIcon />}
            disabled={isLoading}
          >
            Save Changes
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
};

export default EditTaskDialog;