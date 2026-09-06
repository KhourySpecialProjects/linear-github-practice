# Linear + GitHub Practice: Bio Aggregator

A professional bio aggregator for the practicum. Every student adds one YAML
file to `bios/`, and the site is regenerated from whatever files exist at build
time — one card on the home page and one detail page per person.

The point is not the site. The point is the workflow: one Linear issue, one
branch, one pull request, one peer review, one squash merge, one automatic
deploy.

## 60-second quickstart

```sh
git clone git@github.com:KhourySpecialProjects/linear-github-practice.git
cd linear-github-practice
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
file and the fix.

## How the site is built

`bios/*.yml` + `site.yml` -> Jinja2 templates -> `dist/` -> nginx.

The build reads every `bios/*.yml` (skipping `TEMPLATE.yml`), validates it,
groups bios by the teams declared in `site.yml`, and writes `dist/index.html`,
`dist/404.html`, `dist/<slug>/index.html` and `dist/assets/**`. Whatever files
are present at build time are the site — there is no database and no state. A
broken bio fails the build rather than shipping a broken page.

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
  instructor-setup.md        one-time GitHub, Linear and Coolify setup
generator/                   the static site generator (instructor-owned; students never edit)
  __main__.py                the validate / build / serve commands
  bios.py                    parsing and validation rules for one bio file
  config.py                  loads site.yml
  render.py                  renders dist/ from the templates
  templates/                 base, index, bio and 404 Jinja templates
  static/                    CSS and assets, copied to dist/assets/
scripts/roster.py            generates Linear issue text and the review ring from a roster CSV
roster.example.csv           the roster CSV shape: name,github,team
site.yml                     site title, tagline, footer and the four teams (instructor-owned)
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
  Coolify auto-deploys. There is no `staging`, `production` or `main` here.
- Work happens on a branch named by Linear's **Copy git branch name**
  (`lgh-12-add-bio-for-jane-doe`), which is pull-requested into `testing` and
  squash-merged after one approval and green CI.
- Merging to `testing` triggers the Coolify webhook, which rebuilds and
  redeploys the site.

The playbooks describe the full Local -> Testing -> Staging -> Production
promotion path used on real client projects. This teaching repo deliberately
stops at the first deployed environment.

## Documentation

- [Student quickstart](docs/student-quickstart.md) — do the exercise, start to finish
- [In-class exercise runbook](docs/in-class-exercise.md) — instructor timeline and failure modes
- [Instructor setup](docs/instructor-setup.md) — repo, Linear and Coolify configuration
- [`bios/README.md`](bios/README.md) — the bio file contract in two minutes

Workflow playbooks (sibling repo, also published to students separately):

- [Developer Expectations](https://github.com/KhourySpecialProjects/practicum-playbooks/blob/main/developer-expectations.md) — the source of truth
- [Start an Issue](https://github.com/KhourySpecialProjects/practicum-playbooks/blob/main/start-an-issue.md)
- [Working on Your Branch](https://github.com/KhourySpecialProjects/practicum-playbooks/blob/main/working-on-your-branch.md)
- [Open a Pull Request](https://github.com/KhourySpecialProjects/practicum-playbooks/blob/main/open-a-pull-request.md)
- [Reviewing a Pull Request](https://github.com/KhourySpecialProjects/practicum-playbooks/blob/main/reviewing-a-pull-request.md)
- [Respond to Review and Merge](https://github.com/KhourySpecialProjects/practicum-playbooks/blob/main/respond-to-review-and-merge.md)
- [Environments & Deployment](https://github.com/KhourySpecialProjects/practicum-playbooks/blob/main/environments-and-deployment.md)
