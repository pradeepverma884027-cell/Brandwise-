"""
Milestone 4 Empirical Challenger Verification Suite
Author: Milestone 4 Challenger 1
Purpose: Empirical stress harness and parity validator for Milestone 4 (Sync & Deploy, Requirement R6)
"""

import unittest
import hashlib
import json
import io
import os
import sys

from codex.backend.app.core.review_engine import DeterministicReviewEngine
import server


class TestMilestone4ParityAndIntegrity(unittest.TestCase):
    """Empirical verification of cryptographic mirror parity and file properties."""

    def test_server_mirror_parity(self):
        """Verify server.py and codex/server.py are 100% byte-for-byte identical."""
        p1 = 'server.py'
        p2 = 'codex/server.py'
        self.assertTrue(os.path.exists(p1), f'{p1} does not exist')
        self.assertTrue(os.path.exists(p2), f'{p2} does not exist')

        with open(p1, 'rb') as f1, open(p2, 'rb') as f2:
            b1 = f1.read()
            b2 = f2.read()

        h1 = hashlib.sha256(b1).hexdigest()
        h2 = hashlib.sha256(b2).hexdigest()

        self.assertEqual(len(b1), len(b2), f'Byte length mismatch: {len(b1)} vs {len(b2)}')
        self.assertEqual(h1, h2, f'SHA256 digest mismatch: {h1} vs {h2}')
        self.assertEqual(b1, b2, 'Binary content differs between server.py and codex/server.py')
        self.assertEqual(len(b1), len(b2))

    def test_frontend_tri_mirror_parity(self):
        """Verify codex/frontend/index.html, index.html, and docs/index.html are 100% byte-for-byte identical."""
        p_front = 'codex/frontend/index.html'
        p_root = 'index.html'
        p_docs = 'docs/index.html'

        for p in [p_front, p_root, p_docs]:
            self.assertTrue(os.path.exists(p), f'{p} does not exist')

        with open(p_front, 'rb') as f_front, open(p_root, 'rb') as f_root, open(p_docs, 'rb') as f_docs:
            b_front = f_front.read()
            b_root = f_root.read()
            b_docs = f_docs.read()

        h_front = hashlib.sha256(b_front).hexdigest()
        h_root = hashlib.sha256(b_root).hexdigest()
        h_docs = hashlib.sha256(b_docs).hexdigest()

        self.assertEqual(len(b_front), len(b_root), 'Length mismatch between front and root')
        self.assertEqual(len(b_front), len(b_docs), 'Length mismatch between front and docs')
        self.assertEqual(h_front, h_root, f'SHA256 mismatch front vs root: {h_front} vs {h_root}')
        self.assertEqual(h_front, h_docs, f'SHA256 mismatch front vs docs: {h_front} vs {h_docs}')
        self.assertEqual(b_front, b_root, 'Binary content differs front vs root')
        self.assertEqual(b_front, b_docs, 'Binary content differs front vs docs')
        self.assertEqual(len(b_front), len(b_root))


