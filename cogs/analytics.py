# Analytics Dashboard for Discord Task Management Bot
# Main analytics commands and data visualization

from discord.ext import commands
from discord import app_commands
import discord
import datetime
from typing import Dict, List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from config import DB_CONFIG
from .analytics_calculator import AnalyticsCalculator
from .analytics_visualizer import AnalyticsVisualizer

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

class Analytics(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.calculator = AnalyticsCalculator()
        self.visualizer = AnalyticsVisualizer()

    @app_commands.command(name="analytics", description="View your productivity analytics dashboard")
    async def analytics_dashboard(self, interaction: discord.Interaction, 
                                 timeframe: str = "week"):
        """Main analytics dashboard command"""
        user_id = str(interaction.user.id)
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Calculate analytics for the specified timeframe
            analytics_data = await self.calculator.calculate_user_analytics(user_id, timeframe)
            
            if not analytics_data:
                await interaction.followup.send(
                    "📊 No analytics data available yet. Complete some tasks to see your productivity insights!",
                    ephemeral=True
                )
                return
            
            # Create dashboard embed
            embed = await self.create_analytics_embed(analytics_data, timeframe)
            
            # Create analytics view with buttons
            view = AnalyticsView(user_id, timeframe, analytics_data)
            
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error generating analytics: {str(e)}", ephemeral=True)

    async def create_analytics_embed(self, data: Dict, timeframe: str) -> discord.Embed:
        """Create the main analytics dashboard embed"""
        embed = discord.Embed(
            title=f"📊 Productivity Analytics - {timeframe.title()}",
            description="Your task completion and productivity insights",
            color=discord.Color.blue(),
            timestamp=datetime.datetime.now()
        )
        
        # Overview metrics
        embed.add_field(
            name="📈 Overview",
            value=f"**Tasks Completed:** {data['tasks_completed']}\n"
                  f"**Total Tasks:** {data['total_tasks']}\n"
                  f"**Completion Rate:** {data['completion_rate']:.1f}%\n"
                  f"**Average Duration:** {data['avg_duration']:.1f} min",
            inline=True
        )
        
        # Time management
        embed.add_field(
            name="⏱️ Time Management",
            value=f"**On-Time Starts:** {data['on_time_starts']:.1f}%\n"
                  f"**On-Time Finishes:** {data['on_time_finishes']:.1f}%\n"
                  f"**Avg Delay:** {data['avg_delay']:.1f} min\n"
                  f"**Total Time:** {data['total_time']:.1f} hours",
            inline=True
        )
        
        # Productivity trends
        embed.add_field(
            name="📅 Trends",
            value=f"**Most Productive Day:** {data['best_day']}\n"
                  f"**Peak Hour:** {data['peak_hour']}:00\n"
                  f"**Streak:** {data['current_streak']} days\n"
                  f"**Priority Tasks:** {data['priority_completion']:.1f}%",
            inline=True
        )
        
        # Performance indicators
        performance_emoji = "🔥" if data['completion_rate'] >= 80 else "📈" if data['completion_rate'] >= 60 else "⚠️"
        embed.add_field(
            name=f"{performance_emoji} Performance Score",
            value=f"**{data['performance_score']}/100**\n"
                  f"Based on completion rate, timing, and consistency",
            inline=False
        )
        
        embed.set_footer(text="Use buttons below to explore detailed analytics")
        return embed

class AnalyticsView(discord.ui.View):
    def __init__(self, user_id: str, timeframe: str, analytics_data: Dict):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.timeframe = timeframe
        self.analytics_data = analytics_data
        
        # Add timeframe selector
        self.add_item(TimeframeSelect(timeframe))

    @discord.ui.button(label="📈 Detailed Report", style=discord.ButtonStyle.primary)
    async def detailed_report(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show detailed analytics report"""
        calculator = AnalyticsCalculator()
        detailed_data = await calculator.get_detailed_analytics(self.user_id, self.timeframe)
        
        embed = discord.Embed(
            title="📈 Detailed Analytics Report",
            color=discord.Color.green()
        )
        
        # Task breakdown
        embed.add_field(
            name="📋 Task Breakdown",
            value=f"**Completed:** {detailed_data['completed_tasks']}\n"
                  f"**In Progress:** {detailed_data['in_progress_tasks']}\n"
                  f"**Pending:** {detailed_data['pending_tasks']}\n"
                  f"**Overdue:** {detailed_data['overdue_tasks']}",
            inline=True
        )
        
        # Time analysis
        embed.add_field(
            name="⏰ Time Analysis",
            value=f"**Estimated vs Actual:** {detailed_data['estimation_accuracy']:.1f}%\n"
                  f"**Average Session:** {detailed_data['avg_session_length']:.1f} min\n"
                  f"**Total Sessions:** {detailed_data['total_sessions']}\n"
                  f"**Interruptions:** {detailed_data['interruptions']}",
            inline=True
        )
        
        # Productivity patterns
        embed.add_field(
            name="🎯 Patterns",
            value=f"**Best Day Type:** {detailed_data['best_day_type']}\n"
                  f"**Worst Day Type:** {detailed_data['worst_day_type']}\n"
                  f"**Peak Productivity:** {detailed_data['peak_productivity_time']}\n"
                  f"**Low Energy:** {detailed_data['low_energy_time']}",
            inline=True
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="📊 Charts", style=discord.ButtonStyle.secondary)
    async def show_charts(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Generate and show analytics charts"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            visualizer = AnalyticsVisualizer()
            chart_file = await visualizer.create_analytics_chart(self.user_id, self.timeframe)
            
            embed = discord.Embed(
                title="📊 Analytics Charts",
                description="Visual representation of your productivity data",
                color=discord.Color.purple()
            )
            
            file = discord.File(chart_file, filename="analytics_chart.png")
            embed.set_image(url="attachment://analytics_chart.png")
            
            await interaction.followup.send(embed=embed, file=file, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error generating charts: {str(e)}", ephemeral=True)

    @discord.ui.button(label="🎯 Goals", style=discord.ButtonStyle.success)
    async def productivity_goals(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show productivity goals and recommendations"""
        calculator = AnalyticsCalculator()
        recommendations = await calculator.get_productivity_recommendations(self.user_id, self.analytics_data)
        
        embed = discord.Embed(
            title="🎯 Productivity Goals & Recommendations",
            description="Personalized suggestions to improve your productivity",
            color=discord.Color.gold()
        )
        
        for i, rec in enumerate(recommendations[:5], 1):
            embed.add_field(
                name=f"{rec['emoji']} Goal {i}: {rec['title']}",
                value=f"{rec['description']}\n**Target:** {rec['target']}",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class TimeframeSelect(discord.ui.Select):
    def __init__(self, current_timeframe: str):
        options = [
            discord.SelectOption(
                label="This Week", 
                value="week", 
                description="Last 7 days",
                default=current_timeframe=="week"
            ),
            discord.SelectOption(
                label="This Month", 
                value="month", 
                description="Last 30 days",
                default=current_timeframe=="month"
            ),
            discord.SelectOption(
                label="This Quarter", 
                value="quarter", 
                description="Last 90 days",
                default=current_timeframe=="quarter"
            ),
            discord.SelectOption(
                label="All Time", 
                value="all", 
                description="Complete history",
                default=current_timeframe=="all"
            )
        ]
        
        super().__init__(
            placeholder="Select timeframe...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        new_timeframe = self.values[0]
        
        # Recalculate analytics for new timeframe
        calculator = AnalyticsCalculator()
        analytics_data = await calculator.calculate_user_analytics(self.view.user_id, new_timeframe)
        
        # Update the view
        self.view.timeframe = new_timeframe
        self.view.analytics_data = analytics_data
        
        # Create new embed
        analytics_cog = interaction.client.get_cog("Analytics")
        embed = await analytics_cog.create_analytics_embed(analytics_data, new_timeframe)
        
        await interaction.response.edit_message(embed=embed, view=self.view)

async def setup(bot):
    await bot.add_cog(Analytics(bot))