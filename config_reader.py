import re
import configparser

from role_types import RoleTeam

role_active_pattern = re.compile(r"(\w+) TownOfUs\.Roles\.(\w+)\.(\w+)Role", re.IGNORECASE)


def load_config(p: str) -> configparser.ConfigParser:
    config = configparser.ConfigParser()
    loaded = config.read(p)
    if not loaded:
        print("Failed to read config file. Please check the file path.")
        exit()

    return config


def active_config_roles(config: configparser.ConfigParser) -> dict[RoleTeam, list[str]]:
    roles_config = config.items("Roles")
    active_roles: dict[RoleTeam, list[str]] = {}
    for i in range(0, len(roles_config), 2):
        num_config, num_val = roles_config[i]
        num_match = role_active_pattern.search(num_config)
        chance_config, chance_val = roles_config[i+1]
        chance_match = role_active_pattern.search(chance_config)
        if (not num_match or not chance_match or
                (team := num_match.group(2)) != chance_match.group(2) or
                (role := num_match.group(3)) != chance_match.group(3) or
                team.startswith("hns") or
                num_match.group(1) != "num" or int(num_val) <= 0 or
                chance_match.group(1) != "chance" or int(chance_val) <= 0):
            continue
        r_team = RoleTeam[team.capitalize()]
        if r_team not in active_roles:
            active_roles[r_team] = []
        active_roles[r_team].append(role.removesuffix("tou").capitalize())

    return active_roles
