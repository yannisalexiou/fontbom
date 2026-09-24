"""Command-line interface."""

from __future__ import annotations

import sys
import time
from pathlib import Path

import click

from fontbom import __version__
from fontbom.inputs.limits import ArchiveError, Limits
from fontbom.models import ScanResult, Status
from fontbom.report import FORMATS, render
from fontbom.scanner import Progress, ScanOptions, default_jobs, scan

FAIL_ON_CHOICES: tuple[str, ...] = (*(s.value for s in Status), "unreferenced")

EXIT_CLEAN = 0
EXIT_POLICY = 1
EXIT_ERROR = 2


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, prog_name="fontbom")
def main() -> None:
    """Scan app binaries and codebases for bundled fonts and report their license status."""


@main.command("scan")
@click.argument("path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "-f",
    "--format",
    "fmt",
    type=click.Choice(FORMATS),
    default=None,
    help="Report format. Default: terminal when stdout is a terminal, otherwise json.",
)
@click.option(
    "-o",
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Write the report here instead of stdout.",
)
@click.option(
    "--fail-on",
    default="",
    help="Comma-separated statuses that make the exit code 1: " + ", ".join(FAIL_ON_CHOICES) + ".",
)
@click.option(
    "--max-depth",
    type=int,
    default=Limits.max_depth,
    show_default=True,
    help="Maximum archive nesting depth.",
)
@click.option(
    "--max-bytes",
    type=int,
    default=Limits.max_total_bytes,
    show_default=True,
    help="Maximum total bytes extracted from archives.",
)
@click.option(
    "--max-entries",
    type=int,
    default=Limits.max_entries,
    show_default=True,
    help="Maximum number of archive members.",
)
@click.option("--no-references", is_flag=True, help="Skip code reference scanning.")
@click.option(
    "-j",
    "--jobs",
    type=click.IntRange(min=1),
    default=default_jobs,
    show_default="number of CPUs",
    help="Worker processes for searching large binaries.",
)
@click.option(
    "--progress/--no-progress",
    default=None,
    help="Show a live status line on stderr. Default: on when stderr is a terminal.",
)
@click.option("-q", "--quiet", is_flag=True, help="Do not print the summary line or progress.")
def scan_command(
    path: Path,
    fmt: str | None,
    output: Path | None,
    fail_on: str,
    max_depth: int,
    max_bytes: int,
    max_entries: int,
    no_references: bool,
    jobs: int,
    progress: bool | None,
    quiet: bool,
) -> None:
    """Scan PATH: a directory, .ipa, .app, .apk, .aab, .xcframework or .zip."""
    policies = parse_fail_on(fail_on)
    if "unreferenced" in policies and no_references:
        raise click.UsageError("--fail-on unreferenced cannot be combined with --no-references")

    options = ScanOptions(
        limits=Limits(max_depth=max_depth, max_total_bytes=max_bytes, max_entries=max_entries),
        references=not no_references,
        jobs=jobs,
    )
    show_progress = not quiet and (progress if progress is not None else sys.stderr.isatty())
    status = StatusLine(sys.stderr) if show_progress else None
    try:
        result = scan(path, options, on_progress=status.update if status else None)
    except ArchiveError as exc:
        if status:
            status.clear()
        click.echo(f"error: {exc}", err=True)
        sys.exit(EXIT_ERROR)
    finally:
        if status:
            status.clear()

    to_terminal = output is None and sys.stdout.isatty()
    if fmt is None:
        fmt = "terminal" if to_terminal else "json"
    report = render(result, fmt, color=fmt == "terminal" and to_terminal)
    if output is None:
        click.echo(report, nl=False)
    else:
        output.write_text(report)

    # The terminal format already shows the summary; repeating it on stderr is noise.
    if not quiet and not (fmt == "terminal" and output is None):
        click.echo(summary_line(result, output), err=True)

    violations = policy_violations(result, policies)
    if violations:
        for line in violations:
            click.echo(f"fail-on: {line}", err=True)
        sys.exit(EXIT_POLICY)


def parse_fail_on(value: str) -> set[str]:
    policies = {item.strip().lower() for item in value.split(",") if item.strip()}
    invalid = sorted(policies - set(FAIL_ON_CHOICES))
    if invalid:
        raise click.BadParameter(
            f"unknown value(s) {', '.join(invalid)}; choose from {', '.join(FAIL_ON_CHOICES)}",
            param_hint="--fail-on",
        )
    return policies


def summary_line(result: ScanResult, output: Path | None = None) -> str:
    s = result.summary
    parts = [f"{s['fonts']} fonts"]
    parts.extend(f"{s[status.value]} {status.value}" for status in Status if s[status.value])
    parts.append(f"{s['unreferenced']} unreferenced")
    if s["unbundled_references"]:
        parts.append(f"{s['unbundled_references']} referenced but not bundled")
    if output is not None:
        parts.append(f"report written to {output}")
    return "fontbom: " + ", ".join(parts)


class StatusLine:
    """A single in-place status line on a stream, redrawn at most ten times a second."""

    SPINNER = "|/-\\"
    INTERVAL = 0.1
    WIDTH = 100

    def __init__(self, stream: object) -> None:
        self.stream = stream
        self.started = time.monotonic()
        self.last_draw = 0.0
        self.ticks = 0
        self.dirty = False

    def update(self, event: Progress) -> None:
        now = time.monotonic()
        if event.phase != "done" and now - self.last_draw < self.INTERVAL:
            return
        self.last_draw = now
        self.ticks += 1
        spinner = self.SPINNER[self.ticks % len(self.SPINNER)]
        elapsed = now - self.started
        text = (
            f"{spinner} {event.phase:<12} {event.files:>7} files  {event.fonts:>4} fonts  "
            f"{elapsed:5.1f}s  {_shorten(event.current, 40)}"
        )
        self._write("\r" + text[: self.WIDTH].ljust(self.WIDTH))
        self.dirty = True

    def clear(self) -> None:
        if self.dirty:
            self._write("\r" + " " * self.WIDTH + "\r")
            self.dirty = False

    def _write(self, text: str) -> None:
        click.echo(text, err=True, nl=False)


def _shorten(text: str, width: int) -> str:
    return text if len(text) <= width else "…" + text[-(width - 1) :]


def policy_violations(result: ScanResult, policies: set[str]) -> list[str]:
    lines: list[str] = []
    for record in result.fonts:
        label = record.primary.family or record.paths[0]
        status = record.license.status.value
        if status in policies:
            lines.append(f"{label} is {status} ({record.paths[0]})")
        if "unreferenced" in policies and not record.referenced:
            lines.append(f"{label} is bundled but unreferenced ({record.paths[0]})")
    return lines
