"""
Enhanced database manager with async support for multi-user collaboration
Extends the existing database utilities with new collaborative features
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import asyncpg
import redis.asyncio as redis
from utils.database import DatabaseManager as BaseDatabaseManager
from utils.logging_config import get_database_logger, get_performance_logger

from .models import (
    Task,
    TaskAssignment,
    TaskMessage,
    TaskTemplate,
    RecurringTask,
    UserSession,
    APIKey,
    ProductivityGoal,
    UserActivity,
)

logger = get_database_logger()
perf_logger = get_performance_logger()


class AsyncDatabaseManager(BaseDatabaseManager):
    """Enhanced async database manager with collaboration features"""
    
    def __init__(self, db_config: Dict[str, Any], redis_config: Dict[str, Any]):
        super().__init__()
        self.db_config = db_config
        self.redis_config = redis_config
        self._db_pool: Optional[asyncpg.Pool] = None
        self._redis_pool: Optional[redis.Redis] = None
    
    async def initialize(self):
        """Initialize database and Redis connections"""
        try:
            # Initialize PostgreSQL connection pool
            self._db_pool = await asyncpg.create_pool(
                host=self.db_config['host'],
                port=self.db_config['port'],
                user=self.db_config['user'],
                password=self.db_config['password'],
                database=self.db_config['database'],
                min_size=5,
                max_size=20,
                command_timeout=30
            )
            
            # Initialize Redis connection pool
            self._redis_pool = redis.Redis(
                host=self.redis_config['host'],
                port=self.redis_config['port'],
                password=self.redis_config.get('password'),
                decode_responses=True,
                max_connections=20
            )
            
            logger.info("Database connections initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database connections: {e}")
            raise
    
    async def close(self):
        """Close database connections"""
        if self._db_pool:
            await self._db_pool.close()
        if self._redis_pool:
            await self._redis_pool.close()
        logger.info("Database connections closed")
    
    async def execute_query(
        self,
        query: str,
        params: tuple = None,
        fetch_one: bool = False,
        fetch_all: bool = False
    ) -> Optional[Union[Dict, List[Dict]]]:
        """Execute async database query with performance monitoring"""
        start_time = datetime.now()
        
        try:
            async with self._db_pool.acquire() as conn:
                if params:
                    result = await conn.fetch(query, *params) if fetch_all else await conn.fetchrow(query, *params) if fetch_one else await conn.execute(query, *params)
                else:
                    result = await conn.fetch(query) if fetch_all else await conn.fetchrow(query) if fetch_one else await conn.execute(query)
                
                # Convert asyncpg.Record to dict
                if fetch_all and result:
                    result = [dict(row) for row in result]
                elif fetch_one and result:
                    result = dict(result)
                
                duration = (datetime.now() - start_time).total_seconds()
                perf_logger.info(
                    f"Query executed successfully",
                    extra={'operation': 'database_query', 'duration': duration}
                )
                
                return result
                
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"Query execution failed: {query} - Error: {e}")
            perf_logger.error(
                f"Query failed",
                extra={'operation': 'database_query', 'duration': duration}
            )
            raise
    
    async def execute_transaction(self, queries: List[tuple]) -> bool:
        """Execute multiple queries in a transaction"""
        start_time = datetime.now()
        
        try:
            async with self._db_pool.acquire() as conn:
                async with conn.transaction():
                    for query, params in queries:
                        if params:
                            await conn.execute(query, *params)
                        else:
                            await conn.execute(query)
                
                duration = (datetime.now() - start_time).total_seconds()
                perf_logger.info(
                    f"Transaction executed successfully",
                    extra={'operation': 'database_transaction', 'duration': duration}
                )
                return True
                
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"Transaction failed: {e}")
            perf_logger.error(
                f"Transaction failed",
                extra={'operation': 'database_transaction', 'duration': duration}
            )
            return False
    
    # Task-related methods
    async def create_collaborative_task(self, task_data: Dict[str, Any]) -> Optional[int]:
        """Create a collaborative task with assignments"""
        queries = []
        
        # Create the task
        task_query = """
            INSERT INTO tasks (
                description, created_by_user_id, status, priority, due_time,
                duration_minutes, location, is_collaborative, template_id
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING id
        """
        
        try:
            async with self._db_pool.acquire() as conn:
                async with conn.transaction():
                    # Insert task
                    task_id = await conn.fetchval(
                        task_query,
                        task_data['description'],
                        task_data['created_by_user_id'],
                        task_data.get('status', 'pending'),
                        task_data.get('priority', 'normal'),
                        task_data.get('due_time'),
                        task_data.get('duration_minutes', 15),
                        task_data.get('location'),
                        task_data.get('is_collaborative', False),
                        task_data.get('template_id')
                    )
                    
                    # Create assignments if collaborative
                    if task_data.get('assigned_users'):
                        assignment_query = """
                            INSERT INTO task_assignments (
                                task_id, assigned_user_id, assigned_by_user_id
                            ) VALUES ($1, $2, $3)
                        """
                        
                        for user_id in task_data['assigned_users']:
                            await conn.execute(
                                assignment_query,
                                task_id,
                                user_id,
                                task_data['created_by_user_id']
                            )
                    
                    logger.info(f"Created collaborative task {task_id}")
                    return task_id
                    
        except Exception as e:
            logger.error(f"Failed to create collaborative task: {e}")
            return None
    
    async def get_collaborative_tasks(self, user_id: str) -> List[Dict]:
        """Get tasks where user is assigned or is the creator"""
        query = """
            SELECT DISTINCT t.*, 
                   array_agg(DISTINCT ta.assigned_user_id) as assigned_users,
                   array_agg(DISTINCT ta.status) as assignment_statuses
            FROM tasks t
            LEFT JOIN task_assignments ta ON t.id = ta.task_id
            WHERE t.created_by_user_id = $1 
               OR ta.assigned_user_id = $1
               OR t.is_collaborative = true
            GROUP BY t.id
            ORDER BY t.due_time ASC NULLS LAST, t.created_at DESC
        """
        
        return await self.execute_query(query, (user_id,), fetch_all=True) or []
    
    async def assign_task_to_users(
        self,
        task_id: int,
        user_ids: List[str],
        assigned_by: str
    ) -> bool:
        """Assign task to multiple users"""
        queries = []
        
        # First, mark task as collaborative
        queries.append((
            "UPDATE tasks SET is_collaborative = true WHERE id = $1",
            (task_id,)
        ))
        
        # Create assignments
        for user_id in user_ids:
            queries.append((
                """
                INSERT INTO task_assignments (task_id, assigned_user_id, assigned_by_user_id)
                VALUES ($1, $2, $3)
                ON CONFLICT (task_id, assigned_user_id) DO NOTHING
                """,
                (task_id, user_id, assigned_by)
            ))
        
        return await self.execute_transaction(queries)
    
    async def update_task_progress(
        self,
        task_id: int,
        user_id: str,
        progress: int,
        notes: Optional[str] = None
    ) -> bool:
        """Update task progress for a specific user"""
        queries = [
            (
                "UPDATE tasks SET completion_percentage = $1 WHERE id = $2",
                (progress, task_id)
            ),
            (
                """
                UPDATE task_assignments 
                SET completion_notes = $1, completed_at = $2
                WHERE task_id = $3 AND assigned_user_id = $4
                """,
                (notes, datetime.now() if progress == 100 else None, task_id, user_id)
            )
        ]
        
        return await self.execute_transaction(queries)
    
    async def add_task_message(
        self,
        task_id: int,
        user_id: str,
        message: str,
        message_type: str = 'comment',
        parent_id: Optional[int] = None
    ) -> Optional[Dict]:
        """Add a message to task collaboration thread"""
        query = """
            INSERT INTO task_messages (
                task_id, user_id, message, message_type, parent_message_id
            ) VALUES ($1, $2, $3, $4, $5)
            RETURNING id, created_at
        """
        
        result = await self.execute_query(
            query,
            (task_id, user_id, message, message_type, parent_id),
            fetch_one=True
        )
        
        if result:
            return {
                'id': result['id'],
                'task_id': task_id,
                'user_id': user_id,
                'message': message,
                'message_type': message_type,
                'created_at': result['created_at'],
                'parent_message_id': parent_id
            }
        return None
    
    async def get_task_messages(self, task_id: int) -> List[Dict]:
        """Get all messages for a task"""
        query = """
            SELECT * FROM task_messages
            WHERE task_id = $1
            ORDER BY created_at ASC
        """
        
        return await self.execute_query(query, (task_id,), fetch_all=True) or []
    
    # Template-related methods
    async def create_task_template(self, template_data: Dict[str, Any]) -> Optional[int]:
        """Create a task template"""
        query = """
            INSERT INTO task_templates (
                created_by_user_id, name, description, default_duration_minutes,
                default_priority, template_data, is_shared
            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id
        """
        
        result = await self.execute_query(
            query,
            (
                template_data['created_by_user_id'],
                template_data['name'],
                template_data.get('description'),
                template_data.get('default_duration_minutes', 15),
                template_data.get('default_priority', False),
                json.dumps(template_data.get('template_data', {})),
                template_data.get('is_shared', False)
            ),
            fetch_one=True
        )
        
        return result['id'] if result else None
    
    async def get_user_templates(self, user_id: str, include_shared: bool = True) -> List[Dict]:
        """Get templates available to a user"""
        if include_shared:
            query = """
                SELECT * FROM task_templates
                WHERE created_by_user_id = $1 OR is_shared = true
                ORDER BY created_at DESC
            """
            params = (user_id,)
        else:
            query = """
                SELECT * FROM task_templates
                WHERE created_by_user_id = $1
                ORDER BY created_at DESC
            """
            params = (user_id,)
        
        return await self.execute_query(query, params, fetch_all=True) or []
    
    # Session management
    async def create_user_session(self, session_data: Dict[str, Any]) -> bool:
        """Create a user session"""
        query = """
            INSERT INTO user_sessions (
                user_id, session_token, discord_token, expires_at, ip_address, user_agent
            ) VALUES ($1, $2, $3, $4, $5, $6)
        """
        
        try:
            await self.execute_query(
                query,
                (
                    session_data['user_id'],
                    session_data['session_token'],
                    session_data.get('discord_token'),
                    session_data['expires_at'],
                    session_data.get('ip_address'),
                    session_data.get('user_agent')
                )
            )
            return True
        except:
            return False
    
    async def get_user_session(self, session_token: str) -> Optional[Dict]:
        """Get user session by token"""
        query = """
            SELECT * FROM user_sessions
            WHERE session_token = $1 AND expires_at > NOW()
        """
        
        return await self.execute_query(query, (session_token,), fetch_one=True)
    
    async def update_session_activity(self, session_token: str) -> bool:
        """Update session last activity"""
        query = """
            UPDATE user_sessions
            SET last_activity = NOW()
            WHERE session_token = $1
        """
        
        try:
            await self.execute_query(query, (session_token,))
            return True
        except:
            return False
    
    # Cache operations
    async def cache_set(self, key: str, value: Any, expire: int = 3600) -> bool:
        """Set value in Redis cache"""
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            await self._redis_pool.setex(key, expire, value)
            return True
        except Exception as e:
            logger.error(f"Cache set failed for key {key}: {e}")
            return False
    
    async def cache_get(self, key: str) -> Optional[Any]:
        """Get value from Redis cache"""
        try:
            value = await self._redis_pool.get(key)
            if value:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            return None
        except Exception as e:
            logger.error(f"Cache get failed for key {key}: {e}")
            return None
    
    async def cache_delete(self, key: str) -> bool:
        """Delete value from Redis cache"""
        try:
            await self._redis_pool.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete failed for key {key}: {e}")
            return False
    
    # Analytics methods
    async def log_user_activity(self, activity_data: Dict[str, Any]) -> bool:
        """Log user activity"""
        query = """
            INSERT INTO user_activity_log (
                user_id, activity_type, activity_data, source, ip_address
            ) VALUES ($1, $2, $3, $4, $5)
        """
        
        try:
            await self.execute_query(
                query,
                (
                    activity_data['user_id'],
                    activity_data['activity_type'],
                    json.dumps(activity_data.get('activity_data', {})),
                    activity_data['source'],
                    activity_data.get('ip_address')
                )
            )
            return True
        except:
            return False
    
    async def get_user_analytics_data(
        self,
        user_id: str,
        timeframe: str = 'week'
    ) -> Dict[str, Any]:
        """Get analytics data for a user"""
        # This would implement complex analytics queries
        # For now, returning a basic structure
        query = """
            SELECT 
                COUNT(*) as total_tasks,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_tasks,
                AVG(duration_minutes) as avg_duration,
                AVG(actual_duration) as avg_actual_duration
            FROM tasks
            WHERE created_by_user_id = $1
            AND created_at >= NOW() - INTERVAL '1 week'
        """
        
        result = await self.execute_query(query, (user_id,), fetch_one=True)
        
        if result:
            completion_rate = (result['completed_tasks'] / result['total_tasks'] * 100) if result['total_tasks'] > 0 else 0
            
            return {
                'total_tasks': result['total_tasks'],
                'completed_tasks': result['completed_tasks'],
                'completion_rate': completion_rate,
                'avg_duration': result['avg_duration'] or 0,
                'avg_actual_duration': result['avg_actual_duration'] or 0
            }
        
        return {
            'total_tasks': 0,
            'completed_tasks': 0,
            'completion_rate': 0,
            'avg_duration': 0,
            'avg_actual_duration': 0
        }


# Global database manager instance
db_manager: Optional[AsyncDatabaseManager] = None


async def get_database_manager() -> AsyncDatabaseManager:
    """Get the global database manager instance"""
    global db_manager
    if db_manager is None:
        raise RuntimeError("Database manager not initialized")
    return db_manager


async def initialize_database(db_config: Dict[str, Any], redis_config: Dict[str, Any]):
    """Initialize the global database manager"""
    global db_manager
    db_manager = AsyncDatabaseManager(db_config, redis_config)
    await db_manager.initialize()


async def close_database():
    """Close the global database manager"""
    global db_manager
    if db_manager:
        await db_manager.close()
        db_manager = None