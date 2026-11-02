#!/usr/bin/env node
/**
 * EMPIRICAL ADVERSARIAL CHALLENGER: ISSUE 4 RENDER CLOUD DEPLOYMENT
 * =================================================================
 * Validates:
 * 1. render.yaml Blueprint schema, web service declaration, commands, env vars.
 * 2. Dockerfile base image, layer caching, expose, healthcheck safety, and CMD.
 * 3. Procfile syntax and process definition.
 * 4. requirements.txt lean dependency constraints and package specifications.
 * 5. README.md & codex/README.md 1-click button markdown and URL structure.
 * 6. Cryptographic SHA-256 parities across server.py and tri-file HTML/verify mirrors.
 */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const REPO_ROOT = path.resolve(__dirname, '..', '..');

let totalAssertions = 0;
let passedAssertions = 0;
let failedAssertions = 0;

function assert(condition, message) {
  totalAssertions++;
  if (!condition) {
    failedAssertions++;
    console.error(`  ❌ FAIL: ${message}`);
    throw new Error(`Assertion failed: ${message}`);
  } else {
    passedAssertions++;
    console.log(`  ✓ PASS: ${message}`);
  }
}

function getSha256(filePath) {
  const buf = fs.readFileSync(filePath);
  return crypto.createHash('sha256').update(buf).digest('hex');
}

console.log('='.repeat(80));
console.log('EMPIRICAL ADVERSARIAL CHALLENGER: ISSUE 4 (RENDER DEPLOYMENT SUITE)');
console.log('='.repeat(80));

// --- SUITE 1: Cryptographic Mirror Parity ---
console.log('\n--- SUITE 1: Cryptographic Mirror Parity ---');
{
  const s1 = path.join(REPO_ROOT, 'server.py');
  const s2 = path.join(REPO_ROOT, 'codex', 'server.py');
  const hash1 = getSha256(s1);
  const hash2 = getSha256(s2);
  console.log(`  [SERVER] server.py:       ${hash1}`);
  console.log(`  [SERVER] codex/server.py: ${hash2}`);
  assert(hash1 === hash2, '100% SHA-256 parity between server.py and codex/server.py');

  const i1 = path.join(REPO_ROOT, 'index.html');
  const i2 = path.join(REPO_ROOT, 'codex', 'frontend', 'index.html');
  const i3 = path.join(REPO_ROOT, 'docs', 'index.html');
  const hi1 = getSha256(i1);
  const hi2 = getSha256(i2);
  const hi3 = getSha256(i3);
  assert(hi1 === hi2 && hi2 === hi3, '100% SHA-256 parity across all 3 index.html mirrors');

  const v1 = path.join(REPO_ROOT, 'verify.html');
  const v2 = path.join(REPO_ROOT, 'codex', 'frontend', 'verify.html');
  const v3 = path.join(REPO_ROOT, 'docs', 'verify.html');
  const hv1 = getSha256(v1);
  const hv2 = getSha256(v2);
  const hv3 = getSha256(v3);
  assert(hv1 === hv2 && hv2 === hv3, '100% SHA-256 parity across all 3 verify.html mirrors');
}

// --- SUITE 2: render.yaml Blueprint Conformance ---
console.log('\n--- SUITE 2: render.yaml Blueprint Conformance ---');
{
  const yamlPath = path.join(REPO_ROOT, 'render.yaml');
  assert(fs.existsSync(yamlPath), 'render.yaml exists at repository root');
  const content = fs.readFileSync(yamlPath, 'utf8');

  // Verify structure
  assert(/^services:\s*$/m.test(content), "render.yaml declares 'services:'");
  assert(/^\s+-\s+type:\s*web\s*$/m.test(content), "Declared service type is 'web'");
  assert(/^\s+name:\s*brandwise\s*$/m.test(content), "Service name is 'brandwise'");
  assert(/^\s+env:\s*python\s*$/m.test(content), "Service env runtime is 'python'");
  assert(/^\s+plan:\s*free\s*$/m.test(content), "Service plan is 'free'");
  assert(/^\s+buildCommand:\s*pip install -r requirements\.txt\s*$/m.test(content), "buildCommand installs requirements.txt");
  assert(/^\s+startCommand:\s*python server\.py 10000\s*$/m.test(content), "startCommand executes python server.py on 10000");
  assert(/^\s+healthCheckPath:\s*\/api\/health\s*$/m.test(content), "healthCheckPath is '/api/health'");
  assert(/^\s+envVars:\s*$/m.test(content), "Declared 'envVars:' block");
  assert(/key:\s*PORT[\s\S]*?value:\s*10000/.test(content), "envVars contains PORT=10000");
  assert(/key:\s*PYTHON_VERSION[\s\S]*?value:\s*3\.12\.10/.test(content), "envVars contains PYTHON_VERSION=3.12.10");
}

