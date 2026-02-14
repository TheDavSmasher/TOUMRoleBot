from dataclasses import dataclass
from enum import Enum


class RoleTeam(Enum):
    Crewmate = 0
    Impostor = 1
    Neutral = 2


TeamCategories = dict[str, list[str]]
TeamCatRoles = dict[RoleTeam, TeamCategories]


@dataclass
class AlignData:
    team: RoleTeam
    category: str

    def __str__(self):
        return f"{self.team.name} {self.category}"

    @classmethod
    def from_str(cls, s: str):
        s_l = s.split()
        return AlignData(RoleTeam[s_l[0]], s_l[1].rstrip('\u200b'))


RoleAlignment = dict[str, AlignData]


@dataclass
class RoleAbility:
    name: str
    description: str
    icon_url: str


@dataclass
class RoleDesc:
    name: str
    description: str
    overview: str
    alignment: AlignData
    abilities: list[RoleAbility]
