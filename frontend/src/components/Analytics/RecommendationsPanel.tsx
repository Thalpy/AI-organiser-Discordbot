// Recommendations panel component

import React from 'react';
import {
  Paper,
  Typography,
  Box,
  Stack,
  Chip,
  Button,
  IconButton,
  Collapse,
  Alert,
  LinearProgress,
} from '@mui/material';
import {
  Lightbulb as LightbulbIcon,
  TrendingUp as TrendingUpIcon,
  Schedule as ScheduleIcon,
  Assignment as AssignmentIcon,
  Speed as SpeedIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  CheckCircle as CheckCircleIcon,
  Close as CloseIcon,
} from '@mui/icons-material';

interface Recommendation {
  id: string;
  type: 'productivity' | 'time_management' | 'goal_setting' | 'efficiency';
  title: string;
  description: string;
  impact: 'high' | 'medium' | 'low';
  effort: 'high' | 'medium' | 'low';
  category: string;
  actionable_steps?: string[];
  estimated_improvement?: number;
}

interface RecommendationsPanelProps {
  recommendations: Recommendation[];
  performanceScore: number;
}

const RecommendationsPanel: React.FC<RecommendationsPanelProps> = ({
  recommendations,
  performanceScore,
}) => {
  const [expandedRecommendations, setExpandedRecommendations] = React.useState<Set<string>>(new Set());
  const [dismissedRecommendations, setDismissedRecommendations] = React.useState<Set<string>>(new Set());

  // Toggle recommendation expansion
  const toggleRecommendation = (id: string) => {
    const newExpanded = new Set(expandedRecommendations);
    if (newExpanded.has(id)) {
      newExpanded.delete(id);
    } else {
      newExpanded.add(id);
    }
    setExpandedRecommendations(newExpanded);
  };

  // Dismiss recommendation
  const dismissRecommendation = (id: string) => {
    setDismissedRecommendations(prev => new Set([...prev, id]));
  };

  // Get recommendation icon
  const getRecommendationIcon = (type: string) => {
    switch (type) {
      case 'productivity':
        return <TrendingUpIcon color="primary" />;
      case 'time_management':
        return <ScheduleIcon color="warning" />;
      case 'goal_setting':
        return <AssignmentIcon color="success" />;
      case 'efficiency':
        return <SpeedIcon color="error" />;
      default:
        return <LightbulbIcon color="action" />;
    }
  };

  // Get impact color
  const getImpactColor = (impact: string) => {
    switch (impact) {
      case 'high':
        return 'error';
      case 'medium':
        return 'warning';
      case 'low':
        return 'success';
      default:
        return 'default';
    }
  };

  // Get effort color
  const getEffortColor = (effort: string) => {
    switch (effort) {
      case 'high':
        return 'error';
      case 'medium':
        return 'warning';
      case 'low':
        return 'success';
      default:
        return 'default';
    }
  };

  // Filter out dismissed recommendations
  const activeRecommendations = recommendations.filter(rec => !dismissedRecommendations.has(rec.id));

  // Sort recommendations by impact and effort
  const sortedRecommendations = activeRecommendations.sort((a, b) => {
    const impactWeight = { high: 3, medium: 2, low: 1 };
    const effortWeight = { low: 3, medium: 2, high: 1 }; // Lower effort is better
    
    const aScore = impactWeight[a.impact] + effortWeight[a.effort];
    const bScore = impactWeight[b.impact] + effortWeight[b.effort];
    
    return bScore - aScore;
  });

  return (
    <Paper sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
        <LightbulbIcon color="primary" />
        <Typography variant="h6">
          Personalized Recommendations
        </Typography>
      </Box>

      {/* Performance Context */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          Based on your performance score of {performanceScore}%, here are some suggestions to improve:
        </Typography>
        <LinearProgress
          variant="determinate"
          value={performanceScore}
          color={performanceScore >= 80 ? 'success' : performanceScore >= 60 ? 'warning' : 'error'}
          sx={{ height: 6, borderRadius: 3 }}
        />
      </Box>

      {/* Recommendations List */}
      {sortedRecommendations.length === 0 ? (
        <Alert severity="success" icon={<CheckCircleIcon />}>
          Great job! You're performing well. Keep up the excellent work!
        </Alert>
      ) : (
        <Stack spacing={2}>
          {sortedRecommendations.map((recommendation) => (
            <Box
              key={recommendation.id}
              sx={{
                border: 1,
                borderColor: 'divider',
                borderRadius: 1,
                overflow: 'hidden',
              }}
            >
              {/* Recommendation Header */}
              <Box
                sx={{
                  p: 2,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  cursor: 'pointer',
                  '&:hover': {
                    backgroundColor: 'action.hover',
                  },
                }}
                onClick={() => toggleRecommendation(recommendation.id)}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flexGrow: 1 }}>
                  {getRecommendationIcon(recommendation.type)}
                  <Box sx={{ flexGrow: 1 }}>
                    <Typography variant="subtitle2" gutterBottom>
                      {recommendation.title}
                    </Typography>
                    <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                      <Chip
                        label={`${recommendation.impact} impact`}
                        size="small"
                        color={getImpactColor(recommendation.impact)}
                        variant="outlined"
                      />
                      <Chip
                        label={`${recommendation.effort} effort`}
                        size="small"
                        color={getEffortColor(recommendation.effort)}
                        variant="outlined"
                      />
                      <Chip
                        label={recommendation.category}
                        size="small"
                        variant="outlined"
                      />
                    </Box>
                  </Box>
                </Box>
                
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  {recommendation.estimated_improvement && (
                    <Chip
                      label={`+${recommendation.estimated_improvement}%`}
                      size="small"
                      color="primary"
                      icon={<TrendingUpIcon />}
                    />
                  )}
                  <IconButton
                    size="small"
                    onClick={(e) => {
                      e.stopPropagation();
                      dismissRecommendation(recommendation.id);
                    }}
                  >
                    <CloseIcon fontSize="small" />
                  </IconButton>
                  <IconButton size="small">
                    {expandedRecommendations.has(recommendation.id) ? (
                      <ExpandLessIcon />
                    ) : (
                      <ExpandMoreIcon />
                    )}
                  </IconButton>
                </Box>
              </Box>

              {/* Recommendation Details */}
              <Collapse in={expandedRecommendations.has(recommendation.id)}>
                <Box sx={{ p: 2, pt: 0, borderTop: 1, borderColor: 'divider' }}>
                  <Typography variant="body2" color="text.secondary" paragraph>
                    {recommendation.description}
                  </Typography>

                  {/* Actionable Steps */}
                  {recommendation.actionable_steps && recommendation.actionable_steps.length > 0 && (
                    <Box sx={{ mb: 2 }}>
                      <Typography variant="subtitle2" gutterBottom>
                        Action Steps:
                      </Typography>
                      <Stack spacing={1}>
                        {recommendation.actionable_steps.map((step, index) => (
                          <Box key={index} sx={{ display: 'flex', alignItems: 'flex-start', gap: 1 }}>
                            <Typography variant="body2" color="primary.main" sx={{ minWidth: 20 }}>
                              {index + 1}.
                            </Typography>
                            <Typography variant="body2">
                              {step}
                            </Typography>
                          </Box>
                        ))}
                      </Stack>
                    </Box>
                  )}

                  {/* Action Buttons */}
                  <Box sx={{ display: 'flex', gap: 1 }}>
                    <Button
                      size="small"
                      variant="contained"
                      onClick={() => {
                        // TODO: Implement action tracking
                        console.log('Implementing recommendation:', recommendation.id);
                      }}
                    >
                      Implement
                    </Button>
                    <Button
                      size="small"
                      variant="outlined"
                      onClick={() => {
                        // TODO: Implement reminder functionality
                        console.log('Setting reminder for:', recommendation.id);
                      }}
                    >
                      Remind Later
                    </Button>
                  </Box>
                </Box>
              </Collapse>
            </Box>
          ))}
        </Stack>
      )}

      {/* Summary */}
      {sortedRecommendations.length > 0 && (
        <Box sx={{ mt: 3, p: 2, backgroundColor: 'grey.50', borderRadius: 1 }}>
          <Typography variant="subtitle2" gutterBottom>
            Recommendation Summary
          </Typography>
          <Stack direction="row" spacing={2} flexWrap="wrap">
            <Box>
              <Typography variant="caption" color="text.secondary">
                Total Recommendations
              </Typography>
              <Typography variant="body2" fontWeight="medium">
                {sortedRecommendations.length}
              </Typography>
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary">
                High Impact
              </Typography>
              <Typography variant="body2" fontWeight="medium" color="error.main">
                {sortedRecommendations.filter(r => r.impact === 'high').length}
              </Typography>
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary">
                Low Effort
              </Typography>
              <Typography variant="body2" fontWeight="medium" color="success.main">
                {sortedRecommendations.filter(r => r.effort === 'low').length}
              </Typography>
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary">
                Potential Improvement
              </Typography>
              <Typography variant="body2" fontWeight="medium" color="primary.main">
                +{sortedRecommendations.reduce((sum, r) => sum + (r.estimated_improvement || 0), 0)}%
              </Typography>
            </Box>
          </Stack>
        </Box>
      )}
    </Paper>
  );
};

export default RecommendationsPanel;