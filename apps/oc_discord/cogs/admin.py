"""管理员命令 Cog

提供 Slash Commands Group: /admin reload, /admin load, /admin unload,
/admin cogs, /admin shutdown
"""

from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands
from loguru import logger

# Cog 模块前缀 (与 adapter.py 中的 module_prefix 一致)
COG_MODULE_PREFIX: str = "apps.oc_discord.cogs"


async def _cog_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    """Cog 名称自动补全

    Args:
        interaction: 交互对象
        current: 当前输入内容

    Returns:
        匹配的 Cog 名称选项列表
    """
    cogs_dir: Path = Path(__file__).parent
    available: list[str] = [
        f.stem
        for f in cogs_dir.glob("*.py")
        if not f.name.startswith("_")
    ]
    return [
        app_commands.Choice(name=name, value=name)
        for name in available
        if current.lower() in name.lower()
    ][:25]  # Discord 限制最多 25 个选项


class AdminCommands(commands.Cog):
    """管理员命令组

    所有命令归属 /admin 子命令组,需要管理员权限。
    """

    admin = app_commands.Group(
        name="admin",
        description="管理员命令",
        default_permissions=discord.Permissions(administrator=True),
    )

    def __init__(self, bot: commands.Bot) -> None:
        """初始化管理员命令 Cog

        Args:
            bot: Discord Bot 实例
        """
        self.bot = bot

    @admin.command(name="reload", description="重载指定的 Cog")
    @app_commands.describe(cog_name="Cog 模块名称")
    @app_commands.autocomplete(cog_name=_cog_autocomplete)
    async def reload_cog(
        self,
        interaction: discord.Interaction,
        cog_name: str,
    ) -> None:
        """重载指定的 Cog

        Args:
            interaction: 交互对象
            cog_name: Cog 名称
        """
        extension_path: str = f"{COG_MODULE_PREFIX}.{cog_name}"
        try:
            await self.bot.reload_extension(extension_path)
            await interaction.response.send_message(f"✅ 已重载 Cog: {cog_name}")
        except commands.ExtensionNotLoaded:
            await interaction.response.send_message(
                f"❌ Cog 未加载: {cog_name}", ephemeral=True
            )
        except commands.ExtensionNotFound:
            await interaction.response.send_message(
                f"❌ 未找到 Cog: {cog_name}", ephemeral=True
            )
        except Exception as e:
            logger.opt(exception=True).error(f"重载 Cog {cog_name} 失败: {e}")
            await interaction.response.send_message(
                f"❌ 重载失败: {e}", ephemeral=True
            )

    @admin.command(name="load", description="加载指定的 Cog")
    @app_commands.describe(cog_name="Cog 模块名称")
    @app_commands.autocomplete(cog_name=_cog_autocomplete)
    async def load_cog(
        self,
        interaction: discord.Interaction,
        cog_name: str,
    ) -> None:
        """加载指定的 Cog

        Args:
            interaction: 交互对象
            cog_name: Cog 名称
        """
        extension_path: str = f"{COG_MODULE_PREFIX}.{cog_name}"
        try:
            await self.bot.load_extension(extension_path)
            await interaction.response.send_message(f"✅ 已加载 Cog: {cog_name}")
        except commands.ExtensionAlreadyLoaded:
            await interaction.response.send_message(
                f"❌ Cog 已加载: {cog_name}", ephemeral=True
            )
        except commands.ExtensionNotFound:
            await interaction.response.send_message(
                f"❌ 未找到 Cog: {cog_name}", ephemeral=True
            )
        except Exception as e:
            logger.opt(exception=True).error(f"加载 Cog {cog_name} 失败: {e}")
            await interaction.response.send_message(
                f"❌ 加载失败: {e}", ephemeral=True
            )

    @admin.command(name="unload", description="卸载指定的 Cog")
    @app_commands.describe(cog_name="Cog 模块名称")
    @app_commands.autocomplete(cog_name=_cog_autocomplete)
    async def unload_cog(
        self,
        interaction: discord.Interaction,
        cog_name: str,
    ) -> None:
        """卸载指定的 Cog

        Args:
            interaction: 交互对象
            cog_name: Cog 名称
        """
        extension_path: str = f"{COG_MODULE_PREFIX}.{cog_name}"
        try:
            await self.bot.unload_extension(extension_path)
            await interaction.response.send_message(f"✅ 已卸载 Cog: {cog_name}")
        except commands.ExtensionNotLoaded:
            await interaction.response.send_message(
                f"❌ Cog 未加载: {cog_name}", ephemeral=True
            )
        except Exception as e:
            logger.opt(exception=True).error(f"卸载 Cog {cog_name} 失败: {e}")
            await interaction.response.send_message(
                f"❌ 卸载失败: {e}", ephemeral=True
            )

    @admin.command(name="cogs", description="列出所有已加载的 Cogs")
    async def list_cogs(self, interaction: discord.Interaction) -> None:
        """列出所有已加载的 Cogs

        Args:
            interaction: 交互对象
        """
        cog_list: list[str] = list(self.bot.cogs.keys())

        if not cog_list:
            await interaction.response.send_message(
                "❌ 当前没有加载任何 Cog", ephemeral=True
            )
            return

        embed = discord.Embed(
            title="📦 已加载的 Cogs",
            description="\n".join(f"• {cog}" for cog in cog_list),
            color=discord.Color.blue(),
        )

        await interaction.response.send_message(embed=embed)

    @admin.command(name="shutdown", description="关闭机器人 (仅 Bot Owner)")
    async def shutdown(self, interaction: discord.Interaction) -> None:
        """关闭机器人 (仅限 Bot Owner)

        Args:
            interaction: 交互对象
        """
        # 仅允许 Bot Owner 执行
        if not await self.bot.is_owner(interaction.user):
            await interaction.response.send_message(
                "❌ 仅机器人所有者可以执行此命令", ephemeral=True
            )
            return

        await interaction.response.send_message("👋 正在关闭机器人...")
        await self.bot.close()


async def setup(bot: commands.Bot) -> None:
    """加载 Cog

    Args:
        bot: Discord Bot 实例
    """
    await bot.add_cog(AdminCommands(bot))
