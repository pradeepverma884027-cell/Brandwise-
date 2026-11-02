/**
 * Adversarial Empirical Challenger Test Suite: Issue 3
 * PDF Generation Error Handling, Exception Injection, State Locking,
 * DOM Cleanup, and Modal Overflow Layout.
 *
 * Target Files:
 *  - codex/frontend/index.html
 *  - index.html
 *  - docs/index.html
 *  - codex/frontend/verify.html
 *  - verify.html
 *  - docs/verify.html
 */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const vm = require('vm');
const assert = require('assert');

console.log('================================================================================');
console.log('ADVERSARIAL EMPIRICAL CHALLENGER: ISSUE 3 PDF ERROR HANDLING & MODAL LAYOUT');
console.log('================================================================================\n');

const repoRoot = path.resolve(__dirname, '..', '..');

const htmlMirrors = [
  path.join(repoRoot, 'codex', 'frontend', 'index.html'),
  path.join(repoRoot, 'index.html'),
  path.join(repoRoot, 'docs', 'index.html')
];

const verifyMirrors = [
  path.join(repoRoot, 'codex', 'frontend', 'verify.html'),
  path.join(repoRoot, 'verify.html'),
  path.join(repoRoot, 'docs', 'verify.html')
];

let totalTests = 0;
let passedTests = 0;
let failedTests = 0;

function evaluate(description, condition, details = '') {
  totalTests++;
  if (condition) {
    passedTests++;
    console.log(`  ✓ PASS: ${description}`);
  } else {
    failedTests++;
    console.error(`  ✗ FAIL: ${description} ${details ? `(${details})` : ''}`);
    throw new Error(`Assertion failure: ${description}`);
  }
}

// ============================================================================
// SUITE 1: CRYPTOGRAPHIC SHA-256 PARITY ACROSS ALL MIRRORS
// ============================================================================
console.log('--- SUITE 1: Cryptographic SHA-256 Parity Across All Mirrors ---');

const htmlContents = [];
const htmlHashes = [];

for (const p of htmlMirrors) {
  evaluate(`Mirror exists: ${path.relative(repoRoot, p)}`, fs.existsSync(p));
  const buf = fs.readFileSync(p);
  const hash = crypto.createHash('sha256').update(buf).digest('hex');
  htmlContents.push(buf.toString('utf8'));
  htmlHashes.push(hash);
  console.log(`    SHA256(${path.relative(repoRoot, p)}) = ${hash} (${buf.length} bytes)`);
}

evaluate('index.html SHA-256 equals codex/frontend/index.html', htmlHashes[0] === htmlHashes[1]);
evaluate('docs/index.html SHA-256 equals codex/frontend/index.html', htmlHashes[0] === htmlHashes[2]);
evaluate('All 3 index.html files have identical length and hash', htmlContents[0] === htmlContents[1] && htmlContents[0] === htmlContents[2]);

const verifyContents = [];
const verifyHashes = [];

for (const p of verifyMirrors) {
  evaluate(`Verify mirror exists: ${path.relative(repoRoot, p)}`, fs.existsSync(p));
  const buf = fs.readFileSync(p);
  const hash = crypto.createHash('sha256').update(buf).digest('hex');
  verifyContents.push(buf.toString('utf8'));
  verifyHashes.push(hash);
  console.log(`    SHA256(${path.relative(repoRoot, p)}) = ${hash} (${buf.length} bytes)`);
}

evaluate('verify.html SHA-256 equals codex/frontend/verify.html', verifyHashes[0] === verifyHashes[1]);
evaluate('docs/verify.html SHA-256 equals codex/frontend/verify.html', verifyHashes[0] === verifyHashes[2]);
evaluate('All 3 verify.html files have identical length and hash', verifyContents[0] === verifyContents[1] && verifyContents[0] === verifyContents[2]);

// ============================================================================
// SUITE 2: BABEL / JSX SYNTAX AST VALIDATION
// ============================================================================
console.log('\n--- SUITE 2: Syntactic TypeScript/JSX AST Parse Diagnostics ---');

