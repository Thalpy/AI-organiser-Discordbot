// Goal progress tracking card component

import React from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  LinearProgress,
  Stack,
  Chip,
  IconButton,
  Button,
  Divider,
} from '@mui/material';
import {
  TrendingUp as TrendingUpIcon,
  Flag as FlagIcon,
  Add as AddIcon,
  Edit as EditIcon,
  LocalFireDepartment as StreakIcon,
} from '@mui/icons-material';

interface Goal {
  id: number;
  title: string;
  target_value: number;
  current_value: number;
  period_type: 'daily' | 'weekly' | 'monthly';
  goal_type: 'completion_rate' | 'daily_tasks' | 'time_management';
  is_active: boolean;
  end_date?: string;
}

interface GoalProgressCardProps {
  goals: Goal[];
  currentStreak: number;
}

const GoalProgressCard: React.FC<GoalProgressCardProps> = ({ goals, currentStreak }) => {
  const [showAllGoals, setShowAllGoals] = React.useState(false);

  // Filter active goals
  const activeGoals = goals.filter(goal => goal.is_active);
  const displayGoals = showAllGoals ? activeGoals : activeGoals.slice(0, 3);

  // Calculate progress percentage
  const getProgressPercentage = (goal: Goal) => {
    return Math.min((goal.current_value / goal.target_value) * 100, 100);
  };

  // Get goal type display info
  const getGoalTypeInfo = (goalType: string) => {
    switch (goalType) {
      case 'completion_rate':
        return { label: 'Completion Rate', unit: '%', color: 'success' as const };
      case 'daily_tasks':
        return { label: 'Daily Tasks', unit: ' tasks', color: 'primary' as const };
      case 'time_management':
        return { label: 'Time Management', unit: ' min', color: 'warning' as const };
      default:
        return { label: 'Goal', unit: '', color: 'default' as const };
    }
  };

  // Get progress color based on percentage
  const getProgressColor = (percentage: number) => {
    if (percentage >= 100) return 'success';
    if (percentage >= 75) return 'primary';
    if (percentage >= 50) return 'warning';
    return 'error';
  };

  return (
    <Card>
      <CardContent>
        {/* Header */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">
            Goal Progress
          </Typography>
          <IconButton size="small">
            <AddIcon />
          </IconButton>
        </Box>

        {/* Current Streak */}
        <Box sx={{ 
          display: 'flex', 
          alignItems: 'center', 
          gap: 1, 
          mb: 3,
          p: 2,
          backgroundColor: 'primary.50',
          borderRadius: 1,
        }}>
          <StreakIcon color="primary" />
          <Box>
            <Typography variant="h5" fontWeight="bold" color="primary.main">
              {currentStreak}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Day Streak
            </Typography>
          </Box>
        </Box>

        {/* Goals List */}
        {activeGoals.length === 0 ? (
          <Box sx={{ textAlign: 'center', py: 3 }}>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              No active goals set
            </Typography>
            <Button
              variant="outlined"
              size="small"
              startIcon={<AddIcon />}
            >
              Create Goal
            </Button>
          </Box>
        ) : (
          <Stack spacing={2}>
            {displayGoals.map((goal) => {
              const progress = getProgressPercentage(goal);
              const typeInfo = getGoalTypeInfo(goal.goal_type);
              const progressColor = getProgressColor(progress);

              return (
                <Box key={goal.id}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                    <Box sx={{ flexGrow: 1 }}>
                      <Typography variant="body2" fontWeight="medium" gutterBottom>
                        {goal.title}
                      </Typography>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                        <Chip
                          label={typeInfo.label}
                          size="small"
                          color={typeInfo.color}
                          variant="outlined"
                        />
                        <Chip
                          label={goal.period_type}
                          size="small"
                          variant="outlined"
                        />
                      </Box>
                    </Box>
                    <IconButton size="small">
                      <EditIcon fontSize="small" />
                    </IconButton>
                  </Box>

                  {/* Progress Bar */}
                  <Box sx={{ mb: 1 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                      <Typography variant="caption" color="text.secondary">
                        Progress
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {goal.current_value}{typeInfo.unit} / {goal.target_value}{typeInfo.unit}
                      </Typography>
                    </Box>
                    <LinearProgress
                      variant="determinate"
                      value={progress}
                      color={progressColor}
                      sx={{ height: 6, borderRadius: 3 }}
                    />
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 0.5 }}>
                      <Typography variant="caption" color={`${progressColor}.main`}>
                        {Math.round(progress)}%
                      </Typography>
                      {progress >= 100 && (
                        <Chip
                          label="Completed!"
                          size="small"
                          color="success"
                          icon={<TrendingUpIcon />}
                        />
                      )}
                    </Box>
                  </Box>

                  {/* End Date */}
                  {goal.end_date && (
                    <Typography variant="caption" color="text.secondary">
                      Due: {new Date(goal.end_date).toLocaleDateString()}
                    </Typography>
                  )}
                </Box>
              );
            })}

            {/* Show More/Less Button */}
            {activeGoals.length > 3 && (
              <>
                <Divider />
                <Button
                  size="small"
                  onClick={() => setShowAllGoals(!showAllGoals)}
                  sx={{ alignSelf: 'center' }}
                >
                  {showAllGoals ? 'Show Less' : `Show ${activeGoals.length - 3} More`}
                </Button>
              </>
            )}
          </Stack>
        )}

        {/* Goal Summary */}
        {activeGoals.length > 0 && (
          <>
            <Divider sx={{ my: 2 }} />
            <Box>
              <Typography variant="subtitle2" gutterBottom>
                Goal Summary
              </Typography>
              <Stack direction="row" spacing={2} flexWrap="wrap">
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    Active Goals
                  </Typography>
                  <Typography variant="body2" fontWeight="medium">
                    {activeGoals.length}
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    Completed
                  </Typography>
                  <Typography variant="body2" fontWeight="medium" color="success.main">
                    {activeGoals.filter(goal => getProgressPercentage(goal) >= 100).length}
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    In Progress
                  </Typography>
                  <Typography variant="body2" fontWeight="medium" color="primary.main">
                    {activeGoals.filter(goal => {
                      const progress = getProgressPercentage(goal);
                      return progress > 0 && progress < 100;
                    }).length}
                  </Typography>
                </Box>
              </Stack>
            </Box>
          </>
        )}
      </CardContent>
    </Card>
  );
};

export default GoalProgressCard;