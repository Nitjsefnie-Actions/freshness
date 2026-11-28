# freshness

A SHA-pinnable GitHub composite action that fails a pull request whose head
lacks a commit of the default branch that touches a file a required check
reads.

A ruleset that does not require branches to be up to date lets a pull request
merge on a green head whose checks ran against a default branch that has since
moved. A commit that lands there touching a file a required check reads is then
never applied to the pull request before it merges, and the merge publishes a
tree no green run ever saw. This action is the one check that compares the two.

## Usage

Pin the action to a reviewed full commit SHA from this repository. The
`# vX.Y.Z` comment after the pin names the reviewed release carrying that
SHA; the version comment is documentation, never the pin itself: do not
substitute a mutable branch or tag.

```yaml
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false
      - uses: Nitjsefnie-Actions/freshness@5edc2a45ff894cf49c5cc8d293bbae0af33507d4 # v1.0.0
```

Put the step in a job the required aggregate already folds: a new job is a new
required context only once the ruleset or the aggregate names it, and a
`paths:` filter on a workflow with a required job stops that check reporting
and blocks every pull request instead.

## What it checks

The action reads the default branch's rules with the job's token and takes the
required status checks from them. It derives, from the head's own workflows,
every file those required jobs read: the jobs they `needs`, the local reusable
workflows they call, and the tracked scripts their steps run, followed through
imports and the files the scripts name. It then fails when the default branch
holds a commit touching one of those files that the head does not contain. It
passes on every other event, and on a `push` to a head the default branch
already holds.

Every required context must still be found in a workflow of the head, as a job
id or a display name, or the run refuses: a job renamed out of every workflow
would otherwise shrink the set in silence. The derivation reads text, so a file
a required check reads without a `run:` block or `with:` value naming it is
outside the set; the header of `scripts/ci/gate_base_freshness.py` lists each
such limit.

The action needs a checkout of the head (it fetches the default branch itself),
Bash and the GitHub CLI `gh` on the runner (GitHub-hosted runners provide
them), and a `python3` on `PATH`. Its Python uses only the standard library.

| Input | Meaning |
| --- | --- |
| `github-token` | Optional token that reads the default branch's rules; defaults to the job's `github.token`. |

## Development and community

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, the exact checks and commit
attribution. Use the shipped issue and PR templates. Participation follows the
[Code of Conduct](CODE_OF_CONDUCT.md). Report vulnerabilities privately as
described in [SECURITY.md](SECURITY.md). Code is [MIT licensed](LICENSE).
