"""
Comprehensive logging configuration for Discord Task Management Bot
Provides structured logging with performance monitoring and user action tracking
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional

import structlog
from pythonjsonlogger import jsonlogger


class PerformanceFilter(logging.Filter):
    """Filter to add performance metrics to log records"""
    
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, 'duration'):
            record.duration = 0.0
        if not hasattr(record, 'operation'):
            record.operation = 'unknown'
        return True


class UserActionFilter(logging.Filter):
    """Filter to add user context to log records"""
    
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, 'user_id'):
            record.user_id = 'system'
        if not hasattr(record, 'action'):
            record.action = 'unknown'
        return True


def setup_logging(
    log_level: str = "INFO",
    log_dir: str = "logs",
    enable_json: bool = True,
    enable_console: bool = True
) -> None:
    """
    Set up comprehensive logging configuration
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory to store log files
        enable_json: Whether to enable JSON structured logging
        enable_console: Whether to enable console logging
    """
    
    # Create logs directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if enable_json else structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(getattr(logging, log_level.upper()))
        root_logger.addHandler(console_handler)
    
    # File handlers
    if enable_json:
        # JSON structured logs
        json_handler = logging.handlers.RotatingFileHandler(
            os.path.join(log_dir, 'app.json.log'),
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        json_formatter = jsonlogger.JsonFormatter(
            '%(asctime)s %(name)s %(levelname)s %(message)s %(user_id)s %(action)s %(duration)s'
        )
        json_handler.setFormatter(json_formatter)
        json_handler.addFilter(UserActionFilter())
        json_handler.addFilter(PerformanceFilter())
        root_logger.addHandler(json_handler)
    
    # Error log file
    error_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'errors.log'),
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3
    )
    error_handler.setLevel(logging.ERROR)
    error_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s\n%(pathname)s:%(lineno)d\n'
    )
    error_handler.setFormatter(error_formatter)
    root_logger.addHandler(error_handler)
    
    # Performance log file
    perf_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'performance.log'),
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3
    )
    perf_formatter = logging.Formatter(
        '%(asctime)s - %(operation)s - %(duration).3fs - %(message)s'
    )
    perf_handler.setFormatter(perf_formatter)
    perf_handler.addFilter(PerformanceFilter())
    
    # Create performance logger
    perf_logger = logging.getLogger('performance')
    perf_logger.addHandler(perf_handler)
    perf_logger.setLevel(logging.INFO)
    
    # User action log file
    action_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'user_actions.log'),
        maxBytes=5*1024*1024,  # 5MB
        backupCount=5
    )
    action_formatter = logging.Formatter(
        '%(asctime)s - %(user_id)s - %(action)s - %(message)s'
    )
    action_handler.setFormatter(action_formatter)
    action_handler.addFilter(UserActionFilter())
    
    # Create user action logger
    action_logger = logging.getLogger('user_actions')
    action_logger.addHandler(action_handler)
    action_logger.setLevel(logging.INFO)
    
    # Discord.py specific logging
    discord_logger = logging.getLogger('discord')
    discord_logger.setLevel(logging.WARNING)  # Reduce Discord.py verbosity
    
    # Database logging
    db_logger = logging.getLogger('database')
    db_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'database.log'),
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3
    )
    db_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    db_handler.setFormatter(db_formatter)
    db_logger.addHandler(db_handler)
    db_logger.setLevel(logging.INFO)


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a structured logger instance
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


def get_performance_logger() -> logging.Logger:
    """Get the performance logger"""
    return logging.getLogger('performance')


def get_user_action_logger() -> 'UserActionLogger':
    """Get the user action logger"""
    return UserActionLogger()


def get_database_logger() -> logging.Logger:
    """Get the database logger"""
    return logging.getLogger('database')


class PerformanceMonitor:
    """Context manager for performance monitoring"""
    
    def __init__(self, operation: str, logger: Optional[logging.Logger] = None):
        self.operation = operation
        self.logger = logger or get_performance_logger()
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = (datetime.now() - self.start_time).total_seconds()
            self.logger.info(
                f"Operation completed: {self.operation}",
                extra={
                    'operation': self.operation,
                    'duration': duration,
                    'success': exc_type is None
                }
            )


class UserActionLogger:
    """Logger for user actions and interactions"""
    
    def __init__(self):
        self.logger = logging.getLogger('user_actions')
    
    def log_task_action(
        self,
        user_id: str,
        action: str,
        task_id: Optional[int] = None,
        details: Optional[str] = None
    ) -> None:
        """Log a task-related user action"""
        message = f"Task action: {action}"
        if task_id:
            message += f" (Task ID: {task_id})"
        if details:
            message += f" - {details}"
        
        self.logger.info(
            message,
            extra={
                'user_id': user_id,
                'action': action,
                'task_id': task_id,
                'details': details
            }
        )
    
    def log_discord_command(
        self,
        user_id: str,
        command: str,
        guild_id: Optional[str] = None,
        success: bool = True
    ) -> None:
        """Log a Discord command execution"""
        message = f"Discord command: {command}"
        if not success:
            message += " (FAILED)"
        
        self.logger.info(
            message,
            extra={
                'user_id': user_id,
                'action': f'discord_command_{command}',
                'guild_id': guild_id,
                'success': success
            }
        )
    
    def log_web_action(
        self,
        user_id: str,
        action: str,
        endpoint: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> None:
        """Log a web interface action"""
        message = f"Web action: {action}"
        if endpoint:
            message += f" ({endpoint})"
        
        self.logger.info(
            message,
            extra={
                'user_id': user_id,
                'action': f'web_{action}',
                'endpoint': endpoint,
                'ip_address': ip_address
            }
        )
    
    def log_notification_sent(
        self,
        user_id: str,
        notification_type: str,
        channel: str,
        success: bool = True
    ) -> None:
        """Log a notification delivery"""
        message = f"Notification sent: {notification_type} via {channel}"
        if not success:
            message += " (FAILED)"
        
        self.logger.info(
            message,
            extra={
                'user_id': user_id,
                'action': f'notification_{notification_type}',
                'channel': channel,
                'success': success
            }
        )


# Initialize logging on module import
def init_logging():
    """Initialize logging with default configuration"""
    log_level = os.getenv('LOG_LEVEL', 'INFO')
    log_dir = os.getenv('LOG_DIR', 'logs')
    enable_json = os.getenv('ENABLE_JSON_LOGS', 'true').lower() == 'true'
    
    setup_logging(
        log_level=log_level,
        log_dir=log_dir,
        enable_json=enable_json
    )


# Auto-initialize if not in test environment
if os.getenv('ENVIRONMENT') != 'test':
    init_logging()