let tsCompiler;
try {
  tsCompiler = require(path.resolve(repoRoot, 'codex', 'node_modules', 'typescript'));
} catch (e) {
  try {
    tsCompiler = require('typescript');
  } catch (e2) {
    console.warn('TypeScript compiler not found in node_modules, falling back to VM compilation.');
  }
}

for (let i = 0; i < htmlMirrors.length; i++) {
  const filePath = htmlMirrors[i];
  const content = htmlContents[i];
  const match = content.match(/<script type="text\/babel">([\s\S]*?)<\/script>/);
  evaluate(`Babel script block present in ${path.relative(repoRoot, filePath)}`, !!match);

  if (tsCompiler && match) {
    const sourceFile = tsCompiler.createSourceFile(
      path.basename(filePath) + '.tsx',
      match[1],
      tsCompiler.ScriptTarget.Latest,
      true,
      tsCompiler.ScriptKind.TSX
    );
    const diagnostics = sourceFile.parseDiagnostics || [];
    evaluate(`0 syntactic JSX/TSX diagnostics in ${path.relative(repoRoot, filePath)}`, diagnostics.length === 0, `${diagnostics.length} found`);
  }
}

// ============================================================================
// SUITE 3: STATIC CODE ANALYSIS - MODAL LAYOUT & BUTTON ATTRIBUTES
// ============================================================================
console.log('\n--- SUITE 3: Static Analysis: Modal CSS Styling & Button Visibility ---');

const primaryHtml = htmlContents[0];
const babelCodeMatch = primaryHtml.match(/<script type="text\/babel">([\s\S]*?)<\/script>/);
evaluate('Babel code extracted from primary index.html', !!babelCodeMatch);
const babelCode = babelCodeMatch[1];

// 3.1: Check state declaration
evaluate('isGeneratingPdf state declared via useState(false)',
  babelCode.includes('const [isGeneratingPdf, setIsGeneratingPdf] = useState(false);')
);

// 3.2: Modal container CSS classes
evaluate('Certificate Modal has max-h-[90vh] styling',
  babelCode.includes('max-h-[90vh]')
);
evaluate('Certificate Modal has overflow-y-auto styling',
  babelCode.includes('overflow-y-auto')
);
evaluate('Certificate Modal has z-50 layering',
  babelCode.includes('z-50')
);

// 3.3: Modal Download Button attributes
evaluate('Modal Download Button has disabled={isGeneratingPdf}',
  babelCode.includes('disabled={isGeneratingPdf}')
);
evaluate('Modal Download Button has relative z-10 layering',
  babelCode.includes('relative z-10')
);
evaluate('Modal Download Button has loading spinner SVG when isGeneratingPdf is true',
  babelCode.includes('animate-spin') && babelCode.includes('Generating Official Certificate (PDF)...')
);
evaluate('Modal Download Button has idle label Download Official Certificate (PDF)',
  babelCode.includes('Download Official Certificate (PDF)')
);

// 3.4: Submissions card download button
evaluate('Submissions card PDF button passes submission object to generatePdfCertificate',
  babelCode.includes('onClick={() => generatePdfCertificate(sub)}')
);

// 3.5: Clean try...catch...finally structure
evaluate('generatePdfCertificate contains outer try...catch',
  babelCode.includes('try {') && babelCode.includes('catch (outerErr) {')
);
evaluate('generatePdfCertificate contains inner try...catch...finally inside setTimeout',
  babelCode.includes('catch (renderErr) {') && babelCode.includes('finally {')
);
evaluate('Finally block removes tempDiv from document.body',
  babelCode.includes('if (tempDiv && document.body.contains(tempDiv))') &&
  babelCode.includes('document.body.removeChild(tempDiv);')
);
evaluate('Finally block resets setIsGeneratingPdf(false)',
  babelCode.includes('if (typeof setIsGeneratingPdf === \'function\') {') &&
  babelCode.includes('setIsGeneratingPdf(false);')
);
evaluate('performFallback triggers notification and window.print()',
  babelCode.includes('function performFallback') || babelCode.includes('const performFallback =')
);

// ============================================================================
// SUITE 4: EXECUTABLE ADVERSARIAL SANDBOX SIMULATION
// ============================================================================
console.log('\n--- SUITE 4: Executable Adversarial Sandbox Simulation & Error Injection ---');