class TestMilestone4AdversarialHarness(unittest.TestCase):
    """Stress tests on Hinglish review engine and API request handling."""

    @classmethod
    def setUpClass(cls):
        cls.engine = DeterministicReviewEngine()

    def test_adversarial_inputs_engine(self):
        """Stress engine with non-standard inputs, unicode, mixed scripts, whitespace."""
        # 1. Null / empty / blank
        self.assertEqual(self.engine.check_hinglish_and_regional_claims(''), [])
        self.assertEqual(self.engine.check_hinglish_and_regional_claims('     \t\n\r  '), [])

        # 2. Extreme repetition of mixed claims (500 repeats)
        rep_text = "Arre chamatkari 100% asar gora rang #vigyapan " * 500
        findings = self.engine.check_hinglish_and_regional_claims(rep_text)
        self.assertTrue(len(findings) > 0)
        # Verify all findings have valid attributes
        for f in findings:
            self.assertTrue(hasattr(f, 'category'))
            self.assertTrue(hasattr(f, 'severity'))
            self.assertTrue(hasattr(f, 'explanation'))
            self.assertTrue(hasattr(f, 'suggested_fix'))
            self.assertIsNotNone(f.suggested_fix)

        # 3. Unicode and emoji injection
        emoji_text = "🎉 Dosto ye chamatkari 💯 formula 100% asar deta hai! 🌸 Gora rang guaranteed! 🚀 #vigyapan"
        findings_emoji = self.engine.check_hinglish_and_regional_claims(emoji_text)
        # Should flag chamatkari, 100% asar, gora rang
        highlighted = [f.highlighted_text for f in findings_emoji]
        self.assertTrue(any('chamatkari' in h.lower() for h in highlighted))
        self.assertTrue(any('100% asar' in h.lower() for h in highlighted))
        self.assertTrue(any('gora rang' in h.lower() for h in highlighted))

        # 4. Control characters
        ctrl_text = "Hello\x00world\x1b[31m Ye pakka ilaj\x08 hai! #vigyapan"
        findings_ctrl = self.engine.check_hinglish_and_regional_claims(ctrl_text)
        self.assertTrue(any('pakka ilaj' in f.highlighted_text.lower() for f in findings_ctrl))

    def test_server_request_handler_adversarial_matrix(self):
        """Test server request handler against boundary inputs."""
        handler = server.RobustVerificationHandler.__new__(server.RobustVerificationHandler)
        handler.headers = {"Content-Length": "0"}
        handler.rfile = io.BytesIO(b"")
        handler.wfile = io.BytesIO()
        handler.path = "/api/hinglish/check"

        # Mock send_response / send_header / end_headers
        responses = []
        def mock_send_json(data, status=200):
            responses.append((status, data))
        handler.send_json_response = mock_send_json

        # Case 1: Empty body
        handler.rfile = io.BytesIO(b"")
        handler.headers = {"Content-Length": "0"}
        handler.do_POST()
        self.assertEqual(responses[-1][0], 400)
        self.assertIn("cannot be empty", responses[-1][1]["message"])

        # Case 2: Malformed JSON
        handler.rfile = io.BytesIO(b"{ malformed json !!")
        handler.headers = {"Content-Length": str(len(b"{ malformed json !!"))}
        handler.do_POST()
        self.assertEqual(responses[-1][0], 400)
        self.assertIn("Invalid JSON", responses[-1][1]["message"])

        # Case 3: Missing 'text' field
        handler.rfile = io.BytesIO(b'{"channel": "hinglish_instagram"}')
        handler.headers = {"Content-Length": str(len(b'{"channel": "hinglish_instagram"}'))}
        handler.do_POST()
        self.assertEqual(responses[-1][0], 400)
        self.assertIn("Field 'text' is required", responses[-1][1]["message"])

        # Case 4: Non-string 'text' field (e.g. integer)
        handler.rfile = io.BytesIO(b'{"text": 12345}')
        handler.headers = {"Content-Length": str(len(b'{"text": 12345}'))}
        handler.do_POST()
        self.assertEqual(responses[-1][0], 400)
        self.assertIn("must be a string", responses[-1][1]["message"])

        # Case 5: Valid Hinglish payload with multiple violations
        payload = json.dumps({
            "text": "Arre dosto! Ye chamatkari formula deta hai 100% asar aur gora rang sirf 7 din mein! Aaj hi order karein link bio mein!",
            "channel": "hinglish_instagram"
        }).encode("utf-8")
        handler.rfile = io.BytesIO(payload)
        handler.headers = {"Content-Length": str(len(payload))}
        handler.do_POST()
        status, resp_data = responses[-1]
        self.assertEqual(status, 200)
        self.assertEqual(resp_data["status"], "success")
        self.assertEqual(resp_data["compliance_score"], 20)
        self.assertEqual(len(resp_data["findings"]), 4)
        self.assertFalse(resp_data["summary"]["is_compliant"])

        # Case 6: Clean Hinglish copy
        payload_clean = json.dumps({
            "text": "DermaCare serum skin hydration improve karne me madad karta hai. #vigyapan",
            "channel": "hinglish_instagram"
        }).encode("utf-8")
        handler.rfile = io.BytesIO(payload_clean)
        handler.headers = {"Content-Length": str(len(payload_clean))}
        handler.do_POST()
        status, resp_data = responses[-1]
        self.assertEqual(status, 200)
        self.assertEqual(resp_data["compliance_score"], 100)
        self.assertEqual(len(resp_data["findings"]), 0)
        self.assertTrue(resp_data["summary"]["is_compliant"])


if __name__ == '__main__':
    unittest.main()
