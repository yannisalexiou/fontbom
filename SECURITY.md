# Security policy

fontbom reads untrusted input: app archives, font files and source trees, often from third
parties. A bug in how it handles that input can be a security problem, even though fontbom runs
locally and never uses the network.

## Supported versions

Only the latest release receives security fixes.

## Reporting a vulnerability

Don't open a public issue. Report it privately through GitHub's
[private vulnerability reporting](https://github.com/yannisalexiou/fontbom/security/advisories/new),
which is the **Report a vulnerability** button on the repository's **Security** tab.

Include:

- the fontbom version (`fontbom --version`), Python version and operating system
- the command you ran and what happened
- how to reproduce it, ideally with a short script that builds the input, for example with
  fontTools' `FontBuilder` and Python's `zipfile`

Only attach a file if you have the right to share it. Never send proprietary fonts or app
binaries that belong to someone else; a script that builds an equivalent input is enough.

## What happens next

- You get an acknowledgement within 7 days.
- Once the problem is confirmed, a fix is released and a GitHub security advisory is published.
  You are credited unless you'd rather not be.
- Please allow up to 90 days from your report before disclosing it publicly.

## Scope

In scope, for example:

- **Files outside the scan.** An archive member, nested archive or symlink that makes fontbom
  read, write or delete files outside the input and its temporary working directory.
- **Getting past the limits.** A crafted archive that gets around `--max-depth`, `--max-bytes`
  or `--max-entries`, or exhausts disk, memory or time in a way those limits should prevent.
- **Report injection.** Font names and other metadata come from the font file, so whoever made
  the font controls them. Metadata that reaches a report as terminal control sequences, a
  spreadsheet formula in CSV, or links or HTML in Markdown is a vulnerability.
- **Network access.** fontbom promises to work fully offline. Any code path that opens a network
  connection is a vulnerability.
- **Code execution** triggered by any input.

Out of scope:

- A wrong license status, a missed font or a missed code reference. Use the issue templates.
- Scans that are slow or use a lot of disk but stay within the configured limits.
- Vulnerabilities in fontTools, click or Python itself. Report those upstream. If fontbom could
  avoid or contain the problem, report that part here.
