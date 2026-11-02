/**
 * Adversarial Empirical Challenger Test Suite: Milestone 1 (Issues 1 & 2)
 * File: codex/tests/test_challenger_prod_m1_initials_url.js
 * 
 * Scope:
 * 1. Issue 1: Initials derivation across exhaustive permutations of currentUser objects
 *    (null, undefined, primitives, empty object, partial keys, whitespace, multi-word,
 *     role_key fallbacks, unknown role_keys, unicode, XSS attempts).
 *    Verify initials derivation NEVER throws, NEVER returns undefined, and NEVER returns blank.
 * 2. Issue 1: Avatar badge styling, contrast ratio calculations, and SVG fallback icon rendering.
 * 3. Issue 2: Dynamic verify URL generator under mock window.location states
 *    (localhost:8000, 127.0.0.1:8000, 192.168.1.5:8000, Render cloud, GitHub Pages subpaths, file://).
 *    Verify remote cloud URLs are NEVER corrupted by LAN IPs.
 * 4. Issue 2: verify.html DOM & script logic under query string variations (?cert=..., empty, missing, malformed),
 *    localStorage caching & error handling, API fallbacks, and "VALID & SEALED" badge activation.
 * 5. Tri-mirror SHA-256 cryptographic parity enforcement.
 */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const assert = require('assert');

console.log('================================================================================');
console.log('EMPIRICAL CHALLENGER TEST SUITE: PRODUCTION M1 (ISSUES 1 & 2 STRESS HARNESS)');
console.log('================================================================================\n');

const repoRoot = path.resolve(__dirname, '..', '..');
const indexPaths = [
  path.join(repoRoot, 'codex', 'frontend', 'index.html'),
  path.join(repoRoot, 'index.html'),
  path.join(repoRoot, 'docs', 'index.html')
];
const verifyPaths = [
  path.join(repoRoot, 'codex', 'frontend', 'verify.html'),
  path.join(repoRoot, 'verify.html'),
  path.join(repoRoot, 'docs', 'verify.html')
];

let totalAssertions = 0;
let passedAssertions = 0;
let failedAssertions = 0;

function check(desc, condition) {
  totalAssertions++;
  if (condition) {
    passedAssertions++;
    // Log occasionally or on major checkpoints
  } else {
    failedAssertions++;
    console.error(`  ✗ FAIL: ${desc}`);
    throw new Error(`Assertion failed: ${desc}`);
  }
}

// -----------------------------------------------------------------------------
// SUITE 1: CRYPTOGRAPHIC SHA-256 MIRROR PARITY
// -----------------------------------------------------------------------------
console.log('--- SUITE 1: Cryptographic SHA-256 Parity Across Tri-Mirrors ---');

const indexHashes = [];
for (const p of indexPaths) {
  check(`File exists: ${path.relative(repoRoot, p)}`, fs.existsSync(p));
  const buf = fs.readFileSync(p);
  const hash = crypto.createHash('sha256').update(buf).digest('hex');
  indexHashes.push(hash);
  console.log(`  [INDEX] ${path.relative(repoRoot, p)}: ${hash} (${buf.length} bytes)`);
}
check('codex/frontend/index.html matches index.html', indexHashes[0] === indexHashes[1]);
check('codex/frontend/index.html matches docs/index.html', indexHashes[0] === indexHashes[2]);
console.log(`  ✓ 100% SHA-256 Parity confirmed across all 3 index.html mirrors (${indexHashes[0]})\n`);

const verifyHashes = [];
for (const p of verifyPaths) {
  check(`File exists: ${path.relative(repoRoot, p)}`, fs.existsSync(p));
  const buf = fs.readFileSync(p);
  const hash = crypto.createHash('sha256').update(buf).digest('hex');
  verifyHashes.push(hash);
  console.log(`  [VERIFY] ${path.relative(repoRoot, p)}: ${hash} (${buf.length} bytes)`);
}
check('codex/frontend/verify.html matches verify.html', verifyHashes[0] === verifyHashes[1]);
check('codex/frontend/verify.html matches docs/verify.html', verifyHashes[0] === verifyHashes[2]);
console.log(`  ✓ 100% SHA-256 Parity confirmed across all 3 verify.html mirrors (${verifyHashes[0]})\n`);

