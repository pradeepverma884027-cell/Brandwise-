/**
 * Challenger Verification Script: Babel JSX Parsing across All Three Mirrors
 * codex/frontend/index.html, index.html, and docs/index.html
 */

const fs = require('fs');
const path = require('path');

const repoRoot = path.resolve(__dirname, '..', '..');
const tsPath = path.resolve(repoRoot, 'codex', 'node_modules', 'typescript');

let ts;
try {
  ts = require(tsPath);
} catch (e) {
  console.error("Failed to load typescript from:", tsPath, e.message);
  process.exit(1);
}

const targetFiles = [
  path.join(repoRoot, 'codex', 'frontend', 'index.html'),
  path.join(repoRoot, 'index.html'),
  path.join(repoRoot, 'docs', 'index.html')
];

let allPassed = true;

for (const filePath of targetFiles) {
  console.log(`\n============================================================`);
  console.log(`Checking file: ${filePath}`);
  
  if (!fs.existsSync(filePath)) {
    console.error(`FAIL: File does not exist: ${filePath}`);
    allPassed = false;
    continue;
  }

  const html = fs.readFileSync(filePath, 'utf8');
  const match = html.match(/<script type="text\/babel">([\s\S]*?)<\/script>/);
  
  if (!match) {
    console.error(`FAIL: No <script type="text/babel"> block found in: ${filePath}`);
    allPassed = false;
    continue;
  }

  const code = match[1];
  const lineCount = code.split('\n').length;
  console.log(`Extracted Babel JSX script line count: ${lineCount}`);

  // Parse using TypeScript compiler with TSX syntax support
  const sf = ts.createSourceFile(
    path.basename(filePath) + '.tsx',
    code,
    ts.ScriptTarget.Latest,
    true,
    ts.ScriptKind.TSX
  );

  const diagnostics = sf.parseDiagnostics || [];
  console.log(`Syntactic parse diagnostics count: ${diagnostics.length}`);

  if (diagnostics.length > 0) {
    console.error(`FAIL: Found ${diagnostics.length} syntactic error(s) in ${filePath}:`);
    diagnostics.slice(0, 15).forEach(d => {
      const { line, character } = sf.getLineAndCharacterOfPosition(d.start);
      console.error(`  Line ${line + 1}:${character + 1} - ${d.messageText}`);
    });
    allPassed = false;
  } else {
    console.log(`PASS: Zero syntactic/JSX errors in ${path.basename(filePath)}!`);
  }

  // Verify critical Milestone 2 Hinglish identifiers exist inside the Babel script
  const requiredIdentifiers = [
    'simulateHinglishCompliance',
    'handleInspectHinglish',
    'handleOpenCounterEvidenceModal',
    'handleCounterEvidenceSubmit',
    'activeCounterTarget.source === \'hinglish\'',
    'dismissed_with_evidence',
    'hinglishRestoredScoreDelta',
    'openHinglishViolationsCount',
    'Instagram Caption (Hinglish)',
    'Influencer Video Script (Hinglish)'
  ];

  for (const id of requiredIdentifiers) {
    if (!code.includes(id)) {
      console.error(`FAIL: Missing required identifier in Babel script: "${id}"`);
      allPassed = false;
    } else {
      console.log(`  [OK] Found identifier: "${id}"`);
    }
  }
}

if (!allPassed) {
  console.error("\n>>> VERDICT: FAIL - Syntactic errors or missing identifiers detected.");
  process.exit(1);
} else {
  console.log("\n>>> VERDICT: SUCCESS - All 3 HTML files have 100% valid Babel JSX compilation!");
  process.exit(0);
}
