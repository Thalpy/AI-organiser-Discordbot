# Database Utilities for Discord Task Management Bot
# Centralized database connection and query management

import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Optional, Union
import logging
from config import DB_CONFIG

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Centralized database connection and query management"""
    
    @staticmethod
    def get_connection():
        """Get a database connection"""
        try:
            return psycopg2.connect(**DB_CONFIG)
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise

    @staticmethod
    async def execute_query(query: str, params: tuple = None, fetch_one: bool = False, 
                          fetch_all: bool = False, commit: bool = False) -> Optional[Union[Dict, List[Dict]]]:
        """
        Execute a database query with proper error handling
        
        Args:
            query: SQL query string
            params: Query parameters
            fetch_one: Return single row
            fetch_all: Return all rows
            commit: Commit transaction
            
        Returns:
            Query results or None
        """
        try:
            with DatabaseManager.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(query, params)
                    
                    if commit:
                        conn.commit()
                    
                    if fetch_one:
                        return cur.fetchone()
                    elif fetch_all:
                        return cur.fetchall()
                    
                    return None
                    
        except Exception as e:
            logger.error(f"Query execution failed: {query} - Error: {e}")
            raise

    @staticmethod
    async def execute_many(query: str, params_list: List[tuple], commit: bool = True) -> bool:
        """
        Execute multiple queries with the same statement
        
        Args:
            query: SQL query string
            params_list: List of parameter tuples
            commit: Commit transaction
            
        Returns:
            Success status
        """
        try:
            with DatabaseManager.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.executemany(query, params_list)
                    
                    if commit:
                        conn.commit()
                    
                    return True
                    
        except Exception as e:
            logger.error(f"Batch query execution failed: {query} - Error: {e}")
            return False

class TaskQueries:
    """Pre-defined queries for task operations"""
    
    @staticmethod
    async def get_user_tasks(user_id: str, status: str = None, limit: int = 25) -> List[Dict]:
        """Get tasks for a specific user"""
        if status:
            query = """
                SELECT id, description, due_time, duration_minutes, deadline, location, priority, status
                FROM tasks 
                WHERE user_id = %s AND status = %s 
                ORDER BY due_time ASC NULLS LAST, id DESC 
                LIMIT %s
            """
            params = (user_id, status, limit)
        else:
            query = """
                SELECT id, description, due_time, duration_minutes, deadline, location, priority, status
                FROM tasks 
                WHERE user_id = %s 
                ORDER BY due_time ASC NULLS LAST, id DESC 
                LIMIT %s
            """
            params = (user_id, limit)
            
        return await DatabaseManager.execute_query(query, params, fetch_all=True) or []

    @staticmethod
    async def get_task_by_id(task_id: int, user_id: str) -> Optional[Dict]:
        """Get a specific task by ID and user"""
        query = """
            SELECT * FROM tasks 
            WHERE id = %s AND user_id = %s
        """
        return await DatabaseManager.execute_query(query, (task_id, user_id), fetch_one=True)

    @staticmethod
    async def create_task(user_id: str, description: str, **kwargs) -> Optional[int]:
        """Create a new task and return its ID"""
        # Build dynamic query based on provided fields
        fields = ['user_id', 'description']
        values = [user_id, description]
        placeholders = ['%s', '%s']
        
        for field, value in kwargs.items():
            if value is not None:
                fields.append(field)
                values.append(value)
                placeholders.append('%s')
        
        query = f"""
            INSERT INTO tasks ({', '.join(fields)})
            VALUES ({', '.join(placeholders)})
            RETURNING id
        """
        
        result = await DatabaseManager.execute_query(query, tuple(values), fetch_one=True, commit=True)
        return result['id'] if result else None

    @staticmethod
    async def update_task(task_id: int, user_id: str, **kwargs) -> bool:
        """Update a task with provided fields"""
        if not kwargs:
            return False
            
        set_clauses = []
        values = []
        
        for field, value in kwargs.items():
            set_clauses.append(f"{field} = %s")
            values.append(value)
        
        values.extend([task_id, user_id])
        
        query = f"""
            UPDATE tasks 
            SET {', '.join(set_clauses)}
            WHERE id = %s AND user_id = %s
        """
        
        try:
            await DatabaseManager.execute_query(query, tuple(values), commit=True)
            return True
        except:
            return False

    @staticmethod
    async def delete_task(task_id: int, user_id: str) -> bool:
        """Delete a task"""
        query = "DELETE FROM tasks WHERE id = %s AND user_id = %s"
        try:
            await DatabaseManager.execute_query(query, (task_id, user_id), commit=True)
            return True
        except:
            return False

    @staticmethod
    async def get_task_counts(user_id: str) -> Dict[str, int]:
        """Get task counts by status for a user"""
        query = """
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending,
                COUNT(CASE WHEN status = 'in_progress' THEN 1 END) as in_progress,
                COUNT(CASE WHEN status = 'done' THEN 1 END) as done
            FROM tasks 
            WHERE user_id = %s
        """
        result = await DatabaseManager.execute_query(query, (user_id,), fetch_one=True)
        return dict(result) if result else {'total': 0, 'pending': 0, 'in_progress': 0, 'done': 0}

class UserQueries:
    """Pre-defined queries for user operations"""
    
    @staticmethod
    async def get_user_preferences(user_id: str) -> Dict:
        """Get user preferences with defaults"""
        query = "SELECT * FROM user_preferences WHERE user_id = %s"
        result = await DatabaseManager.execute_query(query, (user_id,), fetch_one=True)
        
        if result:
            return dict(result)
        else:
            # Return defaults
            return {
                'user_id': user_id,
                'work_start': '09:00',
                'work_end': '17:00',
                'lunch_duration_minutes': 30,
                'time_zone': 'GMT',
                'lunch_window_start': '12:00',
                'lunch_window_end': '14:00'
            }

    @staticmethod
    async def update_user_preference(user_id: str, field: str, value: Any) -> bool:
        """Update a single user preference"""
        query = f"""
            INSERT INTO user_preferences (user_id, {field})
            VALUES (%s, %s)
            ON CONFLICT (user_id) DO UPDATE SET {field} = EXCLUDED.{field}
        """
        try:
            await DatabaseManager.execute_query(query, (user_id, value), commit=True)
            return True
        except:
            return False

    @staticmethod
    async def get_notification_preferences(user_id: str) -> Dict:
        """Get notification preferences with defaults"""
        query = "SELECT * FROM notification_preferences WHERE user_id = %s"
        result = await DatabaseManager.execute_query(query, (user_id,), fetch_one=True)
        
        if result:
            return dict(result)
        else:
            # Return defaults
            return {
                'user_id': user_id,
                'task_reminders': True,
                'overdue_alerts': True,
                'daily_summaries': True,
                'reminder_minutes': 15,
                'quiet_hours_start': None,
                'quiet_hours_end': None
            }

# Convenience function for backward compatibility
def get_connection():
    """Legacy function for backward compatibility"""
    return DatabaseManager.get_connection()