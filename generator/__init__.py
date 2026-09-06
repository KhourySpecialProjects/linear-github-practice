"""Static site generator for the class professional bio aggregator.

One Markdown file per student in ``bios/`` becomes one card on the home page
and one detail page. The site is whatever files are present at build time.
"""

from .bios import Bio, Link, Problem, load_bios, parse_bio
from .config import ConfigError, SiteConfig, Team
from .render import BuildError, BuildResult, TeamGroup, build, group_by_team
from .text import hue_for, initials, slugify

__all__ = [
    "Bio",
    "BuildError",
    "BuildResult",
    "ConfigError",
    "Link",
    "Problem",
    "SiteConfig",
    "Team",
    "TeamGroup",
    "build",
    "group_by_team",
    "hue_for",
    "initials",
    "load_bios",
    "parse_bio",
    "slugify",
]