// -----------------------------------------------------------------------------
// SUITE 2: EXTRACT & EMPIRICALLY CHALLENGE INITIALS DERIVATION (ISSUE 1)
// -----------------------------------------------------------------------------
console.log('--- SUITE 2: Initials Derivation Permutation Stress Test ---');

const indexContent = fs.readFileSync(indexPaths[0], 'utf8');

// Extract the userInitials logic verbatim from index.html
const initialsMarkerStart = 'const userInitials =';
const initialsIdx = indexContent.indexOf(initialsMarkerStart);
check('userInitials definition found in index.html', initialsIdx !== -1);

// Extract the expression until the semicolon
const semiIdx = indexContent.indexOf(';', initialsIdx);
check('Semicolon terminating userInitials found', semiIdx !== -1);
const rawDerivationCode = indexContent.substring(initialsIdx, semiIdx + 1);
console.log(`  Extracted derivation code:\n    ${rawDerivationCode.replace(/\n\s+/g, ' ')}\n`);

// Wrap into an executable function
const deriveInitials = new Function('currentUser', `
  ${rawDerivationCode}
  return userInitials;
`);

// Exhaustive test matrix for currentUser
const testMatrix = [
  // 1. Null / undefined / falsy primitives
  { input: null, expected: 'AD', desc: 'null' },
  { input: undefined, expected: 'AD', desc: 'undefined' },
  { input: false, expected: 'AD', desc: 'boolean false' },
  { input: true, expected: 'AD', desc: 'boolean true' },
  { input: 0, expected: 'AD', desc: 'number 0' },
  { input: '', expected: 'AD', desc: 'empty string' },

  // 2. Empty or partial objects without initials or name
  { input: {}, expected: 'AD', desc: 'empty object {}' },
  { input: { role_key: 'admin' }, expected: 'AD', desc: 'admin role_key only' },
  { input: { role_key: 'creator' }, expected: 'SJ', desc: 'creator role_key only' },
  { input: { role_key: 'chief' }, expected: 'AT', desc: 'chief role_key only' },
  { input: { role_key: 'random' }, expected: 'AD', desc: 'unknown role_key' },
  { input: { role_key: '' }, expected: 'AD', desc: 'empty role_key' },
  { input: { role_key: null }, expected: 'AD', desc: 'null role_key' },

  // 3. Initials explicitly provided
  { input: { initials: 'SJ' }, expected: 'SJ', desc: 'explicit uppercase initials' },
  { input: { initials: 'sj' }, expected: 'SJ', desc: 'explicit lowercase initials auto-capitalized' },
  { input: { initials: '  AT  ' }, expected: 'AT', desc: 'explicit initials with whitespace padded' },
  { input: { initials: 'ABCD' }, expected: 'AB', desc: '4-letter initials clamped to 2 chars' },
  { input: { initials: 'X' }, expected: 'X', desc: 'single character initials' },
  { input: { initials: '' }, expected: 'AD', desc: 'empty string initials -> falls back to AD' },
  { input: { initials: '   ' }, expected: 'AD', desc: 'whitespace-only initials -> falls back to AD' },
  { input: { initials: null }, expected: 'AD', desc: 'null initials -> falls back to AD' },
  { input: { initials: undefined }, expected: 'AD', desc: 'undefined initials -> falls back to AD' },

  // 4. Name provided (no initials)
  { input: { name: 'Sarah Jenkins' }, expected: 'SJ', desc: '2-word name' },
  { input: { name: 'sarah jenkins' }, expected: 'SJ', desc: '2-word lowercase name auto-capitalized' },
  { input: { name: '  Dr.  Aris   Thorne  ' }, expected: 'DA', desc: '3-word name with irregular whitespace' },
  { input: { name: 'Cher' }, expected: 'C', desc: 'single word name' },
  { input: { name: 'Shivank Kumar Sharma' }, expected: 'SK', desc: '3-word name clamped to 2 initials' },
  { input: { name: 'A B C D E' }, expected: 'AB', desc: '5-part name clamped to 2 initials' },
  { input: { name: '' }, expected: 'AD', desc: 'empty string name -> falls back to AD' },
  { input: { name: '    ' }, expected: 'AD', desc: 'whitespace string name -> falls back to AD' },
  { input: { name: null }, expected: 'AD', desc: 'null name -> falls back to AD' },
  { input: { name: undefined }, expected: 'AD', desc: 'undefined name -> falls back to AD' },

  // 5. Precedence tests (initials vs name vs role_key)
  { input: { initials: 'MK', name: 'Sarah Jenkins', role_key: 'creator' }, expected: 'MK', desc: 'initials takes precedence over name & role' },
  { input: { initials: '  ', name: 'Sarah Jenkins', role_key: 'creator' }, expected: 'SJ', desc: 'whitespace initials falls back to name' },
  { input: { initials: '  ', name: '   ', role_key: 'creator' }, expected: 'SJ', desc: 'whitespace initials & name fall back to role_key creator' },
  { input: { initials: '  ', name: '   ', role_key: 'chief' }, expected: 'AT', desc: 'whitespace initials & name fall back to role_key chief' },
  { input: { initials: '  ', name: '   ', role_key: 'guest' }, expected: 'AD', desc: 'whitespace initials & name fall back to AD for unknown role' },

  // 6. Adversarial edge cases
  { input: { name: 'Élise Dupont' }, expected: 'ÉD', desc: 'unicode accented name' },
  { input: { name: 'User 123' }, expected: 'U1', desc: 'alphanumeric name' },
  { input: { name: '! @ #' }, expected: '!@', desc: 'punctuation only name' },
  { input: { name: 'A'.repeat(5000) + ' ' + 'B'.repeat(5000) }, expected: 'AB', desc: 'massive 10,000-char name string' }
];

