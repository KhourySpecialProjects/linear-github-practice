# Linear + GitHub Practice: Bio Aggregator

A reusable in-class exercise for teaching a Linear + GitHub workflow. Every
student adds one YAML file to `bios/`, and the site is regenerated from whatever
files exist at build time — one card on the home page and one detail page per
person.

The point is not the site. The point is the workflow: one Linear issue, one
branch, one pull request, one peer review, one squash merge, one automatic
deploy.

The shipped content — site title and tagline, team names, the example bios — is
placeholder content that an adopting instructor replaces; no code depends on it.

## 60-second quickstart

Clone the repository, then from its root:

```sh
docker compose up --build
```

Open http://localhost:8088. `Ctrl-C` stops it. Add `--watch` to rebuild when
`bios/`, `site.yml` or `generator/` changes. Keep `--build`: the site is baked
into the image, so a plain `docker compose up` re-serves the previous build.
If something already owns port 8088, use `SITE_PORT=9090 docker compose up --build`.

## Without Docker

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m generator serve      # build + serve on http://localhost:8000
```

Two other commands, both real:

```sh
python -m generator validate   # check every bio file; this is what CI runs
python -m generator build      # render the site into dist/
```

`validate` exits non-zero and prints one actionable line per problem, naming the
file and the fix. `build` is the forgiving one — see below — and takes
`--strict` when a problem should fail the build instead:

```sh
python -m generator build --strict
python -m generator serve --strict
```

## How the site is built

`bios/*.yml` + `site.yml` -> Jinja2 templates -> `dist/` -> nginx.

The build reads every `bios/*.yml` (skipping `TEMPLATE.yml`), validates it,
groups bios by the teams declared in `site.yml`, and writes `dist/index.html`,
`dist/404.html`, `dist/<slug>/index.html` and `dist/assets/**`. Whatever files
are present at build time are the site — there is no database and no state.

A broken bio does not disappear. `build` substitutes fallback values, prints a
`warning:` line and still exits 0, so one bad file degrades one card instead of
taking the whole site down; the Dockerfile deliberately builds without
`--strict` for that reason. `python -m generator validate`, which CI runs on
every pull request, still fails on every one of those substitutions. Details:
[Instructor setup](docs/instructor-setup.md).

A bio file is structured data: `name`, `team`, `headline` and the optional
fields are plain YAML values. The one prose field is `about`, a YAML block
scalar that is rendered as Markdown.

## Repository layout

```
bios/                        one YAML file per person; add yours, edit nobody else's
  TEMPLATE.yml               copy this to bios/firstname-lastname.yml
  README.md                  the folder's field table and filename rule
docs/
  student-quickstart.md      the page a student follows during class
  in-class-exercise.md       instructor runbook for the 50-minute session
  instructor-setup.md        one-time GitHub, Linear and deployment setup
generator/                   the static site generator (instructor-owned; students never edit)
  __main__.py                the validate / build / serve commands
  bios.py                    parsing and validation rules for one bio file
  config.py                  loads site.yml
  render.py                  renders dist/ from the templates
  templates/                 base, index, bio and 404 Jinja templates
  static/                    CSS and assets, copied to dist/assets/
scripts/roster.py            generates Linear issue text and the review ring from a roster CSV
roster.example.csv           the roster CSV shape: name,github,team
site.yml                     site title, tagline, footer and the team list (instructor-owned)
tests/                       tests for the validation rules
Dockerfile                   build the site, serve it with nginx
deploy/nginx.conf            the nginx config baked into the image
docker-compose.yml           local dev on http://localhost:8088 (override with SITE_PORT)
docker-compose.coolify.yml   what Coolify deploys from the testing branch
.github/workflows/ci.yml     the validate-bios and build-site checks that guard testing
requirements.txt             runtime dependencies
requirements-dev.txt         test dependencies
```

## Branches and deploys

- `testing` is the only long-lived branch: default, protected, and the branch
  that is auto-deployed. There is no `staging`, `production` or `main` here.
- Work happens on a branch named by Linear's **Copy git branch name**
  (`abc-12-add-bio-for-jane-doe`, where `abc-12` is the team key and issue
  number), which is pull-requested into `testing` and squash-merged after one
  approval and green CI.
- Merging to `testing` triggers the deploy webhook, which rebuilds and
  redeploys the site.

One branch is a deliberate choice. Real client projects usually promote a change
through several environments; this exercise stops at the first deployed one so a
50-minute class practises the review loop rather than release plumbing.

## Use this in your course

Fork the repo and replace four things: the identity and team list in `site.yml`;
your roster (`name,github,team`, see `roster.example.csv`) fed to
`python scripts/roster.py roster.csv --ring`; the example bios in `bios/` (keep
`TEMPLATE.yml`); and the deployed URL you hand out in class.
[Instructor setup](docs/instructor-setup.md) covers the rest — GitHub, Linear
and deployment configuration.

## Documentation

- [Student quickstart](docs/student-quickstart.md) — do the exercise, start to finish
- [In-class exercise runbook](docs/in-class-exercise.md) — instructor timeline and failure modes
- [Instructor setup](docs/instructor-setup.md) — repo, Linear and deployment configuration
- [`bios/README.md`](bios/README.md) — the bio file contract in two minutes
