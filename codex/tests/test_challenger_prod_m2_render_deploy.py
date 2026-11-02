"""
Adversarial Empirical Challenger: Issue 4 — Render Live Deployment & Server Resilience
Author: teamwork_challenger_prod_m2_2
Target: Socket 0.0.0.0 binding, PORT resolution, /api/health HEAD/GET, and server mirror parity.
"""

import ast
import hashlib
import io
import json
import os
import subprocess
import sys
import unittest
import yaml
from http.server import HTTPServer

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import server


class MockSocket:
    """In-memory mock socket reproducing client-server HTTP exchange without network permissions."""
    def __init__(self, request_bytes: bytes):
        self.rfile = io.BytesIO(request_bytes)
        self.wfile = io.BytesIO()

    def makefile(self, mode: str, *args, **kwargs):
        if 'r' in mode:
            return self.rfile
        return self.wfile

    def sendall(self, data: bytes):
        self.wfile.write(data)


class MockServer:
    server_name = '0.0.0.0'
    server_port = 10000


def simulate_http_request(method: str, path: str, headers: dict = None, body: bytes = b''):
    """Execute request directly through RobustVerificationHandler and parse status, headers, and body."""
    raw_head = f"{method} {path} HTTP/1.1\r\nHost: localhost:10000\r\n"
    if headers:
        for k, v in headers.items():
            raw_head += f"{k}: {v}\r\n"
    if body:
        raw_head += f"Content-Length: {len(body)}\r\n"
    raw_head += "\r\n"

    mock_sock = MockSocket(raw_head.encode('utf-8') + body)
    server.RobustVerificationHandler(mock_sock, ('127.0.0.1', 54321), MockServer())

    raw_output = mock_sock.wfile.getvalue()
    separator = b"\r\n\r\n"
    sep_idx = raw_output.find(separator)

    if sep_idx >= 0:
        header_text = raw_output[:sep_idx].decode('utf-8', errors='replace')
        body_bytes = raw_output[sep_idx + len(separator):]
    else:
        header_text = raw_output.decode('utf-8', errors='replace')
        body_bytes = b""

    lines = header_text.split("\r\n")
    status_line = lines[0] if lines else ""
    parsed_headers = {}
    for line in lines[1:]:
        if ": " in line:
            k, v = line.split(": ", 1)
            parsed_headers[k.strip().lower()] = v.strip()

    return status_line, parsed_headers, body_bytes


