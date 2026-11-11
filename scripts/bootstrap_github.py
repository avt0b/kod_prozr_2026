#!/usr/bin/env python3
"""Create missing project labels and dev from main; preserve existing labels/refs."""

import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def gh(*args: str) -> str:
    return subprocess.check_output(["gh", *args], cwd=ROOT, text=True).strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", help="OWNER/REPO; defaults to this checkout's GitHub repository")
    args = parser.parse_args()
    repo = args.repo or gh("repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner")
    gh("api", "user", "--jq", ".login")  # Fail before mutation if not authenticated.
    pages = json.loads(gh("api", f"repos/{repo}/labels", "--paginate", "--slurp"))
    existing = {label["name"] for page in pages for label in page}
    for label in json.loads((ROOT / ".github/labels.json").read_text()):
        if label["name"] in existing:
            print(f"Preserved label: {label['name']}")
            continue
        gh(
            "label",
            "create",
            label["name"],
            "--repo",
            repo,
            "--color",
            label["color"],
            "--description",
            label["description"],
        )
        print(f"Created label: {label['name']}")
    pages = json.loads(gh("api", f"repos/{repo}/branches", "--paginate", "--slurp"))
    branches = {branch["name"]: branch["commit"]["sha"] for page in pages for branch in page}
    if "dev" in branches:
        print("Preserved existing dev branch")
    else:
        if "main" not in branches:
            raise SystemExit("main is missing; no branch was created")
        gh(
            "api",
            f"repos/{repo}/git/refs",
            "--method",
            "POST",
            "-f",
            "ref=refs/heads/dev",
            "-f",
            f"sha={branches['main']}",
        )
        print("Created dev from main")


if __name__ == "__main__":
    main()
