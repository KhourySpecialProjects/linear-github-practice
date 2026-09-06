# Student Quickstart

Follow this page start to finish during class. It is the whole exercise: one
Linear issue, one branch, one file, one pull request, one review, one merge.

The workflow rules themselves live in the playbooks — this page only tells you
what to do in *this* repository, and links to the playbook for each step. Every
playbook link goes to
[KhourySpecialProjects/practicum-playbooks](https://github.com/KhourySpecialProjects/practicum-playbooks).
That repo is private, so if a link 404s for you, you have not been granted
access yet — say so and it will be fixed.

[Developer Expectations](https://github.com/KhourySpecialProjects/practicum-playbooks/blob/main/developer-expectations.md) is
the source of truth for branches, commits, PRs and review. If this page and that
page ever disagree, that page wins.

## Goal

Add `bios/firstname-lastname.yml` for yourself, get it reviewed and merged into
`testing`, and see it appear on the deployed site.

The file is a YAML file — structured `key: value` data. Only one field,
`about`, is prose, and that prose is Markdown.

## One thing that differs from the playbooks

The playbooks describe four environments — Local, Testing, Staging, Production —
because that is what a real client project uses. This teaching repo has only
**`testing`**: it is the default branch, it is protected, and Coolify deploys it.
There is no `staging`, no `production`, and no `main` here. You branch from
`testing` and you pull-request back into `testing`.

## Checklist

- [ ] Linear issue "Add bio for &lt;Your Name&gt;" assigned to you
- [ ] Branch created from Linear's **Copy git branch name**
- [ ] `bios/firstname-lastname.yml` written and previewed locally
- [ ] PR open into `testing`, CI green, assigned reviewer requested
- [ ] You reviewed the PR you were assigned
- [ ] Squash-merged, Linear issue in **Done**, site rebuilt

## Steps

### 1. Claim your issue

Open the LGH project in Linear, find **Add bio for &lt;Your Name&gt;**, assign it to
yourself, and read the description — it names **the person you must request as
your reviewer**. Playbook: [Start an Issue](https://github.com/KhourySpecialProjects/practicum-playbooks/blob/main/start-an-issue.md).

### 2. Copy the branch name from Linear

On the issue, click **Copy git branch name**. You get something like
`lgh-12-add-bio-for-jane-doe`. Do not invent your own name: the `lgh-12` part is
what moves the issue through Todo -> In Progress -> In Review -> Done.

### 3. Start the branch from an up-to-date `testing`

```sh
git switch testing
git pull
git switch -c lgh-12-add-bio-for-jane-doe   # paste YOUR name from Linear
git push -u origin HEAD
```

Check Linear: the issue should now be **In Progress** with the branch linked.

### 4. Create your file

```sh
cp bios/TEMPLATE.yml bios/jane-doe.yml      # use YOUR name
```

The filename must be the slug of your `name` field: "Jane Doe" ->
`bios/jane-doe.yml`. The extension is `.yml`, not `.yaml`. See
[`bios/README.md`](../bios/README.md) for the filename rule and the full field
table.

### 5. Fill it in

Open your file and edit it. Nothing needs deleting to make it parse — the
template is valid YAML as it ships, and the `#` lines are YAML comments.

- Set `name` and `headline` (90 characters maximum), and set `team` to the one
  named on your Linear issue. It must match a team in
  [`../site.yml`](../site.yml) — as shipped: Team Falcon, Team Kestrel, Team
  Osprey, Team Harrier, Team Merlin, Team Goshawk, Team Kite, Team Caracara,
  Team Peregrine, Team Condor, Team Eagle. Case does not matter; spelling does.
- Replace the `about` text with 40–2000 characters about you. Keep the
  `about: |` line and keep your text indented two spaces under it; it is
  rendered as Markdown, so `**bold**`, links and `-` lists work.
- Uncomment any optional fields you want (`pronouns`, `location`, `focus`,
  `links`, `avatar`, `fun_fact`) and leave the rest commented out.

The result looks like this:

```yaml
name: Jane Doe
team: Team Falcon
headline: Backend engineer who likes boring infrastructure
about: |
  I work on **APIs** and the boring infrastructure underneath them. Most
  recently I built a rate limiter that nobody has had to think about since.

  - Comfortable in Python and Go
  - Learning Kubernetes the hard way
focus:
  - Python
  - Postgres
links:
  GitHub: https://github.com/janedoe
```

### 6. Preview locally

With Docker, from the repository root:

```sh
docker compose up --build
```

Open http://localhost:8088 and find your card. `Ctrl-C` stops it.

Two things that trip people up here:

- **Keep `--build`.** The site is baked into the image, so a plain
  `docker compose up` serves the previous build and your card will be missing.
- **Port already allocated?** Something else on your machine owns 8088. Run
  `SITE_PORT=9090 docker compose up --build` and open that port instead.

Without Docker:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m generator serve      # http://localhost:8000
```

Rules only, no browser:

```sh
python -m generator validate
```

You want `1 bio file(s) valid.` — or however many files are in the folder.

### 7. Commit and push

```sh
git add bios/jane-doe.yml
git commit -m "Add bio for Jane Doe"
git push
```

Imperative mood, one file. Playbook:
[Working on Your Branch](https://github.com/KhourySpecialProjects/practicum-playbooks/blob/main/working-on-your-branch.md).

### 8. Open the pull request

On GitHub, open a PR with **base = `testing`**, compare = your branch. The PR
template fills in the checklist; tick it honestly. The Linear issue links itself
because the branch carries `lgh-12`. Playbook:
[Open a Pull Request](https://github.com/KhourySpecialProjects/practicum-playbooks/blob/main/open-a-pull-request.md).

Then, in the **Reviewers** panel, request **the reviewer named on your Linear
issue**. Not a friend, not whoever is nearest — the assigned one.

### 9. Review the PR you were assigned

You are also somebody's reviewer. The roster is a ring: student *n* reviews
student *n+1*, and the last student reviews the first. Open their PR, read
**Files changed**, and check:

- the file has `name`, `team`, `headline` and `about`; `team` is one of the
  teams listed in `site.yml`
- the filename matches their name and ends in `.yml`
- `about` reads professionally and is a sentence or two, not a placeholder
- no files outside `bios/` were touched

Approve when it is good enough to ship. Playbook:
[Reviewing a Pull Request](https://github.com/KhourySpecialProjects/practicum-playbooks/blob/main/reviewing-a-pull-request.md).

### 10. Address feedback, then squash and merge

Fix or reply to every comment, push, resolve the threads, re-request review.
When you have one approval and green CI, use **Squash and merge**, then
**Delete branch**. Playbook:
[Respond to Review and Merge](https://github.com/KhourySpecialProjects/practicum-playbooks/blob/main/respond-to-review-and-merge.md).

### 11. Confirm Linear and watch the deploy

The merge moves your issue to **Done** automatically. Coolify sees the push to
`testing` and rebuilds; within a minute or two your card is on the deployed site
(the instructor will give you the URL). Then:

```sh
git switch testing
git pull
```

## If something goes wrong

**CI is red.** Open the PR, go to **Files changed**, and read the annotation
attached to your file. It names the exact fix, for example
`bios/jane-d.yml: filename must be 'jane-doe.yml' to match name 'Jane Doe'`. Run
`python -m generator validate` locally to see the same message. Fix, commit,
push — the PR re-runs itself.

**A tab in your indentation.** YAML does not allow tabs anywhere in the
indentation, and most editors insert one if you press Tab:

```
bios/jane-doe.yml: indented with a tab - YAML only allows spaces, so replace tabs with two spaces
```

**An unquoted value containing `': '`.** A colon followed by a space starts a
new key as far as YAML is concerned, so
`headline: Backend engineer: infrastructure` fails:

```
bios/jane-doe.yml: invalid YAML at line 3: mapping values are not allowed here - a value containing ': ' must be wrapped in quotes
```

Wrap the whole value in quotes:
`headline: "Backend engineer: infrastructure"`.

**You saved it as `.yaml`.** The extension is `.yml`. A `.yaml` file is
reported as `filename must be lowercase 'firstname-lastname.yml' (letters,
digits and hyphens only)` rather than being silently skipped.

**Your card shows up under "Unassigned", or with placeholder text where your
headline or bio should be.** The generator could not read part of your file, so
it substituted fallback values: a `team` that does not match `site.yml` lands
in a trailing **Unassigned** group, a missing `headline` renders as
`Bio still needs a headline`, and an unreadable `about` renders a placeholder
telling readers to run the validator. The site stays up so one bad file does
not hide everybody's cards. It does not let you off: `validate` fails on every
one of those substitutions, so CI is still red and the fix is still yours. Run
`python -m generator validate`, fix what it names, push.

**Merge conflict.** You should not get one. Your PR adds one brand-new file that
nobody else touches, and `site.yml` is instructor-owned, so there is no shared
file to collide on. If you somehow do have a conflict, you probably edited
someone else's bio or a repo file — undo that; see
[Working on Your Branch](https://github.com/KhourySpecialProjects/practicum-playbooks/blob/main/working-on-your-branch.md).

**You started on the wrong branch** (you edited files while on `testing`, and
have not committed). Take the work with you:

```sh
git switch -c lgh-12-add-bio-for-jane-doe
```

If you already committed to the wrong branch, ask the instructor before
rewriting anything.

**Your reviewer is stuck or absent.** Say so out loud; the instructor approves
so you are not blocked.

## Verification

- [ ] `python -m generator validate` exits without problems
- [ ] Your card appears at http://localhost:8088 (or `:8000` without Docker)
- [ ] The PR is base `testing`, one file changed, CI green, one approval
- [ ] The PR you were assigned has your submitted review on it
- [ ] The Linear issue is in **Done** and the branch is deleted
- [ ] Your page is live on the deployed site

## Definition of done

Your bio is merged into `testing`, you approved someone else's bio, your Linear
issue is **Done**, and the deployed site shows your card. All six boxes above
ticked.
