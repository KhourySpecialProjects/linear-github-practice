# bios/

One YAML file per person. Whatever files are in this folder at build time are
the site. Add yours; do not edit anyone else's.

The file is **data**, not a document: every field is a `key: value` pair. Only
one field, `about`, holds prose — and that prose is Markdown, so bold, links,
inline code and lists work inside it.

`TEMPLATE.yml` is a reserved name — the loader skips it, so it never shows up on
the site. This README is not picked up at all: the loader only reads YAML files.

## Filename rule

Lowercase `firstname-lastname.yml`, letters, digits and hyphens only, and it
must match the slug of your `name` field.

| Your `name` | Filename |
|---|---|
| Jane Doe | `bios/jane-doe.yml` |
| José Álvarez | `bios/jose-alvarez.yml` |
| Mary Jo Van Buren | `bios/mary-jo-van-buren.yml` |

The name must contain at least one hyphen after slugifying, so `bios/jane.yml`
is rejected. Accents are folded to plain ASCII (`José` -> `jose`). The extension
is `.yml`, not `.yaml` — a `.yaml` file is reported as a filename error rather
than silently ignored.

## Shape

The whole file is one YAML mapping. There is no `---` fence and no Markdown
document body:

```yaml
name: Jane Doe
team: Team Falcon
headline: Backend engineer who likes boring infrastructure
about: |
  I work on **APIs** and the boring infrastructure underneath them. Most
  recently I built a rate limiter that nobody has had to think about since.

  - Comfortable in Python and Go
  - Learning Kubernetes the hard way
pronouns: she/her
location: Boston, MA
focus:
  - Python
  - Postgres
links:
  GitHub: https://github.com/janedoe
  Email: mailto:jane@example.com
avatar: https://example.com/jane.jpg
fun_fact: Has opinions about the correct number of terminal tabs.
```

## Fields

| Key | Type | Required | Limits |
|---|---|---|---|
| `name` | string | yes | filename must equal its slug + `.yml` |
| `team` | string | yes | one of Team Falcon, Team Kestrel, Team Osprey, Team Harrier (case-insensitive) |
| `headline` | string | yes | 90 characters maximum |
| `about` | Markdown block scalar (`about: \|`) | yes | 40–2000 characters; script/iframe/object/embed tags and javascript URLs are rejected |
| `pronouns` | string | no | — |
| `location` | string | no | — |
| `focus` | YAML list | no | at most 6 entries, each at most 24 characters |
| `links` | mapping label -> URL | no | each URL must start with `https://`, `http://` or `mailto:` |
| `avatar` | string | no | `http://` or `https://` URL; use a square image around 400px on a host that allows hotlinking. Omit it for an initials monogram, which is also the fallback if the URL fails to load |
| `fun_fact` | string | no | — |

Any key that is not in that table is a validation error. Copy
[`TEMPLATE.yml`](./TEMPLATE.yml) and you start with the shape already correct.

### About `about`

`about` is the one prose field, written as a block scalar: `about: |` on its own
line, then your text indented by two spaces. Everything indented under it is
yours, blank lines included. It is rendered as Markdown, so `**bold**`,
`` `code` ``, `[links](https://example.com)` and `-` lists all work.

## If you get it wrong

CI runs `python -m generator validate`, which names your file and the fix. A
failing run looks like this:

```
1 problem(s) found in bios/:
  bios/jane-d.yml: filename must be 'jane-doe.yml' to match name 'Jane Doe'

Fix the files listed above, then re-run: python -m generator validate
```

The two mistakes YAML punishes hardest:

- **A tab anywhere in the indentation.** YAML does not accept tabs at all:

  ```
  bios/jane-doe.yml: indented with a tab - YAML only allows spaces, so replace tabs with two spaces
  ```

- **An unquoted value containing `': '`.** A colon-space inside a value starts a
  new key as far as YAML is concerned, so
  `headline: Backend engineer: infrastructure` fails:

  ```
  bios/jane-doe.yml: invalid YAML at line 3: mapping values are not allowed here - a value containing ': ' must be wrapped in quotes
  ```

  Wrap the whole value in quotes:
  `headline: "Backend engineer: infrastructure"`.

Two more worth knowing: a `.yaml` extension is rejected with the
`filename must be lowercase 'firstname-lastname.yml'` message, and an `about`
written as nested keys instead of a `|` block gets
`'about' must be a block of text, written as:` followed by the two-line shape to
copy.

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
If something already owns 8088, use `SITE_PORT=9090 docker compose up --build`.

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
