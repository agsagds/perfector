"""Regression test for the Gradio theme/css wiring (issue #5, PR #6).

Gradio 6 moved `theme`/`css` off the `gr.Blocks()` constructor. There are several
ways the Space can be served, and the theme must survive all of them:

  - run as __main__ (`python app.py`, HF Spaces): launch() gets explicit args.
  - imported and launched by another runner with NO args (the `gradio` CLI reload
    runner, and possibly HF's launcher): only the constructor's `_deprecated_*`
    shim re-applies the theme at launch() time.

This test reproduces the *second*, riskier model — import the app, then call a bare
`launch()` ourselves — and asserts the served config is still themed. A bare
constructor (theme/css only on launch()) fails this test; the belt-and-suspenders
wiring in app.py passes it.
"""

import os
import socket
import sys
import unittest
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Keep the launch() offline — no telemetry network calls.
os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")

import app  # noqa: E402


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class AppThemeTests(unittest.TestCase):
    def test_served_config_is_themed_via_bare_launch(self):
        """Import + bare launch() (no theme args) must still serve our theme/css."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            app.demo.launch(prevent_thread_lock=True, server_port=_free_port(), quiet=True)
        try:
            cfg = app.demo.get_config_file()
        finally:
            app.demo.close()

        self.assertIsNotNone(
            cfg.get("theme"),
            "served config has no theme — theme/css must be on the Blocks "
            "constructor so the _deprecated_* shim survives an argless launch()",
        )
        self.assertIn(
            "block-info",
            cfg.get("css") or "",
            "served config is missing _PAGE_CSS (the uppercase mono label rules)",
        )

    def test_theme_toggle_js_handlers_are_wired(self):
        """The toggle's click + the load-time label sync must reach the config.

        Both are JS-only handlers (fn=None, js=...). If either is dropped, the
        theme button stops working or its label desyncs — a silent regression a
        unit test won't otherwise catch. Mirrors the theme-wiring guard above.
        """
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            app.demo.launch(prevent_thread_lock=True, server_port=_free_port(), quiet=True)
        try:
            cfg = app.demo.get_config_file()
        finally:
            app.demo.close()

        js_blobs = [d.get("js") or "" for d in cfg.get("dependencies", [])]
        self.assertTrue(
            any("classList.toggle('dark')" in js for js in js_blobs),
            "served config is missing the theme-toggle click handler",
        )
        self.assertTrue(
            any("localStorage.getItem('pa-theme')" in js for js in js_blobs),
            "served config is missing the load-time theme-init handler",
        )


if __name__ == "__main__":
    unittest.main()
