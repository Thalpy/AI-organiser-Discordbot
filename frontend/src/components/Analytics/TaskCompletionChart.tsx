// Task completion chart component

import React from 'react';
import {
  Box,
  Typography,
  useTheme,
  Stack,
} from '@mui/material';
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  Legend,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
} from 'recharts';

interface TaskCompletionChartProps {
  data: Array<{
    status: string;
    count: number;
    percentage: number;
  }>;
  completionRate: number;
}

const TaskCompletionChart: React.FC<TaskCompletionChartProps> = ({ 
  data, 
  completionRate 
}) => {
  const theme = useTheme();
  const [chartType, setChartType] = React.useState<'pie' | 'bar'>('pie');

  // Color mapping for task statuses
  const statusColors = {
    completed: theme.palette.success.main,
    in_progress: theme.palette.primary.main,
    pending: theme.palette.warning.main,
    cancelled: theme.palette.error.main,
  };

  // Format data for charts
  const chartData = data.map(item => ({
    ...item,
    name: item.status.replace('_', ' ').toUpperCase(),
    fill: statusColors[item.status as keyof typeof statusColors] || theme.palette.grey[500],
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
            {data.name}
          </Typography>
          <Typography variant="body2">
            Count: {data.count}
          </Typography>
          <Typography variant="body2">
            Percentage: {Math.round(data.percentage)}%
          </Typography>
        </Box>
      );
    }
    return null;
  };

  // Custom label for pie chart
  const renderLabel = (entry: any) => {
    return `${Math.round(entry.percentage)}%`;
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
          No task completion data available
        </Typography>
      </Box>
    );
  }

  return (
    <Box>
      {/* Chart Type Toggle */}
      <Box sx={{ mb: 2 }}>
        <Stack direction="row" spacing={1}>
          <Typography
            variant="body2"
            sx={{
              cursor: 'pointer',
              color: chartType === 'pie' ? 'primary.main' : 'text.secondary',
              textDecoration: chartType === 'pie' ? 'underline' : 'none',
            }}
            onClick={() => setChartType('pie')}
          >
            Pie Chart
          </Typography>
          <Typography variant="body2" color="text.secondary">|</Typography>
          <Typography
            variant="body2"
            sx={{
              cursor: 'pointer',
              color: chartType === 'bar' ? 'primary.main' : 'text.secondary',
              textDecoration: chartType === 'bar' ? 'underline' : 'none',
            }}
            onClick={() => setChartType('bar')}
          >
            Bar Chart
          </Typography>
        </Stack>
      </Box>

      {/* Chart */}
      <Box sx={{ height: 250 }}>
        <ResponsiveContainer width="100%" height="100%">
          {chartType === 'pie' ? (
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={renderLabel}
                outerRadius={80}
                fill="#8884d8"
                dataKey="count"
              >
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.fill} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
              <Legend />
            </PieChart>
          ) : (
            <BarChart data={chartData}>
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
              <Bar dataKey="count" fill={theme.palette.primary.main}>
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          )}
        </ResponsiveContainer>
      </Box>

      {/* Summary Stats */}
      <Box sx={{ mt: 2 }}>
        <Stack direction="row" spacing={3} flexWrap="wrap">
          <Box>
            <Typography variant="caption" color="text.secondary">
              Overall Completion Rate
            </Typography>
            <Typography variant="h6" color="success.main" fontWeight="bold">
              {Math.round(completionRate * 100)}%
            </Typography>
          </Box>
          
          <Box>
            <Typography variant="caption" color="text.secondary">
              Total Tasks
            </Typography>
            <Typography variant="h6" fontWeight="bold">
              {data.reduce((sum, item) => sum + item.count, 0)}
            </Typography>
          </Box>
          
          <Box>
            <Typography variant="caption" color="text.secondary">
              Completed Tasks
            </Typography>
            <Typography variant="h6" color="success.main" fontWeight="bold">
              {data.find(item => item.status === 'completed')?.count || 0}
            </Typography>
          </Box>
        </Stack>
      </Box>

      {/* Status Breakdown */}
      <Box sx={{ mt: 2 }}>
        <Typography variant="subtitle2" gutterBottom>
          Status Breakdown
        </Typography>
        <Stack spacing={1}>
          {chartData.map((item, index) => (
            <Box
              key={index}
              sx={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                p: 1,
                borderRadius: 1,
                backgroundColor: 'grey.50',
              }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Box
                  sx={{
                    width: 12,
                    height: 12,
                    borderRadius: '50%',
                    backgroundColor: item.fill,
                  }}
                />
                <Typography variant="body2">
                  {item.name}
                </Typography>
              </Box>
              <Box sx={{ textAlign: 'right' }}>
                <Typography variant="body2" fontWeight="medium">
                  {item.count}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {Math.round(item.percentage)}%
                </Typography>
              </Box>
            </Box>
          ))}
        </Stack>
      </Box>
    </Box>
  );
};

export default TaskCompletionChart;