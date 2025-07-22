// Productivity trends chart component

import React from 'react';
import {
  Box,
  useTheme,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Area,
  AreaChart,
} from 'recharts';

import { AnalyticsTimeframe } from '../../types';

interface ProductivityChartProps {
  data: Array<{
    date: string;
    completed_tasks: number;
    total_tasks: number;
    completion_rate: number;
    avg_duration: number;
    performance_score: number;
  }>;
  timeframe: AnalyticsTimeframe;
}

const ProductivityChart: React.FC<ProductivityChartProps> = ({ data, timeframe }) => {
  const theme = useTheme();
  const [chartType, setChartType] = React.useState<'line' | 'area'>('area');
  const [metric, setMetric] = React.useState<'completion_rate' | 'performance_score' | 'avg_duration'>('completion_rate');

  // Format data for display
  const chartData = data.map(item => ({
    ...item,
    date: new Date(item.date).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      ...(timeframe === 'year' && { year: '2-digit' }),
    }),
    completion_rate: Math.round(item.completion_rate * 100),
    avg_duration: Math.round(item.avg_duration),
  }));

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
            {label}
          </Typography>
          {payload.map((entry: any, index: number) => (
            <Typography
              key={index}
              variant="body2"
              sx={{ color: entry.color }}
            >
              {entry.name}: {entry.value}
              {entry.dataKey === 'completion_rate' && '%'}
              {entry.dataKey === 'avg_duration' && 'm'}
            </Typography>
          ))}
        </Box>
      );
    }
    return null;
  };

  // Get metric label and color
  const getMetricConfig = (metricKey: string) => {
    switch (metricKey) {
      case 'completion_rate':
        return {
          label: 'Completion Rate (%)',
          color: theme.palette.success.main,
          strokeWidth: 3,
        };
      case 'performance_score':
        return {
          label: 'Performance Score',
          color: theme.palette.primary.main,
          strokeWidth: 3,
        };
      case 'avg_duration':
        return {
          label: 'Avg Duration (min)',
          color: theme.palette.warning.main,
          strokeWidth: 3,
        };
      default:
        return {
          label: 'Value',
          color: theme.palette.primary.main,
          strokeWidth: 2,
        };
    }
  };

  const metricConfig = getMetricConfig(metric);

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
          No productivity data available for the selected period
        </Typography>
      </Box>
    );
  }

  return (
    <Box>
      {/* Chart Controls */}
      <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
        <FormControl size="small" sx={{ minWidth: 150 }}>
          <InputLabel>Metric</InputLabel>
          <Select
            value={metric}
            label="Metric"
            onChange={(e) => setMetric(e.target.value as any)}
          >
            <MenuItem value="completion_rate">Completion Rate</MenuItem>
            <MenuItem value="performance_score">Performance Score</MenuItem>
            <MenuItem value="avg_duration">Avg Duration</MenuItem>
          </Select>
        </FormControl>

        <FormControl size="small" sx={{ minWidth: 120 }}>
          <InputLabel>Chart Type</InputLabel>
          <Select
            value={chartType}
            label="Chart Type"
            onChange={(e) => setChartType(e.target.value as any)}
          >
            <MenuItem value="area">Area</MenuItem>
            <MenuItem value="line">Line</MenuItem>
          </Select>
        </FormControl>
      </Box>

      {/* Chart */}
      <Box sx={{ height: 300 }}>
        <ResponsiveContainer width="100%" height="100%">
          {chartType === 'area' ? (
            <AreaChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
              <XAxis 
                dataKey="date" 
                stroke={theme.palette.text.secondary}
                fontSize={12}
              />
              <YAxis 
                stroke={theme.palette.text.secondary}
                fontSize={12}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend />
              <Area
                type="monotone"
                dataKey={metric}
                stroke={metricConfig.color}
                fill={metricConfig.color}
                fillOpacity={0.3}
                strokeWidth={metricConfig.strokeWidth}
                name={metricConfig.label}
              />
            </AreaChart>
          ) : (
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
              <XAxis 
                dataKey="date" 
                stroke={theme.palette.text.secondary}
                fontSize={12}
              />
              <YAxis 
                stroke={theme.palette.text.secondary}
                fontSize={12}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend />
              <Line
                type="monotone"
                dataKey={metric}
                stroke={metricConfig.color}
                strokeWidth={metricConfig.strokeWidth}
                dot={{ fill: metricConfig.color, strokeWidth: 2, r: 4 }}
                activeDot={{ r: 6, stroke: metricConfig.color, strokeWidth: 2 }}
                name={metricConfig.label}
              />
            </LineChart>
          )}
        </ResponsiveContainer>
      </Box>

      {/* Chart Summary */}
      <Box sx={{ mt: 2, display: 'flex', gap: 3, flexWrap: 'wrap' }}>
        <Box>
          <Typography variant="caption" color="text.secondary">
            Average {metricConfig.label}
          </Typography>
          <Typography variant="body2" fontWeight="medium">
            {Math.round(
              chartData.reduce((sum, item) => sum + item[metric], 0) / chartData.length
            )}
            {metric === 'completion_rate' && '%'}
            {metric === 'avg_duration' && 'm'}
          </Typography>
        </Box>
        
        <Box>
          <Typography variant="caption" color="text.secondary">
            Best Day
          </Typography>
          <Typography variant="body2" fontWeight="medium">
            {chartData.reduce((best, current) => 
              current[metric] > best[metric] ? current : best
            ).date}
          </Typography>
        </Box>
        
        <Box>
          <Typography variant="caption" color="text.secondary">
            Total Data Points
          </Typography>
          <Typography variant="body2" fontWeight="medium">
            {chartData.length}
          </Typography>
        </Box>
      </Box>
    </Box>
  );
};

export default ProductivityChart;