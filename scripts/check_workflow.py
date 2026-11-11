#!/usr/bin/env python3
"""Validate a PR's branch, linked issue and publication messages using read-only gh calls."""

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
AREA_LABELS = {
    "tskbcknd": "back",
    "tskfrntnd": "front",
    "tskdvps": "devops",
    "tskai": "ai",
    "tskdata": "data",
    "tskdocs": "docs",
}
BRANCH = re.compile(
    r"^(feat|bug|fix)/(tskbcknd|tskfrntnd|tskdvps|tskai|tskdata|tskdocs)-"
    r"([1-9][0-9]*)-([a-z0-9]+(?:-[a-z0-9]+)*)$"
)
ISSUE = re.compile(r"^Issue:\s*#([1-9][0-9]*)\s*$", re.MULTILINE)
ATTRIBUTION = re.compile(
    r"co-authored-by\s*:[^\n]*(?:claude|codex|anthropic|openai|copilot|cursor|gemini|"
    r"gpt|aider|assistant|agent|\bbot\b)|"
    r"(?:generated|written|authored|implemented)\s+(?:with|by)\s+"
    r"(?:[^\n]{0,40})(?:claude|codex|copilot|cursor|gemini|gpt|aider|AI\b)|"
    r"\bAI[- ](?:assisted|generated)\b|"
    r"(?:создано|сгенерировано|написано|разработано)\s+(?:с помощью\s+)?"
    r"(?:claude|codex|copilot|cursor|gemini|ИИ\b)|"
    r"^\s*(?:🤖\s*)?(?:powered by|assisted by)\s+[^\n]+",
    re.IGNORECASE | re.MULTILINE,
)


def validate(
    pr: dict[str, Any],
    issue: dict[str, Any],
    commits: list[dict[str, Any]],
    team: dict[str, Any],
    repo: str,
) -> list[str]:
    errors: list[str] = []
    base, head = pr["base"]["ref"], pr["head"]["ref"]
    # Never allow a fork branch merely named dev/main to impersonate release/sync refs.
    same_repo = (pr["head"].get("repo") or {}).get("full_name") == repo
    release = same_repo and base == "main" and head == "dev"
    sync = same_repo and base == "dev" and head == "main"
    branch = BRANCH.fullmatch(head)
    if base not in {"main", "dev"}:
        errors.append("Base must be dev (task) or main (release)")
    if base == "main" and not release:
        errors.append("Only this repository's dev may target main")
    if base == "dev" and not sync and not branch:
        errors.append("Task branch must match type/area-issue-slug")
    numbers = ISSUE.findall(pr.get("body") or "")
    if len(numbers) != 1:
        errors.append("PR body must contain exactly one line: Issue: #N")
    elif branch and not release and not sync and int(branch[3]) != int(numbers[0]):
        errors.append("Branch issue number differs from PR Issue line")
    if numbers and int(issue.get("number", 0)) != int(numbers[0]):
        errors.append("Fetched issue differs from PR Issue line")
    if issue.get("pull_request"):
        errors.append("The task must reference an issue, not another PR")
    if issue.get("state") != "open":
        errors.append("Linked issue must remain open until acceptance")
    owners = {owner["login"] for owner in issue.get("assignees", [])}
    if not owners:
        errors.append("Issue requires a human assignee")
    registered = {entry["github"]: entry for entry in team.values() if entry.get("github")}
    if owners and not owners <= registered.keys():
        errors.append("Issue assignees must be registered in docs/team.json")
    labels = {label["name"] for label in issue.get("labels", [])}
    if release or sync:
        if not {"release", "devops"} <= labels:
            errors.append("Release and sync require release + devops issue labels")
    elif branch:
        label = AREA_LABELS[branch[2]]
        if label not in labels:
            errors.append(f"Issue requires the branch area label: {label}")
        if (
            label != "docs"
            and owners
            and not any(label in registered.get(owner, {}).get("areas", []) for owner in owners)
        ):
            errors.append("No issue assignee owns the branch area in docs/team.json")
    messages = [("PR title", pr.get("title") or ""), ("PR body", pr.get("body") or "")]
    messages.extend(
        (f"commit {commit['sha'][:8]}", commit["commit"]["message"]) for commit in commits
    )
    for source, message in messages:
        if ATTRIBUTION.search(message):
            errors.append(f"Remove tool attribution from {source}")
    return errors


def gh_json(*args: str) -> Any:
    return json.loads(subprocess.check_output(["gh", *args], cwd=ROOT, text=True))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--pr", type=int, required=True)
    args = parser.parse_args()
    pr = gh_json("api", f"repos/{args.repo}/pulls/{args.pr}")
    numbers = ISSUE.findall(pr.get("body") or "")
    if len(numbers) != 1:
        raise SystemExit("PR body must contain exactly one line: Issue: #N")
    issue = gh_json("api", f"repos/{args.repo}/issues/{numbers[0]}")
    pages = gh_json("api", f"repos/{args.repo}/pulls/{args.pr}/commits", "--paginate", "--slurp")
    commits = [commit for page in pages for commit in page]
    errors = validate(
        pr, issue, commits, json.loads((ROOT / "docs/team.json").read_text()), args.repo
    )
    if errors:
        raise SystemExit("Workflow policy failed:\n- " + "\n- ".join(errors))
    print(f"Workflow policy passed for {args.repo}#{args.pr}")


if __name__ == "__main__":
    main()
