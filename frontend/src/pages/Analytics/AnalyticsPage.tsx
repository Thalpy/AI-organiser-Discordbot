// Analytics dashboard page with interactive charts

import React, { useState, useMemo } from 'react';
import {
  Box,
  Grid,
  Paper,
  Typography,
  Card,
  CardContent,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  IconButton,
  Tooltip,
  Alert,
  CircularProgress,
  Chip,
  Stack,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  Download as DownloadIcon,
  TrendingUp as TrendingUpIcon,
  Assignment as AssignmentIcon,
  Timer as TimerIcon,
  CheckCircle as CheckCircleIcon,
  Group as GroupIcon,
  Speed as SpeedIcon,
} from '@mui/icons-material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { subDays, format } from 'date-fns';

import { useGetAnalyticsQuery } from '../../store/api/analyticsApi';
import { AnalyticsTimeframe } from '../../types';

import ProductivityChart from '../../components/Analytics/ProductivityChart';
import TaskCompletionChart from '../../components/Analytics/TaskCompletionChart';
import PriorityDistributionChart from '../../components/Analytics/PriorityDistributionChart';
import TimeTrackingChart from '../../components/Analytics/TimeTrackingChart';
import GoalProgressCard from '../../components/Analytics/GoalProgressCard';
import PerformanceMetrics from '../../components/Analytics/PerformanceMetrics';
import RecommendationsPanel from '../../components/Analytics/RecommendationsPanel';

