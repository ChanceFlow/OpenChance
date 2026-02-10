"""基础命令 Cog

提供 Slash Commands: /ping, /info, /serverinfo, /help
"""

from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands


class BasicCommands(commands.Cog):
    """基础命令组"""

    def __init__(self, bot: commands.Bot) -> None:
        """初始化基础命令 Cog

        Args:
            bot: Discord Bot 实例
        """
        self.bot = bot
        self.start_time: datetime = datetime.now(timezone.utc)

    @app_commands.command(name="ping", description="检查机器人延迟")
    async def ping(self, interaction: discord.Interaction) -> None:
        """检查机器人延迟"""
        latency: int = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"🏓 Pong! 延迟: {latency}ms")

    @app_commands.command(name="info", description="显示机器人信息")
    async def info(self, interaction: discord.Interaction) -> None:
        """显示机器人信息"""
        uptime = datetime.now(timezone.utc) - self.start_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)

        embed = discord.Embed(
            title="🤖 OpenChance 机器人信息",
            color=discord.Color.blue(),
            timestamp=datetime.now(timezone.utc),
        )

        embed.add_field(
            name="📊 状态",
            value=f"运行时间: {hours}h {minutes}m {seconds}s",
            inline=False,
        )

        embed.add_field(
            name="🌐 连接",
            value=f"服务器数: {len(self.bot.guilds)}",
            inline=True,
        )

        embed.add_field(
            name="⚡ 延迟",
            value=f"{round(self.bot.latency * 1000)}ms",
            inline=True,
        )

        embed.set_footer(text=f"请求者: {interaction.user.name}")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="serverinfo", description="显示当前服务器信息")
    @app_commands.guild_only()
    async def server_info(self, interaction: discord.Interaction) -> None:
        """显示当前服务器信息"""
        guild: discord.Guild | None = interaction.guild
        if not guild:
            await interaction.response.send_message(
                "❌ 此命令只能在服务器中使用", ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"📋 {guild.name} 服务器信息",
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc),
        )

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        embed.add_field(
            name="👑 所有者",
            value=guild.owner.mention if guild.owner else "未知",
            inline=True,
        )

        embed.add_field(
            name="👥 成员数",
            value=str(guild.member_count),
            inline=True,
        )

        embed.add_field(
            name="📅 创建时间",
            value=guild.created_at.strftime("%Y-%m-%d"),
            inline=True,
        )

        embed.add_field(
            name="💬 频道数",
            value=str(len(guild.channels)),
            inline=True,
        )

        embed.add_field(
            name="😀 表情数",
            value=str(len(guild.emojis)),
            inline=True,
        )

        embed.add_field(
            name="🔖 身份组数",
            value=str(len(guild.roles)),
            inline=True,
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="help", description="显示可用命令列表")
    async def help_command(self, interaction: discord.Interaction) -> None:
        """显示可用命令列表"""
        embed = discord.Embed(
            title="📖 OpenChance 帮助",
            description="所有可用的 Slash 命令",
            color=discord.Color.blue(),
        )

        embed.add_field(
            name="🔧 基础命令",
            value=(
                "`/ping` - 检查延迟\n"
                "`/info` - 机器人信息\n"
                "`/serverinfo` - 服务器信息\n"
                "`/help` - 显示此帮助"
            ),
            inline=False,
        )

        embed.add_field(
            name="🤖 AI 助理",
            value=(
                "`/ask` - 向 Claude 提问 (创建对话子区)\n"
                "`/code` - 执行编码任务 (创建编码子区)\n"
                "`/sessions` - 查看活跃 AI 会话\n"
                "`/claude-status` - 检查 Claude CLI 状态"
            ),
            inline=False,
        )

        embed.add_field(
            name="⚙️ 管理命令 (需要管理员权限)",
            value=(
                "`/admin reload` - 重载 Cog\n"
                "`/admin load` - 加载 Cog\n"
                "`/admin unload` - 卸载 Cog\n"
                "`/admin cogs` - 列出已加载 Cogs\n"
                "`/admin shutdown` - 关闭机器人"
            ),
            inline=False,
        )

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    """加载 Cog

    Args:
        bot: Discord Bot 实例
    """
    await bot.add_cog(BasicCommands(bot))
