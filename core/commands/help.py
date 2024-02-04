import re
from typing import Iterable, Mapping

import discord
import humanize
from rich import markup

from .. import commands
from ..utils.formatting import EightBitANSI, code, pagify, shorten, wrap
from ..utils.views import CloseButton, FumoView

__all__ = ("FumoHelp",)


class HelpCategorySelect(discord.ui.Select):
    def __init__(self, cogs: list[commands.Cog], help_for: commands.Cog | None):
        options = [
            discord.SelectOption(
                label="Main",
                value="_main",
                description="Go back to the main page.",
                emoji="\N{SHINTO SHRINE}\N{VARIATION SELECTOR-16}",
            ),
        ]
        for cog in cogs:
            cog: commands.Cog
            description = "No description"
            splitted = cog.description.split("\n\n")
            if splitted:
                description = splitted[0]
            options.append(
                discord.SelectOption(
                    label=cog.qualified_name,
                    value=cog.qualified_name,
                    description=description,
                    emoji=cog.display_emoji,
                )
            )
        if help_for:
            option = discord.utils.get(options, value=help_for.qualified_name)
            i = options.index(option)
            options[i].default = True
        else:
            options[0].default = True
        super().__init__(placeholder="Select a category...", options=options)

    async def callback(self, interaction: discord.Interaction):
        self.view: HelpView
        self.view.current_embed = self.view.embeds[self.values[0]]

        default = discord.utils.get(self.options, default=True)
        i = self.options.index(default)
        self.options[i].default = False

        option = discord.utils.get(self.options, value=self.values[0])
        i = self.options.index(option)
        self.options[i].default = True

        await interaction.response.edit_message(embed=self.view.current_embed, view=self.view)


class HelpView(FumoView):
    def __init__(
        self,
        cog: commands.Cog | None,
        cogs: list[commands.Cog],
        embeds: dict[str, discord.Embed],
    ) -> None:
        super().__init__()
        self.embeds = embeds
        self.current_embed = embeds[cog.qualified_name if cog else "_main"]
        self.select_menu = HelpCategorySelect(cogs, cog)
        self.add_item(self.select_menu)
        self.add_item(CloseButton())

    async def start(self, ctx: commands.Context, *, details: str | None = None) -> discord.Message:
        self.author = ctx.author
        self.message = await ctx.reply(details, embed=self.current_embed, view=self)
        return self.message


