import math
from abc import abstractmethod, ABC

import discord
from discord.ui import *


class LazyLayoutView(LayoutView, ABC):
    def __init__(self, parent_view: LayoutView = None):
        super().__init__(timeout=None)
        self.parent_view = parent_view
        self._loaded = False

    @abstractmethod
    def _load_view(self):
        pass

    def load(self):
        if not self._loaded:
            self._load_view()
            self._loaded = True
        return self


class SwitchButton(Button):
    def __init__(self, switch_view: LayoutView, label: str, style: discord.ButtonStyle = discord.ButtonStyle.secondary):
        self.switch_view = switch_view
        super().__init__(label=label, style=style)

    async def callback(self, interaction: discord.Interaction):
        view = self.switch_view
        if isinstance(view, LazyLayoutView):
            view = view.load()
        await interaction.response.edit_message(
            view=view
        )


class BackButton(SwitchButton):
    def __init__(self, parent_view: LayoutView):
        # noinspection PyTypeChecker
        super().__init__(parent_view, label="Back", style=discord.ButtonStyle.red)


class CheckButton(Button):
    is_checked = False

    def __init__(self):
        # noinspection PyTypeChecker
        super().__init__(emoji="✖️", style=discord.ButtonStyle.red)

    async def callback(self, interaction: discord.Interaction):
        self.is_checked = not self.is_checked
        if self.is_checked:
            self.style = discord.ButtonStyle.green
            self.emoji = "✔️"
        else:
            self.style = discord.ButtonStyle.red
            self.emoji = "✖️"
        await interaction.response.edit_message(
            view=self.view
        )


def best_row_length(n: int, max_len: int) -> int:
    if max_len <= 1:
        raise ValueError("max_len must be > 1")
    if n <= max_len:
        return max_len

    max_len = min(max_len, n)

    best_L = None
    best_score = None

    for L in range(max_len, 1, -1):
        rows = math.ceil(n / L)
        last = n - (rows - 1) * L if rows > 1 else n
        imbalance = L - last

        score = (rows, imbalance, -L)

        if best_score is None or score < best_score:
            best_score = score
            best_L = L

    return best_L
