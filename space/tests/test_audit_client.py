"""Unit tests for the inference-backend dispatch in audit_client."""

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import audit_client as ac  # noqa: E402
from prompts import FEW_SHOT_ASSISTANT  # noqa: E402

_ENV_KEYS = (
    "MODAL_AUDIT_URL",
    "MODAL_AUDIT_ENDPOINT",
    "MODAL_AUDIT_TOKEN",
    "OLLAMA_MODEL",
    "OLLAMA_URL",
    "OLLAMA_TIMEOUT",
)


class BackendDispatchTests(unittest.TestCase):
    def setUp(self):
        import os

        self._saved = {k: os.environ.pop(k, None) for k in _ENV_KEYS}
        self._orig_chat = ac._ollama_chat

    def tearDown(self):
        import os

        ac._ollama_chat = self._orig_chat
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_backend_label_matrix(self):
        import os

        self.assertIn("mock", ac.backend_label())
        os.environ["OLLAMA_MODEL"] = "gemma4:e4b"
        self.assertIn("Ollama", ac.backend_label())
        self.assertIn("gemma4:e4b", ac.backend_label())
        os.environ["MODAL_AUDIT_URL"] = "https://x.modal.run"  # Modal wins over Ollama
        self.assertIn("Modal", ac.backend_label())

    def test_mock_when_no_backend_configured(self):
        out = ac.call_modal_audit("Telegram", "g", "a", "a post draft")
        self.assertIsInstance(out, dict)
        self.assertIn("auditReport", out)

    def test_ollama_path_builds_messages_and_parses(self):
        import os

        os.environ["OLLAMA_MODEL"] = "gemma4:e4b"
        captured = {}

        def fake_chat(model, messages, timeout):
            captured["model"] = model
            captured["roles"] = [m["role"] for m in messages]
            return FEW_SHOT_ASSISTANT

        ac._ollama_chat = fake_chat
        out = ac.call_modal_audit("Telegram", "Register for webinar", "PMs", "Webinar link in bio")
        self.assertEqual(captured["model"], "gemma4:e4b")
        self.assertEqual(captured["roles"], ["system", "user", "assistant", "user"])
        self.assertIn("GOAL_ACTION_MISMATCH", out["auditReport"]["goalAlignment"]["cappedBy"])

    def test_ollama_retries_once_on_bad_json(self):
        import os

        os.environ["OLLAMA_MODEL"] = "gemma4:e4b"
        calls = {"n": 0}

        def flaky_chat(model, messages, timeout):
            calls["n"] += 1
            return "not json at all" if calls["n"] == 1 else FEW_SHOT_ASSISTANT

        ac._ollama_chat = flaky_chat
        out = ac.call_modal_audit("Telegram", "g", "a", "p")
        self.assertEqual(calls["n"], 2)  # first bad → one retry
        self.assertIsNotNone(out.get("auditReport"))

    def test_ollama_gives_up_after_retry(self):
        import os

        os.environ["OLLAMA_MODEL"] = "gemma4:e4b"
        ac._ollama_chat = lambda model, messages, timeout: "still not json"
        with self.assertRaises((ValueError, json.JSONDecodeError)):
            ac.call_modal_audit("Telegram", "g", "a", "p")

    def test_timeouts_from_env(self):
        import os

        self.assertEqual(ac.get_modal_timeout(), 300.0)
        self.assertEqual(ac.get_ollama_timeout(), 300.0)
        os.environ["OLLAMA_TIMEOUT"] = "42"
        self.assertEqual(ac.get_ollama_timeout(), 42.0)


if __name__ == "__main__":
    unittest.main()
