// Dashboard page component

import React from 'react';
import {
  Box,
  Grid,
  Paper,
  Typography,
  Card,
  CardContent,
  LinearProgress,
  Chip,
  IconButton,
} from '@mui/material';
import {
  Assignment as TaskIcon,
  TrendingUp as TrendingUpIcon,
  Group as GroupIcon,
  Schedule as ScheduleIcon,
  Add as AddIcon,
} from '@mui/icons-material';

import { useAppSelector } from '../../store/hooks';
import { selectUser } from '../../store/slices/authSlice';
import { useGetTasksQuery } from '../../store/api/taskApi';
import { useGetAnalyticsQuery } from '../../store/api/analyticsApi';

import TaskCard from '../../components/Tasks/TaskCard';
import QuickStats from '../../components/Dashboard/QuickStats';
import RecentActivity from '../../components/Dashboard/RecentActivity';
import ProductivityChart from '../../components/Analytics/ProductivityChart';

const DashboardPage: React.FC = () => {
  const user = useAppSelector(selectUser);
  
  // Fetch recent tasks
  const { data: tasksData, isLoading: tasksLoading } = useGetTasksQuery({
    limit: 5,
    status: undefined,
  });

  // Fetch analytics data
  const { data: analyticsData, isLoading: analyticsLoading } = useGetAnalyticsQuery({
    timeframe: 'week',
  });

  const recentTasks = tasksData?.tasks || [];
  const analytics = analyticsData?.analytics;

  return (
    <Box>
      {/* Welcome Header */}
      <Box sx={{ marginBottom: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Welcome back, {user?.username}!
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Here's what's happening with your tasks today.
        </Typography>
      </Box>

      <Grid container spacing={3}>
        {/* Quick Stats */}
        <Grid item xs={12}>
          <QuickStats 
            analytics={analytics}
            loading={analyticsLoading}
          />
        </Grid>

        {/* Recent Tasks */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ padding: 3 }}>
            <Box sx={{ 
              display: 'flex', 
              justifyContent: 'space-between', 
              alignItems: 'center',
              marginBottom: 2 
            }}>
              <Typography variant="h6" component="h2">
                Recent Tasks
              </Typography>
              <IconButton color="primary" size="small">
                <AddIcon />
              </IconButton>
            </Box>

            {tasksLoading ? (
              <Box sx={{ padding: 2 }}>
                <LinearProgress />
                <Typography variant="body2" sx={{ marginTop: 1 }}>
                  Loading tasks...
                </Typography>
              </Box>
            ) : recentTasks.length > 0 ? (
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                {recentTasks.map((task) => (
                  <TaskCard key={task.id} task={task} compact />
                ))}
              </Box>
            ) : (
              <Box sx={{ 
                textAlign: 'center', 
                padding: 4,
                color: 'text.secondary' 
              }}>
                <TaskIcon sx={{ fontSize: 48, marginBottom: 1 }} />
                <Typography variant="body1">
                  No tasks yet. Create your first task to get started!
                </Typography>
              </Box>
            )}
          </Paper>
        </Grid>

        {/* Productivity Overview */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ padding: 3, height: 'fit-content' }}>
            <Typography variant="h6" component="h2" gutterBottom>
              This Week
            </Typography>
            
            {analyticsLoading ? (
              <LinearProgress />
            ) : analytics ? (
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                {/* Completion Rate */}
                <Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', marginBottom: 1 }}>
                    <Typography variant="body2">Completion Rate</Typography>
                    <Typography variant="body2" fontWeight="medium">
                      {analytics.completion_rate.toFixed(1)}%
                    </Typography>
                  </Box>
                  <LinearProgress 
                    variant="determinate" 
                    value={analytics.completion_rate} 
                    sx={{ height: 8, borderRadius: 4 }}
                  />
                </Box>

                {/* Performance Score */}
                <Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', marginBottom: 1 }}>
                    <Typography variant="body2">Performance Score</Typography>
                    <Typography variant="body2" fontWeight="medium">
                      {analytics.performance_score}/100
                    </Typography>
                  </Box>
                  <LinearProgress 
                    variant="determinate" 
                    value={analytics.performance_score} 
                    color="secondary"
                    sx={{ height: 8, borderRadius: 4 }}
                  />
                </Box>

                {/* Quick Stats */}
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, marginTop: 1 }}>
                  <Chip 
                    icon={<TaskIcon />}
                    label={`${analytics.tasks_completed} completed`}
                    size="small"
                    color="success"
                    variant="outlined"
                  />
                  <Chip 
                    icon={<ScheduleIcon />}
                    label={`${analytics.total_time.toFixed(1)}h total`}
                    size="small"
                    color="primary"
                    variant="outlined"
                  />
                  <Chip 
                    icon={<TrendingUpIcon />}
                    label={`${analytics.current_streak} day streak`}
                    size="small"
                    color="secondary"
                    variant="outlined"
                  />
                </Box>
              </Box>
            ) : (
              <Typography variant="body2" color="text.secondary">
                No analytics data available yet.
              </Typography>
            )}
          </Paper>
        </Grid>

        {/* Productivity Chart */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ padding: 3 }}>
            <Typography variant="h6" component="h2" gutterBottom>
              Productivity Trend
            </Typography>
            <ProductivityChart 
              data={analyticsData?.charts}
              loading={analyticsLoading}
            />
          </Paper>
        </Grid>

        {/* Recent Activity */}
        <Grid item xs={12} md={4}>
          <RecentActivity />
        </Grid>
      </Grid>
    </Box>
  );
};

export default DashboardPage;