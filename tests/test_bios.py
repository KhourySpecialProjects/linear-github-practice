"""Tests for the validator contract that gates every student pull request.

The exercise lives or dies on `python -m generator validate` telling a student
exactly what to fix, so these tests assert on the *problems* a bad bio file
produces (by substring, so wording can be improved without breaking the suite)
and on the values a template is allowed to read off a good one.
"""

from __future__ import annotations

import textwrap

import pytest

from generator.bios import BODY_MAX, BODY_MIN, Link, load_bios, parse_bio
from generator.config import ConfigError, SiteConfig
from generator.text import hue_for, initials, slugify

SITE_YML = """\
title: Practicum Bios
tagline: One file per teammate
course: Khoury Practicum
footer: Northeastern University
teams:
  - name: Team Falcon
    tagline: Fast feedback
    accent: "#7c5cff"
  - name: Team Kestrel
    tagline: Calm releases
    accent: "#00b6a4"
"""

BODY = "Backend engineer who likes boring infrastructure and thorough code review."


@pytest.fixture
def config(tmp_path):
    """A real SiteConfig, loaded from YAML, so the loader is exercised too."""
    path = tmp_path / "site.yml"
    path.write_text(SITE_YML, encoding="utf-8")
    return SiteConfig.load(path)


@pytest.fixture
def bios_dir(tmp_path):
    directory = tmp_path / "bios"
    directory.mkdir()
    return directory


def write_bio(directory, filename: str, frontmatter: str, body: str = BODY):
    """Write one bio file the way a student would, and return its path."""
    path = directory / filename
    meta = textwrap.dedent(frontmatter).strip("\n")
    path.write_text(f"---\n{meta}\n---\n\n{body}\n", encoding="utf-8")
    return path


def messages(problems) -> str:
    """All problem messages joined, for substring assertions."""
    return "\n".join(problem.message for problem in problems)


def test_valid_bio_exposes_the_values_templates_read(bios_dir, config):
    path = write_bio(
        bios_dir,
        "jane-doe.md",
        """
        name: Jane Doe
        team: team falcon
        headline: Backend engineer who likes boring infrastructure
        pronouns: she/her
        location: Boston, MA
        avatar: https://example.com/jane.png
        fun_fact: Keeps a sourdough starter named after a database.
        focus:
          - Python
          - Postgres
        links:
          GitHub: https://github.com/janedoe
          Email: mailto:doe.j@northeastern.edu
        """,
        body="Backend engineer with a **bias for small pull requests** and clear commits.",
    )

    bio, problems = parse_bio(path, config)

    assert problems == []
    assert bio is not None
    assert bio.name == "Jane Doe"
    # The team name is canonicalised to site.yml's spelling, not the student's.
    assert bio.team == "Team Falcon"
    assert bio.slug == "jane-doe"
    assert bio.url == "/jane-doe/"
    assert bio.headline == "Backend engineer who likes boring infrastructure"
    assert bio.pronouns == "she/her"
    assert bio.location == "Boston, MA"
    assert bio.avatar == "https://example.com/jane.png"
    assert bio.fun_fact.startswith("Keeps a sourdough starter")
    assert bio.focus == ("Python", "Postgres")
    assert bio.links == (
        Link(label="GitHub", url="https://github.com/janedoe"),
        Link(label="Email", url="mailto:doe.j@northeastern.edu"),
    )
    assert "<p>" in bio.body_html
    assert "<strong>bias for small pull requests</strong>" in bio.body_html
    assert bio.initials == "JD"


def test_missing_frontmatter_block_is_reported(bios_dir, config):
    path = bios_dir / "jane-doe.md"
    path.write_text("Just some prose, no frontmatter delimiters at all.\n", encoding="utf-8")

    bio, problems = parse_bio(path, config)

    assert bio is None
    assert "no frontmatter" in messages(problems)


def test_missing_required_key_names_the_key(bios_dir, config):
    path = write_bio(
        bios_dir,
        "jane-doe.md",
        """
        name: Jane Doe
        team: Team Falcon
        """,
    )

    bio, problems = parse_bio(path, config)

    assert bio is None
    assert "missing required frontmatter key 'headline'" in messages(problems)


def test_unknown_key_is_rejected_and_lists_the_allowed_keys(bios_dir, config):
    path = write_bio(
        bios_dir,
        "jane-doe.md",
        """
        name: Jane Doe
        team: Team Falcon
        headline: Backend engineer
        twitter: janedoe
        """,
    )

    bio, problems = parse_bio(path, config)

    assert bio is None
    text = messages(problems)
    assert "unknown frontmatter key 'twitter'" in text
    assert "fun_fact" in text  # the allowed-key list is spelled out for the student


def test_unknown_team_lists_the_course_teams(bios_dir, config):
    path = write_bio(
        bios_dir,
        "jane-doe.md",
        """
        name: Jane Doe
        team: Team Penguin
        headline: Backend engineer
        """,
    )

    bio, problems = parse_bio(path, config)

    assert bio is None
    text = messages(problems)
    assert "not one of the course teams" in text
    assert "Team Falcon" in text
    assert "Team Kestrel" in text


def test_filename_must_match_the_name_field(bios_dir, config):
    path = write_bio(
        bios_dir,
        "jane-d.md",
        """
        name: Jane Doe
        team: Team Falcon
        headline: Backend engineer
        """,
    )

    bio, problems = parse_bio(path, config)

    assert bio is None
    text = messages(problems)
    assert "jane-doe.md" in text
    assert "Jane Doe" in text


