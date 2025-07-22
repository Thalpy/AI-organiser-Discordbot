// Tasks page with comprehensive task management features

import React, { useState, useMemo } from 'react';
import {
  Box,
  Grid,
  Paper,
  Typography,
  Button,
  TextField,
  InputAdornment,
  Chip,
  IconButton,
  Menu,
  MenuItem,
  FormControl,
  InputLabel,
  Select,
  Fab,
  Tooltip,
  Alert,
} from '@mui/material';
import {
  Search as SearchIcon,
  FilterList as FilterIcon,
  Add as AddIcon,
  ViewList as ViewListIcon,
  ViewModule as ViewModuleIcon,
  Sort as SortIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';

import { useAppSelector, useAppDispatch } from '../../store/hooks';
import { 
  selectTasks, 
  selectTaskFilters, 
  selectTaskPagination,
  selectTaskLoading,
  selectTaskError,
  setFilters,
  clearFilters,
  setSearchFilter,
  setPage,
  setPerPage,
} from '../../store/slices/taskSlice';
import { useGetTasksQuery } from '../../store/api/taskApi';
import { TaskStatus, TaskPriority, TaskFilters } from '../../types';

import TaskCard from '../../components/Tasks/TaskCard';
import TaskList from '../../components/Tasks/TaskList';
import TaskCreateDialog from '../../components/Tasks/TaskCreateDialog';
import TaskFiltersPanel from '../../components/Tasks/TaskFiltersPanel';
import LoadingSpinner from '../../components/UI/LoadingSpinner';

const TasksPage: React.FC = () => {
  const dispatch = useAppDispatch();
  const filters = useAppSelector(selectTaskFilters);
  const pagination = useAppSelector(selectTaskPagination);
  const loading = useAppSelector(selectTaskLoading);
  const error = useAppSelector(selectTaskError);

  // Local state
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [sortMenuAnchor, setSortMenuAnchor] = useState<null | HTMLElement>(null);
  const [searchValue, setSearchValue] = useState(filters.search || '');

  // Fetch tasks with current filters and pagination
  const { data: tasksData, isLoading, error: apiError, refetch } = useGetTasksQuery({
    ...filters,
    page: pagination.page,
    per_page: pagination.per_page,
  });

  const tasks = tasksData?.tasks || [];
  const totalTasks = tasksData?.total || 0;

  // Handle search with debouncing
  const handleSearchChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const value = event.target.value;
    setSearchValue(value);
    
    // Debounce search
    const timeoutId = setTimeout(() => {
      dispatch(setSearchFilter(value));
    }, 300);

    return () => clearTimeout(timeoutId);
  };

  // Filter handlers
  const handleStatusFilter = (status: TaskStatus | undefined) => {
    dispatch(setFilters({ status }));
  };

  const handlePriorityFilter = (priority: TaskPriority | undefined) => {
    dispatch(setFilters({ priority }));
  };

  const handleCollaborativeFilter = (isCollaborative: boolean | undefined) => {
    dispatch(setFilters({ is_collaborative: isCollaborative }));
  };

  const handleClearFilters = () => {
    dispatch(clearFilters());
    setSearchValue('');
  };

  // Pagination handlers
  const handlePageChange = (page: number) => {
    dispatch(setPage(page));
  };

  const handlePerPageChange = (perPage: number) => {
    dispatch(setPerPage(perPage));
  };

  // Sort handlers
  const handleSortMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setSortMenuAnchor(event.currentTarget);
  };

  const handleSortMenuClose = () => {
    setSortMenuAnchor(null);
  };

  // Active filters count
  const activeFiltersCount = useMemo(() => {
    let count = 0;
    if (filters.status) count++;
    if (filters.priority) count++;
    if (filters.is_collaborative !== undefined) count++;
    if (filters.search) count++;
    if (filters.assigned_to) count++;
    if (filters.created_by) count++;
    return count;
  }, [filters]);

  return (
    <Box>
      {/* Page Header */}
      <Box sx={{ marginBottom: 3 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Tasks
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Manage your tasks and collaborate with your team
        </Typography>
      </Box>

      {/* Error Alert */}
      {(error || apiError) && (
        <Alert severity="error" sx={{ marginBottom: 2 }}>
          {error || 'Failed to load tasks'}
        </Alert>
      )}

      {/* Toolbar */}
      <Paper sx={{ padding: 2, marginBottom: 3 }}>
        <Grid container spacing={2} alignItems="center">
          {/* Search */}
          <Grid item xs={12} md={4}>
            <TextField
              fullWidth
              placeholder="Search tasks..."
              value={searchValue}
              onChange={handleSearchChange}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon />
                  </InputAdornment>
                ),
              }}
              size="small"
            />
          </Grid>

          {/* Quick Filters */}
          <Grid item xs={12} md={4}>
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
              <Chip
                label="Pending"
                onClick={() => handleStatusFilter(TaskStatus.PENDING)}
                color={filters.status === TaskStatus.PENDING ? 'primary' : 'default'}
                variant={filters.status === TaskStatus.PENDING ? 'filled' : 'outlined'}
                size="small"
              />
              <Chip
                label="In Progress"
                onClick={() => handleStatusFilter(TaskStatus.IN_PROGRESS)}
                color={filters.status === TaskStatus.IN_PROGRESS ? 'primary' : 'default'}
                variant={filters.status === TaskStatus.IN_PROGRESS ? 'filled' : 'outlined'}
                size="small"
              />
              <Chip
                label="Collaborative"
                onClick={() => handleCollaborativeFilter(true)}
                color={filters.is_collaborative === true ? 'secondary' : 'default'}
                variant={filters.is_collaborative === true ? 'filled' : 'outlined'}
                size="small"
              />
            </Box>
          </Grid>

          {/* Actions */}
          <Grid item xs={12} md={4}>
            <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1 }}>
              <Tooltip title="Refresh">
                <IconButton onClick={() => refetch()} disabled={isLoading}>
                  <RefreshIcon />
                </IconButton>
              </Tooltip>

              <Tooltip title="Filters">
                <IconButton 
                  onClick={() => setFiltersOpen(true)}
                  color={activeFiltersCount > 0 ? 'primary' : 'default'}
                >
                  <FilterIcon />
                  {activeFiltersCount > 0 && (
                    <Box
                      sx={{
                        position: 'absolute',
                        top: 4,
                        right: 4,
                        width: 16,
                        height: 16,
                        borderRadius: '50%',
                        backgroundColor: 'primary.main',
                        color: 'white',
                        fontSize: '10px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                      }}
                    >
                      {activeFiltersCount}
                    </Box>
                  )}
                </IconButton>
              </Tooltip>

              <Tooltip title="Sort">
                <IconButton onClick={handleSortMenuOpen}>
                  <SortIcon />
                </IconButton>
              </Tooltip>

              <Tooltip title={viewMode === 'grid' ? 'List View' : 'Grid View'}>
                <IconButton 
                  onClick={() => setViewMode(viewMode === 'grid' ? 'list' : 'grid')}
                >
                  {viewMode === 'grid' ? <ViewListIcon /> : <ViewModuleIcon />}
                </IconButton>
              </Tooltip>
            </Box>
          </Grid>
        </Grid>

        {/* Active Filters Display */}
        {activeFiltersCount > 0 && (
          <Box sx={{ marginTop: 2, display: 'flex', gap: 1, alignItems: 'center', flexWrap: 'wrap' }}>
            <Typography variant="body2" color="text.secondary">
              Active filters:
            </Typography>
            
            {filters.status && (
              <Chip
                label={`Status: ${filters.status}`}
                onDelete={() => handleStatusFilter(undefined)}
                size="small"
                color="primary"
              />
            )}
            
            {filters.priority && (
              <Chip
                label={`Priority: ${filters.priority}`}
                onDelete={() => handlePriorityFilter(undefined)}
                size="small"
                color="primary"
              />
            )}
            
            {filters.is_collaborative !== undefined && (
              <Chip
                label={`Collaborative: ${filters.is_collaborative ? 'Yes' : 'No'}`}
                onDelete={() => handleCollaborativeFilter(undefined)}
                size="small"
                color="secondary"
              />
            )}
            
            {filters.search && (
              <Chip
                label={`Search: "${filters.search}"`}
                onDelete={() => {
                  dispatch(setSearchFilter(''));
                  setSearchValue('');
                }}
                size="small"
                color="primary"
              />
            )}

            <Button
              size="small"
              onClick={handleClearFilters}
              sx={{ marginLeft: 1 }}
            >
              Clear All
            </Button>
          </Box>
        )}
      </Paper>

      {/* Tasks Content */}
      {isLoading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', padding: 4 }}>
          <LoadingSpinner message="Loading tasks..." />
        </Box>
      ) : tasks.length === 0 ? (
        <Paper sx={{ padding: 6, textAlign: 'center' }}>
          <Typography variant="h6" gutterBottom>
            No tasks found
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ marginBottom: 3 }}>
            {activeFiltersCount > 0 
              ? 'Try adjusting your filters or search terms'
              : 'Create your first task to get started'
            }
          </Typography>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setCreateDialogOpen(true)}
          >
            Create Task
          </Button>
        </Paper>
      ) : (
        <>
          {/* Tasks Display */}
          {viewMode === 'grid' ? (
            <Grid container spacing={2}>
              {tasks.map((task) => (
                <Grid item xs={12} sm={6} md={4} lg={3} key={task.id}>
                  <TaskCard task={task} />
                </Grid>
              ))}
            </Grid>
          ) : (
            <TaskList 
              tasks={tasks}
              onTaskClick={(task) => {
                // Navigate to task detail
                window.location.href = `/tasks/${task.id}`;
              }}
            />
          )}

          {/* Pagination */}
          {totalTasks > pagination.per_page && (
            <Box sx={{ 
              display: 'flex', 
              justifyContent: 'center', 
              marginTop: 4,
              gap: 2,
              alignItems: 'center'
            }}>
              <Button
                disabled={pagination.page === 1}
                onClick={() => handlePageChange(pagination.page - 1)}
              >
                Previous
              </Button>
              
              <Typography variant="body2">
                Page {pagination.page} of {Math.ceil(totalTasks / pagination.per_page)}
              </Typography>
              
              <Button
                disabled={pagination.page >= Math.ceil(totalTasks / pagination.per_page)}
                onClick={() => handlePageChange(pagination.page + 1)}
              >
                Next
              </Button>

              <FormControl size="small" sx={{ minWidth: 100 }}>
                <InputLabel>Per Page</InputLabel>
                <Select
                  value={pagination.per_page}
                  label="Per Page"
                  onChange={(e) => handlePerPageChange(Number(e.target.value))}
                >
                  <MenuItem value={10}>10</MenuItem>
                  <MenuItem value={25}>25</MenuItem>
                  <MenuItem value={50}>50</MenuItem>
                  <MenuItem value={100}>100</MenuItem>
                </Select>
              </FormControl>
            </Box>
          )}
        </>
      )}

      {/* Floating Action Button */}
      <Fab
        color="primary"
        aria-label="add task"
        sx={{
          position: 'fixed',
          bottom: 24,
          right: 24,
        }}
        onClick={() => setCreateDialogOpen(true)}
      >
        <AddIcon />
      </Fab>

      {/* Sort Menu */}
      <Menu
        anchorEl={sortMenuAnchor}
        open={Boolean(sortMenuAnchor)}
        onClose={handleSortMenuClose}
      >
        <MenuItem onClick={handleSortMenuClose}>Due Date (Ascending)</MenuItem>
        <MenuItem onClick={handleSortMenuClose}>Due Date (Descending)</MenuItem>
        <MenuItem onClick={handleSortMenuClose}>Priority (High to Low)</MenuItem>
        <MenuItem onClick={handleSortMenuClose}>Priority (Low to High)</MenuItem>
        <MenuItem onClick={handleSortMenuClose}>Created Date (Newest)</MenuItem>
        <MenuItem onClick={handleSortMenuClose}>Created Date (Oldest)</MenuItem>
        <MenuItem onClick={handleSortMenuClose}>Status</MenuItem>
      </Menu>

      {/* Dialogs */}
      <TaskCreateDialog
        open={createDialogOpen}
        onClose={() => setCreateDialogOpen(false)}
      />

      <TaskFiltersPanel
        open={filtersOpen}
        onClose={() => setFiltersOpen(false)}
        filters={filters}
        onFiltersChange={(newFilters) => dispatch(setFilters(newFilters))}
        onClearFilters={handleClearFilters}
      />
    </Box>
  );
};

export default TasksPage;