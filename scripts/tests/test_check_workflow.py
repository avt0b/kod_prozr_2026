import unittest
from copy import deepcopy

from scripts.check_workflow import validate

REPO = "avt0b/kod_prozr_2026"
TEAM = {"misha": {"github": "1nsanexeEZ", "areas": ["back"]}}


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.pr = {
            "base": {"ref": "dev"},
            "head": {"ref": "feat/tskbcknd-123-appeals-api", "repo": {"full_name": REPO}},
            "title": "B-13: Анализ обращений (#123)",
            "body": "Issue: #123\nРезультат и проверки.",
        }
        self.issue = {
            "number": 123,
            "state": "open",
            "assignees": [{"login": "1nsanexeEZ"}],
            "labels": [{"name": "back"}],
        }
        self.commits = [{"sha": "abc12345", "commit": {"message": "feat: анализ обращений (#123)"}}]

    def check(self):
        return validate(self.pr, self.issue, self.commits, TEAM, REPO)

    def test_valid_task(self):
        self.assertEqual(self.check(), [])

    def test_task_cannot_target_main(self):
        self.pr["base"]["ref"] = "main"
        self.assertTrue(self.check())

    def test_plan_id_cannot_replace_issue_number(self):
        self.pr["head"]["ref"] = "B-13-appeals-api"
        self.assertTrue(self.check())

    def test_number_must_match(self):
        self.pr["body"] = "Issue: #124"
        self.assertTrue(self.check())

    def test_assignee_and_area_required(self):
        self.issue["assignees"] = []
        self.issue["labels"] = []
        self.assertGreaterEqual(len(self.check()), 2)

    def test_unregistered_owner_rejected(self):
        self.issue["assignees"] = [{"login": "unknown"}]
        self.assertTrue(self.check())

    def test_wrong_area_owner_rejected(self):
        self.pr["head"]["ref"] = "feat/tskfrntnd-123-appeals-ui"
        self.issue["labels"] = [{"name": "front"}]
        self.assertTrue(self.check())

    def test_human_coauthor_preserved(self):
        self.commits[0]["commit"]["message"] += "\n\nCo-authored-by: Roman <roman@example.com>"
        self.assertEqual(self.check(), [])

    def test_tool_attribution_rejected_in_all_publication_messages(self):
        for message in (
            "Co-authored-by: Claude <noreply@anthropic.com>",
            "Generated with Codex",
            "AI-assisted implementation",
            "Сгенерировано ИИ",
        ):
            with self.subTest(message=message):
                self.commits[0]["commit"]["message"] = message
                self.assertTrue(self.check())
                self.commits[0]["commit"]["message"] = "fix: message"
                old_body = self.pr["body"]
                self.pr["body"] += "\n" + message
                self.assertTrue(self.check())
                self.pr["body"] = old_body
                old_title = self.pr["title"]
                self.pr["title"] = message
                self.assertTrue(self.check())
                self.pr["title"] = old_title

    def test_release_and_sync_require_release_issue(self):
        self.issue["labels"] = [{"name": "release"}, {"name": "devops"}]
        for base, head in (("main", "dev"), ("dev", "main")):
            self.pr["base"]["ref"], self.pr["head"]["ref"] = base, head
            self.assertEqual(self.check(), [])
        self.issue["labels"] = [{"name": "devops"}]
        self.assertTrue(self.check())

    def test_fork_cannot_impersonate_release(self):
        self.pr["base"]["ref"] = "main"
        self.pr["head"]["ref"] = "dev"
        self.pr["head"]["repo"]["full_name"] = "someone/fork"
        self.issue["labels"] = [{"name": "release"}, {"name": "devops"}]
        self.assertTrue(self.check())

    def test_duplicate_issue_line_rejected(self):
        self.pr["body"] += "\nIssue: #123"
        self.assertTrue(self.check())

    def test_existing_closed_issue_or_pr_rejected(self):
        original = deepcopy(self.issue)
        self.issue["state"] = "closed"
        self.assertTrue(self.check())
        self.issue = original
        self.issue["pull_request"] = {"url": "a-pr"}
        self.assertTrue(self.check())


if __name__ == "__main__":
    unittest.main()
