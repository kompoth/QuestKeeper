#!/usr/bin/env python3
"""Generate release notes from Conventional Commits for a tag range.

Usage: scripts/release_notes.py <tag> [out_path]

Finds the previous tag (by version sort), collects commits in `<previous>..<tag>`
(or all history if there is no previous tag), and groups commit subjects by
Conventional Commits type into a markdown document.
"""

import re
import subprocess
import sys
from pathlib import Path

TYPE_LABELS = {
    "feat": "Features",
    "fix": "Bug Fixes",
    "perf": "Performance Improvements",
    "revert": "Reverts",
    "refactor": "Code Refactoring",
    "docs": "Documentation",
    "style": "Styles",
    "test": "Tests",
    "build": "Build System",
    "ci": "Continuous Integration",
    "chore": "Chores",
}

TYPE_ORDER = list(TYPE_LABELS)

COMMIT_RE = re.compile(
    rf"^(?P<type>{'|'.join(TYPE_LABELS)})(\((?P<scope>[^)]+)\))?(?P<breaking>!)?: (?P<description>.+)$"
)

BREAKING_FOOTER_RE = re.compile(r"^BREAKING CHANGE:\s*(.+)$", re.MULTILINE)
BULLET_RE = re.compile(r"^[-*]\s+(.+)$")

SEP = "\x1e"
FIELD_SEP = "\x1f"


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout.strip()


def previous_tag(current_tag: str) -> str | None:
    tags = [t for t in git("tag", "--sort=-v:refname").splitlines() if t]
    if current_tag not in tags:
        return None
    index = tags.index(current_tag)
    if index == len(tags) - 1:
        return None
    return tags[index + 1]


def parse_commits(commit_range: str) -> list[tuple[str, str]]:
    log = git("log", commit_range, f"--pretty=format:%s{FIELD_SEP}%b{SEP}")
    if not log:
        return []
    commits = []
    for entry in log.split(SEP):
        entry = entry.strip()
        if not entry:
            continue
        subject, _, body = entry.partition(FIELD_SEP)
        commits.append((subject.strip(), body.strip()))
    return commits


def candidate_lines(subject: str, body: str) -> list[str]:
    lines = [subject]
    for line in body.splitlines():
        match = BULLET_RE.match(line)
        if match:
            lines.append(match.group(1).strip())
    return lines


def build_notes(commits: list[tuple[str, str]]) -> str:
    sections: dict[str, list[str]] = {}
    breaking: list[str] = []

    for subject, body in commits:
        for line in candidate_lines(subject, body):
            match = COMMIT_RE.match(line)
            if not match:
                continue
            commit_type = match.group("type")
            scope = match.group("scope")
            description = match.group("description")
            entry = f"**{scope}:** {description}" if scope else description

            if match.group("breaking"):
                breaking.append(entry)

            sections.setdefault(commit_type, []).append(entry)

        breaking.extend(m.strip() for m in BREAKING_FOOTER_RE.findall(body))

    lines: list[str] = []

    if breaking:
        lines += ["### ⚠ BREAKING CHANGES", ""]
        lines += [f"- {entry}" for entry in breaking]
        lines.append("")

    for commit_type in TYPE_ORDER:
        entries = sections.get(commit_type)
        if not entries:
            continue
        lines += [f"### {TYPE_LABELS[commit_type]}", ""]
        lines += [f"- {entry}" for entry in entries]
        lines.append("")

    if not lines:
        return "_No conventional commits found for this release._\n"

    return "\n".join(lines).strip() + "\n"


def main() -> None:
    if len(sys.argv) not in (2, 3):
        raise SystemExit(__doc__)
    current_tag = sys.argv[1]
    out_path = Path(sys.argv[2]) if len(sys.argv) == 3 else Path("release-notes.md")

    prev_tag = previous_tag(current_tag)
    commit_range = f"{prev_tag}..{current_tag}" if prev_tag else current_tag

    notes = build_notes(parse_commits(commit_range))
    out_path.write_text(notes)

    print(f"Release notes for {current_tag} (range {commit_range}) written to {out_path}:\n")
    print(notes)


if __name__ == "__main__":
    main()
