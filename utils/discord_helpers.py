# Discord Utilities for Discord Task Management Bot
# Standardized embed builders and UI helpers

import discord
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime

class EmbedBuilder:
    """Standardized embed creation with consistent styling"""
    
    # Standard colors
    SUCCESS = discord.Color.green()
    ERROR = discord.Color.red()
    WARNING = discord.Color.orange()
    INFO = discord.Color.blue()
    PRIMARY = discord.Color.purple()
    SECONDARY = discord.Color.teal()
    
    @staticmethod
    def create_embed(
        title: str,
        description: str = None,
        color: discord.Color = INFO,
        fields: List[Tuple[str, str, bool]] = None,
        footer: str = None,
        thumbnail: str = None,
        timestamp: bool = True
    ) -> discord.Embed:
        """
        Create a standardized embed
        
        Args:
            title: Embed title
            description: Embed description
            color: Embed color
            fields: List of (name, value, inline) tuples
            footer: Footer text
            thumbnail: Thumbnail URL
            timestamp: Whether to add timestamp
            
        Returns:
            Configured Discord embed
        """
        embed = discord.Embed(
            title=title,
            description=description,
            color=color
        )
        
        if fields:
            for name, value, inline in fields:
                embed.add_field(name=name, value=value, inline=inline)
        
        if footer:
            embed.set_footer(text=footer)
        
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
            
        if timestamp:
            embed.timestamp = datetime.now()
        
        return embed

    @staticmethod
    def success_embed(title: str, description: str = None, **kwargs) -> discord.Embed:
        """Create a success embed with green color"""
        return EmbedBuilder.create_embed(
            title=f"✅ {title}",
            description=description,
            color=EmbedBuilder.SUCCESS,
            **kwargs
        )

    @staticmethod
    def error_embed(title: str, description: str = None, **kwargs) -> discord.Embed:
        """Create an error embed with red color"""
        return EmbedBuilder.create_embed(
            title=f"❌ {title}",
            description=description,
            color=EmbedBuilder.ERROR,
            **kwargs
        )

    @staticmethod
    def warning_embed(title: str, description: str = None, **kwargs) -> discord.Embed:
        """Create a warning embed with orange color"""
        return EmbedBuilder.create_embed(
            title=f"⚠️ {title}",
            description=description,
            color=EmbedBuilder.WARNING,
            **kwargs
        )

    @staticmethod
    def info_embed(title: str, description: str = None, **kwargs) -> discord.Embed:
        """Create an info embed with blue color"""
        return EmbedBuilder.create_embed(
            title=f"ℹ️ {title}",
            description=description,
            color=EmbedBuilder.INFO,
            **kwargs
        )

    @staticmethod
    def task_embed(task: Dict, title_prefix: str = "") -> discord.Embed:
        """Create a standardized task embed"""
        title = f"{title_prefix}{task.get('description', 'Untitled Task')}"
        
        fields = []
        
        if task.get('due_time'):
            fields.append(("📅 Due Time", task['due_time'].strftime('%Y-%m-%d %H:%M'), True))
        
        if task.get('duration_minutes'):
            fields.append(("⏱️ Duration", f"{task['duration_minutes']} minutes", True))
        
        if task.get('location'):
            fields.append(("📍 Location", task['location'], True))
        
        if task.get('priority'):
            fields.append(("🔥 Priority", "High" if task['priority'] else "Normal", True))
        
        if task.get('status'):
            status_emoji = {
                'pending': '🕓',
                'in_progress': '▶️',
                'done': '✅',
                'delayed': '⏸️'
            }
            fields.append(("Status", f"{status_emoji.get(task['status'], '❓')} {task['status'].title()}", True))
        
        color = EmbedBuilder.SUCCESS if task.get('status') == 'done' else EmbedBuilder.INFO
        
        return EmbedBuilder.create_embed(
            title=title,
            color=color,
            fields=fields,
            footer=f"Task ID: {task.get('id', 'Unknown')}"
        )

