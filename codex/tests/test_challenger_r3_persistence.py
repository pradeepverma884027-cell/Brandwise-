"""
Empirical Challenger Test Suite: LocalStorage F5 Persistence & Mirror Parity
Author: teamwork_challenger_r3_h_2
Target: Round 3 PRD Hardening & F5 State Survival
"""

import hashlib
import json
import os
import subprocess
import sys
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


class TestLocalStorageF5PersistenceChallenger(unittest.TestCase):
    """Empirical verification of LocalStorage F5 persistence mechanism and tri-mirror parity."""

    def test_tri_mirror_sha256_cryptographic_parity(self):
        """Verify codex/frontend/index.html, index.html, and docs/index.html are byte-for-byte identical."""
        p_front = os.path.join(REPO_ROOT, 'codex', 'frontend', 'index.html')
        p_root = os.path.join(REPO_ROOT, 'index.html')
        p_docs = os.path.join(REPO_ROOT, 'docs', 'index.html')

        for path in [p_front, p_root, p_docs]:
            self.assertTrue(os.path.exists(path), f"Mirror file not found: {path}")

        with open(p_front, 'rb') as f:
            b_front = f.read()
        with open(p_root, 'rb') as f:
            b_root = f.read()
        with open(p_docs, 'rb') as f:
            b_docs = f.read()

        h_front = hashlib.sha256(b_front).hexdigest()
        h_root = hashlib.sha256(b_root).hexdigest()
        h_docs = hashlib.sha256(b_docs).hexdigest()

        self.assertEqual(len(b_front), len(b_root), "Byte count mismatch between front and root")
        self.assertEqual(len(b_front), len(b_docs), "Byte count mismatch between front and docs")
        self.assertEqual(h_front, h_root, "SHA256 mismatch front vs root")
        self.assertEqual(h_front, h_docs, "SHA256 mismatch front vs docs")
        self.assertEqual(b_front, b_root, "Binary content mismatch front vs root")
        self.assertEqual(b_front, b_docs, "Binary content mismatch front vs docs")

    def test_server_mirror_sha256_parity(self):
        """Verify server.py and codex/server.py are byte-for-byte identical."""
        p_root = os.path.join(REPO_ROOT, 'server.py')
        p_codex = os.path.join(REPO_ROOT, 'codex', 'server.py')

        for path in [p_root, p_codex]:
            self.assertTrue(os.path.exists(path), f"Server file not found: {path}")

        with open(p_root, 'rb') as f:
            b_root = f.read()
        with open(p_codex, 'rb') as f:
            b_codex = f.read()

        h_root = hashlib.sha256(b_root).hexdigest()
        h_codex = hashlib.sha256(b_codex).hexdigest()

        self.assertEqual(len(b_root), len(b_codex), "Byte count mismatch between server.py and codex/server.py")
        self.assertEqual(h_root, h_codex, "SHA256 mismatch server.py vs codex/server.py")
        self.assertEqual(b_root, b_codex, "Binary content differs server.py vs codex/server.py")

    def test_persistence_source_tokens_present(self):
        """Verify all 3 mirrors contain required persistence tokens and hooks."""
        paths = [
            os.path.join(REPO_ROOT, 'codex', 'frontend', 'index.html'),
            os.path.join(REPO_ROOT, 'index.html'),
            os.path.join(REPO_ROOT, 'docs', 'index.html')
        ]
        required_tokens = [
            "BW_WORKSPACE_STORAGE_KEY = 'bw_workspace_state_v3'",
            "function loadWorkspaceState()",
            "window.localStorage.getItem(BW_WORKSPACE_STORAGE_KEY)",
            "window.localStorage.setItem(BW_WORKSPACE_STORAGE_KEY,",
            "window.localStorage.removeItem(BW_WORKSPACE_STORAGE_KEY)",
            "restoredScoreDelta",
            "auditLogs",
            "clinicalStudies",
            "visualViolations",
            "hinglishViolations",
            "Reset Session"
        ]

        for p in paths:
            with open(p, 'r', encoding='utf-8') as f:
                content = f.read()
            for token in required_tokens:
                self.assertIn(token, content, f"Missing token '{token}' in {os.path.basename(p)}")

    def test_node_empirical_challenger_persistence_suite(self):
        """Execute node test_challenger_r3_persistence.js and verify all 290+ empirical assertions pass."""
        js_test = os.path.join(REPO_ROOT, 'codex', 'tests', 'test_challenger_r3_persistence.js')
        self.assertTrue(os.path.exists(js_test), f"Test script not found at {js_test}")

        res = subprocess.run(
            ['node', js_test],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT
        )
        self.assertEqual(res.returncode, 0, f"Node persistence suite failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}")
        self.assertIn("VERDICT: APPROVE", res.stdout)
        self.assertIn("Total Assertions:", res.stdout)
        self.assertIn("Failed:            0", res.stdout)


if __name__ == '__main__':
    unittest.main()