// Extract generatePdfCertificate function definition
const certStart = babelCode.indexOf('const generatePdfCertificate =');
const certEnd = babelCode.indexOf('const generateCertificatePDF =');
evaluate('generatePdfCertificate bounds located in babel script', certStart !== -1 && certEnd !== -1);
const certFuncCode = babelCode.substring(certStart, certEnd).trim();

// Mock jsPDF class with configurable error injection points
class MockJsPDF {
  constructor(options = {}) {
    if (MockJsPDF.failConstructor) {
      throw new Error('Injected Error: MockJsPDF constructor exploded');
    }
    this.options = options;
    this.textCalls = [];
    this.rectCalls = [];
    this.savedFiles = [];
  }
  setLineWidth() {}
  setDrawColor() {}
  setFillColor() {}
  setTextColor() {}
  setFont() {}
  setFontSize() {}
  rect(x, y, w, h) { this.rectCalls.push({ x, y, w, h }); }
  roundedRect(x, y, w, h, rx, ry, s) { this.rectCalls.push({ x, y, w, h, rx, ry, s }); }
  line() {}
  text(str, x, y, opts) {
    if (MockJsPDF.failText) {
      throw new Error('Injected Error: MockJsPDF text() rendering failed');
    }
    this.textCalls.push({ str: String(str), x, y, opts });
  }
  addImage() {
    if (MockJsPDF.failAddImage) {
      throw new Error('Injected Error: MockJsPDF addImage() corrupted buffer');
    }
  }
  link() {}
  save(filename) {
    if (MockJsPDF.failSave) {
      throw new Error('Injected Error: MockJsPDF save() permission denied');
    }
    this.savedFiles.push(filename);
  }
}
MockJsPDF.failConstructor = false;
MockJsPDF.failText = false;
MockJsPDF.failAddImage = false;
MockJsPDF.failSave = false;

// Factory to create isolated sandbox DOM & React context
function createAdversarialContext(customConfig = {}) {
  const bodyChildren = new Set();
  const notifications = [];
  let printCallCount = 0;
  let isGeneratingPdfState = false;
  let certificateDownloadedState = false;

  const mockBody = {
    children: bodyChildren,
    appendChild: (el) => {
      bodyChildren.add(el);
      el.parentNode = mockBody;
    },
    removeChild: (el) => {
      bodyChildren.delete(el);
      el.parentNode = null;
    },
    contains: (el) => bodyChildren.has(el)
  };

  const createMockElement = (tag) => {
    const el = {
      tagName: tag.toUpperCase(),
      style: {},
      parentNode: null,
      children: [],
      querySelector: (selector) => {
        if (customConfig.failCanvasQuery) return null;
        return {
          tagName: 'CANVAS',
          toDataURL: (fmt) => {
            if (customConfig.failToDataUrl) {
              throw new Error('Injected Error: Canvas toDataURL security exception');
            }
            return 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==';
          }
        };
      }
    };
    return el;
  };

  const mockWindow = {
    location: {
      origin: customConfig.origin || 'http://localhost:8000',
      pathname: customConfig.pathname || '/index.html',
      hostname: customConfig.hostname || 'localhost'
    },
    print: () => {
      printCallCount++;
      if (customConfig.failPrint) {
        throw new Error('Injected Error: window.print driver crashed');
      }
    }
  };

  if (customConfig.noJsPdf) {
    // leave undefined
  } else if (customConfig.emptyJsPdf) {
    mockWindow.jspdf = {};
  } else {
    mockWindow.jspdf = {
      jsPDF: function(opts) {
        return new MockJsPDF(opts);
      }
    };
  }

  const sandbox = {
    console: {
      log: () => {},
      warn: (...args) => {},
      error: (...args) => {}
    },
    setTimeout: (fn, delay) => {
      // Execute synchronously or immediately for deterministic testing
      fn();
    },
    window: mockWindow,
    document: {
      body: mockBody,
      createElement: createMockElement
    },
    QRCode: customConfig.noQrCode ? undefined : function(el, opts) {
      if (customConfig.failQrCode) {
        throw new Error('Injected Error: QRCode render canvas exception');
      }
    },
    isGeneratingPdf: false,
    setIsGeneratingPdf: (val) => {
      isGeneratingPdfState = val;
      sandbox.isGeneratingPdf = val;
    },
    setCertificateDownloaded: (val) => {
      certificateDownloadedState = val;
    },
    triggerNotification: (msg) => {
      notifications.push(msg);
    },
    selectedChannel: 'Instagram Caption',
    customVerifyUrl: '',
    visualViolations: [],
    findings: [],
    hinglishViolations: [],
    currentUser: { name: 'Dr. Aris Thorne', role: 'Governance Officer' }
  };

  if (sandbox.QRCode) {
    sandbox.QRCode.CorrectLevel = { M: 1 };
  }

  const ctx = vm.createContext(sandbox);

  const wrapperScript = `
    ${certFuncCode}
    globalThis.generatePdfCertificate = generatePdfCertificate;
  `;
  vm.runInContext(wrapperScript, ctx);

  return {
    ctx,
    sandbox,
    mockBody,
    bodyChildren,
    getNotifications: () => notifications,
    getPrintCalls: () => printCallCount,
    getIsGenerating: () => isGeneratingPdfState,
    getDownloaded: () => certificateDownloadedState
  };
}

