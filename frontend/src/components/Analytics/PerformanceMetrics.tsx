// Performance metrics component

import React from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  Stack,
  Chip,
  LinearProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Divider,
  useTheme,
} from '@mui/material';
import {
  Speed as SpeedIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  TrendingFlat as TrendingFlatIcon,
  Timer as TimerIcon,
  CheckCircle as CheckCircleIcon,
  Assignment as AssignmentIcon,
} from '@mui/icons-material';

import { AnalyticsData } from '../../types';

interface PerformanceMetricsProps {
  analytics: AnalyticsData | undefined;
  selectedMetric: string;
  onMetricChange: (metric: string) => void;
}

const PerformanceMetrics: React.FC<PerformanceMetricsProps> = ({
  analytics,
  selectedMetric,
  onMetricChange,
}) => {
  const theme = useTheme();

  if (!analytics) {
    return (
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Performance Metrics
          </Typography>
          <Typography variant="body2" color="text.secondary">
            No performance data available
          </Typography>
        </CardContent>
      </Card>
    );
  }

  // Calculate performance indicators
  const performanceIndicators = [
    {
      key: 'completion_rate',
      label: 'Completion Rate',
      value: Math.round(analytics.completion_rate * 100),
      unit: '%',
      icon: <CheckCircleIcon />,
      color: analytics.completion_rate >= 0.8 ? 'success' : analytics.completion_rate >= 0.6 ? 'warning' : 'error',
      trend: analytics.completion_rate >= 0.8 ? 'up' : analytics.completion_rate >= 0.6 ? 'flat' : 'down',
    },
    {
      key: 'on_time_starts',
      label: 'On-Time Starts',
      value: Math.round(analytics.on_time_starts * 100),
      unit: '%',
      icon: <TimerIcon />,
      color: analytics.on_time_starts >= 0.8 ? 'success' : analytics.on_time_starts >= 0.6 ? 'warning' : 'error',
      trend: analytics.on_time_starts >= 0.8 ? 'up' : analytics.on_time_starts >= 0.6 ? 'flat' : 'down',
    },
    {
      key: 'on_time_finishes',
      label: 'On-Time Finishes',
      value: Math.round(analytics.on_time_finishes * 100),
      unit: '%',
      icon: <AssignmentIcon />,
      color: analytics.on_time_finishes >= 0.8 ? 'success' : analytics.on_time_finishes >= 0.6 ? 'warning' : 'error',
      trend: analytics.on_time_finishes >= 0.8 ? 'up' : analytics.on_time_finishes >= 0.6 ? 'flat' : 'down',
    },
    {
      key: 'priority_completion',
      label: 'Priority Task Completion',
      value: Math.round(analytics.priority_completion * 100),
      unit: '%',
      icon: <SpeedIcon />,
      color: analytics.priority_completion >= 0.8 ? 'success' : analytics.priority_completion >= 0.6 ? 'warning' : 'error',
      trend: analytics.priority_completion >= 0.8 ? 'up' : analytics.priority_completion >= 0.6 ? 'flat' : 'down',
    },
  ];

  // Get trend icon
  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'up':
        return <TrendingUpIcon fontSize="small" color="success" />;
      case 'down':
        return <TrendingDownIcon fontSize="small" color="error" />;
      default:
        return <TrendingFlatIcon fontSize="small" color="action" />;
    }
  };

  // Get performance score color
  const getPerformanceScoreColor = (score: number) => {
    if (score >= 80) return 'success';
    if (score >= 60) return 'warning';
    return 'error';
  };

  const selectedIndicator = performanceIndicators.find(indicator => indicator.key === selectedMetric) || performanceIndicators[0];

  return (
    <Card>
      <CardContent>
        {/* Header */}
        <Typography variant="h6" gutterBottom>
          Performance Metrics
        </Typography>

        {/* Overall Performance Score */}
        <Box sx={{ mb: 3, textAlign: 'center' }}>
          <Box sx={{ position: 'relative', display: 'inline-flex', mb: 2 }}>
            <Box
              sx={{
                width: 80,
                height: 80,
                borderRadius: '50%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: `${getPerformanceScoreColor(analytics.performance_score)}.light`,
                color: `${getPerformanceScoreColor(analytics.performance_score)}.dark`,
              }}
            >
              <Typography variant="h4" fontWeight="bold">
                {analytics.performance_score}
              </Typography>
            </Box>
          </Box>
          <Typography variant="subtitle2" gutterBottom>
            Overall Performance Score
          </Typography>
          <Chip
            label={
              analytics.performance_score >= 80 ? 'Excellent' :
              analytics.performance_score >= 60 ? 'Good' : 'Needs Improvement'
            }
            color={getPerformanceScoreColor(analytics.performance_score)}
            size="small"
          />
        </Box>

        <Divider sx={{ mb: 2 }} />

        {/* Metric Selector */}
        <FormControl fullWidth size="small" sx={{ mb: 2 }}>
          <InputLabel>Select Metric</InputLabel>
          <Select
            value={selectedMetric}
            label="Select Metric"
            onChange={(e) => onMetricChange(e.target.value)}
          >
            {performanceIndicators.map((indicator) => (
              <MenuItem key={indicator.key} value={indicator.key}>
                {indicator.label}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        {/* Selected Metric Details */}
        <Box sx={{ mb: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
            {selectedIndicator.icon}
            <Typography variant="subtitle2">
              {selectedIndicator.label}
            </Typography>
            {getTrendIcon(selectedIndicator.trend)}
          </Box>
          
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
            <Typography variant="h4" fontWeight="bold" color={`${selectedIndicator.color}.main`}>
              {selectedIndicator.value}{selectedIndicator.unit}
            </Typography>
            <Chip
              label={selectedIndicator.color === 'success' ? 'Great' : selectedIndicator.color === 'warning' ? 'Good' : 'Poor'}
              color={selectedIndicator.color}
              size="small"
            />
          </Box>
          
          <LinearProgress
            variant="determinate"
            value={selectedIndicator.value}
            color={selectedIndicator.color}
            sx={{ height: 8, borderRadius: 4 }}
          />
        </Box>

        <Divider sx={{ mb: 2 }} />

        {/* All Metrics Summary */}
        <Typography variant="subtitle2" gutterBottom>
          All Metrics
        </Typography>
        <Stack spacing={1.5}>
          {performanceIndicators.map((indicator) => (
            <Box
              key={indicator.key}
              sx={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                p: 1,
                borderRadius: 1,
                backgroundColor: selectedMetric === indicator.key ? 'action.selected' : 'transparent',
                cursor: 'pointer',
                '&:hover': {
                  backgroundColor: 'action.hover',
                },
              }}
              onClick={() => onMetricChange(indicator.key)}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                {indicator.icon}
                <Typography variant="body2">
                  {indicator.label}
                </Typography>
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Typography variant="body2" fontWeight="medium" color={`${indicator.color}.main`}>
                  {indicator.value}{indicator.unit}
                </Typography>
                {getTrendIcon(indicator.trend)}
              </Box>
            </Box>
          ))}
        </Stack>

        <Divider sx={{ my: 2 }} />

        {/* Additional Stats */}
        <Typography variant="subtitle2" gutterBottom>
          Additional Stats
        </Typography>
        <Stack spacing={1}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
            <Typography variant="body2" color="text.secondary">
              Average Delay:
            </Typography>
            <Typography variant="body2" fontWeight="medium">
              {Math.round(analytics.avg_delay)} min
            </Typography>
          </Box>
          
          <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
            <Typography variant="body2" color="text.secondary">
              Total Time Tracked:
            </Typography>
            <Typography variant="body2" fontWeight="medium">
              {Math.round(analytics.total_time / 60)} hours
            </Typography>
          </Box>
          
          <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
            <Typography variant="body2" color="text.secondary">
              Current Streak:
            </Typography>
            <Typography variant="body2" fontWeight="medium" color="primary.main">
              {analytics.current_streak} days
            </Typography>
          </Box>
        </Stack>
      </CardContent>
    </Card>
  );
};

export default PerformanceMetrics;