// --- SUITE 3: Dockerfile Layering & Healthcheck Verification ---
console.log('\n--- SUITE 3: Dockerfile Layering & Healthcheck Verification ---');
{
  const dfPath = path.join(REPO_ROOT, 'Dockerfile');
  assert(fs.existsSync(dfPath), 'Dockerfile exists at repository root');
  const content = fs.readFileSync(dfPath, 'utf8');

  assert(/^FROM\s+python:3\.12-slim/m.test(content), 'Dockerfile uses python:3.12-slim base image');
  assert(/^WORKDIR\s+\/app/m.test(content), 'Dockerfile sets WORKDIR /app');

  const idxCopyReq = content.indexOf('COPY requirements.txt');
  const idxPip = content.indexOf('RUN pip install');
  const idxCopyAll = content.indexOf('COPY . .');

  assert(idxCopyReq !== -1 && idxPip !== -1 && idxCopyAll !== -1, 'Dockerfile contains all essential copy/run steps');
  assert(idxCopyReq < idxPip, 'Optimal layer caching: COPY requirements.txt precedes RUN pip install');
  assert(idxPip < idxCopyAll, 'Optimal layer caching: RUN pip install precedes COPY . .');

  assert(/^EXPOSE\s+10000/m.test(content), 'Dockerfile exposes port 10000');
  assert(/HEALTHCHECK\s+--interval=30s\s+--timeout=5s\s+--start-period=5s\s+--retries=3/m.test(content), 'HEALTHCHECK parameters configured safely');
  assert(!content.includes('curl '), 'HEALTHCHECK does not depend on curl (not present in python:3.12-slim)');
  assert(!content.includes('wget '), 'HEALTHCHECK does not depend on wget (not present in python:3.12-slim)');
  assert(content.includes('urllib.request'), 'HEALTHCHECK uses python standard library urllib.request');
  assert(content.includes('/api/health'), 'HEALTHCHECK tests /api/health endpoint');
  assert(/CMD\s+\["python",\s*"server\.py",\s*"10000"\]/m.test(content), 'CMD executes ["python", "server.py", "10000"]');
}

// --- SUITE 4: Procfile Syntax ---
console.log('\n--- SUITE 4: Procfile Syntax ---');
{
  const pfPath = path.join(REPO_ROOT, 'Procfile');
  assert(fs.existsSync(pfPath), 'Procfile exists at repository root');
  const content = fs.readFileSync(pfPath, 'utf8').trim();
  assert(content === 'web: python server.py $PORT', "Procfile syntax equals 'web: python server.py $PORT'");
}

// --- SUITE 5: requirements.txt Dependency Audit ---
console.log('\n--- SUITE 5: requirements.txt Dependency Audit ---');
{
  const reqPath = path.join(REPO_ROOT, 'requirements.txt');
  assert(fs.existsSync(reqPath), 'requirements.txt exists at repository root');
  const content = fs.readFileSync(reqPath, 'utf8');
  const activeLines = content.split('\n')
    .map(l => l.trim())
    .filter(l => l && !l.startsWith('#'));

  assert(activeLines.some(l => l.startsWith('pypdf')), 'requirements.txt contains pypdf');
  assert(activeLines.some(l => l.startsWith('requests')), 'requirements.txt contains requests');
  assert(activeLines.length <= 5, `requirements.txt is lean (contains ${activeLines.length} packages, max 5)`);

  const forbidden = ['torch', 'tensorflow', 'celery', 'redis', 'psycopg2', 'pandas', 'numpy'];
  for (const pkg of forbidden) {
    assert(!activeLines.some(l => l.startsWith(pkg)), `requirements.txt excludes heavyweight dependency '${pkg}'`);
  }
}

