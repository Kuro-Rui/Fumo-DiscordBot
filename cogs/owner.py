import discord

from core import commands
from core.bot import FumoBot
from core.utils.formatting import format_perms, pagify


class Owner(commands.Cog):
    """Owner-only commands."""

    def __init__(self, bot: FumoBot):
        super().__init__(bot, discord.PartialEmoji(name="RemiliaSmile", id=1189592920379105330))

    @commands.is_owner()
    @commands.group(aliases=["bl"], invoke_without_command=True)
    async def blacklist(self, ctx: commands.Context):
        """List all blacklisted users."""
        if not self.bot.blacklist:
            await ctx.send("No users are blacklisted.")
            return

        embeds = []
        embed = discord.Embed(color=ctx.embed_color, title="Blacklisted Users")
        users = []
        unknown = []
        for user_id in self.bot.blacklist:
            if user := self.bot.get_user(user_id):
                users.append(user)
                continue
            unknown.append(user_id)
        pages = []
        if users:
            pages.extend([f"- `{user}` ({user.mention})" for user in users])
        if unknown:
            pages.extend([f"- `{user_id}` (Unknown)" for user_id in unknown])

        for page in pagify("\n".join(pages), page_length=4096):
            embed = embed.copy()
            embed.description = page
            embeds.append(embed)
        await ctx.send_menu(embeds, reply=True)

    @blacklist.command(name="add")
    async def blacklist_add(self, ctx: commands.Context, *users: discord.User):
        """Blacklist users from using the bot."""
        success = []
        for user in users:
            if user in self.bot.blacklist:
                continue
            self.bot.add_to_blacklist(user.id)
            success.append(user)
        if not success:
            await ctx.cross()
            await ctx.send("Provided users are already blacklisted.")
            return
        await ctx.tick()

    @blacklist.command(name="remove")
    @commands.is_owner()
    async def blacklist_remove(self, ctx: commands.Context, *users: discord.User):
        """Unblacklist users from using the bot."""
        success = []
        for user in users:
            if user not in self.bot.blacklist:
                continue
            self.bot.remove_from_blacklist(user.id)
            success.append(user)
        if not success:
            await ctx.cross()
            await ctx.send("Provided users aren't blacklisted.")
            return
        await ctx.tick()

    @commands.is_owner()
    @commands.group(aliases=["set", "settings"], invoke_without_command=True)
    async def config(self, ctx: commands.Context):
        """Show the bot's config."""
        config = self.bot.config
        config_dict = {
            "Description": config.description,
            "Embed Colour": "#" + hex(config.embed_colour.value)[2:],
            "Mobile": "Yes" if config.mobile else "No",
            "Permissions": format_perms(config.permissions, True),
            "Prefix": config.prefix,
        }
        embed = discord.Embed(color=ctx.embed_color, title="Bot Configuration")
        for name, value in config_dict.items():
            embed.add_field(name=name, value=value)
        await ctx.send(embed=embed)

    @config.command(name="description")
    async def config_description(self, ctx: commands.Context, *, value: str):
        """Set the bot's config."""
        self.bot.description = value
        self.bot._config.description = value
        await ctx.tick()

    @config.command(name="embedcolour", aliases=["embedcolor", "colour", "color"])
    async def config_embed_colour(self, ctx: commands.Context, *, value: discord.Colour):
        """Set the bot's embed colour."""
        self.bot._config.embed_colour = value
        await ctx.tick()

    @config.command(name="mobile")
    async def config_mobile(self, ctx: commands.Context, *, value: bool):
        """Set whether the bot should be on mobile status or not."""
        if value == self.bot._config.mobile:
            await ctx.tick()
            return
        self.bot._config.mobile = value
        await self.bot.monkeypatch_ws(mobile=value, reconnect=True)
        await ctx.tick()

    @config.command(name="permissions", aliases=["perms"])
    async def config_permissions(self, ctx: commands.Context, *, value: int):
        """Set the bot's permissions."""
        self.bot._config.permissions = discord.Permissions(value)
        await ctx.tick()

    @config.command(name="prefix")
    async def config_prefix(self, ctx: commands.Context, *, value: str):
        """Set the bot's prefix."""
        self.bot._config.prefix = value
        await ctx.tick()


async def setup(bot: FumoBot):
    await bot.add_cog(Owner(bot))