const AnalyticsPage: React.FC = () => {
  // Local state
  const [timeframe, setTimeframe] = useState<AnalyticsTimeframe>('week');
  const [startDate, setStartDate] = useState<Date>(subDays(new Date(), 7));
  const [endDate, setEndDate] = useState<Date>(new Date());
  const [selectedMetric, setSelectedMetric] = useState<string>('completion_rate');

  // Fetch analytics data
  const { 
    data: analyticsData, 
    isLoading, 
    error, 
    refetch 
  } = useGetAnalyticsQuery({
    timeframe,
    start_date: startDate.toISOString(),
    end_date: endDate.toISOString(),
  });

  const analytics = analyticsData?.analytics;
  const recommendations = analyticsData?.recommendations || [];
  const charts = analyticsData?.charts || {};

  // Handle timeframe change
  const handleTimeframeChange = (newTimeframe: AnalyticsTimeframe) => {
    setTimeframe(newTimeframe);
    
    // Update date range based on timeframe
    const now = new Date();
    switch (newTimeframe) {
      case 'day':
        setStartDate(subDays(now, 1));
        break;
      case 'week':
        setStartDate(subDays(now, 7));
        break;
      case 'month':
        setStartDate(subDays(now, 30));
        break;
      case 'quarter':
        setStartDate(subDays(now, 90));
        break;
      case 'year':
        setStartDate(subDays(now, 365));
        break;
    }
    setEndDate(now);
  };

  // Handle data export
  const handleExport = async (format: 'csv' | 'pdf') => {
    try {
      // This would call an export API endpoint
      const exportData = {
        timeframe,
        start_date: startDate.toISOString(),
        end_date: endDate.toISOString(),
        format,
      };
      
      console.log('Exporting analytics data:', exportData);
      // TODO: Implement actual export functionality
      alert(`Exporting analytics data as ${format.toUpperCase()}...`);
    } catch (error) {
      console.error('Failed to export data:', error);
    }
  };

  // Calculate key metrics
  const keyMetrics = useMemo(() => {
    if (!analytics) return [];

    return [
      {
        title: 'Completion Rate',
        value: `${Math.round(analytics.completion_rate * 100)}%`,
        icon: <CheckCircleIcon />,
        color: 'success' as const,
        trend: analytics.completion_rate > 0.8 ? 'up' : analytics.completion_rate > 0.6 ? 'stable' : 'down',
      },
      {
        title: 'Total Tasks',
        value: analytics.total_tasks.toString(),
        icon: <AssignmentIcon />,
        color: 'primary' as const,
        trend: 'stable' as const,
      },
      {
        title: 'Avg Duration',
        value: `${Math.round(analytics.avg_duration)}m`,
        icon: <TimerIcon />,
        color: 'info' as const,
        trend: analytics.avg_duration < 30 ? 'up' : 'stable',
      },
      {
        title: 'Performance Score',
        value: analytics.performance_score.toString(),
        icon: <SpeedIcon />,
        color: 'warning' as const,
        trend: analytics.performance_score > 80 ? 'up' : analytics.performance_score > 60 ? 'stable' : 'down',
      },
    ];
  }, [analytics]);

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '400px' }}>
        <CircularProgress size={60} />
      </Box>
    );
  }

  if (error) {
    return (
      <Box>
        <Typography variant="h4" component="h1" gutterBottom>
          Analytics Dashboard
        </Typography>
        <Alert severity="error">
          Failed to load analytics data. Please try again.
        </Alert>
      </Box>
    );
  }

  return (
    <Box>
      {/* Page Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" component="h1" gutterBottom>
            Analytics Dashboard
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Track your productivity and performance metrics
          </Typography>
        </Box>
        
        <Stack direction="row" spacing={1}>
          <Tooltip title="Refresh Data">
            <IconButton onClick={() => refetch()} disabled={isLoading}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
          
          <Button
            variant="outlined"
            startIcon={<DownloadIcon />}
            onClick={() => handleExport('csv')}
          >
            Export CSV
          </Button>
          
          <Button
            variant="outlined"
            startIcon={<DownloadIcon />}
            onClick={() => handleExport('pdf')}
          >
            Export PDF
          </Button>
        </Stack>
      </Box>

      {/* Filters */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} sm={6} md={3}>
            <FormControl fullWidth size="small">
              <InputLabel>Timeframe</InputLabel>
              <Select
                value={timeframe}
                label="Timeframe"
                onChange={(e) => handleTimeframeChange(e.target.value as AnalyticsTimeframe)}
              >
                <MenuItem value="day">Last 24 Hours</MenuItem>
                <MenuItem value="week">Last Week</MenuItem>
                <MenuItem value="month">Last Month</MenuItem>
                <MenuItem value="quarter">Last Quarter</MenuItem>
                <MenuItem value="year">Last Year</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          
          <Grid item xs={12} sm={6} md={3}>
            <DatePicker
              label="Start Date"
              value={startDate}
              onChange={(date) => date && setStartDate(date)}
              slotProps={{
                textField: {
                  size: 'small',
                  fullWidth: true,
                },
              }}
            />
          </Grid>
          
          <Grid item xs={12} sm={6} md={3}>
            <DatePicker
              label="End Date"
              value={endDate}
              onChange={(date) => date && setEndDate(date)}
              slotProps={{
                textField: {
                  size: 'small',
                  fullWidth: true,
                },
              }}
            />
          </Grid>
          
          <Grid item xs={12} sm={6} md={3}>
            <Typography variant="body2" color="text.secondary">
              Period: {format(startDate, 'MMM d')} - {format(endDate, 'MMM d, yyyy')}
            </Typography>
          </Grid>
        </Grid>
      </Paper>

      {/* Key Metrics Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        {keyMetrics.map((metric, index) => (
          <Grid item xs={12} sm={6} md={3} key={index}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <Box>
                    <Typography variant="h4" component="div" gutterBottom>
                      {metric.value}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {metric.title}
                    </Typography>
                  </Box>
                  <Box sx={{ color: `${metric.color}.main` }}>
                    {metric.icon}
                  </Box>
                </Box>
                
                <Box sx={{ mt: 1 }}>
                  <Chip
                    size="small"
                    label={metric.trend === 'up' ? 'Trending Up' : metric.trend === 'down' ? 'Trending Down' : 'Stable'}
                    color={metric.trend === 'up' ? 'success' : metric.trend === 'down' ? 'error' : 'default'}
                    icon={<TrendingUpIcon />}
                  />
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Charts Grid */}
      <Grid container spacing={3}>
        {/* Productivity Chart */}
        <Grid item xs={12} lg={8}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Productivity Trends
            </Typography>
            <ProductivityChart 
              data={charts.productivity || []}
              timeframe={timeframe}
            />
          </Paper>
        </Grid>

        {/* Goal Progress */}
        <Grid item xs={12} lg={4}>
          <GoalProgressCard 
            goals={analytics?.goals || []}
            currentStreak={analytics?.current_streak || 0}
          />
        </Grid>

        {/* Task Completion Chart */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Task Completion
            </Typography>
            <TaskCompletionChart 
              data={charts.completion || []}
              completionRate={analytics?.completion_rate || 0}
            />
          </Paper>
        </Grid>

        {/* Priority Distribution */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Priority Distribution
            </Typography>
            <PriorityDistributionChart 
              data={charts.priority_distribution || []}
            />
          </Paper>
        </Grid>

        {/* Time Tracking */}
        <Grid item xs={12} lg={8}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Time Tracking Analysis
            </Typography>
            <TimeTrackingChart 
              data={charts.time_tracking || []}
              avgDuration={analytics?.avg_duration || 0}
              bestDay={analytics?.best_day || 'Monday'}
              peakHour={analytics?.peak_hour || 9}
            />
          </Paper>
        </Grid>

        {/* Performance Metrics */}
        <Grid item xs={12} lg={4}>
          <PerformanceMetrics 
            analytics={analytics}
            selectedMetric={selectedMetric}
            onMetricChange={setSelectedMetric}
          />
        </Grid>

        {/* Recommendations */}
        <Grid item xs={12}>
          <RecommendationsPanel 
            recommendations={recommendations}
            performanceScore={analytics?.performance_score || 0}
          />
        </Grid>
      </Grid>
    </Box>
  );
};

export default AnalyticsPage;