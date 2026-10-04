# GitHub contributor attribution cleanup

Prepared on 2026-10-02 for `watermelon588/Walkthru` at the founder's request.
Status: **published and verified**. The founder approved the history rewrite;
the atomic, lease-protected push completed on 2026-10-02. GitHub's public
contributors API now lists **only `watermelon588`**, with 111 contributions.

The existing histories contain 23 commits authored and committed as Claude,
plus 80 AI co-author trailers. The prepared histories attribute those AI-tool
commits to the founder's existing Git identity, `Rohit Maity
<maityrohit021@gmail.com>`, and remove only the AI co-author trailers. Existing
human identities remain byte-for-byte unchanged. No Codex author or co-author
attribution was found. These counts cover the 111 commits across all local
branch histories, including the preserved local branch-1 work.

## Exact published branches prepared

| Branch | Current tip | Prepared tip | Commit count |
|---|---|---|---:|
| `main` | `207d6abd4a64aa883e9c0005b187539354e11f87` | `fd76ccc4f974bd11f2de12e4af03316781bde6ec` | 110 |
| `1` | `df101fcfc7650e244c5b45cdcf2e58de5cd1fe22` | `8529fdf863d9dab5e2242db60753a4eef43e79c1` | 60 |
| `claude/practical-hopper-j64i4s` | `86ab3d3aea7d7c758eb97f213ab71104a0eb3b0c` | `5cbfcc06d8bde0772dbd49ec3ff9590da12e25ad` | 94 |

Every one of the 111 inspected commits retains its exact tree hash, which
verifies that every historical file snapshot is unchanged. Parent ordering,
merge structure, author/committer timestamps, and non-attribution message
content are preserved. The local unpublished commit on branch `1` is preserved
in the prepared clone and is excluded from the published branch-1 update.
No branch is deleted or renamed; the branch name containing `claude/` does not
give an account contributor credit.

Rewriting metadata changed all 111 commit IDs and invalidated signatures.
29 signature headers are removed from the rewritten objects. The original
signed objects remain recoverable in the backup. Other clones and active
agent sessions must synchronize with the new history before committing or
pushing, so they do not restore the old attribution.

## Backup and verification

Everything below is inside ignored `evals/results/contributor-cleanup-2026-10-02/`:

- `before.bundle`: verified full backup, 137,303,277 bytes. Contains original
  refs and history, including local unpublished work and Codex checkpoint trees.
- `prepared.git/`: isolated clone retaining the verified rewritten histories.
  Five live branch/remote-tracking refs were synchronized through the commit map.
  The symbolic `origin/HEAD` follows the synchronized `origin/main`.
- `review.json`: complete old/new commit map, per-commit attribution changes,
  original refs, intended published refs and verification totals.
- `prepare.py`: preparation and validation script. It never pushes or edits
  the live checkout. Its resume guard intentionally rejects an already
  rewritten clone; inspect `review.json` instead of rerunning it.

Git object integrity (`git fsck`) passes. All historical tree and parent checks
pass; no AI author/committer identity or AI co-author trailer remains in the
prepared commit graph. Internal checkpoint refs that point to trees are preserved.

An authenticated dry-run atomic push passed for precisely the three branches
above, using explicit `--force-with-lease` expected tips. After founder approval,
live branch tips were rechecked and the actual atomic push succeeded. All three
published tips were verified against the prepared objects. No internal
checkpoint or backup refs were published.

## Future attribution

The local `.claude/settings.json` disables commit and PR attribution using
`attribution.commit` and `attribution.pr` set to empty strings, with the legacy
`includeCoAuthoredBy: false` flag for older versions. `AGENTS.md` now requires
the founder's configured identity for AI-tool work and preserves real human
contributor credit. Only these two files were committed under the founder's
identity in `ef5a6e13ccb42e380ec0c3e2211e69f3f074f91f` and pushed normally to
`main`. That is the final published `main` tip; the table above records the
initial metadata-only rewrite. No AI co-author trailer was added.

## Completed verification

The approved atomic, lease-protected force-push replaced published history
on all three branches. Local refs were then synchronized without checkout,
reset or clean. Before/after hashes verify that staged content, tracked
working changes and all 16 untracked files were preserved during synchronization.
The unpublished local branch-1 commit remains one commit ahead of `origin/1`.
Existing unrelated changes to `.gitignore`, `CURRENT_STATE.md` and the new
launch films were preserved.

The attribution-policy commit changes only `.claude/settings.json` and
`AGENTS.md`; application code is byte-for-byte unchanged from the original
published tree. The public GitHub contributors endpoint returned only
`watermelon588` after publication. The response is saved as
`contributors-after.json` beside the private verification report.

GitHub's contributor displays can take about 24 hours to refresh after history
changes; if they remain incorrect after that, contact GitHub Support.
[GitHub contributor documentation](https://docs.github.com/en/repositories/viewing-activity-and-data-for-your-repository/viewing-a-projects-contributors).

Sources for attribution:
[GitHub co-author trailers](https://docs.github.com/en/pull-requests/how-tos/commit-changes/creating-a-commit-with-multiple-authors),
[Claude Code settings scopes](https://code.claude.com/docs/en/settings),
[Claude Code attribution precedence](https://github.com/anthropics/claude-code/issues/19176).
