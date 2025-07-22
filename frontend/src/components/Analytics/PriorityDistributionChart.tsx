// Priority distribution chart component

import React from 'react';
import {
  Box,
  Typography,
  useTheme,
  Stack,
  LinearProgress,
} from '@mui/material';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import {
  Flag as FlagIcon,
} from '@mui/icons-material';

interface PriorityDistributionChartProps {
  data: Array<{
    priority: string;
    count: number;
    percentage: number;
    completion_rate: number;
  }>;
}

const PriorityDistributionChart: React.FC<PriorityDistributionChartProps> = ({ data }) => {
  const theme = useTheme();

  // Color mapping for priorities
  const priorityColors = {
    urgent: theme.palette.error.main,
    high: theme.palette.warning.main,
    normal: theme.palette.primary.main,
    low: theme.palette.success.main,
  };

  // Format data for chart
  const chartData = data.map(item => ({
    ...item,
    name: item.priority.toUpperCase(),
    fill: priorityColors[item.priority as keyof typeof priorityColors] || theme.palette.grey[500],
  }));

  // Custom tooltip
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <Box
          sx={{
            backgroundColor: 'background.paper',
            border: 1,
            borderColor: 'divider',
            borderRadius: 1,
            p: 2,
            boxShadow: 2,
          }}
        >
          <Typography variant="subtitle2" gutterBottom>
            {data.name} Priority
          </Typography>
          <Typography variant="body2">
            Tasks: {data.count}
          </Typography>
          <Typography variant="body2">
            Distribution: {Math.round(data.percentage)}%
          </Typography>
          <Typography variant="body2">
            Completion Rate: {Math.round(data.completion_rate * 100)}%
          </Typography>
        </Box>
      );
    }
    return null;
  };

  if (!data || data.length === 0) {
    return (
      <Box sx={{ 
        height: 300, 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        color: 'text.secondary'
      }}>
        <Typography variant="body2">
          No priority distribution data available
        </Typography>
      </Box>
    );
  }

  return (
    <Box>
      {/* Bar Chart */}
      <Box sx={{ height: 200, mb: 3 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
            <XAxis 
              dataKey="name" 
              stroke={theme.palette.text.secondary}
              fontSize={12}
            />
            <YAxis 
              stroke={theme.palette.text.secondary}
              fontSize={12}
            />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="count" radius={[4, 4, 0, 0]}>
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.fill} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </Box>

      {/* Priority Breakdown */}
      <Box>
        <Typography variant="subtitle2" gutterBottom>
          Priority Analysis
        </Typography>
        <Stack spacing={2}>
          {chartData.map((item, index) => (
            <Box key={index}>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <FlagIcon 
                    sx={{ 
                      color: item.fill, 
                      fontSize: 16 
                    }} 
                  />
                  <Typography variant="body2" fontWeight="medium">
                    {item.name}
                  </Typography>
                </Box>
                <Box sx={{ textAlign: 'right' }}>
                  <Typography variant="body2" fontWeight="medium">
                    {item.count} tasks
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {Math.round(item.percentage)}% of total
                  </Typography>
                </Box>
              </Box>
              
              {/* Completion Rate Progress Bar */}
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Typography variant="caption" color="text.secondary" sx={{ minWidth: 80 }}>
                  Completion:
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={item.completion_rate * 100}
                  sx={{
                    flexGrow: 1,
                    height: 6,
                    borderRadius: 3,
                    backgroundColor: 'grey.200',
                    '& .MuiLinearProgress-bar': {
                      backgroundColor: item.fill,
                      borderRadius: 3,
                    },
                  }}
                />
                <Typography variant="caption" color="text.secondary" sx={{ minWidth: 35 }}>
                  {Math.round(item.completion_rate * 100)}%
                </Typography>
              </Box>
            </Box>
          ))}
        </Stack>
      </Box>

      {/* Summary Stats */}
      <Box sx={{ mt: 3, p: 2, backgroundColor: 'grey.50', borderRadius: 1 }}>
        <Typography variant="subtitle2" gutterBottom>
          Priority Insights
        </Typography>
        <Stack spacing={1}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
            <Typography variant="body2" color="text.secondary">
              Most Common Priority:
            </Typography>
            <Typography variant="body2" fontWeight="medium">
              {chartData.reduce((max, current) => 
                current.count > max.count ? current : max
              ).name}
            </Typography>
          </Box>
          
          <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
            <Typography variant="body2" color="text.secondary">
              Best Completion Rate:
            </Typography>
            <Typography variant="body2" fontWeight="medium">
              {chartData.reduce((max, current) => 
                current.completion_rate > max.completion_rate ? current : max
              ).name} ({Math.round(chartData.reduce((max, current) => 
                current.completion_rate > max.completion_rate ? current : max
              ).completion_rate * 100)}%)
            </Typography>
          </Box>
          
          <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
            <Typography variant="body2" color="text.secondary">
              Total Tasks:
            </Typography>
            <Typography variant="body2" fontWeight="medium">
              {data.reduce((sum, item) => sum + item.count, 0)}
            </Typography>
          </Box>
        </Stack>
      </Box>
    </Box>
  );
};

export default PriorityDistributionChart;