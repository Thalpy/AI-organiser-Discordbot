# Persistent Reminder System for Discord Task Management Bot
# Handles continuous reminders until task activation

from discord.ext import commands, tasks
from discord import app_commands
import discord
import datetime
from typing import Dict, Set, Optional
import asyncio
from utils.database import TaskQueries, DatabaseManager
from utils.discord_helpers import EmbedBuilder, ErrorHandler
from utils.logging_config import get_logger, get_user_action_logger
import logging

logger = get_logger(__name__)
user_logger = get_user_action_logger()

class PersistentReminderManager(commands.Cog):
    """Manages persistent reminders that continue until task activation"""
    
    def __init__(self, bot):
        self.bot = bot
        # Track active reminders: {task_id: reminder_info}
        self.active_reminders: Dict[int, Dict] = {}
        # Track users who have been reminded: {user_id: {task_id, last_reminded}}
        self.user_reminder_state: Dict[str, Dict] = {}
        
        # Start background tasks
        self.check_new_reminders.start()
        self.send_persistent_reminders.start()
        
        logger.info("PersistentReminderManager initialized")

    def cog_unload(self):
        self.check_new_reminders.cancel()
        self.send_persistent_reminders.cancel()
        logger.info("PersistentReminderManager unloaded")

    @tasks.loop(minutes=1)
    async def check_new_reminders(self):
        """Check for tasks that need to start sending reminders"""
        try:
            now = datetime.datetime.now()
            
            # Get all users and their reminder preferences
            query = """
                SELECT DISTINCT t.id, t.user_id, t.description, t.due_time, t.duration_minutes, t.location,
                       COALESCE(np.reminder_minutes, 15) as reminder_minutes,
                       COALESCE(np.task_reminders, true) as reminders_enabled
                FROM tasks t
                LEFT JOIN notification_preferences np ON t.user_id = np.user_id
                WHERE t.status = 'pending' 
                AND t.due_time IS NOT NULL
                AND t.due_time > %s
            """
            
            tasks = await DatabaseManager.execute_query(query, (now,), fetch_all=True)
            
            for task in tasks:
                task_id = task['id']
                user_id = task['user_id']
                reminder_minutes = task['reminder_minutes']
                
                # Skip if reminders disabled
                if not task['reminders_enabled']:
                    continue
                
                # Skip if already in active reminders
                if task_id in self.active_reminders:
                    continue
                
                # Check if it's time to start reminding
                reminder_time = task['due_time'] - datetime.timedelta(minutes=reminder_minutes)
                
                if now >= reminder_time:
                    # Start persistent reminding
                    await self.start_persistent_reminder(task)
                    
        except Exception as e:
            logger.error(f"Error checking new reminders: {e}")

    @tasks.loop(minutes=2)  # Send reminders every 2 minutes
    async def send_persistent_reminders(self):
        """Send reminders for all active reminder tasks"""
        try:
            current_time = datetime.datetime.now()
            
            for task_id, reminder_info in list(self.active_reminders.items()):
                try:
                    # Check if task is still pending
                    task = await TaskQueries.get_task_by_id(task_id, reminder_info['user_id'])
                    
                    if not task or task['status'] != 'pending':
                        # Task was started, completed, or deleted - stop reminding
                        await self.stop_persistent_reminder(task_id, "Task status changed")
                        continue
                    
                    # Check if task time has passed
                    if current_time > task['due_time']:
                        # Task is overdue - send overdue reminder instead
                        await self.send_overdue_reminder(task)
                        await self.stop_persistent_reminder(task_id, "Task overdue")
                        continue
                    
                    # Send the persistent reminder
                    await self.send_reminder_message(task, reminder_info)
                    
                    # Update last reminded time
                    reminder_info['last_reminded'] = current_time
                    reminder_info['reminder_count'] += 1
                    
                    # Log the reminder
                    user_logger.log_task_action(
                        reminder_info['user_id'], 
                        "persistent_reminder_sent", 
                        task_id,
                        f"Count: {reminder_info['reminder_count']}"
                    )
                    
                except Exception as e:
                    logger.error(f"Error sending persistent reminder for task {task_id}: {e}")
                    
        except Exception as e:
            logger.error(f"Error in persistent reminder loop: {e}")

    async def start_persistent_reminder(self, task: Dict):
        """Start persistent reminding for a task"""
        task_id = task['id']
        user_id = task['user_id']
        
        logger.info(f"Starting persistent reminder for task {task_id} (user {user_id})")
        
        # Add to active reminders
        self.active_reminders[task_id] = {
            'user_id': user_id,
            'task': task,
            'started_at': datetime.datetime.now(),
            'last_reminded': None,
            'reminder_count': 0
        }
        
        # Initialize user reminder state
        if user_id not in self.user_reminder_state:
            self.user_reminder_state[user_id] = {}
        
        self.user_reminder_state[user_id][task_id] = {
            'active': True,
            'started_at': datetime.datetime.now()
        }
        
        # Send initial reminder immediately
        await self.send_reminder_message(task, self.active_reminders[task_id])
        
        user_logger.log_task_action(user_id, "persistent_reminder_started", task_id)

    async def stop_persistent_reminder(self, task_id: int, reason: str = "Manual stop"):
        """Stop persistent reminding for a task"""
        if task_id in self.active_reminders:
            reminder_info = self.active_reminders[task_id]
            user_id = reminder_info['user_id']
            
            logger.info(f"Stopping persistent reminder for task {task_id}: {reason}")
            
            # Remove from active reminders
            del self.active_reminders[task_id]
            
            # Update user reminder state
            if user_id in self.user_reminder_state and task_id in self.user_reminder_state[user_id]:
                self.user_reminder_state[user_id][task_id]['active'] = False
                self.user_reminder_state[user_id][task_id]['stopped_at'] = datetime.datetime.now()
                self.user_reminder_state[user_id][task_id]['stop_reason'] = reason
            
            user_logger.log_task_action(user_id, "persistent_reminder_stopped", task_id, reason)

    async def send_reminder_message(self, task: Dict, reminder_info: Dict):
        """Send a persistent reminder message to the user"""
        try:
            user = await self.bot.fetch_user(int(task['user_id']))
            if not user:
                logger.warning(f"Could not fetch user {task['user_id']} for reminder")
                return

            now = datetime.datetime.now()
            time_until = task['due_time'] - now
            minutes_until = int(time_until.total_seconds() / 60)
            
            # Create reminder embed with urgency indicators
            if minutes_until <= 5:
                color = discord.Color.red()
                urgency = "🚨 URGENT"
            elif minutes_until <= 10:
                color = discord.Color.orange()
                urgency = "⚠️ SOON"
            else:
                color = discord.Color.yellow()
                urgency = "⏰ REMINDER"
            
            embed = EmbedBuilder.create_embed(
                title=f"{urgency} - Task Starting Soon!",
                description=f"**{task['description']}** starts in {minutes_until} minutes",
                color=color,
                fields=[
                    ("📅 Scheduled Time", task['due_time'].strftime('%H:%M'), True),
                    ("⏱️ Duration", f"{task.get('duration_minutes', 15)} minutes", True),
                    ("🔔 Reminder #", str(reminder_info['reminder_count'] + 1), True)
                ]
            )
            
            if task.get('location'):
                embed.add_field(name="📍 Location", value=task['location'], inline=False)
            
            # Add action buttons
            view = ReminderActionView(task['id'], task['user_id'])
            
            embed.set_footer(text="Use the buttons below or type /start to begin the task")
            
            await user.send(embed=embed, view=view)
            
            logger.debug(f"Sent persistent reminder #{reminder_info['reminder_count'] + 1} to user {task['user_id']}")
            
        except discord.Forbidden:
            logger.warning(f"Cannot send DM to user {task['user_id']} - DMs disabled")
            await self.stop_persistent_reminder(task['id'], "DMs disabled")
        except Exception as e:
            logger.error(f"Error sending reminder message: {e}")

    async def send_overdue_reminder(self, task: Dict):
        """Send an overdue task reminder"""
        try:
            user = await self.bot.fetch_user(int(task['user_id']))
            if not user:
                return

            now = datetime.datetime.now()
            overdue_duration = now - task['due_time']
            overdue_minutes = int(overdue_duration.total_seconds() / 60)
            
            embed = EmbedBuilder.create_embed(
                title="🚨 OVERDUE TASK",
                description=f"**{task['description']}** was scheduled {overdue_minutes} minutes ago!",
                color=discord.Color.red(),
                fields=[
                    ("📅 Was Scheduled", task['due_time'].strftime('%H:%M'), True),
                    ("⏰ Overdue By", f"{overdue_minutes} minutes", True),
                    ("⏱️ Duration", f"{task.get('duration_minutes', 15)} minutes", True)
                ]
            )
            
            view = ReminderActionView(task['id'], task['user_id'], is_overdue=True)
            embed.set_footer(text="Start now or reschedule this task")
            
            await user.send(embed=embed, view=view)
            
        except Exception as e:
            logger.error(f"Error sending overdue reminder: {e}")

    @check_new_reminders.before_loop
    @send_persistent_reminders.before_loop
    async def before_reminder_loops(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="reminder_status", description="Check your active reminders")
    async def reminder_status(self, interaction: discord.Interaction):
        """Show user their active reminders"""
        user_id = str(interaction.user.id)
        
        # Get user's active reminders
        user_reminders = [
            (task_id, info) for task_id, info in self.active_reminders.items()
            if info['user_id'] == user_id
        ]
        
        if not user_reminders:
            embed = EmbedBuilder.info_embed(
                "No Active Reminders",
                "You don't have any active task reminders right now."
            )
        else:
            embed = EmbedBuilder.create_embed(
                title="🔔 Your Active Reminders",
                description=f"You have {len(user_reminders)} active reminder(s)",
                color=EmbedBuilder.WARNING
            )
            
            for task_id, reminder_info in user_reminders:
                task = reminder_info['task']
                time_until = task['due_time'] - datetime.datetime.now()
                minutes_until = int(time_until.total_seconds() / 60)
                
                embed.add_field(
                    name=f"📋 {task['description']}",
                    value=f"Starts in {minutes_until} minutes\nReminders sent: {reminder_info['reminder_count']}",
                    inline=False
                )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class ReminderActionView(discord.ui.View):
    """Action buttons for reminder messages"""
    
    def __init__(self, task_id: int, user_id: str, is_overdue: bool = False):
        super().__init__(timeout=300)  # 5 minute timeout
        self.task_id = task_id
        self.user_id = user_id
        self.is_overdue = is_overdue

    @discord.ui.button(label="▶️ Start Now", style=discord.ButtonStyle.success)
    async def start_task(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Start the task immediately"""
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ This is not your reminder.", ephemeral=True)
            return
        
        try:
            # Start the task
            now = datetime.datetime.now()
            success = await TaskQueries.update_task(
                self.task_id, self.user_id,
                start_time=now,
                status='in_progress',
                num_sessions=1
            )
            
            if success:
                # Stop the persistent reminder
                cog = interaction.client.get_cog("PersistentReminderManager")
                if cog:
                    await cog.stop_persistent_reminder(self.task_id, "Started via reminder button")
                
                embed = EmbedBuilder.success_embed(
                    "Task Started!",
                    f"You're now working on this task. Use `/finish` when complete."
                )
                
                # Disable all buttons
                for item in self.children:
                    item.disabled = True
                
                await interaction.response.edit_message(embed=embed, view=self)
                
                user_logger.log_task_action(self.user_id, "started_via_reminder", self.task_id)
            else:
                await interaction.response.send_message("❌ Failed to start task. Please try `/start` command.", ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error starting task via reminder: {e}")
            await ErrorHandler.handle_error(interaction, e, "Failed to start task from reminder.")

    @discord.ui.button(label="⏸️ Snooze 5min", style=discord.ButtonStyle.secondary)
    async def snooze_reminder(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Snooze the reminder for 5 minutes"""
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ This is not your reminder.", ephemeral=True)
            return
        
        try:
            # Update task due time
            new_due_time = datetime.datetime.now() + datetime.timedelta(minutes=5)
            success = await TaskQueries.update_task(
                self.task_id, self.user_id,
                due_time=new_due_time
            )
            
            if success:
                embed = EmbedBuilder.warning_embed(
                    "Reminder Snoozed",
                    f"Task rescheduled to {new_due_time.strftime('%H:%M')}. Reminders will resume closer to the new time."
                )
                
                # Disable buttons
                for item in self.children:
                    item.disabled = True
                
                await interaction.response.edit_message(embed=embed, view=self)
                
                user_logger.log_task_action(self.user_id, "snoozed_reminder", self.task_id, "5 minutes")
            else:
                await interaction.response.send_message("❌ Failed to snooze reminder.", ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error snoozing reminder: {e}")
            await ErrorHandler.handle_error(interaction, e, "Failed to snooze reminder.")

    @discord.ui.button(label="🔕 Stop Reminders", style=discord.ButtonStyle.danger)
    async def stop_reminders(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Stop all reminders for this task"""
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ This is not your reminder.", ephemeral=True)
            return
        
        try:
            # Stop the persistent reminder
            cog = interaction.client.get_cog("PersistentReminderManager")
            if cog:
                await cog.stop_persistent_reminder(self.task_id, "Stopped by user request")
            
            embed = EmbedBuilder.warning_embed(
                "Reminders Stopped",
                "No more reminders will be sent for this task. You can still start it manually with `/start`."
            )
            
            # Disable all buttons
            for item in self.children:
                item.disabled = True
            
            await interaction.response.edit_message(embed=embed, view=self)
            
            user_logger.log_task_action(self.user_id, "stopped_reminders", self.task_id)
            
        except Exception as e:
            logger.error(f"Error stopping reminders: {e}")
            await ErrorHandler.handle_error(interaction, e, "Failed to stop reminders.")

async def setup(bot):
    await bot.add_cog(PersistentReminderManager(bot))
    logger.info("PersistentReminderManager cog loaded")