"""
Analytics service for productivity insights and recommendations
Provides comprehensive data analysis and personalized suggestions
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict
import statistics

from utils.logging_config import get_logger, PerformanceMonitor

from .database import get_database_manager
from .models import AnalyticsData, ProductivityGoal, UserActivity

logger = get_logger(__name__)


class AnalyticsService:
    """Service for calculating productivity analytics and insights"""
    
    def __init__(self):
        self.db = None
    
    async def initialize(self):
        """Initialize the analytics service"""
        self.db = await get_database_manager()
    
    async def calculate_user_analytics(
        self,
        user_id: str,
        timeframe: str = 'week',
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Calculate comprehensive analytics for a user"""
        with PerformanceMonitor("calculate_user_analytics"):
            try:
                # Set default date range if not provided
                if not end_date:
                    end_date = datetime.now()
                
                if not start_date:
                    if timeframe == 'day':
                        start_date = end_date - timedelta(days=1)
                    elif timeframe == 'week':
                        start_date = end_date - timedelta(weeks=1)
                    elif timeframe == 'month':
                        start_date = end_date - timedelta(days=30)
                    elif timeframe == 'quarter':
                        start_date = end_date - timedelta(days=90)
                    elif timeframe == 'year':
                        start_date = end_date - timedelta(days=365)
                    else:
                        start_date = end_date - timedelta(weeks=1)
                
                # Get task data for the period
                tasks_data = await self._get_tasks_data(user_id, start_date, end_date)
                
                # Calculate basic metrics
                basic_metrics = await self._calculate_basic_metrics(tasks_data)
                
                # Calculate time-based metrics
                time_metrics = await self._calculate_time_metrics(tasks_data)
                
                # Calculate performance metrics
                performance_metrics = await self._calculate_performance_metrics(tasks_data)
                
                # Calculate productivity patterns
                patterns = await self._calculate_productivity_patterns(tasks_data)
                
                # Get user goals
                goals = await self._get_user_goals(user_id)
                
                # Calculate current streak
                current_streak = await self._calculate_current_streak(user_id)
                
                # Combine all analytics
                analytics = AnalyticsData(
                    user_id=user_id,
                    timeframe=timeframe,
                    tasks_completed=basic_metrics['completed'],
                    total_tasks=basic_metrics['total'],
                    completion_rate=basic_metrics['completion_rate'],
                    avg_duration=time_metrics['avg_duration'],
                    on_time_starts=performance_metrics['on_time_starts'],
                    on_time_finishes=performance_metrics['on_time_finishes'],
                    avg_delay=time_metrics['avg_delay'],
                    total_time=time_metrics['total_time'],
                    best_day=patterns['best_day'],
                    peak_hour=patterns['peak_hour'],
                    current_streak=current_streak,
                    priority_completion=performance_metrics['priority_completion'],
                    performance_score=await self._calculate_performance_score(
                        basic_metrics, time_metrics, performance_metrics
                    ),
                    goals=goals
                )
                
                return analytics.__dict__
                
            except Exception as e:
                logger.error(f"Failed to calculate analytics for user {user_id}: {e}")
                raise
    
    async def get_productivity_recommendations(
        self,
        user_id: str,
        analytics_data: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Generate personalized productivity recommendations"""
        with PerformanceMonitor("get_productivity_recommendations"):
            try:
                # Get analytics data if not provided
                if not analytics_data:
                    analytics_data = await self.calculate_user_analytics(user_id)
                
                recommendations = []
                
                # Completion rate recommendations
                if analytics_data['completion_rate'] < 0.7:
                    recommendations.append({
                        'id': f'completion_rate_{user_id}',
                        'type': 'productivity',
                        'title': 'Improve Task Completion Rate',
                        'description': f'Your completion rate is {analytics_data["completion_rate"]*100:.1f}%. Focus on completing smaller tasks first to build momentum.',
                        'impact': 'high',
                        'effort': 'medium',
                        'category': 'Task Management',
                        'actionable_steps': [
                            'Break large tasks into smaller, manageable subtasks',
                            'Use the Pomodoro technique for better focus',
                            'Set daily completion goals',
                            'Review and adjust task priorities regularly'
                        ],
                        'estimated_improvement': 15
                    })
                
                # Time management recommendations
                if analytics_data['avg_delay'] > 30:
                    recommendations.append({
                        'id': f'time_management_{user_id}',
                        'type': 'time_management',
                        'title': 'Reduce Task Delays',
                        'description': f'Your average delay is {analytics_data["avg_delay"]:.1f} minutes. Better time estimation can improve punctuality.',
                        'impact': 'medium',
                        'effort': 'low',
                        'category': 'Time Management',
                        'actionable_steps': [
                            'Add buffer time to task estimates',
                            'Track actual vs estimated time for better planning',
                            'Set reminders 10 minutes before task start times',
                            'Review and adjust your daily schedule'
                        ],
                        'estimated_improvement': 10
                    })
                
                # On-time performance recommendations
                if analytics_data['on_time_starts'] < 0.8:
                    recommendations.append({
                        'id': f'punctuality_{user_id}',
                        'type': 'efficiency',
                        'title': 'Improve Task Start Punctuality',
                        'description': f'You start tasks on time only {analytics_data["on_time_starts"]*100:.1f}% of the time. Better scheduling can help.',
                        'impact': 'medium',
                        'effort': 'low',
                        'category': 'Scheduling',
                        'actionable_steps': [
                            'Set calendar reminders for task start times',
                            'Block time for task preparation',
                            'Review your schedule the night before',
                            'Minimize context switching between tasks'
                        ],
                        'estimated_improvement': 12
                    })
                
                # Priority task recommendations
                if analytics_data['priority_completion'] < 0.8:
                    recommendations.append({
                        'id': f'priority_focus_{user_id}',
                        'type': 'productivity',
                        'title': 'Focus on High-Priority Tasks',
                        'description': f'Your high-priority task completion rate is {analytics_data["priority_completion"]*100:.1f}%. Prioritize important work.',
                        'impact': 'high',
                        'effort': 'medium',
                        'category': 'Prioritization',
                        'actionable_steps': [
                            'Start each day with your highest priority task',
                            'Use the Eisenhower Matrix for task prioritization',
                            'Limit work-in-progress to 3 high-priority items',
                            'Review priorities weekly with your team'
                        ],
                        'estimated_improvement': 20
                    })
                
                # Performance score recommendations
                if analytics_data['performance_score'] < 70:
                    recommendations.append({
                        'id': f'overall_performance_{user_id}',
                        'type': 'productivity',
                        'title': 'Boost Overall Performance',
                        'description': f'Your performance score is {analytics_data["performance_score"]}. A holistic approach can help improve all areas.',
                        'impact': 'high',
                        'effort': 'high',
                        'category': 'Overall Performance',
                        'actionable_steps': [
                            'Conduct a weekly productivity review',
                            'Set specific, measurable goals',
                            'Track your energy levels and work during peak hours',
                            'Eliminate or delegate low-value tasks',
                            'Invest in productivity tools and training'
                        ],
                        'estimated_improvement': 25
                    })
                
                # Goal-setting recommendations
                if not analytics_data.get('goals') or len(analytics_data['goals']) == 0:
                    recommendations.append({
                        'id': f'goal_setting_{user_id}',
                        'type': 'goal_setting',
                        'title': 'Set Productivity Goals',
                        'description': 'Setting specific goals can significantly improve your productivity and motivation.',
                        'impact': 'medium',
                        'effort': 'low',
                        'category': 'Goal Setting',
                        'actionable_steps': [
                            'Set a daily task completion goal',
                            'Create weekly productivity targets',
                            'Track your progress regularly',
                            'Celebrate achievements to maintain motivation'
                        ],
                        'estimated_improvement': 15
                    })
                
                # Sort recommendations by impact and effort
                recommendations.sort(key=lambda x: (
                    {'high': 3, 'medium': 2, 'low': 1}[x['impact']] +
                    {'low': 3, 'medium': 2, 'high': 1}[x['effort']]
                ), reverse=True)
                
                return recommendations
                
            except Exception as e:
                logger.error(f"Failed to generate recommendations for user {user_id}: {e}")
                return []
    
    async def get_team_analytics(
        self,
        team_users: List[str],
        timeframe: str = 'week'
    ) -> Dict[str, Any]:
        """Calculate analytics for a team of users"""
        with PerformanceMonitor("get_team_analytics"):
            try:
                team_analytics = {
                    'team_size': len(team_users),
                    'individual_analytics': {},
                    'team_metrics': {},
                    'collaboration_metrics': {},
                    'recommendations': []
                }
                
                # Get individual analytics for each team member
                individual_results = await asyncio.gather(*[
                    self.calculate_user_analytics(user_id, timeframe)
                    for user_id in team_users
                ])
                
                for user_id, analytics in zip(team_users, individual_results):
                    team_analytics['individual_analytics'][user_id] = analytics
                
                # Calculate team-wide metrics
                team_analytics['team_metrics'] = await self._calculate_team_metrics(
                    individual_results
                )
                
                # Calculate collaboration metrics
                team_analytics['collaboration_metrics'] = await self._calculate_collaboration_metrics(
                    team_users, timeframe
                )
                
                # Generate team recommendations
                team_analytics['recommendations'] = await self._generate_team_recommendations(
                    team_analytics
                )
                
                return team_analytics
                
            except Exception as e:
                logger.error(f"Failed to calculate team analytics: {e}")
                raise
    
    async def get_chart_data(
        self,
        user_id: str,
        chart_type: str,
        timeframe: str = 'week'
    ) -> List[Dict[str, Any]]:
        """Get formatted data for specific chart types"""
        with PerformanceMonitor("get_chart_data"):
            try:
                if chart_type == 'productivity':
                    return await self._get_productivity_chart_data(user_id, timeframe)
                elif chart_type == 'completion':
                    return await self._get_completion_chart_data(user_id, timeframe)
                elif chart_type == 'priority_distribution':
                    return await self._get_priority_distribution_data(user_id, timeframe)
                elif chart_type == 'time_tracking':
                    return await self._get_time_tracking_data(user_id, timeframe)
                else:
                    return []
                    
            except Exception as e:
                logger.error(f"Failed to get chart data for {chart_type}: {e}")
                return []
    
    # Private helper methods
    
    async def _get_tasks_data(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Get task data for analytics calculations"""
        query = """
            SELECT t.*, ta.status as assignment_status, ta.completed_at
            FROM tasks t
            LEFT JOIN task_assignments ta ON t.id = ta.task_id AND ta.assigned_user_id = $1
            WHERE (t.created_by_user_id = $1 OR ta.assigned_user_id = $1)
            AND t.created_at >= $2 AND t.created_at <= $3
            ORDER BY t.created_at
        """
        
        return await self.db.execute_query(query, (user_id, start_date, end_date))
    
    async def _calculate_basic_metrics(self, tasks_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate basic task completion metrics"""
        total_tasks = len(tasks_data)
        completed_tasks = len([t for t in tasks_data if t['status'] == 'completed'])
        
        return {
            'total': total_tasks,
            'completed': completed_tasks,
            'completion_rate': completed_tasks / total_tasks if total_tasks > 0 else 0,
            'pending': len([t for t in tasks_data if t['status'] == 'pending']),
            'in_progress': len([t for t in tasks_data if t['status'] == 'in_progress']),
            'cancelled': len([t for t in tasks_data if t['status'] == 'cancelled'])
        }
    
    async def _calculate_time_metrics(self, tasks_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate time-related metrics"""
        completed_tasks = [t for t in tasks_data if t['status'] == 'completed']
        
        if not completed_tasks:
            return {
                'avg_duration': 0,
                'total_time': 0,
                'avg_delay': 0
            }
        
        durations = [t['duration_minutes'] for t in completed_tasks if t['duration_minutes']]
        delays = []
        
        for task in completed_tasks:
            if task['due_time'] and task['stop_time']:
                due_time = task['due_time']
                stop_time = task['stop_time']
                if stop_time > due_time:
                    delay = (stop_time - due_time).total_seconds() / 60
                    delays.append(delay)
                else:
                    delays.append(0)
        
        return {
            'avg_duration': statistics.mean(durations) if durations else 0,
            'total_time': sum(durations) if durations else 0,
            'avg_delay': statistics.mean(delays) if delays else 0
        }
    
    async def _calculate_performance_metrics(self, tasks_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate performance-related metrics"""
        total_tasks = len(tasks_data)
        
        if total_tasks == 0:
            return {
                'on_time_starts': 0,
                'on_time_finishes': 0,
                'priority_completion': 0
            }
        
        # Calculate on-time starts
        on_time_starts = 0
        for task in tasks_data:
            if task['start_time'] and task['due_time']:
                if task['start_time'] <= task['due_time']:
                    on_time_starts += 1
        
        # Calculate on-time finishes
        on_time_finishes = 0
        completed_tasks = [t for t in tasks_data if t['status'] == 'completed']
        for task in completed_tasks:
            if task['stop_time'] and task['due_time']:
                if task['stop_time'] <= task['due_time']:
                    on_time_finishes += 1
        
        # Calculate priority task completion
        high_priority_tasks = [t for t in tasks_data if t['priority'] in ['high', 'urgent']]
        completed_high_priority = [t for t in high_priority_tasks if t['status'] == 'completed']
        
        return {
            'on_time_starts': on_time_starts / total_tasks,
            'on_time_finishes': on_time_finishes / len(completed_tasks) if completed_tasks else 0,
            'priority_completion': len(completed_high_priority) / len(high_priority_tasks) if high_priority_tasks else 1
        }
    
    async def _calculate_productivity_patterns(self, tasks_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate productivity patterns and trends"""
        if not tasks_data:
            return {
                'best_day': 'Monday',
                'peak_hour': 9
            }
        
        # Calculate best day of week
        day_completion = defaultdict(int)
        day_total = defaultdict(int)
        
        for task in tasks_data:
            day = task['created_at'].strftime('%A')
            day_total[day] += 1
            if task['status'] == 'completed':
                day_completion[day] += 1
        
        best_day = max(day_completion.keys(), 
                      key=lambda d: day_completion[d] / day_total[d] if day_total[d] > 0 else 0,
                      default='Monday')
        
        # Calculate peak hour
        hour_completion = defaultdict(int)
        hour_total = defaultdict(int)
        
        for task in tasks_data:
            hour = task['created_at'].hour
            hour_total[hour] += 1
            if task['status'] == 'completed':
                hour_completion[hour] += 1
        
        peak_hour = max(hour_completion.keys(),
                       key=lambda h: hour_completion[h] / hour_total[h] if hour_total[h] > 0 else 0,
                       default=9)
        
        return {
            'best_day': best_day,
            'peak_hour': peak_hour
        }
    
    async def _calculate_performance_score(
        self,
        basic_metrics: Dict[str, Any],
        time_metrics: Dict[str, Any],
        performance_metrics: Dict[str, Any]
    ) -> int:
        """Calculate overall performance score (0-100)"""
        # Weight different metrics
        completion_weight = 0.3
        punctuality_weight = 0.25
        priority_weight = 0.25
        efficiency_weight = 0.2
        
        # Calculate component scores
        completion_score = basic_metrics['completion_rate'] * 100
        punctuality_score = (performance_metrics['on_time_starts'] + performance_metrics['on_time_finishes']) / 2 * 100
        priority_score = performance_metrics['priority_completion'] * 100
        
        # Efficiency score based on average delay (inverse relationship)
        avg_delay = time_metrics['avg_delay']
        efficiency_score = max(0, 100 - (avg_delay / 60) * 10)  # Penalize delays
        
        # Calculate weighted average
        performance_score = (
            completion_score * completion_weight +
            punctuality_score * punctuality_weight +
            priority_score * priority_weight +
            efficiency_score * efficiency_weight
        )
        
        return min(100, max(0, int(performance_score)))
    
    async def _get_user_goals(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's productivity goals"""
        query = """
            SELECT * FROM productivity_goals
            WHERE user_id = $1 AND is_active = true
            ORDER BY created_at DESC
        """
        
        goals = await self.db.execute_query(query, (user_id,))
        return [dict(goal) for goal in goals]
    
    async def _calculate_current_streak(self, user_id: str) -> int:
        """Calculate current consecutive days with completed tasks"""
        query = """
            SELECT DATE(created_at) as date, COUNT(*) as completed
            FROM tasks
            WHERE created_by_user_id = $1 AND status = 'completed'
            AND created_at >= NOW() - INTERVAL '30 days'
            GROUP BY DATE(created_at)
            ORDER BY date DESC
        """
        
        daily_completions = await self.db.execute_query(query, (user_id,))
        
        if not daily_completions:
            return 0
        
        streak = 0
        current_date = datetime.now().date()
        
        for day_data in daily_completions:
            if day_data['date'] == current_date - timedelta(days=streak):
                if day_data['completed'] > 0:
                    streak += 1
                else:
                    break
            else:
                break
        
        return streak
    
    async def _get_productivity_chart_data(
        self,
        user_id: str,
        timeframe: str
    ) -> List[Dict[str, Any]]:
        """Get data for productivity trend chart"""
        # Implementation for productivity chart data
        # This would return daily/weekly productivity metrics
        return []
    
    async def _get_completion_chart_data(
        self,
        user_id: str,
        timeframe: str
    ) -> List[Dict[str, Any]]:
        """Get data for task completion chart"""
        # Implementation for completion chart data
        return []
    
    async def _get_priority_distribution_data(
        self,
        user_id: str,
        timeframe: str
    ) -> List[Dict[str, Any]]:
        """Get data for priority distribution chart"""
        # Implementation for priority distribution data
        return []
    
    async def _get_time_tracking_data(
        self,
        user_id: str,
        timeframe: str
    ) -> List[Dict[str, Any]]:
        """Get data for time tracking chart"""
        # Implementation for time tracking data
        return []
    
    async def _calculate_team_metrics(self, individual_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate team-wide metrics from individual analytics"""
        if not individual_results:
            return {}
        
        # Calculate team averages
        team_completion_rate = statistics.mean([r['completion_rate'] for r in individual_results])
        team_performance_score = statistics.mean([r['performance_score'] for r in individual_results])
        
        return {
            'team_completion_rate': team_completion_rate,
            'team_performance_score': team_performance_score,
            'total_tasks_completed': sum([r['tasks_completed'] for r in individual_results]),
            'total_tasks': sum([r['total_tasks'] for r in individual_results])
        }
    
    async def _calculate_collaboration_metrics(
        self,
        team_users: List[str],
        timeframe: str
    ) -> Dict[str, Any]:
        """Calculate collaboration-specific metrics"""
        # Implementation for collaboration metrics
        return {
            'collaborative_tasks': 0,
            'cross_team_assignments': 0,
            'message_exchanges': 0
        }
    
    async def _generate_team_recommendations(self, team_analytics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate team-specific recommendations"""
        # Implementation for team recommendations
        return []


# Global service instance
analytics_service: Optional[AnalyticsService] = None


async def get_analytics_service() -> AnalyticsService:
    """Get the global analytics service instance"""
    global analytics_service
    if analytics_service is None:
        analytics_service = AnalyticsService()
        await analytics_service.initialize()
    return analytics_service