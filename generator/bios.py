"""Parsing and validation for one YAML bio file per student.

A bio file is a YAML mapping. Everything is structured data except ``about``,
which is a block scalar holding a few sentences of Markdown:

    name: Jane Doe
    team: Team Falcon
    headline: Backend engineer who likes boring infrastructure
    about: |
      Two or three sentences about Jane. This is **Markdown**, so bold,
      links and lists all work.

Parsing always yields a :class:`Bio`, even for a file that is broken beyond
repair: unreadable fields are replaced with the fallbacks below and every
substitution is reported as a :class:`Problem`. That split is deliberate.

* ``validate`` treats any problem as a failure, so a pull request with a bad
  bio still goes red and the student still has to fix it.
* ``build`` renders the salvaged bio and only warns, so one malformed file
  merged past the gate degrades a single card instead of taking the whole
  deployed site down.

YAML is unforgiving about tab indentation, an unquoted ``": "`` inside a value,
and block-scalar indentation, so each of those gets its own message here rather
than leaking PyYAML's wording.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace

import markdown
import yaml
from markupsafe import Markup

from .config import SiteConfig
from .text import hue_for, initials, slugify

FILENAME = re.compile(r"\A[a-z0-9]+(?:-[a-z0-9]+)+\.yml\Z")
UNSAFE_HTML = re.compile(r"<\s*/?\s*(?:script|iframe|object|embed)\b[^>]*>?|javascript:", re.IGNORECASE)
LEADING_TAB = re.compile(r"^[ ]*\t", re.MULTILINE)
FENCE = re.compile(r"^\s*(?:```|~~~)")

#: Files in ``bios/`` that are documentation, not student bios.
RESERVED_FILES = frozenset({"TEMPLATE.yml"})

REQUIRED_KEYS = ("name", "team", "headline", "about")
ALLOWED_KEYS = frozenset(
    {
        "name",
        "team",
        "headline",
        "about",
        "pronouns",
        "location",
        "focus",
        "links",
        "avatar",
        "fun_fact",
    }
)

HEADLINE_MAX = 90
ABOUT_MIN = 40
ABOUT_MAX = 2000
FOCUS_MAX = 6
FOCUS_ITEM_MAX = 24

MARKDOWN_EXTENSIONS = ("extra", "sane_lists", "smarty")

#: Substituted when a field cannot be read. Visible on the site on purpose:
#: a placeholder that says what is wrong beats a card that quietly lies.
FALLBACK_NAME = "Unnamed Student"
FALLBACK_HEADLINE = "Bio still needs a headline"
FALLBACK_ABOUT = (
    "This bio could not be read yet. Fix the fields reported by "
    "`python -m generator validate` and it will appear here on the next deploy."
)

_ABOUT_SHAPE = "about: |\n  Two or three sentences about you."


@dataclass(frozen=True, slots=True)
class Problem:
    """One actionable validation failure, tied to the file that caused it."""

    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.message}"


@dataclass(frozen=True, slots=True)
class Link:
    label: str
    url: str


@dataclass(frozen=True, slots=True)
class Bio:
    slug: str
    name: str
    team: str
    headline: str
    body_html: Markup
    source: str
    pronouns: str | None = None
    location: str | None = None
    fun_fact: str | None = None
    avatar: str | None = None
    focus: tuple[str, ...] = ()
    links: tuple[Link, ...] = ()
    #: True when any field had to be replaced or repaired to render this bio.
    salvaged: bool = False

    @property
    def url(self) -> str:
        return f"/{self.slug}/"

    @property
    def initials(self) -> str:
        return initials(self.name)

    @property
    def hue(self) -> int:
        return hue_for(self.slug)

    @property
    def sort_key(self) -> tuple[str, str]:
        """Sort by family name, falling back to the slug for stability."""
        parts = self.name.split()
        family = slugify(parts[-1]) if parts else self.slug
        return (family, self.slug)


def _as_text(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool) or isinstance(value, (dict, list)):
        return None
    return str(value).strip()


def _yaml_message(exc: yaml.YAMLError) -> str:
    """Turn a PyYAML error into something a first-time YAML author can act on."""
    problem = getattr(exc, "problem", None) or "could not be parsed"
    mark = getattr(exc, "problem_mark", None)
    where = f"line {mark.line + 1}" if mark is not None else "somewhere in the file"
    hint = ""
    if "mapping values are not allowed" in problem:
        hint = " - a value containing ': ' must be wrapped in quotes"
    elif "could not find expected ':'" in problem:
        hint = " - every field is 'key: value', and continuation lines must be indented"
    elif "found character '\\t'" in problem:
        hint = " - YAML does not allow tabs; indent with spaces"
    elif "another document" in problem or "expected a single document" in problem:
        hint = " - remove the '---' lines; the whole file is YAML, not Markdown with front matter"
    return f"invalid YAML at {where}: {problem}{hint}"


def name_from_filename(path: Path) -> str:
    """Best guess at a display name when ``name`` is missing or unreadable."""
    words = [word for word in slugify(path.stem).split("-") if word]
    return " ".join(word.capitalize() for word in words) or FALLBACK_NAME


def _render_about(about: str) -> tuple[Markup, bool]:
    """Render ``about`` as Markdown, repairing anything that would look broken.

    Returns the HTML and whether a repair was needed. Markdown turns a
    four-space indent or a `````` fence into a grey code block, which is never
    what a bio wants, so those get flattened rather than published.
    """
    html = Markup(markdown.markdown(about, extensions=list(MARKDOWN_EXTENSIONS)))
    if "<pre" not in html:
        return html, False

    flattened = "\n".join(
        "" if FENCE.match(line) else line.strip() for line in about.splitlines()
    )
    return Markup(markdown.markdown(flattened, extensions=list(MARKDOWN_EXTENSIONS))), True


def _truncate(text: str, limit: int) -> str:
    """Cut ``text`` to ``limit`` characters on a word boundary."""
    if len(text) <= limit:
        return text
    clipped = text[: limit - 1].rsplit(" ", 1)[0].rstrip(",.;:-")
    return f"{clipped}\u2026"


def parse_bio(path: Path, config: SiteConfig, *, display_path: str | None = None) -> tuple[Bio, list[Problem]]:
    """Parse and validate a single bio file.

    Always returns a renderable :class:`Bio`. ``problems`` is empty only when
    the file needed no repair; a caller that wants strictness (``validate``)
    treats a non-empty list as a failure, and one that wants the site to stay
    up (``build``) renders the bio anyway.
    """
    rel = display_path or path.as_posix()
    problems: list[Problem] = []

    def report(message: str) -> None:
        problems.append(Problem(rel, message))

    slug = slugify(path.stem) or "student"
    data: dict[object, object] = {}
    text = ""

    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        report("file is not valid UTF-8 text - re-save it as UTF-8")
    except OSError as exc:
        report(f"could not read file - {exc}")

    if not FILENAME.match(path.name):
        report(
            "filename must be lowercase 'firstname-lastname.yml' "
            "(letters, digits and hyphens only)"
        )

    if text:
        if LEADING_TAB.search(text):
            report("indented with a tab - YAML only allows spaces, so replace tabs with two spaces")
        try:
            loaded = yaml.safe_load(text.lstrip("\ufeff"))
        except yaml.YAMLError as exc:
            report(_yaml_message(exc))
        else:
            if loaded is None:
                report("file is empty - start from bios/TEMPLATE.yml")
            elif isinstance(loaded, dict):
                data = loaded
            else:
                report("file must be a list of 'key: value' fields - start from bios/TEMPLATE.yml")
    elif not problems:
        report("file is empty - start from bios/TEMPLATE.yml")

    for key in sorted(str(key) for key in set(data) - ALLOWED_KEYS):
        report(f"unknown key {key!r} - allowed keys are: {', '.join(sorted(ALLOWED_KEYS))}")

    # name -------------------------------------------------------------------
    name = _as_text(data.get("name"))
    if not name:
        if "name" in data:
            report("'name' must be text, e.g. 'name: Jane Doe'")
        else:
            report("missing required key 'name'")
        name = name_from_filename(path)
    else:
        expected_filename = f"{slugify(name)}.yml"
        if path.name != expected_filename:
            report(f"filename must be {expected_filename!r} to match name {name!r}")

    # team -------------------------------------------------------------------
    team_name = _as_text(data.get("team"))
    team = config.team(team_name) if team_name else None
    if team is None:
        if not team_name:
            report("missing required key 'team'")
        else:
            report(
                f"team {team_name!r} is not one of the course teams - use one of: "
                f"{', '.join(config.team_names)}"
            )
        team_label = config.fallback_team.name
    else:
        team_label = team.name

    # headline ---------------------------------------------------------------
    headline = _as_text(data.get("headline"))
    if not headline:
        report("missing required key 'headline'")
        headline = FALLBACK_HEADLINE
    elif len(headline) > HEADLINE_MAX:
        report(f"headline is {len(headline)} characters - keep it under {HEADLINE_MAX}")
        headline = _truncate(headline, HEADLINE_MAX)

    # focus ------------------------------------------------------------------
    focus_raw = data.get("focus") or []
    focus: list[str] = []
    if isinstance(focus_raw, str):
        report("'focus' must be a YAML list, e.g. '- Python'")
    elif isinstance(focus_raw, list):
        for item in focus_raw:
            value = _as_text(item)
            if not value:
                report("'focus' entries must be short strings")
                continue
            if len(value) > FOCUS_ITEM_MAX:
                report(f"focus entry {value!r} is too long - keep each under {FOCUS_ITEM_MAX} characters")
                continue
            focus.append(value)
        if len(focus) > FOCUS_MAX:
            report(f"'focus' has {len(focus)} entries - keep at most {FOCUS_MAX}")
            focus = focus[:FOCUS_MAX]
    else:
        report("'focus' must be a YAML list of short strings")

    # links ------------------------------------------------------------------
    links_raw = data.get("links") or {}
    links: list[Link] = []
    if isinstance(links_raw, dict):
        for label, url in links_raw.items():
            label_text = _as_text(label)
            url_text = _as_text(url)
            if not label_text or not url_text:
                report("each link needs a label and a URL")
                continue
            if not url_text.startswith(("http://", "https://", "mailto:")):
                report(f"link {label_text!r} must start with 'https://' (got {url_text!r})")
                continue
            links.append(Link(label=label_text, url=url_text))
    else:
        report("'links' must be a mapping of label to URL, e.g. 'GitHub: https://github.com/you'")

    # avatar -----------------------------------------------------------------
    avatar = _as_text(data.get("avatar"))
    if avatar and not avatar.startswith(("http://", "https://")):
        report("'avatar' must be an https URL, or leave it out for a monogram")
        avatar = None

    # about ------------------------------------------------------------------
    about = data.get("about")
    if isinstance(about, (dict, list)):
        report(f"'about' must be a block of text, written as:\n{_ABOUT_SHAPE}")
        about = None
    about = _as_text(about)
    if not about:
        report(f"missing required key 'about', written as:\n{_ABOUT_SHAPE}")
        about = FALLBACK_ABOUT
    else:
        if UNSAFE_HTML.search(about):
            report("remove embedded HTML/JavaScript - 'about' is Markdown only")
            about = UNSAFE_HTML.sub("", about).strip() or FALLBACK_ABOUT
        if len(about) < ABOUT_MIN:
            report(f"'about' is {len(about)} characters - write at least {ABOUT_MIN} (a sentence or two)")
        elif len(about) > ABOUT_MAX:
            report(f"'about' is {len(about)} characters - trim it to under {ABOUT_MAX}")
            about = _truncate(about, ABOUT_MAX)

    body_html, repaired = _render_about(about)
    if repaired:
        report(
            "part of 'about' renders as a code block instead of prose - indent every line "
            "exactly two spaces under 'about: |' and drop any ``` fences"
        )

    bio = Bio(
        slug=slug,
        name=name,
        team=team_label,
        headline=headline,
        body_html=body_html,
        source=rel,
        pronouns=_as_text(data.get("pronouns")),
        location=_as_text(data.get("location")),
        fun_fact=_as_text(data.get("fun_fact")),
        avatar=avatar,
        focus=tuple(focus),
        links=tuple(links),
        salvaged=bool(problems),
    )
    return bio, problems


def load_bios(bios_dir: Path, config: SiteConfig) -> tuple[tuple[Bio, ...], tuple[Problem, ...]]:
    """Load every ``bios/*.yml`` file: whatever is present makes up the site."""
    problems: list[Problem] = []
    if not bios_dir.is_dir():
        return (), (Problem(bios_dir.as_posix(), "bios directory not found"),)

    bios: list[Bio] = []
    seen: set[str] = set()
    for path in sorted(bios_dir.glob("*.y*ml")):
        if path.name in RESERVED_FILES:
            continue
        bio, file_problems = parse_bio(path, config, display_path=path.as_posix())
        problems.extend(file_problems)

        if bio.slug in seen:
            # Two files that slug to the same page would silently overwrite each
            # other, so keep both and let the duplicate be visibly reported.
            suffix = 2
            while f"{bio.slug}-{suffix}" in seen:
                suffix += 1
            problems.append(
                Problem(bio.source, f"another file already renders /{bio.slug}/ - rename one of them")
            )
            bio = replace(bio, slug=f"{bio.slug}-{suffix}", salvaged=True)
        seen.add(bio.slug)
        bios.append(bio)

    bios.sort(key=lambda item: item.sort_key)
    return tuple(bios), tuple(problems)