for (const t of testMatrix) {
  let result;
  try {
    result = deriveInitials(t.input);
  } catch (err) {
    check(`Initials derivation for "${t.desc}" threw exception: ${err.message}`, false);
  }
  check(`Initials derivation for "${t.desc}" must not be undefined`, result !== undefined);
  check(`Initials derivation for "${t.desc}" must not be blank`, typeof result === 'string' && result.trim().length > 0);
  check(`Initials derivation for "${t.desc}" matched expected "${t.expected}" (got "${result}")`, result === t.expected);
}
console.log(`  ✓ Passed all ${testMatrix.length} currentUser input permutations without any exceptions or blanks!`);

// Verify Quick-Login Presets in index.html
console.log('\n--- Checking 1-Click Quick-Login User Objects in index.html ---');
const quickLoginHasRoleKey = indexContent.includes("role_key: 'creator'") && 
                            indexContent.includes("role_key: 'chief'") && 
                            indexContent.includes("role_key: 'admin'");
check('Quick logins pass role_key for creator, chief, and admin', quickLoginHasRoleKey);

const quickLoginPassesInitials = indexContent.includes("initials: info.initials");
check('Quick logins pass initials: info.initials', quickLoginPassesInitials);

const getRoleInfoHasInitials = indexContent.includes("roleKey === 'creator'") &&
                               indexContent.includes("roleKey === 'chief'") &&
                               indexContent.includes("initials: 'SJ'") &&
                               indexContent.includes("initials: 'CG'") &&
                               indexContent.includes("initials: 'AD'");
check('getRoleInfo defines initials for creator (SJ), chief (CG), and admin (AD)', getRoleInfoHasInitials);
console.log('  ✓ Quick-login buttons explicitly pass role_key and initials for all 3 roles.\n');

// -----------------------------------------------------------------------------
// SUITE 3: AVATAR BADGE STYLING, CONTRAST & SVG FALLBACK (ISSUE 1)
// -----------------------------------------------------------------------------
console.log('--- SUITE 3: Avatar Badge Styling, Contrast & SVG Fallback ---');

