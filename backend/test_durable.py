import gzip, tempfile, unittest
from pathlib import Path
from durable import DurableState, StateConflict
from engine import Engine


class ProviderError(Exception):
    def __init__(self, code):
        self.code = code


class Blob:
    def __init__(self):
        self.data = None
        self.generation = 0

    def reload(self, **kw):
        if self.data is None:
            raise ProviderError(404)

    def download_as_bytes(self, if_generation_match, **kw):
        if if_generation_match != self.generation:
            raise ProviderError(412)
        return self.data

    def upload_from_filename(self, path, if_generation_match, **kw):
        if if_generation_match != self.generation:
            raise ProviderError(412)
        self.data = Path(path).read_bytes()
        self.generation += 1


class DurableTests(unittest.TestCase):
    def test_restart_retains_reviews_and_connections(self):
        with tempfile.TemporaryDirectory() as folder:
            blob = Blob()
            first = DurableState(blob, folder + "/one.db")
            e = first.open()
            e.set("project_repos", [{"repo": "owner/code", "commits": []}])
            e.db.commit()
            f = e.launch("banking")["finding"]
            e.action("ignore", f["id"])
            first.persist(e)
            other = DurableState(blob, folder + "/two.db")
            restored = other.open()
            self.assertEqual(restored.finding()["status"], "ignored")
            self.assertEqual(restored.bank_summary()["mismatches"], 200)
            self.assertEqual(restored.get("project_repos")[0]["repo"], "owner/code")
            e.db.close()
            restored.db.close()

    def test_conflicting_revision_cannot_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            blob = Blob()
            a = DurableState(blob, folder + "/a.db")
            ea = a.open()
            b = DurableState(blob, folder + "/b.db")
            eb = b.open()
            ea.set("winner", "a")
            ea.db.commit()
            a.persist(ea)
            eb.set("winner", "b")
            eb.db.commit()
            with self.assertRaises(StateConflict):
                b.persist(eb)
            eb = b.refresh(eb, force=True)
            self.assertEqual(eb.get("winner"), "a")
            ea.db.close()
            eb.db.close()

    def test_no_ambient_identity(self):
        import os
        from unittest.mock import patch
        from cloud_identity import credentials, configured

        with patch.dict(
            os.environ,
            {"GCP_PROJECT": "work", "GOOGLE_APPLICATION_CREDENTIALS": "/work"},
            clear=True,
        ):
            self.assertFalse(configured())
            with self.assertRaises(ValueError):
                credentials()


class PublicAccessTests(unittest.TestCase):
    def test_public_demo_does_not_expose_owner_state(self):
        from public_demo import connections, dashboard
        import os
        from unittest.mock import patch

        with patch.dict(
            os.environ, {"IMPACTGUARD_SHOPIFY_TOKEN": "private-token"}, clear=True
        ):
            info = connections("security")
            self.assertEqual(info["repos"], [])
            self.assertFalse(info["credentials"]["shopify"])
            self.assertNotIn("private-token", str(info))
        self.assertEqual(dashboard("checkout")["deployment"]["access"], "public")

    def test_anonymous_cannot_be_owner(self):
        from access import owner
        from unittest.mock import patch
        import os

        with patch.dict(os.environ, {"IMPACTGUARD_PUBLIC_PREVIEW": "1"}, clear=True):
            self.assertFalse(owner({}))
            self.assertFalse(owner({"Authorization": "Bearer malformed"}))

    def test_cached_demo_analysis_does_not_call_model(self):
        from public_demo import analysis

        class State:
            def get(self, key, default):
                return {
                    "checkout": {
                        "summary": "Generated evidence",
                        "provider": "Vertex AI",
                    }
                }

        result = analysis(State(), "checkout")
        self.assertTrue(result["cached"])
        self.assertEqual(result["mode"], "synthetic")