class MessageFormatter:
    """Utilities for formatting Discord messages"""
    
    @staticmethod
    def format_time(dt: datetime, user_timezone: str = None) -> str:
        """Format datetime for Discord display"""
        if user_timezone:
            # TODO: Add timezone conversion when timezone utils are implemented
            pass
        return dt.strftime('%H:%M')
    
    @staticmethod
    def format_date(dt: datetime, user_timezone: str = None) -> str:
        """Format date for Discord display"""
        if user_timezone:
            # TODO: Add timezone conversion when timezone utils are implemented
            pass
        return dt.strftime('%Y-%m-%d')
    
    @staticmethod
    def format_duration(minutes: int) -> str:
        """Format duration in a human-readable way"""
        if minutes < 60:
            return f"{minutes} minutes"
        elif minutes < 1440:  # Less than 24 hours
            hours = minutes // 60
            mins = minutes % 60
            if mins == 0:
                return f"{hours} hour{'s' if hours != 1 else ''}"
            return f"{hours}h {mins}m"
        else:  # Days
            days = minutes // 1440
            remaining_minutes = minutes % 1440
            hours = remaining_minutes // 60
            if hours == 0:
                return f"{days} day{'s' if days != 1 else ''}"
            return f"{days}d {hours}h"
    
    @staticmethod
    def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
        """Truncate text for Discord field limits"""
        if len(text) <= max_length:
            return text
        return text[:max_length - len(suffix)] + suffix
    
    @staticmethod
    def format_user_mention(user_id: str) -> str:
        """Format user ID as Discord mention"""
        return f"<@{user_id}>"
    
    @staticmethod
    def format_task_list(tasks: List[Dict], max_tasks: int = 10) -> str:
        """Format a list of tasks for display"""
        if not tasks:
            return "No tasks found."
        
        lines = []
        for i, task in enumerate(tasks[:max_tasks]):
            status_emoji = {
                'pending': '🕓',
                'in_progress': '▶️',
                'done': '✅',
                'delayed': '⏸️'
            }
            emoji = status_emoji.get(task.get('status', 'pending'), '❓')
            description = MessageFormatter.truncate_text(task.get('description', 'Untitled'), 50)
            
            time_str = ""
            if task.get('due_time'):
                time_str = f" - {MessageFormatter.format_time(task['due_time'])}"
            
            lines.append(f"{emoji} **{description}**{time_str}")
        
        if len(tasks) > max_tasks:
            lines.append(f"... and {len(tasks) - max_tasks} more tasks")
        
        return "\n".join(lines)

class ErrorHandler:
    """Standardized error handling for Discord interactions"""
    
    @staticmethod
    async def handle_error(interaction: discord.Interaction, error: Exception, 
                          user_message: str = "An unexpected error occurred. Please try again."):
        """Handle errors in Discord interactions"""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.error(f"Error in {interaction.command.name if interaction.command else 'interaction'}: {error}")
        
        embed = EmbedBuilder.error_embed(
            title="Error",
            description=user_message,
            footer="If this problem persists, please contact support."
        )
        
        try:
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)
        except:
            # Fallback if embed fails
            try:
                if interaction.response.is_done():
                    await interaction.followup.send(f"❌ {user_message}", ephemeral=True)
                else:
                    await interaction.response.send_message(f"❌ {user_message}", ephemeral=True)
            except:
                pass  # Give up if we can't send any message

class ValidationHelpers:
    """Input validation utilities"""
    
    @staticmethod
    def validate_time_format(time_str: str) -> bool:
        """Validate HH:MM time format"""
        try:
            parts = time_str.split(':')
            if len(parts) != 2:
                return False
            hour, minute = map(int, parts)
            return 0 <= hour <= 23 and 0 <= minute <= 59
        except:
            return False
    
    @staticmethod
    def validate_date_format(date_str: str) -> bool:
        """Validate YYYY-MM-DD date format"""
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            return True
        except:
            return False
    
    @staticmethod
    def validate_datetime_format(datetime_str: str) -> bool:
        """Validate YYYY-MM-DD HH:MM datetime format"""
        try:
            datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
            return True
        except:
            return False
    
    @staticmethod
    def validate_duration(duration_str: str, min_minutes: int = 1, max_minutes: int = 1440) -> bool:
        """Validate duration in minutes"""
        try:
            minutes = int(duration_str)
            return min_minutes <= minutes <= max_minutes
        except:
            return False