@pytest.mark.parametrize("filename", ["Jane-Doe.md", "jane doe.md", "jane_doe.md", "jane.md"])
def test_filename_must_be_lowercase_hyphenated(bios_dir, config, filename):
    path = write_bio(
        bios_dir,
        filename,
        """
        name: Jane Doe
        team: Team Falcon
        headline: Backend engineer
        """,
    )

    bio, problems = parse_bio(path, config)

    assert bio is None
    assert "filename must be lowercase" in messages(problems)


def test_body_shorter_than_the_minimum_is_rejected(bios_dir, config):
    short = "Too short."
    assert len(short) < BODY_MIN
    path = write_bio(
        bios_dir,
        "jane-doe.md",
        """
        name: Jane Doe
        team: Team Falcon
        headline: Backend engineer
        """,
        body=short,
    )

    bio, problems = parse_bio(path, config)

    assert bio is None
    assert f"at least {BODY_MIN}" in messages(problems)


def test_body_of_exactly_the_minimum_length_is_valid(bios_dir, config):
    exact = "Exactly the minimum length of bio prose."
    assert len(exact) == BODY_MIN
    path = write_bio(
        bios_dir,
        "jane-doe.md",
        """
        name: Jane Doe
        team: Team Falcon
        headline: Backend engineer
        """,
        body=exact,
    )

    bio, problems = parse_bio(path, config)

    assert problems == []
    assert bio is not None


def test_body_longer_than_the_maximum_is_rejected(bios_dir, config):
    path = write_bio(
        bios_dir,
        "jane-doe.md",
        """
        name: Jane Doe
        team: Team Falcon
        headline: Backend engineer
        """,
        body="word " * (BODY_MAX // 2),
    )

    bio, problems = parse_bio(path, config)

    assert bio is None
    assert f"under {BODY_MAX}" in messages(problems)


def test_link_without_a_scheme_is_rejected(bios_dir, config):
    path = write_bio(
        bios_dir,
        "jane-doe.md",
        """
        name: Jane Doe
        team: Team Falcon
        headline: Backend engineer
        links:
          GitHub: github.com/janedoe
        """,
    )

    bio, problems = parse_bio(path, config)

    assert bio is None
    text = messages(problems)
    assert "GitHub" in text
    assert "https://" in text


def test_raw_script_in_the_body_is_rejected(bios_dir, config):
    path = write_bio(
        bios_dir,
        "jane-doe.md",
        """
        name: Jane Doe
        team: Team Falcon
        headline: Backend engineer
        """,
        body="Backend engineer. <script>alert('hi')</script> And some more prose here.",
    )

    bio, problems = parse_bio(path, config)

    assert bio is None
    assert "HTML/JavaScript" in messages(problems)


def test_load_bios_skips_the_reserved_documentation_files(bios_dir, config):
    (bios_dir / "TEMPLATE.md").write_text("---\nnot: a bio\n---\n\nCopy me.\n", encoding="utf-8")
    (bios_dir / "README.md").write_text("# How to add your bio\n", encoding="utf-8")
    write_bio(
        bios_dir,
        "jane-doe.md",
        """
        name: Jane Doe
        team: Team Falcon
        headline: Backend engineer
        """,
    )

    bios, problems = load_bios(bios_dir, config)

    assert problems == ()
    assert [bio.slug for bio in bios] == ["jane-doe"]


def test_load_bios_sorts_by_family_name(bios_dir, config):
    for filename, name in (
        ("jane-zebra.md", "Jane Zebra"),
        ("ada-apple.md", "Ada Apple"),
        ("bo-mango.md", "Bo Mango"),
    ):
        write_bio(
            bios_dir,
            filename,
            f"""
            name: {name}
            team: Team Falcon
            headline: Backend engineer
            """,
        )

    bios, problems = load_bios(bios_dir, config)

    assert problems == ()
    assert [bio.name for bio in bios] == ["Ada Apple", "Bo Mango", "Jane Zebra"]


def test_load_bios_accumulates_problems_from_every_bad_file(bios_dir, config):
    write_bio(
        bios_dir,
        "jane-doe.md",
        """
        name: Jane Doe
        team: Team Falcon
        headline: Backend engineer
        """,
    )
    write_bio(
        bios_dir,
        "bad-team.md",
        """
        name: Bad Team
        team: Team Penguin
        headline: Backend engineer
        """,
    )
    write_bio(
        bios_dir,
        "no-headline.md",
        """
        name: No Headline
        team: Team Falcon
        """,
    )

    bios, problems = load_bios(bios_dir, config)

    # The valid file still loads, and neither bad file hides the other.
    assert [bio.slug for bio in bios] == ["jane-doe"]
    assert {problem.path.rsplit("/", 1)[-1] for problem in problems} == {
        "bad-team.md",
        "no-headline.md",
    }


def test_slugify_folds_accents_to_the_expected_filename():
    assert slugify("José Álvarez") == "jose-alvarez"


def test_initials_fall_back_to_a_single_letter():
    assert initials("José Álvarez") == "JÁ"
    assert initials("Prince") == "P"


def test_hue_is_stable_across_processes():
    # Pinned rather than compared to itself: a per-process salted hash (or a
    # changed algorithm) would churn the generated CSS between deploys.
    assert hue_for("jane-doe") == 276
    assert hue_for("ada-lovelace") == 145


def test_site_config_without_teams_is_a_config_error(tmp_path):
    path = tmp_path / "site.yml"
    path.write_text("title: No Teams Here\n", encoding="utf-8")

    with pytest.raises(ConfigError):
        SiteConfig.load(path)
