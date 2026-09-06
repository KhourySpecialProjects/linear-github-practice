# bios/

One Markdown file per person. Whatever files are in this folder at build time
are the site. Add yours; do not edit anyone else's.

This README and `TEMPLATE.md` are reserved names — the loader skips them, so
they never show up on the site.

## Filename rule

Lowercase `firstname-lastname.md`, letters, digits and hyphens only, and it must
match the slug of your `name` field.

| Your `name` | Filename |
|---|---|
| Jane Doe | `bios/jane-doe.md` |
| Jose Alvarez | `bios/jose-alvarez.md` |
| Mary Jo Van Buren | `bios/mary-jo-van-buren.md` |

The name must contain at least one hyphen after slugifying, so `bios/jane.md`
is rejected. Accents are folded to plain ASCII (`José` -> `jose`).

## Fields

Frontmatter first (between two `---` lines, starting on line 1), then the
Markdown body.

| Key | Type | Required | Limits |
|---|---|---|---|
| `name` | string | yes | filename must equal its slug + `.md` |
| `team` | string | yes | one of Team Falcon, Team Kestrel, Team Osprey, Team Harrier (case-insensitive) |
| `headline` | string | yes | 90 characters maximum |
| `pronouns` | string | no | — |
| `location` | string | no | — |
| `focus` | YAML list | no | at most 6 entries, each at most 24 characters |
| `links` | mapping label -> URL | no | each URL must start with `https://`, `http://` or `mailto:` |
| `avatar` | string | no | `http://` or `https://` URL; use a square image around 400px on a host that allows hotlinking. Omit it for an initials monogram, which is also the fallback if the URL fails to load |
| `fun_fact` | string | no | — |
| body | Markdown | yes | 40–2000 characters; script/iframe/object/embed tags and javascript URLs are rejected |

Any key that is not in that table is a validation error. Copy
[`TEMPLATE.md`](./TEMPLATE.md) and you start with the shape already correct.

## If you get it wrong

CI runs `python -m generator validate`, which names your file and the fix. A
failing run looks like this:

```
1 problem(s) found in bios/:
  bios/jane-d.md: filename must be 'jane-doe.md' to match name 'Jane Doe'

Fix the files listed above, then re-run: python -m generator validate
```

On a pull request the same message appears as an inline annotation on your file
in the **Files changed** tab. Fix it on your branch, commit, push — the PR and
CI update themselves.

## Preview before you push

With Docker, from the repository root:

```sh
docker compose up --build
```

Open http://localhost:8088. Stop with `Ctrl-C`. Keep `--build` — the site is
baked into the image, so a plain `docker compose up` re-serves the last build.

Without Docker:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m generator serve
```

Open http://localhost:8000. To check only the rules, without a browser:

```sh
python -m generator validate
```

## Why this never conflicts

Your pull request adds exactly one new file that nobody else touches, so two
students merging at the same time cannot conflict. `site.yml` (title, teams,
accents) is instructor-owned for the same reason — nobody has to edit a shared
file to add themselves.

Full walkthrough: [`../docs/student-quickstart.md`](../docs/student-quickstart.md).
