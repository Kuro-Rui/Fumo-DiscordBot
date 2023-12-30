from typing import Any, Dict, List, Optional

import discord

from . import menus
from .. import commands

__all__ = ("CloseButton", "FumoView", "MenuView")

MENU_EMOJIS = {
    "first": "\N{BLACK LEFT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}",
    "previous": "\N{BLACK LEFT-POINTING TRIANGLE}",
    "next": "\N{BLACK RIGHT-POINTING TRIANGLE}",
    "last": "\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}",
    "goto": "\N{RIGHTWARDS ARROW WITH HOOK}",
    "close": "\N{HEAVY MULTIPLICATION X}\N{VARIATION SELECTOR-16}",
}


class FumoView(discord.ui.View):
    """Custom view for FumoBot."""

    def __init__(self, *, timeout: Optional[float] = 180.0):
        super().__init__(timeout=timeout)

        self.author: Optional[discord.abc.User] = None
        self.message: Optional[discord.Message] = None

    async def start(self, ctx: commands.Context, **kwargs) -> None:
        self.author = ctx.author
        self.message = await ctx.send(view=self, **kwargs)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ensure only the author is allowed to interact with the menu."""
        if interaction.user.id != self.author.id:
            await interaction.response.send_message(
                content="You are not authorized to interact with this help menu.",
                ephemeral=True,
            )
            return False
        return True

    async def on_timeout(self) -> None:
        try:
            for child in self.children:
                child.disabled = True
            await self.message.edit(view=self)
        except discord.HTTPException:
            # message could no longer be there or we may not be able to edit/delete it anymore
            pass


class MenuViewPageSource(menus.ListPageSource):
    def __init__(self, items: List[Any]) -> None:
        super().__init__(items, per_page=1)

    async def format_page(self, view: discord.ui.View, page: Any) -> Any:
        return page


class CloseButton(discord.ui.Button):
    def __init__(
        self,
        emoji: str | discord.Emoji | discord.PartialEmoji = MENU_EMOJIS["close"],
        label: Optional[str] = "Close",
        style: discord.ButtonStyle = discord.ButtonStyle.red,
    ):
        super().__init__(style=style, label=label, emoji=emoji)

    async def callback(self, interaction: discord.Interaction):
        self.view.stop()
        if interaction.message.flags.ephemeral:
            await interaction.response.edit_message(view=None)
            return
        await interaction.message.delete()


class MenuViewJumpModal(discord.ui.Modal):
    def __init__(self, max_pages: int) -> None:
        super().__init__(title="Go to Page...")
        self.interaction: Optional[discord.Interaction] = None
        self.page_input = discord.ui.TextInput(
            label=f"Page Number (1-{max_pages})",
            placeholder=f"Enter a number between 1 and {max_pages}",
            min_length=1,
            max_length=len(str(max_pages)),
        )
        self.add_item(self.page_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        self.interaction = interaction
        self.stop()


class MenuView(FumoView):
    def __init__(self, pages: List[Any], page_start: int = 0, timeout: float = 180.0) -> None:
        super().__init__(timeout=timeout)
        self.current_page = page_start  # This will only be changed by the navigation buttons
        self.source = MenuViewPageSource(pages)
        self.max_pages = self.source.get_max_pages()
        self.clear_items()

        self.close_button = CloseButton()
        if self.source.is_paginating():
            self.add_item(self.first_button)
            self.add_item(self.previous_button)
            self.add_item(self.current_button)
            self.add_item(self.next_button)
            self.last_button.label = f"{MENU_EMOJIS['last']} {self.max_pages}"
            self.add_item(self.last_button)
            if self.max_pages > 3:
                # It's no use to have a goto button if there's only 3 pages
                # To go to page 2, you can just click the next button
                # To go to page 3, you can just click the last button
                # And vice versa to go to previous pages.
                self.add_item(self.goto_button)
            self.close_button.row = 1
            self.add_item(self.close_button)
        else:
            self.add_item(self.close_button)

    def _update_button_labels(self) -> None:
        self.first_button.disabled = self.current_page == 0
        self.previous_button.disabled = False
        self.previous_button.label = f"{self.current_page} \u200b {MENU_EMOJIS['previous']}"
        if self.current_page == 0:
            self.previous_button.disabled = True
            self.previous_button.label = f"... \u200b {MENU_EMOJIS['previous']}"
        self.current_button.label = str(self.current_page + 1)
        self.next_button.disabled = False
        self.next_button.label = f"{MENU_EMOJIS['next']} \u200b {self.current_page + 2}"
        if self.current_page + 1 >= self.max_pages:
            self.next_button.disabled = True
            self.next_button.label = f"{MENU_EMOJIS['next']} \u200b ..."
        self.last_button.disabled = self.current_page + 1 >= self.max_pages

    async def get_page(self, page_number: int) -> Dict[str, Optional[Any]]:
        try:
            page = await self.source.get_page(page_number)
        except IndexError:
            self.current_page = 0
            page = await self.source.get_page(self.current_page)
        value = await self.source.format_page(self, page)
        self._update_button_labels()

        ret: Dict[str, Optional[str | discord.Embed]] = {"view": self}
        if isinstance(value, dict):
            ret.update(value)
        elif isinstance(value, str):
            ret.update({"content": value, "embed": None})
        elif isinstance(value, discord.Embed):
            ret.update({"embed": value, "content": None})
        return ret

    async def start(
        self, ctx: commands.Context, *, reply: bool = False, ephemeral: bool = False
    ) -> None:
        self.author = ctx.author
        kwargs = await self.get_page(self.current_page)
        if reply:
            self.message = await ctx.reply(**kwargs, ephemeral=ephemeral)
        else:
            self.message = await ctx.send(**kwargs, ephemeral=ephemeral)

    @discord.ui.button(label=f"1 \u200b {MENU_EMOJIS['first']}")
    async def first_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to the first page."""
        self.current_page = 0
        kwargs = await self.get_page(self.current_page)
        await interaction.response.edit_message(**kwargs)

    @discord.ui.button(label=MENU_EMOJIS["previous"], style=discord.ButtonStyle.blurple)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to the previous page."""
        self.current_page -= 1
        kwargs = await self.get_page(self.current_page)
        await interaction.response.edit_message(**kwargs)

    @discord.ui.button(disabled=True, style=discord.ButtonStyle.green)
    async def current_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Displays the current page."""
        pass

    @discord.ui.button(label=MENU_EMOJIS["next"], style=discord.ButtonStyle.blurple)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to the next page."""
        self.current_page += 1
        kwargs = await self.get_page(self.current_page)
        await interaction.response.edit_message(**kwargs)

    @discord.ui.button(label=MENU_EMOJIS["last"])
    async def last_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to the last page."""
        self.current_page = self.max_pages - 1
        kwargs = await self.get_page(self.current_page)
        await interaction.response.edit_message(**kwargs)

    @discord.ui.button(
        label=f"{MENU_EMOJIS['goto']} \u200b Go to Page...",
        style=discord.ButtonStyle.blurple,
    )
    async def goto_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to a specific page."""
        modal = MenuViewJumpModal(self.max_pages)
        await interaction.response.send_modal(modal)
        timed_out = await modal.wait()
        if timed_out:
            await interaction.followup.send("You took too long to respond.", ephemeral=True)
            return
        if self.is_finished():
            await modal.interaction.response.send_message(
                "You took too long to respond.", ephemeral=True
            )
            return

        page_input = modal.page_input.value
        if not page_input.isdigit():
            await modal.interaction.response.send_message(
                f"{page_input} is not a valid number!", ephemeral=True
            )
            return
        page = int(page_input)
        if not 1 <= page <= self.max_pages:
            await modal.interaction.response.send_message(
                f"Page number must be between 1 and {self.max_pages}.", ephemeral=True
            )
            return

        self.current_page = int(page_input) - 1
        kwargs = await self.get_page(self.current_page)
        await modal.interaction.response.edit_message(**kwargs)
