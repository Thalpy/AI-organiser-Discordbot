// Time tracking analysis chart component

import React from 'react';
import {
  Box,
  Typography,
  useTheme,
  Grid,
  Card,
  CardContent,
  Stack,
  Chip,
} from '@mui/material';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell,
} from 'recharts';
import {
  Schedule as ScheduleIcon,
  TrendingUp as TrendingUpIcon,
  AccessTime as AccessTimeIcon,
} from '@mui/icons-material';

interface TimeTrackingChartProps {
  data: Array<{
    hour: number;
    tasks_completed: number;
    avg_duration: number;
    efficiency_score: number;
  }>;
  avgDuration: number;
  bestDay: string;
  peakHour: number;
}

const TimeTrackingChart: React.FC<TimeTrackingChartProps> = ({ 
  data, 
  avgDuration, 
  bestDay, 
  peakHour 
}) => {
  const theme = useTheme();
  const [chartType, setChartType] = React.useState<'hourly' | 'efficiency'>('hourly');

  // Format data for hourly productivity chart
  const hourlyData = data.map(item => ({
    ...item,
    hour_label: `${item.hour}:00`,
    tasks_completed: item.tasks_completed || 0,
    avg_duration: Math.round(item.avg_duration || 0),
    efficiency_score: Math.round(item.efficiency_score || 0),
  }));

  // Generate weekly pattern data (mock data for demonstration)
  const weeklyData = [
    { day: 'Mon', tasks: 12, duration: 25, efficiency: 85 },
    { day: 'Tue', tasks: 15, duration: 22, efficiency: 90 },
    { day: 'Wed', tasks: 10, duration: 30, efficiency: 75 },
    { day: 'Thu', tasks: 18, duration: 20, efficiency: 95 },
    { day: 'Fri', tasks: 14, duration: 28, efficiency: 80 },
    { day: 'Sat', tasks: 8, duration: 35, efficiency: 70 },
    { day: 'Sun', tasks: 6, duration: 40, efficiency: 65 },
  ];

  // Custom tooltip
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
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
            {chartType === 'hourly' ? `${label}` : label}
          </Typography>
          {payload.map((entry: any, index: number) => (
            <Typography
              key={index}
              variant="body2"
              sx={{ color: entry.color }}
            >
              {entry.name}: {entry.value}
              {entry.dataKey === 'avg_duration' && ' min'}
              {entry.dataKey === 'efficiency_score' && '%'}
            </Typography>
          ))}
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
          No time tracking data available
        </Typography>
      </Box>
    );
  }

  return (
    <Box>
      {/* Chart Type Toggle */}
      <Box sx={{ mb: 2 }}>
        <Stack direction="row" spacing={1}>
          <Chip
            label="Hourly Productivity"
            variant={chartType === 'hourly' ? 'filled' : 'outlined'}
            onClick={() => setChartType('hourly')}
            size="small"
          />
          <Chip
            label="Weekly Pattern"
            variant={chartType === 'efficiency' ? 'filled' : 'outlined'}
            onClick={() => setChartType('efficiency')}
            size="small"
          />
        </Stack>
      </Box>

      {/* Main Chart */}
      <Box sx={{ height: 250, mb: 3 }}>
        <ResponsiveContainer width="100%" height="100%">
          {chartType === 'hourly' ? (
            <AreaChart data={hourlyData}>
              <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
              <XAxis 
                dataKey="hour_label" 
                stroke={theme.palette.text.secondary}
                fontSize={12}
              />
              <YAxis 
                stroke={theme.palette.text.secondary}
                fontSize={12}
              />
              <Tooltip content={<CustomTooltip />} />
              <Area
                type="monotone"
                dataKey="tasks_completed"
                stroke={theme.palette.primary.main}
                fill={theme.palette.primary.main}
                fillOpacity={0.3}
                name="Tasks Completed"
              />
            </AreaChart>
          ) : (
            <BarChart data={weeklyData}>
              <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
              <XAxis 
                dataKey="day" 
                stroke={theme.palette.text.secondary}
                fontSize={12}
              />
              <YAxis 
                stroke={theme.palette.text.secondary}
                fontSize={12}
              />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="tasks" fill={theme.palette.secondary.main} name="Tasks" />
            </BarChart>
          )}
        </ResponsiveContainer>
      </Box>

      {/* Time Insights Cards */}
      <Grid container spacing={2}>
        <Grid item xs={12} sm={4}>
          <Card variant="outlined">
            <CardContent sx={{ textAlign: 'center' }}>
              <AccessTimeIcon color="primary" sx={{ fontSize: 32, mb: 1 }} />
              <Typography variant="h6" fontWeight="bold">
                {Math.round(avgDuration)}m
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Average Duration
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={4}>
          <Card variant="outlined">
            <CardContent sx={{ textAlign: 'center' }}>
              <TrendingUpIcon color="success" sx={{ fontSize: 32, mb: 1 }} />
              <Typography variant="h6" fontWeight="bold">
                {peakHour}:00
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Peak Productivity Hour
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={4}>
          <Card variant="outlined">
            <CardContent sx={{ textAlign: 'center' }}>
              <ScheduleIcon color="warning" sx={{ fontSize: 32, mb: 1 }} />
              <Typography variant="h6" fontWeight="bold">
                {bestDay}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Most Productive Day
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Time Distribution Analysis */}
      <Box sx={{ mt: 3 }}>
        <Typography variant="subtitle2" gutterBottom>
          Time Distribution Analysis
        </Typography>
        
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <Box sx={{ p: 2, backgroundColor: 'grey.50', borderRadius: 1 }}>
              <Typography variant="body2" fontWeight="medium" gutterBottom>
                Peak Hours (Most Active)
              </Typography>
              <Stack spacing={1}>
                {hourlyData
                  .sort((a, b) => b.tasks_completed - a.tasks_completed)
                  .slice(0, 3)
                  .map((item, index) => (
                    <Box key={index} sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography variant="body2">
                        {item.hour_label}
                      </Typography>
                      <Typography variant="body2" color="primary.main">
                        {item.tasks_completed} tasks
                      </Typography>
                    </Box>
                  ))}
              </Stack>
            </Box>
          </Grid>

          <Grid item xs={12} md={6}>
            <Box sx={{ p: 2, backgroundColor: 'grey.50', borderRadius: 1 }}>
              <Typography variant="body2" fontWeight="medium" gutterBottom>
                Efficiency Hours (Best Performance)
              </Typography>
              <Stack spacing={1}>
                {hourlyData
                  .sort((a, b) => b.efficiency_score - a.efficiency_score)
                  .slice(0, 3)
                  .map((item, index) => (
                    <Box key={index} sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography variant="body2">
                        {item.hour_label}
                      </Typography>
                      <Typography variant="body2" color="success.main">
                        {item.efficiency_score}% efficiency
                      </Typography>
                    </Box>
                  ))}
              </Stack>
            </Box>
          </Grid>
        </Grid>
      </Box>
    </Box>
  );
};

export default TimeTrackingChart;