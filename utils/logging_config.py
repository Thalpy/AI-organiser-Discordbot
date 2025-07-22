"""Logging configuration for the application"""

import logging
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name"""
    return logging.getLogger(name)


class UserActionLogger:
    """Logger for user actions"""
    
    def __init__(self):
        self.logger = logging.getLogger("user_actions")
    
    def log_task_action(self, user_id: str, action: str, task_id: Any, details: Optional[str] = None):
        """Log a task-related action"""
        self.logger.info(
            f"User {user_id} {action} task {task_id}" + 
            (f": {details}" if details else "")
        )
    
    def log_user_action(self, user_id: str, action: str, details: Optional[str] = None):
        """Log a general user action"""
        self.logger.info(
            f"User {user_id} {action}" + 
            (f": {details}" if details else "")
        )
    
    def log_admin_action(self, admin_id: str, action: str, details: Optional[str] = None):
        """Log an admin action"""
        self.logger.info(
            f"Admin {admin_id} {action}" + 
            (f": {details}" if details else "")
        )


def get_user_action_logger() -> UserActionLogger:
    """Get the user action logger"""
    return UserActionLogger()


class PerformanceMonitor:
    """Context manager for monitoring function performance"""
    
    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.logger = logging.getLogger("performance")
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        if duration > 1.0:  # Log slow operations (> 1 second)
            self.logger.warning(f"Slow operation: {self.operation_name} took {duration:.4f} seconds")
        else:
            self.logger.debug(f"Operation: {self.operation_name} took {duration:.4f} seconds")


def performance_monitor(func: Callable) -> Callable:
    """Decorator for monitoring function performance"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        with PerformanceMonitor(func.__name__):
            return func(*args, **kwargs)
    return wrapper


def setup_logging(log_level: str = "INFO") -> None:
    """Setup logging with the specified log level"""
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        numeric_level = logging.INFO
    
    # Configure root logger
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )