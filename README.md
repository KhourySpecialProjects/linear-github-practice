# Linear + GitHub Practice: Bio Aggregator

A professional bio aggregator for the practicum. Every student adds one Markdown
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

Open http://localhost:8080. `Ctrl-C` stops it. Add `--watch` to rebuild when
`bios/`, `site.yml` or `generator/` changes.

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

`bios/*.md` + `site.yml` -> Jinja2 templates -> `dist/` -> nginx.

The build reads every `bios/*.md` (skipping `TEMPLATE.md` and `README.md`),
validates it, groups bios by the teams declared in `site.yml`, and writes
`dist/index.html`, `dist/404.html`, `dist/<slug>/index.html` and
`dist/assets/**`. Whatever files are present at build time are the site — there
is no database and no state. A broken bio fails the build rather than shipping a
broken page.

## Repository layout

```
bios/                        one Markdown file per person; add yours, edit nobody else's
  TEMPLATE.md                copy this to bios/firstname-lastname.md
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
docker-compose.yml           local dev on http://localhost:8080
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

- [Developer Expectations](../practicum-playbooks/developer-expectations.md) — the source of truth
- [Start an Issue](../practicum-playbooks/start-an-issue.md)
- [Working on Your Branch](../practicum-playbooks/working-on-your-branch.md)
- [Open a Pull Request](../practicum-playbooks/open-a-pull-request.md)
- [Reviewing a Pull Request](../practicum-playbooks/reviewing-a-pull-request.md)
- [Respond to Review and Merge](../practicum-playbooks/respond-to-review-and-merge.md)
- [Environments & Deployment](../practicum-playbooks/environments-and-deployment.md)
