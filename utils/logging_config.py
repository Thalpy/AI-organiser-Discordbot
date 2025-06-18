# Logging Configuration for Discord Task Management Bot
# Comprehensive logging setup with different levels and handlers

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from typing import Optional

class BotLogger:
    """Centralized logging configuration for the Discord bot"""
    
    @staticmethod
    def setup_logging(
        log_level: str = "INFO",
        log_to_file: bool = True,
        log_to_console: bool = True,
        log_directory: str = "logs",
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5
    ):
        """
        Setup comprehensive logging for the bot
        
        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_to_file: Whether to log to files
            log_to_console: Whether to log to console
            log_directory: Directory for log files
            max_file_size: Maximum size of each log file in bytes
            backup_count: Number of backup files to keep
        """
        
        # Create logs directory if it doesn't exist
        if log_to_file and not os.path.exists(log_directory):
            os.makedirs(log_directory)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, log_level.upper()))
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            fmt='%(asctime)s | %(levelname)-8s | %(name)-20s | %(funcName)-15s:%(lineno)-4d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        simple_formatter = logging.Formatter(
            fmt='%(asctime)s | %(levelname)-8s | %(name)-15s | %(message)s',
            datefmt='%H:%M:%S'
        )
        
        # Console handler
        if log_to_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(simple_formatter)
            root_logger.addHandler(console_handler)
        
        if log_to_file:
            # Main log file (all levels)
            main_log_file = os.path.join(log_directory, 'bot.log')
            main_handler = logging.handlers.RotatingFileHandler(
                main_log_file,
                maxBytes=max_file_size,
                backupCount=backup_count,
                encoding='utf-8'
            )
            main_handler.setLevel(logging.DEBUG)
            main_handler.setFormatter(detailed_formatter)
            root_logger.addHandler(main_handler)
            
            # Error log file (errors and critical only)
            error_log_file = os.path.join(log_directory, 'errors.log')
            error_handler = logging.handlers.RotatingFileHandler(
                error_log_file,
                maxBytes=max_file_size,
                backupCount=backup_count,
                encoding='utf-8'
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(detailed_formatter)
            root_logger.addHandler(error_handler)
            
            # Discord interactions log (for debugging user interactions)
            discord_log_file = os.path.join(log_directory, 'discord_interactions.log')
            discord_handler = logging.handlers.RotatingFileHandler(
                discord_log_file,
                maxBytes=max_file_size,
                backupCount=backup_count,
                encoding='utf-8'
            )
            discord_handler.setLevel(logging.INFO)
            discord_handler.setFormatter(detailed_formatter)
            
            # Add filter to only log discord-related messages
            discord_handler.addFilter(lambda record: 'discord' in record.name.lower() or 'cogs' in record.name.lower())
            root_logger.addHandler(discord_handler)
            
            # Database operations log
            db_log_file = os.path.join(log_directory, 'database.log')
            db_handler = logging.handlers.RotatingFileHandler(
                db_log_file,
                maxBytes=max_file_size,
                backupCount=backup_count,
                encoding='utf-8'
            )
            db_handler.setLevel(logging.DEBUG)
            db_handler.setFormatter(detailed_formatter)
            
            # Add filter for database-related logs
            db_handler.addFilter(lambda record: 'database' in record.name.lower() or 'utils.database' in record.name)
            root_logger.addHandler(db_handler)
        
        # Configure discord.py logging (reduce verbosity)
        discord_logger = logging.getLogger('discord')
        discord_logger.setLevel(logging.WARNING)
        
        # Configure asyncio logging
        asyncio_logger = logging.getLogger('asyncio')
        asyncio_logger.setLevel(logging.WARNING)
        
        logging.info(f"Logging configured - Level: {log_level}, File: {log_to_file}, Console: {log_to_console}")

class PerformanceLogger:
    """Logger for performance monitoring and metrics"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(f"performance.{name}")
        self.start_times = {}
    
    def start_timer(self, operation: str):
        """Start timing an operation"""
        self.start_times[operation] = datetime.now()
        self.logger.debug(f"Started timing: {operation}")
    
    def end_timer(self, operation: str, additional_info: str = ""):
        """End timing an operation and log the duration"""
        if operation in self.start_times:
            duration = datetime.now() - self.start_times[operation]
            duration_ms = duration.total_seconds() * 1000
            
            log_message = f"Operation '{operation}' completed in {duration_ms:.2f}ms"
            if additional_info:
                log_message += f" | {additional_info}"
            
            # Log as warning if operation took too long
            if duration_ms > 1000:  # More than 1 second
                self.logger.warning(f"SLOW: {log_message}")
            else:
                self.logger.info(log_message)
            
            del self.start_times[operation]
        else:
            self.logger.error(f"Timer for '{operation}' was not started")

class UserActionLogger:
    """Logger for tracking user actions and interactions"""
    
    def __init__(self):
        self.logger = logging.getLogger("user_actions")
    
    def log_command_usage(self, user_id: str, command_name: str, guild_id: Optional[str] = None):
        """Log when a user uses a command"""
        guild_info = f" in guild {guild_id}" if guild_id else " in DM"
        self.logger.info(f"User {user_id} used command /{command_name}{guild_info}")
    
    def log_task_action(self, user_id: str, action: str, task_id: Optional[int] = None, details: str = ""):
        """Log task-related actions"""
        task_info = f" (Task ID: {task_id})" if task_id else ""
        detail_info = f" | {details}" if details else ""
        self.logger.info(f"User {user_id} {action}{task_info}{detail_info}")
    
    def log_error_interaction(self, user_id: str, error_type: str, command: str, error_message: str):
        """Log when a user encounters an error"""
        self.logger.error(f"User {user_id} encountered {error_type} in /{command}: {error_message}")
    
    def log_preference_change(self, user_id: str, preference: str, old_value: str, new_value: str):
        """Log preference changes"""
        self.logger.info(f"User {user_id} changed {preference}: {old_value} -> {new_value}")

class DatabaseLogger:
    """Logger for database operations and performance"""
    
    def __init__(self):
        self.logger = logging.getLogger("database")
        self.perf_logger = PerformanceLogger("database")
    
    def log_query(self, query_type: str, table: str, user_id: Optional[str] = None):
        """Log database queries"""
        user_info = f" for user {user_id}" if user_id else ""
        self.logger.debug(f"{query_type} on {table}{user_info}")
    
    def log_slow_query(self, query: str, duration_ms: float, params: Optional[tuple] = None):
        """Log slow database queries"""
        param_info = f" with params {params}" if params else ""
        self.logger.warning(f"SLOW QUERY ({duration_ms:.2f}ms): {query[:100]}...{param_info}")
    
    def log_connection_error(self, error: Exception):
        """Log database connection errors"""
        self.logger.error(f"Database connection error: {error}")
    
    def log_transaction(self, operation: str, affected_rows: int = 0):
        """Log database transactions"""
        self.logger.info(f"Transaction {operation} - Affected rows: {affected_rows}")

# Convenience functions for easy logging setup
def setup_bot_logging(debug: bool = False):
    """Quick setup for bot logging"""
    level = "DEBUG" if debug else "INFO"
    BotLogger.setup_logging(log_level=level)

def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name"""
    return logging.getLogger(name)

def get_performance_logger(name: str) -> PerformanceLogger:
    """Get a performance logger for timing operations"""
    return PerformanceLogger(name)

def get_user_action_logger() -> UserActionLogger:
    """Get the user action logger"""
    return UserActionLogger()

def get_database_logger() -> DatabaseLogger:
    """Get the database logger"""
    return DatabaseLogger()

# Context manager for timing operations
class TimedOperation:
    """Context manager for timing operations"""
    
    def __init__(self, logger: PerformanceLogger, operation_name: str, additional_info: str = ""):
        self.logger = logger
        self.operation_name = operation_name
        self.additional_info = additional_info
    
    def __enter__(self):
        self.logger.start_timer(self.operation_name)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.additional_info += f" | ERROR: {exc_type.__name__}"
        self.logger.end_timer(self.operation_name, self.additional_info)