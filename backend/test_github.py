import unittest
from unittest.mock import patch
from github_integration import DEMO_COMMITS, rank_commits, normalize_repo, fetch_commits


class GitHubTests(unittest.TestCase):
    def test_checkout_diff_is_top_candidate(self):
        ranked = rank_commits(DEMO_COMMITS, "checkout")
        self.assertEqual(ranked[0]["sha"][:7], "a8f31c2")
        self.assertGreater(ranked[0]["score"], 0.9)
        self.assertTrue(ranked[0]["eligible"])

    def test_business_changes_rank(self):
        self.assertEqual(
            rank_commits(DEMO_COMMITS, "promotion")[0]["sha"][:7], "c516ee8"
        )
        self.assertEqual(
            rank_commits(DEMO_COMMITS, "delivery")[0]["sha"][:7], "d112a3a"
        )

    def test_future_commit_loses_timing_weight(self):
        commits = [{**DEMO_COMMITS[0], "timestamp": "2026-10-10T15:00:00+00:00"}]
        c = rank_commits(commits, "checkout")[0]
        self.assertEqual(c["factors"]["timing"], 0)
        self.assertFalse(c["eligible"])

    def test_repo_validation(self):
        self.assertEqual(
            normalize_repo("https://github.com/acme/commerce.git"), "acme/commerce"
        )
        for invalid in [
            "https://other.example/foo",
            "../bad/repo",
            "repo",
            "a/b?token=secret",
        ]:
            with self.assertRaises(ValueError):
                normalize_repo(invalid)

    @patch("github_integration.github_get")
    def test_sync_stores_patches(self, get):
        get.side_effect = [
            [
                {
                    "sha": "abc",
                    "commit": {
                        "message": "Fix payment",
                        "author": {"name": "Dev", "date": "2026-10-10T14:00:00Z"},
                    },
                    "html_url": "https://github.com/acme/shop/commit/abc",
                }
            ],
            {
                "files": [
                    {
                        "filename": "src/pay.ts",
                        "additions": 1,
                        "deletions": 1,
                        "patch": "-old\n+new",
                    }
                ]
            },
        ]
        commits = fetch_commits("acme/shop")
        self.assertEqual(commits[0]["files"][0]["patch"], "-old\n+new")
        self.assertEqual(get.call_count, 2)
