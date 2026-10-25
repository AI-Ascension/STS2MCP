#!/usr/bin/env python3
"""Prove endpoint inventory and last-route fallback assertions detect regressions."""
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
from pathlib import Path
import tempfile
import unittest

import audit_endpoints


class EndpointContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='sts-endpoints-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        source = Path(__file__).resolve().parents[1]
        for name in ['McpMod.cs', 'README.md', 'docs/raw-full.md']:
            dest = self.root / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text((source / name).read_text())

    def audit(self):
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            audit_endpoints.audit_docs(self.root)

    def test_documented_routes_pass(self):
        self.audit()

    def test_uncoded_fallback_detected_even_in_last_route(self):
        path = self.root / 'McpMod.cs'
        original = path.read_text()
        for route in ['/api/v1/compendium', '/api/v1/wiki']:
            with self.subTest(route=route):
                start = original.index(f'path == "{route}"')
                suffix = original[start:].replace('SendMethodNotAllowed(response);', 'SendError(response, 405, "Method not allowed");', 1)
                path.write_text(original[:start] + suffix)
                with self.assertRaises(SystemExit):
                    self.audit()
        path.write_text(original)

    def test_missing_wiki_index_entry_detected(self):
        path = self.root / 'McpMod.cs'
        path.write_text('\n'.join(line for line in path.read_text().splitlines() if '["path"] = "/api/v1/wiki"' not in line))
        with self.assertRaises(SystemExit):
            self.audit()


if __name__ == '__main__':
    unittest.main()