class FumoHelp(commands.HelpCommand):
    """Custom help command for Fumo."""

    context: commands.Context

    def __init__(self, **options):
        super().__init__(
            command_attrs={
                "help": "Shows help about the bot, a category, or a command.",
                "usage": "[category|command]",
            },
            **options,
        )

    async def filter_cogs(
        self, cogs: Iterable[commands.Cog | None], *, sort: bool = False
    ) -> list[commands.Cog]:
        filtered = []
        for cog in cogs:
            if not cog:
                continue
            cmds = await self.filter_commands(
                filter(lambda c: c.parent is None, cog.get_commands())
            )
            if cmds:
                filtered.append(cog)
        return sorted(filtered, key=lambda c: c.qualified_name) if sort else filtered

    def _make_embed(self, footer: str, **kwargs) -> discord.Embed:
        bot = self.context.bot
        embed = discord.Embed(color=self.context.embed_color, **kwargs)
        embed.set_author(name=f"{bot.user.name} Help Menu", icon_url=bot.user.avatar.url)
        embed.set_footer(text=footer)
        return embed

    async def _create_embeds(
        self, mapping: Mapping[commands.Cog | None, list[commands.Command]]
    ) -> dict[str, discord.Embed]:
        bot = self.context.bot
        prefix = self.context.clean_prefix

        embeds = {}
        main_embed = self._make_embed(
            f"Type {prefix}help <category> for more info on a category.",
            title=bot.description,
        )
        cogs = await self.filter_cogs(mapping.keys(), sort=True)
        for cog in cogs:
            description = "No description"
            splitted = cog.description.split("\n\n")
            if splitted:
                description = splitted[0]
            description += "\n" + wrap(f"{prefix}help {cog.qualified_name}", "`")
            main_embed.add_field(
                name=f"{cog.display_emoji} {cog.qualified_name}", value=description
            )
        embeds["_main"] = main_embed
        for cog, cmds in mapping.items():
            if cog not in cogs:
                continue
            if cog.description:
                splitted = filter(None, cog.description.split("\n\n"))
                try:
                    name = next(splitted)
                except StopIteration:
                    # all parts are empty
                    pass
                value = "\n\n".join(splitted)
                if not value:
                    value = "\N{ZERO WIDTH SPACE}"
            cmds = await self.filter_commands(filter(lambda c: c.parent is None, cmds), sort=True)
            spacing = len(max([c.name for c in cmds], key=len, default=""))
            description = "\n".join(
                shorten(f"`{cmd.name:<{spacing}} :` {cmd.short_doc}", 70) for cmd in cmds
            )
            embed = self._make_embed(
                f"Type {prefix}help <command> for more info on a command.",
                title=cog.qualified_name,
            )
            embed.add_field(name=name[:250], value=value[:1024], inline=False)
            embed.add_field(name="Commands", value=description, inline=False)
            embeds[cog.qualified_name] = embed
        return embeds

    async def send_bot_help(
        self,
        mapping: Mapping[commands.Cog | None, list[commands.Command]],
        /,
        *,
        details: str | None = None,
    ) -> None:
        cogs = await self.filter_cogs(mapping.keys(), sort=True)
        embeds = await self._create_embeds(mapping)
        view = HelpView(None, cogs, embeds)
        await view.start(self.context, details=details)

    async def send_cog_help(
        self,
        cog: commands.Cog,
        /,
        *,
        details: str | None = None,
    ) -> None:
        mapping = self.get_bot_mapping()
        cogs = await self.filter_cogs(mapping.keys(), sort=True)
        embeds = await self._create_embeds(mapping)
        view = HelpView(cog, cogs, embeds)
        await view.start(self.context, details=details)

    def get_command_signature(self, command: commands.Command | commands.Group) -> str:
        # Handling command name
        aliases = sorted(command.aliases, key=len)
        prefix = self.context.clean_prefix
        signatures = [
            EightBitANSI.paint_white("Syntax :" if len(aliases) > 1 else "Syntax:", bold=True),
            EightBitANSI.paint_red(markup.escape(prefix))
            + EightBitANSI.paint_magenta(command.qualified_name),
        ]

        # Handling command signature
        # Split the string with multiple chars which is "<", ">", "[", "]", and " "
        # For example, <user> turns to ["<", "user", ">"]
        splitted_signature = re.findall(r"[<>\[\]\s.|=]|\w+", command.signature)
        piece = ""
        for char in splitted_signature:
            piece += EightBitANSI.paint_blue(char, bold=True) if char.isalnum() else char
        signatures.append(piece)
        signature = " ".join(signatures)

        # Handling command aliases, if there's any.
        if aliases:
            signature += "\n" + EightBitANSI.paint_white(
                "Aliases: " if len(aliases) > 1 else "Alias : ", bold=True
            )
            count = 0
            valid_aliases = []
            for alias in aliases:
                if (count := count + len(alias)) < 500:
                    valid_aliases.append(alias)
                else:
                    break
            diff = len(aliases) - len(valid_aliases)
            aliases_list = [
                "{prefix}{parent}{alias}".format(
                    prefix=EightBitANSI.paint_red(prefix),
                    parent=(
                        EightBitANSI.paint_magenta(command.parent.qualified_name) + " "
                        if command.parent
                        else ""
                    ),
                    alias=EightBitANSI.paint_magenta(alias),
                )
                for alias in valid_aliases
            ]
            formatted_aliases = ", ".join(aliases_list)
            if len(valid_aliases) < 10:
                signature += formatted_aliases
            else:
                signature += "{aliases} and {number} more alias{es}.".format(
                    aliases=formatted_aliases,
                    number=EightBitANSI.paint_blue(humanize.intcomma(diff), bold=True),
                    es="es" if diff > 1 else "",
                )
        return signature

    @staticmethod
    def get_cooldowns(command: commands.Command | commands.Group):
        cooldowns = []
        if cd := command.cooldown:
            bucket_type = command._buckets.type.name
            cooldown = (
                f"{cd.rate} time{'s' if cd.rate > 1 else ''} in {humanize.precisedelta(cd.per)}"
            )
            if bucket_type == "default":
                cooldown += " globally."
            else:
                cooldown += f" per {bucket_type}."
            cooldowns.append(cooldown)
        if mc := command._max_concurrency:
            cooldowns.append(f"Max concurrent uses: {mc.number} per {mc.per.name.capitalize()}")
        return "\n".join(cooldowns)

    async def _make_command_help_embed(
        self, command: commands.Command | commands.Group
    ) -> discord.Embed:
        footer = (
            "<argument> means required argument, [argument] means optional argument,\n"
            "[a|b] means it can be a or b, and [argument...] means you can have multiple arguments."
        )
        embed = self._make_embed(
            footer, description=code(self.get_command_signature(command), lang="ansi")
        )
        if command.help:
            splitted = filter(None, command.help.split("\n\n"))
            try:
                name = next(splitted)
            except StopIteration:
                # all parts are empty
                pass
            value = "\n\n".join(splitted)
            if not value:
                value = "\N{ZERO WIDTH SPACE}"
            embed.add_field(name=name[:250], value=value[:1024], inline=False)
        if cooldowns := self.get_cooldowns(command):
            embed.add_field(name="Cooldowns", value=cooldowns, inline=False)
        return embed

    def _make_pages(self, embeds: list[discord.Embed], *, details: str | None = None):
        pages = []
        for embed in embeds:
            pages.append({"content": details, "embed": embed})
        return pages

    async def send_group_help(
        self,
        group: commands.Group,
        /,
        *,
        details: str | None = None,
    ) -> None:
        subcommands = await self.filter_commands(group.commands, sort=True)
        if not subcommands:
            await self.send_command_help(group)
            return
        embeds = []
        spacing = len(max([s.name for s in subcommands], key=len))
        subtext = "\n".join(
            shorten(f"`{subcommand.name:<{spacing}} :` {subcommand.short_doc}", 70)
            for subcommand in subcommands
        )
        pages = list(pagify(subtext, page_length=1024))
        for i, page in enumerate(pages, start=1):
            embed = await self._make_command_help_embed(group)
            embed.title = f"Page {i} of {len(pages)}"
            embed.add_field(name="Subcommands", value=page, inline=False)
            embeds.append(embed)
        pages = self._make_pages(embeds, details=details)
        await self.context.send_menu(pages)

    async def send_command_help(
        self,
        command: commands.Command,
        /,
        *,
        details: str | None = None,
    ) -> None:
        embed = await self._make_command_help_embed(command)
        pages = self._make_pages([embed], details=details)
        await self.context.send_menu(pages)