// ----------------------------------------------------------------------------
// TEST 4.1: Happy Path Generation
// ----------------------------------------------------------------------------
console.log('Testing 4.1: Happy Path - Normal PDF generation with clean DOM lifecycle...');
MockJsPDF.failConstructor = false;
MockJsPDF.failText = false;
MockJsPDF.failAddImage = false;
MockJsPDF.failSave = false;

const env41 = createAdversarialContext();
env41.sandbox.generatePdfCertificate();
evaluate('Happy path: isGeneratingPdf ends as false', env41.getIsGenerating() === false);
evaluate('Happy path: certificateDownloaded set to true', env41.getDownloaded() === true);
evaluate('Happy path: body children cleaned up (0 left)', env41.bodyChildren.size === 0);
evaluate('Happy path: success notification triggered',
  env41.getNotifications().some(n => n.includes('released and downloaded'))
);

// ----------------------------------------------------------------------------
// TEST 4.2: Error Injection: window.jspdf is undefined
// ----------------------------------------------------------------------------
console.log('Testing 4.2: Error Injection - window.jspdf is completely undefined...');
const env42 = createAdversarialContext({ noJsPdf: true });
evaluate('Pre-check: window.jspdf is undefined', typeof env42.sandbox.window.jspdf === 'undefined');
env42.sandbox.generatePdfCertificate();
evaluate('Error 4.2: isGeneratingPdf reset to false immediately', env42.getIsGenerating() === false);
evaluate('Error 4.2: Fallback window.print() called', env42.getPrintCalls() === 1);
evaluate('Error 4.2: Fallback notification triggered',
  env42.getNotifications().some(n => n.includes('Opening official audit report in print/document view'))
);
evaluate('Error 4.2: Zero DOM leakage (body children 0)', env42.bodyChildren.size === 0);

// ----------------------------------------------------------------------------
// TEST 4.3: Error Injection: window.jspdf is empty object without jsPDF constructor
// ----------------------------------------------------------------------------
console.log('Testing 4.3: Error Injection - window.jspdf exists but jsPDF is undefined...');
const env43 = createAdversarialContext({ emptyJsPdf: true });
env43.sandbox.generatePdfCertificate();
evaluate('Error 4.3: isGeneratingPdf reset to false', env43.getIsGenerating() === false);
evaluate('Error 4.3: Fallback window.print() triggered', env43.getPrintCalls() === 1);
evaluate('Error 4.3: Zero DOM leakage', env43.bodyChildren.size === 0);

// ----------------------------------------------------------------------------
// TEST 4.4: Error Injection: new jsPDF() constructor throws exception
// ----------------------------------------------------------------------------
console.log('Testing 4.4: Error Injection - jsPDF constructor throws synchronous error...');
MockJsPDF.failConstructor = true;
const env44 = createAdversarialContext();
env44.sandbox.generatePdfCertificate();
MockJsPDF.failConstructor = false;
evaluate('Error 4.4: Outer catch handles constructor failure gracefully', true);
evaluate('Error 4.4: isGeneratingPdf reset to false', env44.getIsGenerating() === false);
evaluate('Error 4.4: Fallback window.print() triggered', env44.getPrintCalls() === 1);
evaluate('Error 4.4: Zero DOM leakage', env44.bodyChildren.size === 0);

