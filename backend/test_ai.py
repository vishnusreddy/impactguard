import os, sys, types, unittest
from unittest.mock import patch
import investigator as ai


class AITests(unittest.TestCase):
    def setUp(self):
        ai._CACHE.clear()
        ai._CALLS = 0

    def call(self, text):
        self.requests = []

        def generate(**kwargs):
            self.requests.append(kwargs)
            return types.SimpleNamespace(text=text)

        client = types.SimpleNamespace(
            models=types.SimpleNamespace(generate_content=generate)
        )
        google = types.ModuleType("google")
        google.__path__ = []
        genai = types.ModuleType("google.genai")
        genai.Client = lambda **kwargs: client
        config = types.ModuleType("google.genai.types")
        config.GenerateContentConfig = lambda **kwargs: kwargs
        genai.types = config
        google.genai = genai
        auth = types.ModuleType("google.auth")
        auth.load_credentials_from_file = lambda *a, **kw: (object(), None)
        oauth = types.ModuleType("google.oauth2")
        oauth.__path__ = []
        account = types.ModuleType("google.oauth2.service_account")
        account.Credentials = types.SimpleNamespace(
            from_service_account_file=lambda *a, **kw: object()
        )
        return patch.dict(
            sys.modules,
            {
                "google": google,
                "google.genai": genai,
                "google.genai.types": config,
                "google.auth": auth,
                "google.oauth2": oauth,
                "google.oauth2.service_account": account,
            },
        )

    def test_cache_redaction_and_no_unmapped_regression(self):
        finding = {"summary": "Decline", "commits": [], "evidence": ["ghp_" + "a" * 36]}
        with self.call(
            '{"classification":"business_regression","summary":"Observed decline","recommended_verification":"Check deployment"}'
        ), patch.dict(
            os.environ,
            {
                "IMPACTGUARD_VERTEX_PROJECT": "personal",
                "IMPACTGUARD_VERTEX_CREDENTIALS": "/explicit/file",
                "GEMINI_MODEL": "test-model",
            },
            clear=True,
        ):
            result = ai.investigate(finding)
            self.assertEqual(result["classification"], "inconclusive")
            self.assertTrue(ai.investigate(finding)["cached"])
        self.assertEqual(len(self.requests), 1)
        self.assertNotIn("ghp_", self.requests[0]["contents"])
        self.assertEqual(self.requests[0]["config"]["max_output_tokens"], 1200)

    def test_invalid_output_rejected(self):
        with self.call('{"classification":"made_up"}'), patch.dict(
            os.environ,
            {
                "IMPACTGUARD_VERTEX_PROJECT": "personal",
                "IMPACTGUARD_VERTEX_CREDENTIALS": "/file",
                "GEMINI_MODEL": "test",
            },
            clear=True,
        ):
            with self.assertRaises(ValueError):
                ai.investigate({"summary": "Test"})
        self.assertEqual(len(ai._CACHE), 0)

    def test_budget_prevents_call(self):
        with patch.dict(
            os.environ,
            {
                "IMPACTGUARD_VERTEX_PROJECT": "personal",
                "IMPACTGUARD_VERTEX_CREDENTIALS": "/file",
                "GEMINI_MODEL": "test",
                "IMPACTGUARD_AI_CALL_LIMIT": "0",
            },
            clear=True,
        ):
            with self.assertRaises(ValueError):
                ai.investigate({"summary": "Test"})
