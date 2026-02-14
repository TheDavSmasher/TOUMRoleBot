import re
import configparser
from typing import Callable

from role_types import RoleTeam

role_active_pattern = re.compile(r"(\w+) TownOfUs\.Roles\.(\w+)\.(\w+)Role", re.IGNORECASE)


def load_config(p: str | bytes) -> configparser.ConfigParser:
    config = configparser.ConfigParser()
    loaded = config.read(p)
    if not loaded:
        raise configparser.ParsingError("Failed to read config file. Please check the file path or contents.")

    return config


def mod_config_roles(
        config: configparser.ConfigParser,
        role_pred: Callable[[re.Match[str], int, re.Match[str], int], bool] | None = None
) -> dict[RoleTeam, list[str]]:
    roles_config = config.items("Roles")
    roles: dict[RoleTeam, list[str]] = {}
    for team in RoleTeam:
        roles[team] = []
    for i in range(0, len(roles_config), 2):
        num_config, num_val = roles_config[i]
        num_match = role_active_pattern.search(num_config)
        chance_config, chance_val = roles_config[i + 1]
        chance_match = role_active_pattern.search(chance_config)
        if (not num_match or not chance_match or
                (team := num_match.group(2)) != chance_match.group(2) or
                (role := num_match.group(3)) != chance_match.group(3) or
                team.startswith("hns") or role_pred and
                role_pred(num_match, int(num_val), chance_match, int(chance_val))):
            continue
        r_team = RoleTeam[team.capitalize()]
        roles[r_team].append(role.removesuffix("tou").capitalize())

    return roles


def active_config_roles(config: configparser.ConfigParser) -> dict[RoleTeam, list[str]]:
    return mod_config_roles(
        config,
        lambda num_match, num_val, chance_match, chance_val:
        num_match.group(1) != "num" or num_val <= 0 or
        chance_match.group(1) != "chance" or chance_val <= 0
    )