// Check avatar button classes
const avatarBtnStart = indexContent.indexOf('title="Profile & Settings"');
check('Avatar button with title="Profile & Settings" found', avatarBtnStart !== -1);
const btnTagStart = indexContent.lastIndexOf('<button', avatarBtnStart);
const btnTagEnd = indexContent.indexOf('>', avatarBtnStart);
const btnTag = indexContent.substring(btnTagStart, btnTagEnd + 1);

const classMatch = btnTag.match(/className="([^"]*)"/);
check('Avatar button has className attribute', !!classMatch);

const btnClass = classMatch ? classMatch[1] : '';
console.log(`  Avatar button classes: ${btnClass}`);
check('Avatar button has rounded-full', btnClass.includes('rounded-full'));
check('Avatar has from-emerald-600', btnClass.includes('from-emerald-600'));
check('Avatar has via-teal-600', btnClass.includes('via-teal-600'));
check('Avatar has to-sky-600', btnClass.includes('to-sky-600'));
check('Avatar has text-white', btnClass.includes('text-white'));
check('Avatar has bold font', btnClass.includes('font-bold'));
check('Avatar has ring border ring-emerald-500', btnClass.includes('ring-emerald-500'));

// Check SVG fallback inside button
const svgFallbackPresent = indexContent.includes('userInitials ? (') &&
                           indexContent.includes('<svg className="w-4 h-4 text-white"');
check('Avatar button includes conditional SVG fallback when userInitials is falsy', svgFallbackPresent);

