# Student Quickstart

Follow this page start to finish during class. It is the whole exercise: one
Linear issue, one branch, one file, one pull request, one review, one merge.

The workflow rules themselves live in the playbooks — this page only tells you
what to do in *this* repository, and links to the playbook for each step. The
playbooks are the sibling repo `practicum-playbooks` (also published to you
separately); links below assume it is cloned next to this one.

[Developer Expectations](../../practicum-playbooks/developer-expectations.md) is
the source of truth for branches, commits, PRs and review. If this page and that
page ever disagree, that page wins.

## Goal

Add `bios/firstname-lastname.md` for yourself, get it reviewed and merged into
`testing`, and see it appear on the deployed site.

## One thing that differs from the playbooks

The playbooks describe four environments — Local, Testing, Staging, Production —
because that is what a real client project uses. This teaching repo has only
**`testing`**: it is the default branch, it is protected, and Coolify deploys it.
There is no `staging`, no `production`, and no `main` here. You branch from
`testing` and you pull-request back into `testing`.

## Checklist

- [ ] Linear issue "Add bio for &lt;Your Name&gt;" assigned to you
- [ ] Branch created from Linear's **Copy git branch name**
- [ ] `bios/firstname-lastname.md` written and previewed locally
- [ ] PR open into `testing`, CI green, assigned reviewer requested
- [ ] You reviewed the PR you were assigned
- [ ] Squash-merged, Linear issue in **Done**, site rebuilt

## Steps

### 1. Claim your issue

Open the LGH project in Linear, find **Add bio for &lt;Your Name&gt;**, assign it to
yourself, and read the description — it names **the person you must request as
your reviewer**. Playbook: [Start an Issue](../../practicum-playbooks/start-an-issue.md).

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
cp bios/TEMPLATE.md bios/jane-doe.md        # use YOUR name
```

The filename must be the slug of your `name` field: "Jane Doe" ->
`bios/jane-doe.md`. See [`bios/README.md`](../bios/README.md) for the filename
rule and the full field table.

### 5. Fill it in

Open your file and edit it:

- **Delete the HTML comment on line 1.** Your file must start with `---` on
  line 1 or validation fails with "no frontmatter found".
- Set `name`, `team` (Team Falcon, Team Kestrel, Team Osprey or Team Harrier)
  and `headline` (90 characters maximum).
- Uncomment any optional fields you want, delete the rest.
- Replace the body with 40–2000 characters of Markdown about you.

### 6. Preview locally

With Docker, from the repository root:

```sh
docker compose up --build
```

Open http://localhost:8080 and find your card. `Ctrl-C` stops it.

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
git add bios/jane-doe.md
git commit -m "Add bio for Jane Doe"
git push
```

Imperative mood, one file. Playbook:
[Working on Your Branch](../../practicum-playbooks/working-on-your-branch.md).

### 8. Open the pull request

On GitHub, open a PR with **base = `testing`**, compare = your branch. The PR
template fills in the checklist; tick it honestly. The Linear issue links itself
because the branch carries `lgh-12`. Playbook:
[Open a Pull Request](../../practicum-playbooks/open-a-pull-request.md).

Then, in the **Reviewers** panel, request **the reviewer named on your Linear
issue**. Not a friend, not whoever is nearest — the assigned one.

### 9. Review the PR you were assigned

You are also somebody's reviewer. The roster is a ring: student *n* reviews
student *n+1*, and the last student reviews the first. Open their PR, read
**Files changed**, and check:

- frontmatter has `name`, `team`, `headline`; team is one of the four
- the filename matches their name
- the body reads professionally and is a sentence or two, not a placeholder
- no files outside `bios/` were touched

Approve when it is good enough to ship. Playbook:
[Reviewing a Pull Request](../../practicum-playbooks/reviewing-a-pull-request.md).

### 10. Address feedback, then squash and merge

Fix or reply to every comment, push, resolve the threads, re-request review.
When you have one approval and green CI, use **Squash and merge**, then
**Delete branch**. Playbook:
[Respond to Review and Merge](../../practicum-playbooks/respond-to-review-and-merge.md).

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
`bios/jane-d.md: filename must be 'jane-doe.md' to match name 'Jane Doe'`. Run
`python -m generator validate` locally to see the same message. Fix, commit,
push — the PR re-runs itself.

**Merge conflict.** You should not get one. Your PR adds one brand-new file that
nobody else touches, and `site.yml` is instructor-owned, so there is no shared
file to collide on. If you somehow do have a conflict, you probably edited
someone else's bio or a repo file — undo that; see
[Working on Your Branch](../../practicum-playbooks/working-on-your-branch.md).

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
- [ ] Your card appears at http://localhost:8080 (or `:8000` without Docker)
- [ ] The PR is base `testing`, one file changed, CI green, one approval
- [ ] The PR you were assigned has your submitted review on it
- [ ] The Linear issue is in **Done** and the branch is deleted
- [ ] Your page is live on the deployed site

## Definition of done

Your bio is merged into `testing`, you approved someone else's bio, your Linear
issue is **Done**, and the deployed site shows your card. All six boxes above
ticked.
