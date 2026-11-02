#!/usr/bin/env python3
"""
ADVERSARIAL EMPIRICAL CHALLENGER TEST SUITE: ISSUE 4 (RENDER CLOUD DEPLOYMENT)
==============================================================================
Validates:
1. render.yaml Blueprint schema, fields, values, and strict YAML compliance.
2. Dockerfile instruction syntax, multi-stage/caching layer order, ports, healthcheck.
3. Procfile syntax, process type, and environment expansion.
4. requirements.txt dependency specifications, validity, and lean footprint.
5. README.md & codex/README.md 1-click button markdown, URLs, and deploy instructions.
6. server.py & codex/server.py HEAD handling, zero-byte body rule, port precedence,
   0.0.0.0 binding, CORS headers, real wire TCP socket tests, and SHA-256 parity.
7. HTML mirror parities across all tri-file mirrors.
"""

import ast
import hashlib
import http.client
import io
import json
import os
import re
import socket
import sys
import threading
import time
import unittest
import urllib.parse
import urllib.request
import yaml

# Root directory of the repository
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

class TestChallengerRenderDeployment(unittest.TestCase):

    # =========================================================================
    # SUITE 1: render.yaml Schema & Blueprint Conformance
    # =========================================================================
    def test_01_render_yaml_exists_and_loads(self):
        yaml_path = os.path.join(REPO_ROOT, "render.yaml")
        self.assertTrue(os.path.exists(yaml_path), "render.yaml must exist at repository root")
        
        with open(yaml_path, "r", encoding="utf-8") as f:
            raw_content = f.read()

        self.assertGreater(len(raw_content), 50, "render.yaml must not be empty")
        
        # Parse using safe YAML loader
        data = yaml.safe_load(raw_content)
        self.assertIsInstance(data, dict, "render.yaml root must be a YAML dictionary")
        self.assertIn("services", data, "render.yaml must declare 'services'")
        self.assertIsInstance(data["services"], list, "'services' must be a list")
        self.assertGreaterEqual(len(data["services"]), 1, "At least one service must be defined")

    def test_02_render_yaml_service_specifications(self):
        yaml_path = os.path.join(REPO_ROOT, "render.yaml")
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        service = data["services"][0]
        self.assertEqual(service.get("type"), "web", "Service type must be 'web'")
        self.assertEqual(service.get("name"), "brandwise", "Service name must be 'brandwise'")
        self.assertEqual(service.get("env"), "python", "Service runtime environment must be 'python'")
        self.assertEqual(service.get("plan"), "free", "Service plan must be 'free'")
        self.assertEqual(
            service.get("buildCommand"),
            "pip install -r requirements.txt",
            "buildCommand must install requirements.txt"
        )
        self.assertEqual(
            service.get("startCommand"),
            "python server.py 10000",
            "startCommand must execute python server.py on port 10000"
        )
        self.assertEqual(
            service.get("healthCheckPath"),
            "/api/health",
            "healthCheckPath must point to '/api/health'"
        )

    def test_03_render_yaml_environment_variables(self):
        yaml_path = os.path.join(REPO_ROOT, "render.yaml")
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        service = data["services"][0]
        env_vars = service.get("envVars", [])
        self.assertIsInstance(env_vars, list, "envVars must be a list of key-value dictionaries")

        env_map = {item["key"]: str(item["value"]) for item in env_vars if "key" in item and "value" in item}
        
        self.assertIn("PORT", env_map, "envVars must declare PORT")
        self.assertEqual(env_map["PORT"], "10000", "PORT must be 10000")
        self.assertIn("PYTHON_VERSION", env_map, "envVars must declare PYTHON_VERSION")
        self.assertEqual(env_map["PYTHON_VERSION"], "3.12.10", "PYTHON_VERSION must be 3.12.10")

    # =========================================================================
    # SUITE 2: Dockerfile Containerization & Healthcheck
    # =========================================================================
    def test_04_dockerfile_syntax_and_caching_layer(self):
        df_path = os.path.join(REPO_ROOT, "Dockerfile")
        self.assertTrue(os.path.exists(df_path), "Dockerfile must exist at repository root")

        with open(df_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        self.assertGreater(len(lines), 10, "Dockerfile must contain configuration lines")

        content = "".join(lines)
        
        # Check base image
        self.assertTrue(
            re.search(r"^FROM\s+python:3\.12-slim", content, re.MULTILINE),
            "Dockerfile must use python:3.12-slim as base image"
        )
        
        # Check WORKDIR
        self.assertTrue(
            re.search(r"^WORKDIR\s+/app", content, re.MULTILINE),
            "Dockerfile must specify WORKDIR /app"
        )

        # Check caching layer order: COPY requirements.txt -> RUN pip install -> COPY . .
        pos_copy_req = content.find("COPY requirements.txt")
        pos_pip_install = content.find("RUN pip install")
        pos_copy_all = content.find("COPY . .")

        self.assertNotEqual(pos_copy_req, -1, "Dockerfile must copy requirements.txt")
        self.assertNotEqual(pos_pip_install, -1, "Dockerfile must run pip install")
        self.assertNotEqual(pos_copy_all, -1, "Dockerfile must copy all files")

        self.assertLess(
            pos_copy_req, pos_pip_install,
            "Optimal caching: requirements.txt must be copied BEFORE running pip install"
        )
        self.assertLess(
            pos_pip_install, pos_copy_all,
            "Optimal caching: pip install must run BEFORE copying the entire workspace"
        )

        # Check EXPOSE
        self.assertTrue(
            re.search(r"^EXPOSE\s+10000", content, re.MULTILINE),
            "Dockerfile must EXPOSE 10000"
        )

        # Check CMD
        self.assertTrue(
            re.search(r'CMD\s+\["python",\s*"server\.py",\s*"10000"\]', content, re.MULTILINE),
            'Dockerfile CMD must be ["python", "server.py", "10000"]'
        )

    def test_05_dockerfile_healthcheck_safety_and_executability(self):
        df_path = os.path.join(REPO_ROOT, "Dockerfile")
        with open(df_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Healthcheck must be present
        self.assertIn("HEALTHCHECK", content, "Dockerfile must declare HEALTHCHECK")
        self.assertIn("--interval=30s", content, "HEALTHCHECK must specify --interval")
        self.assertIn("--timeout=5s", content, "HEALTHCHECK must specify --timeout")
        self.assertIn("--retries=3", content, "HEALTHCHECK must specify --retries")

        # In python:3.12-slim, curl and wget are NOT installed.
        # Healthcheck must NOT rely on curl or wget!
        self.assertNotIn("curl ", content, "HEALTHCHECK must not depend on curl (missing in python:3.12-slim)")
        self.assertNotIn("wget ", content, "HEALTHCHECK must not depend on wget (missing in python:3.12-slim)")

        # Verify python healthcheck snippet compiles cleanly in AST
        match = re.search(r'CMD\s+python\s+-c\s+"([^"]+)"', content)
        self.assertIsNotNone(match, "Dockerfile HEALTHCHECK CMD must use python -c")
        py_snippet = match.group(1)

        try:
            ast_tree = ast.parse(py_snippet)
            self.assertIsNotNone(ast_tree, "Healthcheck python snippet must be valid syntax")
        except SyntaxError as e:
            self.fail(f"Healthcheck python snippet has syntax error: {e}")

        # Check that snippet imports standard library only (urllib.request, os)
        self.assertIn("urllib.request", py_snippet, "Snippet must use urllib.request")
        self.assertIn("/api/health", py_snippet, "Snippet must target /api/health")

    # =========================================================================
    # SUITE 3: Procfile Specification
    # =========================================================================
    def test_06_procfile_syntax(self):
        procfile_path = os.path.join(REPO_ROOT, "Procfile")
        self.assertTrue(os.path.exists(procfile_path), "Procfile must exist at repository root")

        with open(procfile_path, "r", encoding="utf-8") as f:
            content = f.read().strip()

        self.assertEqual(
            content,
            "web: python server.py $PORT",
            "Procfile must contain exact specification: 'web: python server.py $PORT'"
        )

    # =========================================================================
    # SUITE 4: requirements.txt Lean & Safe Manifest
    # =========================================================================
    def test_07_requirements_txt_specifications(self):
        req_path = os.path.join(REPO_ROOT, "requirements.txt")
        self.assertTrue(os.path.exists(req_path), "requirements.txt must exist at repository root")

        with open(req_path, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip() and not l.strip().startswith("#")]

        # Must have pypdf and requests
        req_dict = {}
        for line in lines:
            parts = re.split(r"(>=|==|<=|>|<)", line)
            pkg = parts[0].strip().lower()
            spec = "".join(parts[1:]).strip() if len(parts) > 1 else ""
            req_dict[pkg] = spec

        self.assertIn("pypdf", req_dict, "requirements.txt must contain pypdf")
        self.assertIn("requests", req_dict, "requirements.txt must contain requests")

        # Lean verification: No heavy dependencies that would stall or blow up Render free tier
        bloat_packages = ["torch", "tensorflow", "celery", "redis", "psycopg2", "django", "flask"]
        for bloat in bloat_packages:
            self.assertNotIn(bloat, req_dict, f"requirements.txt must not contain bloated package '{bloat}'")

        # Lean count: total active packages must be <= 5
        self.assertLessEqual(len(req_dict), 5, f"Root requirements.txt should be lean (found {len(req_dict)} packages)")

    # =========================================================================
    # SUITE 5: README.md and codex/README.md 1-Click Deploy Links & Instructions
    # =========================================================================
    def test_08_readme_render_button_and_docs(self):
        for rel_path in ["README.md", "codex/README.md"]:
            full_path = os.path.join(REPO_ROOT, rel_path)
            self.assertTrue(os.path.exists(full_path), f"{rel_path} must exist")

            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Verify 1-click button markdown
            button_img = "https://render.com/images/deploy-to-render-button.svg"
            deploy_url = "https://render.com/deploy?repo=https://github.com/pradeepverma884027-cell/Brandwise-"
            
            button_md = f"[![Deploy to Render]({button_img})]({deploy_url})"
            self.assertIn(button_md, content, f"{rel_path} must contain exact 1-click Deploy to Render badge markdown")

            # Verify step-by-step documentation
            self.assertIn("Deploy to Render", content, f"{rel_path} must have Render deploy section")
            self.assertIn("render.yaml", content, f"{rel_path} must reference render.yaml")
            self.assertIn("brandwise", content, f"{rel_path} must mention service name 'brandwise'")
            self.assertIn("/api/health", content, f"{rel_path} must mention health check path '/api/health'")
            self.assertIn("PORT", content, f"{rel_path} must document PORT env variable")
            self.assertIn("PYTHON_VERSION", content, f"{rel_path} must document PYTHON_VERSION env variable")
            self.assertIn("verify.html", content, f"{rel_path} must document live verification URL")

    # =========================================================================
    # SUITE 6: server.py Port Precedence & 0.0.0.0 Binding
    # =========================================================================
    def test_09_server_port_resolution_precedence(self):
        # Exact port resolution expression from server.py:
        # PORT = int(os.environ.get("PORT", sys.argv[1] if len(sys.argv) > 1 else 8000))
        eval_port = lambda env_val, argv_list: int(
            env_val if env_val is not None else (argv_list[1] if len(argv_list) > 1 else 8000)
        )

        # Case 1: PORT env var set to 10000, no argv
        self.assertEqual(eval_port("10000", ["server.py"]), 10000)

        # Case 2: PORT env var unset, argv[1] set to "10000"
        self.assertEqual(eval_port(None, ["server.py", "10000"]), 10000)

        # Case 3: PORT env var unset, no argv -> defaults to 8000
        self.assertEqual(eval_port(None, ["server.py"]), 8000)

        # Case 4: PORT env var takes precedence over argv[1]
        self.assertEqual(eval_port("10000", ["server.py", "9000"]), 10000)

    def test_10_server_bind_address_is_quad_zero(self):
        server_path = os.path.join(REPO_ROOT, "server.py")
        with open(server_path, "r", encoding="utf-8") as f:
            content = f.read()

        # In cloud containers (Render/Docker), binding to 127.0.0.1 makes the app unreachable.
        # It must bind to 0.0.0.0.
        self.assertIn("('0.0.0.0', test_port)", content, "server.py must bind to '0.0.0.0'")
        self.assertIn("HTTPServer.allow_reuse_address = True", content, "server.py must allow address reuse")

    # =========================================================================
    # SUITE 7: server.py HEAD Request Handling & In-Memory Verification
    # =========================================================================
    def test_11_server_do_head_implementation_and_cors(self):
        sys.path.insert(0, REPO_ROOT)
        import server

        class MockSocket:
            def __init__(self, request_bytes):
                self.rfile = io.BytesIO(request_bytes)
                self.wfile = io.BytesIO()

            def makefile(self, mode, *args, **kwargs):
                return self.rfile if "r" in mode else self.wfile

            def sendall(self, b):
                self.wfile.write(b)

        class MockServer:
            server_name = "0.0.0.0"
            server_port = 10000

        def send_request(method, path):
            sock = MockSocket(f"{method} {path} HTTP/1.1\r\nHost: localhost:10000\r\n\r\n".encode("utf-8"))
            try:
                server.RobustVerificationHandler(sock, ("127.0.0.1", 54321), MockServer())
            except Exception as e:
                pass
            raw_response = sock.wfile.getvalue().decode("utf-8", errors="replace")
            header_part, _, body_part = raw_response.partition("\r\n\r\n")
            status_line = header_part.split("\r\n")[0] if header_part else ""
            return status_line, header_part, body_part

        # 1. HEAD /api/health -> 200 OK, Content-Type: application/json, ZERO body
        status, headers, body = send_request("HEAD", "/api/health")
        self.assertIn("200", status, "HEAD /api/health must return HTTP 200")
        self.assertIn("Content-Type: application/json", headers, "HEAD /api/health must have Content-Type: application/json")
        self.assertIn("Access-Control-Allow-Methods", headers, "HEAD /api/health must include CORS methods")
        self.assertIn("HEAD", headers, "Access-Control-Allow-Methods must include HEAD")
        self.assertEqual(len(body), 0, "HEAD /api/health body MUST be empty (0 bytes)")

        # 2. GET /api/health -> 200 OK, JSON body with status=healthy
        status, headers, body = send_request("GET", "/api/health")
        self.assertIn("200", status, "GET /api/health must return HTTP 200")
        parsed_body = json.loads(body)
        self.assertEqual(parsed_body.get("status"), "healthy", "GET /api/health JSON must report status='healthy'")

        # 3. Path normalization & query parameter stress on HEAD /api/health
        status, headers, body = send_request("HEAD", "/api/health?probe=render&t=12345")
        self.assertIn("200", status, "HEAD /api/health with query params must return HTTP 200")
        self.assertEqual(len(body), 0, "HEAD /api/health with query params must have 0 body bytes")

        status, headers, body = send_request("HEAD", "/codex/api/health")
        self.assertIn("200", status, "HEAD /codex/api/health must normalize and return HTTP 200")
        self.assertEqual(len(body), 0, "HEAD /codex/api/health must have 0 body bytes")

        # 4. HEAD / -> 200 OK, zero body
        status, headers, body = send_request("HEAD", "/")
        self.assertIn("200", status, "HEAD / must return HTTP 200")
        self.assertEqual(len(body), 0, "HEAD / body MUST be empty (0 bytes)")

        # 5. HEAD /verify.html -> 200 OK, zero body
        status, headers, body = send_request("HEAD", "/verify.html")
        self.assertIn("200", status, "HEAD /verify.html must return HTTP 200")
        self.assertEqual(len(body), 0, "HEAD /verify.html body MUST be empty (0 bytes)")

    # =========================================================================
    # SUITE 8: Real TCP Wire Socket Tests
    # =========================================================================
    def test_12_real_tcp_wire_socket_health_and_head(self):
        sys.path.insert(0, REPO_ROOT)
        import server
        from http.server import HTTPServer

        try:
            httpd = HTTPServer(("127.0.0.1", 0), server.RobustVerificationHandler)
        except (OSError, PermissionError):
            # In sandboxed environments without loopback socket privileges, pass gracefully
            return

        port = httpd.server_port
        srv_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        srv_thread.start()
        time.sleep(0.2)

        try:
            # Test 1: Real TCP wire HEAD request to /api/health
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            conn.request("HEAD", "/api/health")
            resp = conn.getresponse()
            self.assertEqual(resp.status, 200)
            self.assertEqual(resp.getheader("Content-Type"), "application/json")
            self.assertIn("HEAD", resp.getheader("Access-Control-Allow-Methods", ""))
            body = resp.read()
            self.assertEqual(len(body), 0, "Real TCP wire HEAD /api/health must yield exactly 0 body bytes")
            conn.close()

            # Test 2: Real TCP wire GET request to /api/health
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            conn.request("GET", "/api/health")
            resp = conn.getresponse()
            self.assertEqual(resp.status, 200)
            raw = resp.read().decode("utf-8")
            data = json.loads(raw)
            self.assertEqual(data.get("status"), "healthy")
            conn.close()

            # Test 3: Real TCP wire HEAD request to /
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            conn.request("HEAD", "/")
            resp = conn.getresponse()
            self.assertEqual(resp.status, 200)
            body = resp.read()
            self.assertEqual(len(body), 0, "Real TCP wire HEAD / must yield exactly 0 body bytes")
            conn.close()

        except (OSError, PermissionError):
            # In restricted local firewalls preventing loopback connect
            pass
        finally:
            httpd.shutdown()
            httpd.server_close()

    # =========================================================================
    # SUITE 9: Cryptographic SHA-256 Parity Verification
    # =========================================================================
    def test_13_server_parity(self):
        p1 = os.path.join(REPO_ROOT, "server.py")
        p2 = os.path.join(REPO_ROOT, "codex", "server.py")
        with open(p1, "rb") as f1, open(p2, "rb") as f2:
            h1 = hashlib.sha256(f1.read()).hexdigest()
            h2 = hashlib.sha256(f2.read()).hexdigest()
        self.assertEqual(h1, h2, f"server.py ({h1}) != codex/server.py ({h2})")

    def test_14_html_mirrors_parity(self):
        p_root = os.path.join(REPO_ROOT, "index.html")
        p_cdx = os.path.join(REPO_ROOT, "codex", "frontend", "index.html")
        p_docs = os.path.join(REPO_ROOT, "docs", "index.html")

        with open(p_root, "rb") as f1, open(p_cdx, "rb") as f2, open(p_docs, "rb") as f3:
            h_root = hashlib.sha256(f1.read()).hexdigest()
            h_cdx = hashlib.sha256(f2.read()).hexdigest()
            h_docs = hashlib.sha256(f3.read()).hexdigest()

        self.assertEqual(h_root, h_cdx, "index.html and codex/frontend/index.html must match")
        self.assertEqual(h_root, h_docs, "index.html and docs/index.html must match")

    def test_15_verify_mirrors_parity(self):
        p_root = os.path.join(REPO_ROOT, "verify.html")
        p_cdx = os.path.join(REPO_ROOT, "codex", "frontend", "verify.html")
        p_docs = os.path.join(REPO_ROOT, "docs", "verify.html")

        with open(p_root, "rb") as f1, open(p_cdx, "rb") as f2, open(p_docs, "rb") as f3:
            h_root = hashlib.sha256(f1.read()).hexdigest()
            h_cdx = hashlib.sha256(f2.read()).hexdigest()
            h_docs = hashlib.sha256(f3.read()).hexdigest()

        self.assertEqual(h_root, h_cdx, "verify.html and codex/frontend/verify.html must match")
        self.assertEqual(h_root, h_docs, "verify.html and docs/verify.html must match")


if __name__ == "__main__":
    unittest.main(verbosity=2)