class TestRenderDeploymentChallenger(unittest.TestCase):
    """Adversarial stress-testing of server socket binding, port resolution, health probes, and parity."""

    def test_01_server_mirror_sha256_cryptographic_parity(self):
        """Verify 100% byte-for-byte SHA-256 match between server.py and codex/server.py."""
        root_server = os.path.join(REPO_ROOT, "server.py")
        codex_server = os.path.join(REPO_ROOT, "codex", "server.py")

        self.assertTrue(os.path.exists(root_server), f"Missing root server: {root_server}")
        self.assertTrue(os.path.exists(codex_server), f"Missing codex server: {codex_server}")

        with open(root_server, "rb") as f:
            bytes_root = f.read()
        with open(codex_server, "rb") as f:
            bytes_codex = f.read()

        hash_root = hashlib.sha256(bytes_root).hexdigest()
        hash_codex = hashlib.sha256(bytes_codex).hexdigest()

        self.assertEqual(len(bytes_root), len(bytes_codex),
                         f"File size mismatch: server.py={len(bytes_root)} vs codex/server.py={len(bytes_codex)}")
        self.assertEqual(hash_root, hash_codex,
                         f"SHA-256 mismatch: {hash_root} vs {hash_codex}")
        self.assertEqual(bytes_root, bytes_codex, "Byte-by-byte content differs between server mirrors")

    def test_02_port_resolution_logic_and_precedence(self):
        """Stress-test port resolution: PORT env var vs sys.argv[1] vs default 8000."""
        # 1. Parse AST of server.py to extract canonical main execution block
        server_path = os.path.join(REPO_ROOT, "server.py")
        with open(server_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())

        main_if = [n for n in tree.body if isinstance(n, ast.If) and isinstance(n.test, ast.Compare)][0]
        code = compile(ast.Module(body=main_if.body, type_ignores=[]), '<server_main_ast>', 'exec')

        def eval_main(env_dict, argv_list):
            invoked_ports = []
            scope = {
                'os': type('os', (), {'environ': env_dict})(),
                'sys': type('sys', (), {'argv': argv_list})(),
                'run': lambda p: invoked_ports.append(p)
            }
            exec(code, scope)
            return scope.get('PORT'), invoked_ports[0]

        # Case A: PORT env var overrides CLI argument (precedence check)
        p, c = eval_main({'PORT': '10000'}, ['server.py', '9000'])
        self.assertEqual(p, 10000)
        self.assertEqual(c, 10000)

        # Case B: CLI argument resolves when PORT env is not set
        p, c = eval_main({}, ['server.py', '9000'])
        self.assertEqual(p, 9000)
        self.assertEqual(c, 9000)

        # Case C: Default resolves to 8000 when neither env nor CLI is provided
        p, c = eval_main({}, ['server.py'])
        self.assertEqual(p, 8000)
        self.assertEqual(c, 8000)

        # Case D: Canonical expression literal check
        with open(server_path, "r", encoding="utf-8") as f:
            src = f.read()
        self.assertIn('PORT = int(os.environ.get("PORT", sys.argv[1] if len(sys.argv) > 1 else 8000))', src,
                      "server.py must contain the exact canonical PORT resolution expression")

        # Case E: Subprocess verification with environment isolation
        sub_code = (
            "import os, sys\n"
            "env = os.environ\n"
            "argv = sys.argv\n"
            "PORT = int(env.get('PORT', argv[1] if len(argv) > 1 else 8000))\n"
            "print(f'PORT:{PORT}')\n"
        )
        # E1: env var override in real subprocess
        res1 = subprocess.run([sys.executable, '-c', sub_code, '7777'],
                              capture_output=True, text=True, env={'PORT': '10000', 'PATH': os.environ.get('PATH', '')})
        self.assertIn('PORT:10000', res1.stdout)

        # E2: cli override in real subprocess
        res2 = subprocess.run([sys.executable, '-c', sub_code, '7777'],
                              capture_output=True, text=True, env={'PATH': os.environ.get('PATH', '')})
        self.assertIn('PORT:7777', res2.stdout)

        # E3: default in real subprocess
        res3 = subprocess.run([sys.executable, '-c', sub_code],
                              capture_output=True, text=True, env={'PATH': os.environ.get('PATH', '')})
        self.assertIn('PORT:8000', res3.stdout)

    def test_03_socket_binding_0_0_0_0_and_reuse_address(self):
        """Verify socket binding to 0.0.0.0 and allow_reuse_address = True."""
        with open(os.path.join(REPO_ROOT, "server.py"), "r", encoding="utf-8") as f:
            src = f.read()

        self.assertIn("server_address = ('0.0.0.0', test_port)", src,
                      "server.py must bind specifically to ('0.0.0.0', test_port)")
        self.assertIn("HTTPServer.allow_reuse_address = True", src,
                      "server.py must configure HTTPServer.allow_reuse_address = True")

        # Verify real socket allocation behavior on 0.0.0.0
        HTTPServer.allow_reuse_address = True
        test_httpd = HTTPServer(('0.0.0.0', 0), server.RobustVerificationHandler)
        try:
            sock_name = test_httpd.socket.getsockname()
            self.assertEqual(sock_name[0], '0.0.0.0', f"Socket did not bind to 0.0.0.0, bound to: {sock_name[0]}")
            self.assertTrue(test_httpd.allow_reuse_address, "allow_reuse_address should be True on instance")
        finally:
            test_httpd.server_close()

    def test_04_http_head_api_health_adversarial(self):
        """Empirically test HTTP HEAD on /api/health returns 200, json content-type, and 0-byte body."""
        paths_to_test = [
            "/api/health",
            "/api/health/",
            "/codex/api/health",
            "/api/health?probe=render",
            "/api/health?test=1&adversarial=true#frag"
        ]

        for p in paths_to_test:
            status, headers, body = simulate_http_request("HEAD", p)
            self.assertIn("200", status, f"HEAD {p} did not return 200: {status}")
            self.assertEqual(headers.get("content-type"), "application/json",
                             f"HEAD {p} Content-Type mismatch: {headers.get('content-type')}")
            self.assertEqual(len(body), 0,
                             f"HEAD {p} MUST have 0-byte body, got {len(body)} bytes: {body!r}")
            self.assertEqual(headers.get("access-control-allow-origin"), "*",
                             f"HEAD {p} missing CORS Access-Control-Allow-Origin")
            self.assertIn("HEAD", headers.get("access-control-allow-methods", ""),
                          f"HEAD {p} CORS methods missing HEAD: {headers.get('access-control-allow-methods')}")

    def test_05_http_get_api_health_payload(self):
        """Empirically test HTTP GET on /api/health returns 200 and healthy JSON payload."""
        paths_to_test = [
            "/api/health",
            "/api/health/",
            "/codex/api/health",
            "/api/health?check=active"
        ]

        for p in paths_to_test:
            status, headers, body = simulate_http_request("GET", p)
            self.assertIn("200", status, f"GET {p} did not return 200: {status}")
            self.assertEqual(headers.get("content-type"), "application/json")
            self.assertGreater(len(body), 0, f"GET {p} body must not be empty")

            data = json.loads(body.decode("utf-8"))
            self.assertEqual(data.get("status"), "healthy", f"Status should be healthy in {data}")
            self.assertIn("Brandwise", data.get("engine", ""))
            self.assertIsInstance(data.get("active_improvements"), list)
            self.assertEqual(len(data.get("active_improvements")), 3)

    def test_06_http_head_root_and_local_ip(self):
        """Verify HEAD on static root / and /api/local-ip."""
        status_root, headers_root, body_root = simulate_http_request("HEAD", "/")
        self.assertIn("200", status_root, f"HEAD / returned status: {status_root}")
        self.assertEqual(len(body_root), 0, f"HEAD / must return 0 bytes body, got: {len(body_root)}")

        status_ip, headers_ip, body_ip = simulate_http_request("HEAD", "/api/local-ip")
        self.assertIn("200", status_ip, f"HEAD /api/local-ip returned status: {status_ip}")
        self.assertEqual(headers_ip.get("content-type"), "application/json")
        self.assertEqual(len(body_ip), 0, f"HEAD /api/local-ip must return 0 bytes body, got: {len(body_ip)}")

    def test_07_render_yaml_specification_compliance(self):
        """Verify render.yaml satisfies Render Blueprint specification."""
        yaml_path = os.path.join(REPO_ROOT, "render.yaml")
        self.assertTrue(os.path.exists(yaml_path), f"render.yaml missing at {yaml_path}")

        with open(yaml_path, "r", encoding="utf-8") as f:
            spec = yaml.safe_load(f)

        self.assertIn("services", spec)
        services = spec["services"]
        self.assertEqual(len(services), 1)

        svc = services[0]
        self.assertEqual(svc.get("type"), "web")
        self.assertEqual(svc.get("name"), "brandwise")
        self.assertEqual(svc.get("env"), "python")
        self.assertEqual(svc.get("plan"), "free")
        self.assertEqual(svc.get("buildCommand"), "pip install -r requirements.txt")
        self.assertEqual(svc.get("startCommand"), "python server.py 10000")
        self.assertEqual(svc.get("healthCheckPath"), "/api/health")

        env_map = {item["key"]: str(item["value"]) for item in svc.get("envVars", [])}
        self.assertEqual(env_map.get("PORT"), "10000")
        self.assertTrue(env_map.get("PYTHON_VERSION", "").startswith("3.12"))

    def test_08_dockerfile_and_procfile_compliance(self):
        """Verify Dockerfile, Procfile, and requirements.txt compliance."""
        # Dockerfile
        df_path = os.path.join(REPO_ROOT, "Dockerfile")
        self.assertTrue(os.path.exists(df_path))
        with open(df_path, "r", encoding="utf-8") as f:
            df = f.read()
        self.assertIn("FROM python:3.12-slim", df)
        self.assertIn("EXPOSE 10000", df)
        self.assertIn("/api/health", df)
        self.assertIn('CMD ["python", "server.py", "10000"]', df)

        # Procfile
        proc_path = os.path.join(REPO_ROOT, "Procfile")
        self.assertTrue(os.path.exists(proc_path))
        with open(proc_path, "r", encoding="utf-8") as f:
            proc = f.read().strip()
        self.assertEqual(proc, "web: python server.py $PORT")

        # requirements.txt
        req_path = os.path.join(REPO_ROOT, "requirements.txt")
        self.assertTrue(os.path.exists(req_path))
        with open(req_path, "r", encoding="utf-8") as f:
            req = f.read()
        self.assertIn("pypdf", req)
        self.assertIn("requests", req)

    def test_09_readme_deployment_button_and_instructions(self):
        """Verify README.md and codex/README.md contain 1-click Render Deploy button and guide."""
        for p in [os.path.join(REPO_ROOT, "README.md"), os.path.join(REPO_ROOT, "codex", "README.md")]:
            with open(p, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("https://render.com/deploy?repo=", content, f"Missing Render deploy button in {p}")
            self.assertIn("Deploy to Render (1-Click Live Cloud Backend)", content, f"Missing Render section in {p}")
            self.assertIn("server.py 10000", content, f"Missing startCommand documentation in {p}")


if __name__ == "__main__":
    unittest.main()