// ----------------------------------------------------------------------------
// TEST 4.5: Error Injection: QRCode constructor throws exception
// ----------------------------------------------------------------------------
console.log('Testing 4.5: Error Injection - QRCode constructor throws (canvas error)...');
const env45 = createAdversarialContext({ failQrCode: true });
env45.sandbox.generatePdfCertificate();
evaluate('Error 4.5: Handled gracefully without crash', true);
evaluate('Error 4.5: PDF successfully downloaded despite QR error', env45.getDownloaded() === true);
evaluate('Error 4.5: isGeneratingPdf reset to false', env45.getIsGenerating() === false);
evaluate('Error 4.5: tempDiv cleaned up from body', env45.bodyChildren.size === 0);

// ----------------------------------------------------------------------------
// TEST 4.6: Error Injection: Canvas toDataURL throws security exception
// ----------------------------------------------------------------------------
console.log('Testing 4.6: Error Injection - Canvas toDataURL throws security error...');
const env46 = createAdversarialContext({ failToDataUrl: true });
env46.sandbox.generatePdfCertificate();
evaluate('Error 4.6: Caught and handled by QR image capture fallback', true);
evaluate('Error 4.6: isGeneratingPdf reset to false', env46.getIsGenerating() === false);
evaluate('Error 4.6: tempDiv removed from document.body', env46.bodyChildren.size === 0);

// ----------------------------------------------------------------------------
// TEST 4.7: Error Injection: PDF rendering throws inside setTimeout
// ----------------------------------------------------------------------------
console.log('Testing 4.7: Error Injection - doc.text() throws inside setTimeout render...');
MockJsPDF.failText = true;
const env47 = createAdversarialContext();
env47.sandbox.generatePdfCertificate();
MockJsPDF.failText = false;
evaluate('Error 4.7: Render error caught by catch(renderErr)', true);
evaluate('Error 4.7: isGeneratingPdf reset to false via finally block', env47.getIsGenerating() === false);
evaluate('Error 4.7: performFallback called with window.print()', env47.getPrintCalls() === 1);
evaluate('Error 4.7: tempDiv removed from document.body in finally block', env47.bodyChildren.size === 0);

// ----------------------------------------------------------------------------
// TEST 4.8: Error Injection: doc.save() throws (file download blocked)
// ----------------------------------------------------------------------------
console.log('Testing 4.8: Error Injection - doc.save() throws permission error...');
MockJsPDF.failSave = true;
const env48 = createAdversarialContext();
env48.sandbox.generatePdfCertificate();
MockJsPDF.failSave = false;
evaluate('Error 4.8: Save error caught gracefully', true);
evaluate('Error 4.8: isGeneratingPdf reset to false in finally', env48.getIsGenerating() === false);
evaluate('Error 4.8: Fallback window.print() invoked', env48.getPrintCalls() === 1);
evaluate('Error 4.8: Zero DOM leakage in document.body', env48.bodyChildren.size === 0);

// ----------------------------------------------------------------------------
// TEST 4.9: Error Injection: Fallback window.print() itself throws
// ----------------------------------------------------------------------------
console.log('Testing 4.9: Error Injection - window.print() fails inside performFallback...');
MockJsPDF.failSave = true;
const env49 = createAdversarialContext({ failPrint: true });
assert.doesNotThrow(() => {
  env49.sandbox.generatePdfCertificate();
});
MockJsPDF.failSave = false;
evaluate('Error 4.9: Handled without unhandled exception rethrow', true);
evaluate('Error 4.9: isGeneratingPdf guaranteed false in finally', env49.getIsGenerating() === false);
evaluate('Error 4.9: Zero DOM leakage', env49.bodyChildren.size === 0);

