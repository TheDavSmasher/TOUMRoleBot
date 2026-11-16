import requests
import bs4
from bs4 import BeautifulSoup

from role_types import RoleDesc, RoleAbility, RoleTeam, AlignData, TeamCatRoles, RoleAlignment

WIKI_URL = "https://au-avengers.github.io/docs.toum.gg/{path}"

MODIFS_PATH = "docs/category/crewmate"
MODIF_URL = "docs/modifiers/{category}/{modifier}"

ROLES_PATH = "docs/category/crewmates"
ROLE_URL = "docs/roles/{team}/{al_type}/{role}"

IMAGE_URL = WIKI_URL.format(path="img/Icons/{icon}.png")


def fetch_url_soup(path: str, name: str, att_class: str) -> BeautifulSoup:
    url = WIKI_URL.format(path=path)
    response = requests.get(url)
    if response.status_code != 200:
        raise requests.exceptions.HTTPError(f"Failed to retrieve page.\nStatus code: {response.status_code}\nURL: {url}")

    html_content = response.text
    soup = BeautifulSoup(html_content, 'html.parser')

    element = soup.find(name, {"class": att_class})

    if not element:
        raise bs4.exceptions.FeatureNotFound("Main content div not found.")

    return element


def fetch_all_roles() -> tuple[TeamCatRoles, RoleAlignment]:
    roles_list = fetch_url_soup(ROLES_PATH, "ul", "theme-doc-sidebar-menu menu__list")

    team_dict: TeamCatRoles = {}
    roles_dict: RoleAlignment = {}
    for team in roles_list.find_all("li", recursive=False):
        name_str = team.find("a").get_text().removesuffix("s")
        role_team = RoleTeam[name_str]
        team_dict[role_team] = {}
        for category in team.find_next("ul").find_all("li", recursive=False):
            cat_name = category.find("a").get_text().split()[1]
            team_dict[role_team][cat_name] = []
            for cat_role in category.find_next("ul").find_all("li", recursive=False):
                role_name = cat_role.find("a").get_text()
                team_dict[role_team][cat_name].append(role_name)
                roles_dict[role_name] = AlignData(role_team, cat_name)
    return team_dict, roles_dict


def get_role_desc(team: RoleTeam, al_type: str, role: str) -> RoleDesc:
    role_info = fetch_url_soup(ROLE_URL.format(team=team.name.lower(), al_type=al_type, role=role),
                               "div", "theme-doc-markdown markdown")

    name = role_info.find_next("h1")
    desc = role_info.find_next("h3")
    align = role_info.find_next("h4")
    overview = role_info.find_next("p")

    ab_list: list[RoleAbility] = []
    next_table = overview
    while next_table := next_table.find_next("table"):
        if next_table.find_next("th").get_text() != "Button":
            continue

        for ability in next_table.find("tbody").find_all("tr"):
            ab_icon = ability.find_next("td")
            ab_name = ab_icon.find_next("td")
            ab_desc = ab_name.find_next("td")
            ab_list.append(RoleAbility(
                ab_name.get_text(),
                ab_desc.get_text(),
                f"https://au-avengers.github.io{ab_icon.find_next("img").get("src")}"
            ))
        break

    return RoleDesc(
        name.get_text(),
        desc.get_text(),
        overview.get_text(),
        AlignData.from_str(align.get_text().replace("Alignment: ", "").strip()),
        ab_list
    )