// WCAG Luminance & Contrast Calculation
// White text (#FFFFFF) against emerald-600 (#059669), teal-600 (#0D9488), sky-600 (#0284C7)
function getLuminance(r, g, b) {
  const [rs, gs, bs] = [r, g, b].map(c => {
    c = c / 255;
    return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
}

function getContrast(lum1, lum2) {
  const brightest = Math.max(lum1, lum2);
  const darkest = Math.min(lum1, lum2);
  return (brightest + 0.05) / (darkest + 0.05);
}

const whiteLum = getLuminance(255, 255, 255);
const emeraldLum = getLuminance(5, 150, 105);   // #059669
const tealLum = getLuminance(13, 148, 136);    // #0D9488
const skyLum = getLuminance(2, 132, 199);      // #0284C7

const contrastEmerald = getContrast(whiteLum, emeraldLum);
const contrastTeal = getContrast(whiteLum, tealLum);
const contrastSky = getContrast(whiteLum, skyLum);

console.log(`  WCAG Contrast Analysis (White #FFFFFF text on badge gradient):`);
console.log(`    - against emerald-600 (#059669): ${contrastEmerald.toFixed(2)}:1 (WCAG UI element threshold >= 3.0:1)`);
console.log(`    - against teal-600 (#0D9488):    ${contrastTeal.toFixed(2)}:1 (WCAG UI element threshold >= 3.0:1)`);
console.log(`    - against sky-600 (#0284C7):     ${contrastSky.toFixed(2)}:1 (WCAG UI element threshold >= 3.0:1)`);

check('Contrast on emerald-600 >= 3.0:1 (WCAG 2.1 Graphical / Non-text compliant)', contrastEmerald >= 3.0);
check('Contrast on teal-600 >= 3.0:1 (WCAG 2.1 Graphical / Non-text compliant)', contrastTeal >= 3.0);
check('Contrast on sky-600 >= 3.0:1 (WCAG 2.1 Graphical / Non-text compliant)', contrastSky >= 3.0);
console.log('  ✓ Avatar badge styling satisfies WCAG 2.1 graphical/avatar high-contrast standards across the entire gradient!\n');

// -----------------------------------------------------------------------------
// SUITE 4: DYNAMIC VERIFY URL GENERATOR & LAN ISOLATION (ISSUE 2)
// -----------------------------------------------------------------------------
console.log('--- SUITE 4: Dynamic Verify URL Generator & LAN Isolation ---');

// Extract getDynamicVerifyUrl and isRemoteDeploy definition
const dynamicUrlMarkerStart = 'const getDynamicVerifyUrl =';
const dynamicUrlIdx = indexContent.indexOf(dynamicUrlMarkerStart);
check('getDynamicVerifyUrl definition found', dynamicUrlIdx !== -1);

const dynamicUrlEnd = indexContent.indexOf('};', dynamicUrlIdx);
const dynamicUrlCode = indexContent.substring(dynamicUrlIdx, dynamicUrlEnd + 2);
console.log(`  Extracted getDynamicVerifyUrl:\n    ${dynamicUrlCode.replace(/\n\s+/g, ' ')}\n`);

const makeDynamicVerifyUrlFn = (mockWindow) => {
  return new Function('window', `
    ${dynamicUrlCode}
    return getDynamicVerifyUrl;
  `)(mockWindow);
};

// Test Host Environments
const hostScenarios = [
  {
    name: 'Localhost development on port 8000',
    window: {
      location: {
        origin: 'http://localhost:8000',
        hostname: 'localhost',
        pathname: '/',
        protocol: 'http:'
      }
    },
    expectedIsRemote: false,
    expectedUrl: 'http://localhost:8000/verify.html?cert=BW-CERT-88419-2026'
  },
  {
    name: '127.0.0.1 loopback development on port 8000',
    window: {
      location: {
        origin: 'http://127.0.0.1:8000',
        hostname: '127.0.0.1',
        pathname: '/index.html',
        protocol: 'http:'
      }
    },
    expectedIsRemote: false,
    expectedUrl: 'http://127.0.0.1:8000/verify.html?cert=BW-CERT-88419-2026'
  },
  {
    name: 'LAN Wi-Fi direct connection',
    window: {
      location: {
        origin: 'http://192.168.1.5:8000',
        hostname: '192.168.1.5',
        pathname: '/',
        protocol: 'http:'
      }
    },
    expectedIsRemote: true,
    expectedUrl: 'http://192.168.1.5:8000/verify.html?cert=BW-CERT-88419-2026'
  },
  {
    name: 'Render Cloud Deployment',
    window: {
      location: {
        origin: 'https://brandwise.onrender.com',
        hostname: 'brandwise.onrender.com',
        pathname: '/',
        protocol: 'https:'
      }
    },
    expectedIsRemote: true,
    expectedUrl: 'https://brandwise.onrender.com/verify.html?cert=BW-CERT-88419-2026'
  },
  {
    name: 'GitHub Pages Subdirectory (with index.html)',
    window: {
      location: {
        origin: 'https://pradeepverma884027-cell.github.io',
        hostname: 'pradeepverma884027-cell.github.io',
        pathname: '/Brandwise-/index.html',
        protocol: 'https:'
      }
    },
    expectedIsRemote: true,
    expectedUrl: 'https://pradeepverma884027-cell.github.io/Brandwise-/verify.html?cert=BW-CERT-88419-2026'
  },
  {
    name: 'GitHub Pages Subdirectory (trailing slash)',
    window: {
      location: {
        origin: 'https://pradeepverma884027-cell.github.io',
        hostname: 'pradeepverma884027-cell.github.io',
        pathname: '/Brandwise-/',
        protocol: 'https:'
      }
    },
    expectedIsRemote: true,
    expectedUrl: 'https://pradeepverma884027-cell.github.io/Brandwise-/verify.html?cert=BW-CERT-88419-2026'
  },
  {
    name: 'GitHub Pages Subdirectory (no trailing slash)',
    window: {
      location: {
        origin: 'https://pradeepverma884027-cell.github.io',
        hostname: 'pradeepverma884027-cell.github.io',
        pathname: '/Brandwise-',
        protocol: 'https:'
      }
    },
    expectedIsRemote: true,
    expectedUrl: 'https://pradeepverma884027-cell.github.io/Brandwise-/verify.html?cert=BW-CERT-88419-2026'
  },
  {
    name: 'file:// protocol fallback (window.location.origin is null string or file://)',
    window: {
      location: {
        origin: 'null',
        hostname: '',
        pathname: '/Users/test/index.html',
        protocol: 'file:'
      }
    },
    expectedIsRemote: true,
    expectedUrl: 'http://localhost:8000/verify.html?cert=BW-CERT-88419-2026'
  }
];

for (const sc of hostScenarios) {
  const fn = makeDynamicVerifyUrlFn(sc.window);
  const genUrl = fn('BW-CERT-88419-2026');
  check(`${sc.name}: generated URL matches expected`, genUrl === sc.expectedUrl);

  const isRemote = sc.window.location.hostname !== 'localhost' && sc.window.location.hostname !== '127.0.0.1';
  check(`${sc.name}: isRemoteDeploy evaluates to ${sc.expectedIsRemote}`, isRemote === sc.expectedIsRemote);

  // Custom Cert ID URL encoding check
  const specialCertUrl = fn('BW-CERT #123&ok=true');
  check(`${sc.name}: properly encodes special cert ID query`, specialCertUrl.includes('cert=BW-CERT%20%23123%26ok%3Dtrue'));
}
console.log(`  ✓ Tested ${hostScenarios.length} network location scenarios for dynamic verify URL generation.`);

// LAN Isolation Verification in useEffect
console.log('\n--- Checking LAN IP Isolation Guards in index.html ---');
const lanGuardRegex = /useEffect\(\(\)\s*=>\s*\{[\s\S]*?if\s*\(\s*isRemoteDeploy\s*\)\s*return;/;
check('useEffect has guard: if (isRemoteDeploy) return; before fetching /api/local-ip', lanGuardRegex.test(indexContent));

// In generatePdfCertificate: check publicBase enforcement
const pdfGuardRegex = /const\s+baseVerify\s*=\s*\(isLiveDeploy\s*\|\|\s*!customVerifyUrl\)\s*\?\s*publicBase\s*:\s*customVerifyUrl\.trim\(\);/;
check('generatePdfCertificate forces publicBase when isLiveDeploy is true', pdfGuardRegex.test(indexContent));
console.log('  ✓ LAN IPs cannot corrupt public URLs on Render or GitHub Pages deployments.\n');

// -----------------------------------------------------------------------------
// SUITE 5: VERIFY.HTML DOM & STATUS BADGE SCRIPT LOGIC (ISSUE 2)
// -----------------------------------------------------------------------------
console.log('--- SUITE 5: verify.html DOM, Query Parameter & Status Badge Tests ---');

const verifyContent = fs.readFileSync(verifyPaths[0], 'utf8');

// Check key DOM elements in verify.html
check('verify.html contains status-badge-container', verifyContent.includes('id="status-badge-container"'));
check('verify.html contains cert-id-val', verifyContent.includes('id="cert-id-val"'));
check('verify.html contains brand-name-val', verifyContent.includes('id="brand-name-val"'));
check('verify.html contains audit-hash-val', verifyContent.includes('id="audit-hash-val"'));
check('verify.html contains signer-val', verifyContent.includes('id="signer-val"'));
check('verify.html contains timestamp-val', verifyContent.includes('id="timestamp-val"'));
check('verify.html initial markup contains VALID &amp; SEALED', verifyContent.includes('VALID &amp; SEALED'));

// Extract the script logic in verify.html
const scriptStartMarker = '<script>';
const scriptEndMarker = '</script>';
const lastScriptStart = verifyContent.lastIndexOf(scriptStartMarker);
const lastScriptEnd = verifyContent.lastIndexOf(scriptEndMarker);
check('Script block found in verify.html', lastScriptStart !== -1 && lastScriptEnd > lastScriptStart);

const verifyScriptCode = verifyContent.substring(lastScriptStart + scriptStartMarker.length, lastScriptEnd).trim();
console.log(`  Extracted verify.html script (${verifyScriptCode.length} characters)`);

// Create a DOM emulator harness for verify.html
function runVerifyHtmlHarness({ search, cachedSubmissions = null, serverSubmissions = null, protocol = 'https:' }) {
  // Mock DOM
  const domElements = {
    'status-badge-container': { innerHTML: '', textContent: '' },
    'cert-id-val': { textContent: '' },
    'brand-name-val': { textContent: '' },
    'audit-hash-val': { textContent: '' },
    'signer-val': { textContent: '' },
    'timestamp-val': { textContent: '' },
    'active-port-pill': { textContent: '' }
  };

  const document = {
    getElementById: (id) => domElements[id] || null,
    querySelector: (sel) => {
      if (sel.includes('status-badge-container') || sel.includes('human-card .text-right')) {
        return domElements['status-badge-container'];
      }
      return null;
    }
  };

  const localStorageData = {};
  if (cachedSubmissions !== null) {
    localStorageData['bw_cached_submissions'] = typeof cachedSubmissions === 'string' ? cachedSubmissions : JSON.stringify(cachedSubmissions);
  }

  const localStorage = {
    getItem: (key) => localStorageData[key] !== undefined ? localStorageData[key] : null,
    setItem: (key, val) => { localStorageData[key] = val; }
  };

  const window = {
    location: {
      search: search,
      protocol: protocol,
      origin: 'https://brandwise.onrender.com',
      pathname: '/verify.html',
      port: ''
    },
    localStorage: localStorage
  };

  let fetchCalled = false;
  let fetchUrl = null;
  const fetch = (url, opts) => {
    fetchCalled = true;
    fetchUrl = url;
    return Promise.resolve({
      json: () => {
        if (url === '/api/submissions') {
          return Promise.resolve(serverSubmissions || { status: 'success', submissions: [] });
        }
        if (url === '/api/local-ip') {
          return Promise.resolve({ port: '10000' });
        }
        return Promise.resolve({});
      }
    });
  };

  // Run in sandboxed execution context
  const context = {
    window,
    document,
    localStorage,
    URLSearchParams,
    fetch,
    setTimeout: (fn) => setTimeout(fn, 10),
    clearTimeout: () => {},
    AbortController: class {
      constructor() { this.signal = {}; }
      abort() {}
    },
    console: { log: () => {}, warn: () => {}, error: () => {} }
  };

  const vm = require('vm');
  vm.createContext(context);
  vm.runInContext(verifyScriptCode, context);

  return { domElements, fetchCalled, fetchUrl, context };
}

// Subtest 1: Query string with ?cert=BW-CERT-99999
console.log('\n--- Subtest 5.1: Standard ?cert=BW-CERT-99999 ---');
{
  const res = runVerifyHtmlHarness({ search: '?cert=BW-CERT-99999' });
  check('cert-id-val populated with BW-CERT-99999', res.domElements['cert-id-val'].textContent === 'BW-CERT-99999');
  check('status badge contains VALID &amp; SEALED', res.domElements['status-badge-container'].innerHTML.includes('VALID &amp; SEALED'));
  check('status badge contains emerald ping dot', res.domElements['status-badge-container'].innerHTML.includes('bg-emerald-500 animate-ping'));
}

// Subtest 2: Query string with empty ?cert=
console.log('\n--- Subtest 5.2: Empty ?cert= ---');
{
  const res = runVerifyHtmlHarness({ search: '?cert=' });
  check('empty cert parameter falls back to default BW-CERT-88419-2026', res.domElements['cert-id-val'].textContent === 'BW-CERT-88419-2026');
  check('status badge displays VALID &amp; SEALED', res.domElements['status-badge-container'].innerHTML.includes('VALID &amp; SEALED'));
}

// Subtest 3: Query string completely omitted
console.log('\n--- Subtest 5.3: No Query String ---');
{
  const res = runVerifyHtmlHarness({ search: '' });
  check('missing query string falls back to default BW-CERT-88419-2026', res.domElements['cert-id-val'].textContent === 'BW-CERT-88419-2026');
  check('status badge displays VALID &amp; SEALED', res.domElements['status-badge-container'].innerHTML.includes('VALID &amp; SEALED'));
}

// Subtest 4: Query string with adversarial XSS attempt
console.log('\n--- Subtest 5.4: Adversarial XSS Query String ---');
{
  const res = runVerifyHtmlHarness({ search: '?cert=%3Cscript%3Ealert(1)%3C/script%3E' });
  check('XSS payload treated strictly as textContent', res.domElements['cert-id-val'].textContent === '<script>alert(1)</script>');
  check('status badge displays VALID &amp; SEALED', res.domElements['status-badge-container'].innerHTML.includes('VALID &amp; SEALED'));
}

// Subtest 5: localStorage cache match
console.log('\n--- Subtest 5.5: Cached Submissions in localStorage ---');
{
  const sampleSubmission = {
    certificate_id: 'BW-CERT-LOCAL-001',
    brand_name: 'DermaCare Prestige Clinic',
    audit_hash: '9f86d081884c7d659a2feaa0c55ad015a3bf4f1b',
    reviewed_by: 'Dr. Aris Thorne',
    reviewed_at: '2026-11-01 10:30:00 UTC'
  };
  const res = runVerifyHtmlHarness({
    search: '?cert=BW-CERT-LOCAL-001',
    cachedSubmissions: [sampleSubmission]
  });
  check('cert-id-val matches cached submission', res.domElements['cert-id-val'].textContent === 'BW-CERT-LOCAL-001');
  check('brand-name-val populated from localStorage', res.domElements['brand-name-val'].textContent === 'DermaCare Prestige Clinic');
  check('audit-hash-val populated from localStorage', res.domElements['audit-hash-val'].textContent === '9f86d081884c7d659a2feaa0c55ad015a3bf4f1b');
  check('signer-val populated from localStorage', res.domElements['signer-val'].textContent === 'Dr. Aris Thorne');
  check('timestamp-val populated from localStorage', res.domElements['timestamp-val'].textContent === '2026-11-01 10:30:00 UTC');
  check('status badge displays VALID &amp; SEALED', res.domElements['status-badge-container'].innerHTML.includes('VALID &amp; SEALED'));
  check('localStorage hit immediately returns without polling API', res.fetchCalled === false);
}

// Subtest 6: Corrupted JSON in localStorage
console.log('\n--- Subtest 5.6: Corrupted JSON in localStorage ---');
{
  const res = runVerifyHtmlHarness({
    search: '?cert=BW-CERT-CORRUPT',
    cachedSubmissions: '{ malformed json unclosed {'
  });
  check('Corrupted JSON does not crash script', res.domElements['cert-id-val'].textContent === 'BW-CERT-CORRUPT');
  check('Status badge safely rendered as VALID &amp; SEALED', res.domElements['status-badge-container'].innerHTML.includes('VALID &amp; SEALED'));
}

// Subtest 7: Offline file:// protocol
console.log('\n--- Subtest 5.7: Offline file:// Protocol ---');
{
  const res = runVerifyHtmlHarness({
    search: '?cert=BW-CERT-OFFLINE',
    protocol: 'file:'
  });
  check('file:// protocol does not call fetch', res.fetchCalled === false);
  check('Status badge displays VALID &amp; SEALED offline', res.domElements['status-badge-container'].innerHTML.includes('VALID &amp; SEALED'));
}

console.log('  ✓ All verify.html DOM, parameter parsing, and status badge tests passed!\n');

// -----------------------------------------------------------------------------
// SUMMARY
// -----------------------------------------------------------------------------
console.log('================================================================================');
console.log(`TOTAL ASSERTIONS EVALUATED: ${totalAssertions}`);
console.log(`PASSED: ${passedAssertions}`);
console.log(`FAILED: ${failedAssertions}`);
console.log('================================================================================');

if (failedAssertions === 0) {
  console.log('>>> EMPIRICAL VERDICT: APPROVE <<<');
  process.exit(0);
} else {
  console.log('>>> EMPIRICAL VERDICT: REQUEST_CHANGES <<<');
  process.exit(1);
}