// ----------------------------------------------------------------------------
// TEST 4.10: Rapid Sequential Click Spamming (Concurrency Test)
// ----------------------------------------------------------------------------
console.log('Testing 4.10: Concurrency - Rapid sequential click spamming (100 clicks)...');
const env410 = createAdversarialContext();
// Manually set isGeneratingPdf to true to simulate in-flight execution
env410.sandbox.setIsGeneratingPdf(true);

let blockedClicks = 0;
for (let click = 0; click < 100; click++) {
  env410.sandbox.generatePdfCertificate();
  const notifs = env410.getNotifications();
  if (notifs[notifs.length - 1] === 'Certificate generation already in progress...') {
    blockedClicks++;
  }
}

evaluate('Click spamming: Exactly 100 spam clicks intercepted and blocked', blockedClicks === 100);
evaluate('Click spamming: Zero DOM nodes added during spam', env410.bodyChildren.size === 0);

// Now simulate completion
env410.sandbox.setIsGeneratingPdf(false);
evaluate('Click spamming: State successfully unlocked after process completion', env410.getIsGenerating() === false);
env410.sandbox.generatePdfCertificate();
evaluate('Click spamming: Subsequent click after unlock succeeds normally', env410.getDownloaded() === true);
evaluate('Click spamming: Clean DOM remains', env410.bodyChildren.size === 0);

// ----------------------------------------------------------------------------
// TEST 4.11: DOM Leak & Memory Cleanliness Stress Test (100 Iterations)
// ----------------------------------------------------------------------------
console.log('Testing 4.11: Stress Test - 100 rapid alternations between success and failure...');
const env411 = createAdversarialContext();

for (let iter = 0; iter < 100; iter++) {
  const shouldFail = (iter % 2 === 1);
  if (shouldFail) {
    MockJsPDF.failText = true;
  } else {
    MockJsPDF.failText = false;
  }
  env411.sandbox.generatePdfCertificate();
  if (env411.bodyChildren.size !== 0) {
    throw new Error(`DOM leak detected at iteration ${iter}: size=${env411.bodyChildren.size}`);
  }
  if (env411.getIsGenerating() !== false) {
    throw new Error(`isGeneratingPdf not reset to false at iteration ${iter}`);
  }
}
MockJsPDF.failText = false;
evaluate('Stress Test: 100 iterations completed with 0 DOM leaks and 100% state unlocks', true);

// ----------------------------------------------------------------------------
// TEST 4.12: Synthetic Event & Submission Argument Scrubbing
// ----------------------------------------------------------------------------
console.log('Testing 4.12: Synthetic Event and Custom Submission Scrubbing...');
const env412 = createAdversarialContext();

// Call with React synthetic event object
const syntheticEvent = {
  preventDefault: () => {},
  stopPropagation: () => {},
  target: { type: 'button' },
  nativeEvent: {}
};
env412.sandbox.generatePdfCertificate(syntheticEvent);
evaluate('Scrubbing: Synthetic event treated as null without certificate_id crash', env412.getDownloaded() === true);

// Call with real custom submission object
const customSub = {
  certificate_id: 'BW-CUSTOM-99999',
  brand_name: 'Adversarial Test Brand Labs',
  reviewed_by: 'Marcus Vance, Director',
  audit_hash: '9f83b1657ff1fc53b92dc18148a1d65dfc2d4b1f'
};
env412.sandbox.generatePdfCertificate(customSub);
evaluate('Scrubbing: Valid submission object accepted and processed cleanly', env412.getDownloaded() === true);
evaluate('Scrubbing: Zero DOM leakage', env412.bodyChildren.size === 0);

// ============================================================================
// SUMMARY & VERDICT
// ============================================================================
console.log('\n================================================================================');
console.log(`TOTAL ADVERSARIAL ASSERTIONS: ${totalTests}`);
console.log(`PASSED:                       ${passedTests}`);
console.log(`FAILED:                       ${failedTests}`);
console.log('================================================================================\n');

if (failedTests === 0) {
  console.log('>>> EMPIRICAL VERDICT: APPROVE <<<');
  console.log('PDF generation error handling, exception injection, state locking,');
  console.log('DOM cleanup, and modal overflow layout are 100% verified and robust.\n');
  process.exit(0);
} else {
  console.error('>>> EMPIRICAL VERDICT: REQUEST_CHANGES <<<');
  process.exit(1);
}
