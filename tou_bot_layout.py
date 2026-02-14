import math

import discord
from discord.ui import *
from discord import SelectOption

from config_reader import load_config, active_config_roles
from role_types import TeamCatRoles, RoleTeam, RoleDesc, AlignData, RoleAlignment
from wiki_ref import fetch_all_roles, get_role_desc, IMAGE_URL
from general_layout import BackButton, SwitchButton, LazyLayoutView, best_row_length


# region Data

config = load_config('conf/Default.cfg')

filtered_roles: dict[RoleTeam, list[str]] = {}

filter_data = False

role_data: dict[tuple[RoleTeam, str, str], RoleDesc] = {}

data: TeamCatRoles = {}

roles_list: RoleAlignment = {}

team_colors = {
    RoleTeam.Crewmate: 0x54baef,
    RoleTeam.Impostor: 0xb70000,
    RoleTeam.Neutral: 0x767676
}

# endregion


# region Helper Functions

def filtered(f: bool):
    global filter_data
    filter_data = f
    global filtered_roles
    if len(filtered_roles) == 0:
        filtered_roles = active_config_roles(config)


def reload_config(b: str | bytes):
    global config
    config = load_config(b)
    global filtered_roles
    filtered_roles = {}


def load_data():
    global data
    global roles_list
    if len(data) == 0:
        data, roles_list = fetch_all_roles()

# endregion


# region Roles

class RoleContainer(Container):
    def __init__(self, data: RoleDesc):
        super().__init__(accent_color=team_colors[data.alignment.team])
        self.add_item(Section(
            TextDisplay(f'## {data.name}'),
            TextDisplay(f'### {data.description}'),
            TextDisplay(f"**Alignment: {data.alignment}**"),
            accessory=Thumbnail(IMAGE_URL.format(icon=data.name)),
        ))
        self.add_item(TextDisplay(data.overview))
        if len(data.abilities) > 0:
            self.add_item(Separator(visible=False))
            self.add_item(TextDisplay("### Abilities:"))
            for ability in data.abilities:
                self.add_item(Section(
                    TextDisplay(f"**{ability.name}**"),
                    TextDisplay(f"{ability.description}"),
                    accessory=Thumbnail(ability.icon_url)
                ))


class RoleLayout(LazyLayoutView):
    def __init__(self, alignment: AlignData, name: str, parent_view: LayoutView = None):
        super().__init__(parent_view)
        self.team = alignment.team
        self.category = alignment.category
        self.name = name

    def _load_view(self):
        role_key = (self.team, self.category, self.name)
        if role_key not in role_data:
            role_data[role_key] = get_role_desc(self.team, self.category.lower(), self.name)
        self.add_item(RoleContainer(role_data[role_key]))
        if self.parent_view:
            self.add_item(ActionRow(BackButton(self.parent_view)))

# endregion


# region Category

class CategoryContainer(Container):
    def __init__(self, alignment: AlignData, parent_view: LayoutView = None):
        team = alignment.team
        category = alignment.category
        super().__init__(accent_color=team_colors[team])
        self.add_item(TextDisplay(f"## {team.name} {category} Roles"))
        action_row = ActionRow()
        roles = data[team][category]
        if filter_data:
            roles = [c_role for c_role in roles if c_role in filtered_roles[team]]
        max_name = max([len(role) for role in roles])
        row_len = best_row_length(len(roles), 5)
        for role in roles:
            if len(action_row.children) == row_len:
                self.add_item(action_row)
                action_row = ActionRow()
            padding = (max_name - len(role)) / 2
            action_row.add_item(SwitchButton(
                RoleLayout(alignment, role, parent_view),
                f"\u200b{' ' * math.ceil(padding)}{role}{' ' * math.floor(padding)}\u200b"
            ))
        if len(action_row.children) > 0:
            self.add_item(action_row)


class CategoryLayout(LazyLayoutView):
    def __init__(self, alignment: AlignData, parent_view: LayoutView = None):
        super().__init__(parent_view)
        self.alignment = alignment

    def _load_view(self):
        self.add_item(CategoryContainer(self.alignment, self))
        if self.parent_view:
            self.add_item(ActionRow(BackButton(self.parent_view)))

# endregion


# region Teams

class TeamContainer(Container):
    def __init__(self, team: RoleTeam, parent_view: LayoutView = None):
        super().__init__(accent_color=team_colors[team])
        self.add_item(TextDisplay(f"## {team.name} Roles"))

        for cat_n, cat_roles in data[team].items():
            if filter_data:
                cat_roles = [c_role for c_role in cat_roles if c_role in filtered_roles[team]]
            if len(cat_roles) == 0:
                continue
            self.add_item(Section(
                TextDisplay(f"### {cat_n}"),
                accessory=SwitchButton(
                    CategoryLayout(AlignData(team, cat_n), parent_view),
                    "View"
                )
            ))
            self.add_item(TextDisplay(', '.join(cat_roles)))
            self.add_item(Separator(visible=False))


class TeamLayout(LayoutView):
    def __init__(self, team: RoleTeam, parent_view: LayoutView = None):
        super().__init__(timeout=None)
        self.add_item(TeamContainer(team, self))
        if parent_view:
            self.add_item(ActionRow(BackButton(parent_view)))

# endregion


# region Main

class MongyTeamSelect(Select):
    def __init__(self):
        super().__init__(
            placeholder="Select the team of the Role...",
            options=[
                SelectOption(label=team.name, value=str(team.value))
                for team in RoleTeam
            ]
        )
        load_data()

    async def callback(self, interaction: discord.Interaction):
        team = RoleTeam(int(self.values[0]))
        await interaction.response.edit_message(
            view=TeamLayout(team, self.view)
        )


class MongyLayout(LayoutView):
    action_row = ActionRow(MongyTeamSelect())

# endregion
