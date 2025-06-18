# Daily Schedule Generator for Discord Task Management Bot
# This cog implements intelligent task scheduling based on user preferences

from discord.ext import commands, tasks
from discord import app_commands
import discord
import datetime
import pytz
from typing import List, Dict, Optional, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor
from config import DB_CONFIG

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

class TaskScheduler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Start the daily schedule generation task
        self.daily_schedule_generator.start()

    def cog_unload(self):
        self.daily_schedule_generator.cancel()

    @tasks.loop(hours=24)
    async def daily_schedule_generator(self):
        """Background task that runs daily to generate schedules for all users"""
        await self.generate_all_user_schedules()

    @daily_schedule_generator.before_loop
    async def before_daily_schedule_generator(self):
        await self.bot.wait_until_ready()

    async def generate_all_user_schedules(self):
        """Generate schedules for all users who have tasks"""
        with get_connection() as conn:
            with conn.cursor() as cur:
                # Get all users with pending tasks
                cur.execute("""
                    SELECT DISTINCT user_id FROM tasks 
                    WHERE status = 'pending' AND due_time IS NULL
                """)
                users = cur.fetchall()
                
        for (user_id,) in users:
            try:
                await self.generate_user_schedule(user_id)
            except Exception as e:
                print(f"Error generating schedule for user {user_id}: {e}")

    async def generate_user_schedule(self, user_id: str, target_date: Optional[datetime.date] = None) -> List[Dict]:
        """
        Generate a daily schedule for a specific user
        
        Args:
            user_id: Discord user ID
            target_date: Date to schedule for (defaults to tomorrow)
            
        Returns:
            List of scheduled tasks with assigned time slots
        """
        if target_date is None:
            target_date = datetime.date.today() + datetime.timedelta(days=1)
            
        # Get user preferences
        user_prefs = await self.get_user_preferences(user_id)
        
        # Get unscheduled tasks for the user
        unscheduled_tasks = await self.get_unscheduled_tasks(user_id)
        
        # Get existing scheduled tasks for the target date
        existing_schedule = await self.get_existing_schedule(user_id, target_date)
        
        # Generate available time slots
        available_slots = self.generate_time_slots(user_prefs, target_date, existing_schedule)
        
        # Schedule tasks using intelligent algorithm
        scheduled_tasks = self.schedule_tasks_algorithm(unscheduled_tasks, available_slots, user_prefs)
        
        # Save scheduled tasks to database
        await self.save_scheduled_tasks(scheduled_tasks, target_date)
        
        return scheduled_tasks

    async def get_user_preferences(self, user_id: str) -> Dict:
        """Get user preferences with defaults"""
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM user_preferences WHERE user_id = %s
                """, (user_id,))
                prefs = cur.fetchone()
                
        if not prefs:
            # Return default preferences
            return {
                'work_start': datetime.time(9, 0),
                'work_end': datetime.time(17, 0),
                'lunch_duration_minutes': 30,
                'lunch_window_start': datetime.time(12, 0),
                'lunch_window_end': datetime.time(14, 0),
                'time_zone': 'UTC'
            }
        return dict(prefs)

    async def get_unscheduled_tasks(self, user_id: str) -> List[Dict]:
        """Get tasks that haven't been scheduled yet"""
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT id, description, duration_minutes, priority, deadline
                    FROM tasks 
                    WHERE user_id = %s 
                    AND status = 'pending' 
                    AND due_time IS NULL
                    ORDER BY 
                        priority DESC,
                        deadline ASC NULLS LAST,
                        id ASC
                """, (user_id,))
                return cur.fetchall()

    async def get_existing_schedule(self, user_id: str, target_date: datetime.date) -> List[Dict]:
        """Get already scheduled tasks for the target date"""
        start_of_day = datetime.datetime.combine(target_date, datetime.time.min)
        end_of_day = datetime.datetime.combine(target_date, datetime.time.max)
        
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT id, description, due_time, duration_minutes
                    FROM tasks 
                    WHERE user_id = %s 
                    AND due_time BETWEEN %s AND %s
                    ORDER BY due_time ASC
                """, (user_id, start_of_day, end_of_day))
                return cur.fetchall()

    def generate_time_slots(self, user_prefs: Dict, target_date: datetime.date, existing_schedule: List[Dict]) -> List[Tuple[datetime.datetime, datetime.datetime]]:
        """
        Generate available time slots based on user preferences and existing schedule
        
        Returns:
            List of (start_time, end_time) tuples representing available slots
        """
        # Convert user timezone
        tz = pytz.timezone(user_prefs.get('time_zone', 'UTC'))
        
        # Create work day boundaries
        work_start = datetime.datetime.combine(target_date, user_prefs['work_start'])
        work_end = datetime.datetime.combine(target_date, user_prefs['work_end'])
        work_start = tz.localize(work_start)
        work_end = tz.localize(work_end)
        
        # Create lunch window
        lunch_start = datetime.datetime.combine(target_date, user_prefs['lunch_window_start'])
        lunch_end = datetime.datetime.combine(target_date, user_prefs['lunch_window_end'])
        lunch_start = tz.localize(lunch_start)
        lunch_end = tz.localize(lunch_end)
        
        # Start with the full work day as one slot
        available_slots = [(work_start, work_end)]
        
        # Remove lunch time
        available_slots = self.subtract_time_block(available_slots, lunch_start, lunch_end)
        
        # Remove existing scheduled tasks
        for task in existing_schedule:
            if task['due_time'] and task['duration_minutes']:
                task_start = task['due_time']
                task_end = task_start + datetime.timedelta(minutes=task['duration_minutes'])
                available_slots = self.subtract_time_block(available_slots, task_start, task_end)
        
        return available_slots

    def subtract_time_block(self, slots: List[Tuple[datetime.datetime, datetime.datetime]], 
                           block_start: datetime.datetime, block_end: datetime.datetime) -> List[Tuple[datetime.datetime, datetime.datetime]]:
        """Remove a time block from available slots"""
        new_slots = []
        
        for slot_start, slot_end in slots:
            # No overlap
            if block_end <= slot_start or block_start >= slot_end:
                new_slots.append((slot_start, slot_end))
            # Partial overlap - split the slot
            else:
                # Add time before the block
                if slot_start < block_start:
                    new_slots.append((slot_start, block_start))
                # Add time after the block
                if slot_end > block_end:
                    new_slots.append((block_end, slot_end))
        
        return new_slots

    def schedule_tasks_algorithm(self, tasks: List[Dict], available_slots: List[Tuple[datetime.datetime, datetime.datetime]], 
                               user_prefs: Dict) -> List[Dict]:
        """
        Intelligent algorithm to schedule tasks in available time slots
        
        Algorithm priorities:
        1. High priority tasks first
        2. Tasks with deadlines first
        3. Fit tasks into appropriate time slots
        4. Leave buffer time between tasks
        """
        scheduled_tasks = []
        buffer_minutes = 5  # Buffer time between tasks
        
        # Sort slots by start time
        available_slots = sorted(available_slots, key=lambda x: x[0])
        
        for task in tasks:
            duration = task.get('duration_minutes', 15)
            task_duration = datetime.timedelta(minutes=duration + buffer_minutes)
            
            # Find the first available slot that can fit this task
            for i, (slot_start, slot_end) in enumerate(available_slots):
                slot_duration = slot_end - slot_start
                
                if slot_duration >= task_duration:
                    # Schedule the task at the beginning of this slot
                    task_start = slot_start
                    task_end = slot_start + datetime.timedelta(minutes=duration)
                    
                    scheduled_task = {
                        'id': task['id'],
                        'description': task['description'],
                        'scheduled_time': task_start,
                        'duration_minutes': duration,
                        'priority': task.get('priority', False),
                        'deadline': task.get('deadline')
                    }
                    scheduled_tasks.append(scheduled_task)
                    
                    # Update the available slot
                    new_slot_start = slot_start + task_duration
                    if new_slot_start < slot_end:
                        available_slots[i] = (new_slot_start, slot_end)
                    else:
                        available_slots.pop(i)
                    
                    break
            else:
                # Task couldn't be scheduled - add to overflow
                print(f"Warning: Could not schedule task {task['id']} - {task['description']}")
        
        return scheduled_tasks

    async def save_scheduled_tasks(self, scheduled_tasks: List[Dict], target_date: datetime.date):
        """Save the scheduled tasks to the database"""
        with get_connection() as conn:
            with conn.cursor() as cur:
                for task in scheduled_tasks:
                    cur.execute("""
                        UPDATE tasks 
                        SET due_time = %s, schedule_date = %s, schedule_time = %s
                        WHERE id = %s
                    """, (
                        task['scheduled_time'],
                        target_date,
                        task['scheduled_time'].time(),
                        task['id']
                    ))
                conn.commit()

    @app_commands.command(name="generate_schedule", description="Generate your daily schedule for tomorrow")
    async def generate_schedule_command(self, interaction: discord.Interaction):
        """Manual command to generate a schedule"""
        user_id = str(interaction.user.id)
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            scheduled_tasks = await self.generate_user_schedule(user_id)
            
            if not scheduled_tasks:
                await interaction.followup.send("📭 No unscheduled tasks found to schedule.", ephemeral=True)
                return
            
            # Create schedule display
            embed = discord.Embed(
                title="📅 Generated Schedule for Tomorrow",
                description=f"Scheduled {len(scheduled_tasks)} tasks",
                color=discord.Color.green()
            )
            
            for task in scheduled_tasks:
                time_str = task['scheduled_time'].strftime('%H:%M')
                priority_icon = "🔥" if task['priority'] else "📋"
                embed.add_field(
                    name=f"{priority_icon} {time_str}",
                    value=f"{task['description']} ({task['duration_minutes']}min)",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error generating schedule: {str(e)}", ephemeral=True)

    @app_commands.command(name="view_schedule", description="View your schedule for today or a specific date")
    async def view_schedule_command(self, interaction: discord.Interaction, date: str = None):
        """View existing schedule"""
        user_id = str(interaction.user.id)
        
        if date:
            try:
                target_date = datetime.datetime.strptime(date, '%Y-%m-%d').date()
            except ValueError:
                await interaction.response.send_message("❌ Invalid date format. Use YYYY-MM-DD", ephemeral=True)
                return
        else:
            target_date = datetime.date.today()
        
        existing_schedule = await self.get_existing_schedule(user_id, target_date)
        
        if not existing_schedule:
            await interaction.response.send_message(f"📭 No scheduled tasks found for {target_date}", ephemeral=True)
            return
        
        embed = discord.Embed(
            title=f"📅 Schedule for {target_date}",
            color=discord.Color.blue()
        )
        
        for task in existing_schedule:
            time_str = task['due_time'].strftime('%H:%M')
            embed.add_field(
                name=f"⏰ {time_str}",
                value=f"{task['description']} ({task['duration_minutes']}min)",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(TaskScheduler(bot))