// --- SUITE 6: README.md and codex/README.md 1-Click Button & Docs ---
console.log('\n--- SUITE 6: README 1-Click Button & Documentation ---');
{
  const expectedImg = 'https://render.com/images/deploy-to-render-button.svg';
  const expectedDeploy = 'https://render.com/deploy?repo=https://github.com/pradeepverma884027-cell/Brandwise-';
  const expectedBadgeMd = `[![Deploy to Render](${expectedImg})](${expectedDeploy})`;

  for (const relPath of ['README.md', 'codex/README.md']) {
    const fullPath = path.join(REPO_ROOT, relPath);
    assert(fs.existsSync(fullPath), `${relPath} exists`);
    const content = fs.readFileSync(fullPath, 'utf8');

    assert(content.includes(expectedBadgeMd), `${relPath} contains 1-click Deploy to Render badge`);
    assert(content.includes('Deploy to Render (1-Click Live Cloud Backend)'), `${relPath} contains dedicated Render section`);
    assert(content.includes('render.yaml'), `${relPath} documents render.yaml Blueprint`);
    assert(content.includes('PORT'), `${relPath} documents PORT environment variable`);
    assert(content.includes('PYTHON_VERSION'), `${relPath} documents PYTHON_VERSION variable`);
    assert(content.includes('/api/health'), `${relPath} documents /api/health probe`);
    assert(content.includes('verify.html'), `${relPath} documents public verify portal`);

    // Validate URL syntax with WHATWG URL parser
    const parsedDeployUrl = new URL(expectedDeploy);
    assert(parsedDeployUrl.hostname === 'render.com', 'Deploy URL host is render.com');
    assert(parsedDeployUrl.pathname === '/deploy', 'Deploy URL path is /deploy');
    assert(parsedDeployUrl.searchParams.get('repo') === 'https://github.com/pradeepverma884027-cell/Brandwise-', 'Deploy URL repo parameter targets repository');

    const parsedImgUrl = new URL(expectedImg);
    assert(parsedImgUrl.hostname === 'render.com', 'Button image host is render.com');
    assert(parsedImgUrl.pathname === '/images/deploy-to-render-button.svg', 'Button image path is SVG');
  }
}

// --- SUITE 7: server.py Source Analysis for Port & HEAD Handling ---
console.log('\n--- SUITE 7: server.py Code Conformance ---');
{
  const sPath = path.join(REPO_ROOT, 'server.py');
  const code = fs.readFileSync(sPath, 'utf8');

  assert(code.includes("('0.0.0.0', test_port)"), "server.py binds to '0.0.0.0' for container compatibility");
  assert(code.includes('HTTPServer.allow_reuse_address = True'), 'server.py enables address reuse');
  assert(/PORT\s*=\s*int\(os\.environ\.get\("PORT",\s*sys\.argv\[1\]\s+if\s+len\(sys\.argv\)\s*>\s*1\s+else\s+8000\)\)/.test(code), 'server.py implements exact port precedence expression');
  assert(code.includes('def do_HEAD(self):'), 'server.py implements do_HEAD handler');
  assert(code.includes('if clean_path == "/api/health":'), 'server.py do_HEAD explicitly handles /api/health');
  assert(code.includes('Access-Control-Allow-Methods", "GET, POST, OPTIONS, HEAD"'), 'server.py advertises HEAD in CORS methods');
}

console.log('\n' + '='.repeat(80));
console.log(`TOTAL ASSERTIONS EVALUATED: ${totalAssertions}`);
console.log(`PASSED: ${passedAssertions}`);
console.log(`FAILED: ${failedAssertions}`);
console.log('='.repeat(80));

if (failedAssertions === 0) {
  console.log('\n>>> EMPIRICAL VERDICT: APPROVE <<<');
  process.exit(0);
} else {
  console.log('\n>>> EMPIRICAL VERDICT: REQUEST_CHANGES <<<');
  process.exit(1);
}
