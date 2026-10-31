// Empirical Challenger Test Suite for Milestone 2:
// Multilingual & Code-Mixed (Hinglish) Advertising Compliance Engine
// File: codex/tests/test_empirical_challenger_m2.js

const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assert = require('assert');

console.log('================================================================');
console.log('CHALLENGER 1 EMPIRICAL TEST SUITE: MILESTONE 2 (FRONTEND SIMULATION)');
console.log('================================================================\n');

// 1. Load codex/frontend/index.html and extract simulateHinglishCompliance
const htmlPath = path.resolve(__dirname, '../frontend/index.html');
assert(fs.existsSync(htmlPath), `HTML file does not exist at ${htmlPath}`);
const htmlContent = fs.readFileSync(htmlPath, 'utf8');

const startMarker = 'const simulateHinglishCompliance =';
const endMarker = 'const handleInspectHinglish =';
const startIdx = htmlContent.indexOf(startMarker);
assert(startIdx !== -1, 'Start marker for simulateHinglishCompliance not found');
const endIdx = htmlContent.indexOf(endMarker, startIdx);
assert(endIdx !== -1, 'End marker handleInspectHinglish not found');

const simFunctionCode = htmlContent.substring(startIdx, endIdx).trim();
console.log(`[PASS] Extracted simulateHinglishCompliance (${simFunctionCode.length} bytes)`);

// Create executable function
const simulateHinglishCompliance = new Function(`${simFunctionCode}\nreturn simulateHinglishCompliance;`)();
assert(typeof simulateHinglishCompliance === 'function', 'Extracted simulateHinglishCompliance is not a function');

// Track overall test metrics
let totalAssertions = 0;
let passedAssertions = 0;
let failedAssertions = 0;

function check(desc, condition) {
  totalAssertions++;
  if (condition) {
    passedAssertions++;
    // console.log(`  ✓ ${desc}`);
  } else {
    failedAssertions++;
    console.error(`  ✗ FAIL: ${desc}`);
    throw new Error(`Assertion failed: ${desc}`);
  }
}

// -------------------------------------------------------------
// SUITE 1: SYNTHETIC PRESETS FROM UI
// -------------------------------------------------------------
console.log('\n--- SUITE 1: Synthetic Presets from codex/frontend/index.html ---');

// Preset 1: Violation Sample
const presetViolation = "Hey guys!! DermaCare leke aaya hai chamatkari formula jo dega 100% asar acne par aur 7 din mein gora rang! Aaj hi order karein link bio mein aur paayein 50% discount!";
console.log('\nTesting Preset 1 (Violation Sample):');
const resPreset1 = simulateHinglishCompliance(presetViolation, 'hinglish_instagram');
console.log(`  Findings count: ${resPreset1.findings.length}, Score: ${resPreset1.compliance_score}`);

check('Preset 1 status is success', resPreset1.status === 'success');
check('Preset 1 is not compliant', resPreset1.summary.is_compliant === false);
check('Preset 1 score is bounded [0, 100]', resPreset1.compliance_score >= 0 && resPreset1.compliance_score <= 100);
check('Preset 1 flags multiple violations (>= 4)', resPreset1.findings.length >= 4);

const p1Highlighted = resPreset1.findings.map(f => f.highlighted_text);
console.log('  Highlighted phrases:', p1Highlighted);
check('Preset 1 flags "chamatkari"', p1Highlighted.some(t => /chamatkari/i.test(t)));
check('Preset 1 flags "100% asar"', p1Highlighted.some(t => /100%\s*asar/i.test(t)));
check('Preset 1 flags "gora rang"', p1Highlighted.some(t => /gora\s*rang/i.test(t)));
check('Preset 1 flags missing vernacular disclosure', resPreset1.findings.some(f => f.rule_id === 'HINGLISH-DISCLOSURE-04'));
check('Preset 1 score is 20 (4 high violations x -20)', resPreset1.compliance_score === 20);
check('Preset 1 does NOT flag commercial "50% discount" as clinical exaggeration', !resPreset1.findings.some(f => f.rule_id === 'HINGLISH-CLINICAL-EXAGGERATION-05' && f.highlighted_text.includes('50%')));

// Preset 2: Clean Copy Sample
const presetClean = "DermaCare ka naya hydrating moisturizer daily skin barrier support karta hai aur hydration improve karta hai. Aaj hi try karein! #vigyapan #ad";
console.log('\nTesting Preset 2 (Clean Copy Sample):');
const resPreset2 = simulateHinglishCompliance(presetClean, 'hinglish_instagram');
console.log(`  Findings count: ${resPreset2.findings.length}, Score: ${resPreset2.compliance_score}`);

check('Preset 2 status is success', resPreset2.status === 'success');
check('Preset 2 findings is empty', resPreset2.findings.length === 0);
check('Preset 2 score is exactly 100', resPreset2.compliance_score === 100);
check('Preset 2 is_compliant is true', resPreset2.summary.is_compliant === true);

// Preset 3: Clinical Exaggeration & Traditional Cure Sample
const presetExaggeration = "Dosto agar acne se pareshan ho toh ye cream hai aapka ramban ilaj! Clinical trials mein 100% asar dekha gaya hai jo acne ko jad se khatam karega! Loot lo ye offer #vigyapan";
console.log('\nTesting Preset 3 (Clinical Exaggeration Sample):');
const resPreset3 = simulateHinglishCompliance(presetExaggeration, 'hinglish_instagram');
console.log(`  Findings count: ${resPreset3.findings.length}, Score: ${resPreset3.compliance_score}`);

check('Preset 3 status is success', resPreset3.status === 'success');
check('Preset 3 is not compliant', resPreset3.summary.is_compliant === false);
check('Preset 3 score is bounded [0, 100]', resPreset3.compliance_score >= 0 && resPreset3.compliance_score <= 100);

const p3Highlighted = resPreset3.findings.map(f => f.highlighted_text);
console.log('  Highlighted phrases:', p3Highlighted);
check('Preset 3 flags "ramban ilaj"', p3Highlighted.some(t => /ramban\s*ilaj/i.test(t)));
check('Preset 3 flags "jad se khatam"', p3Highlighted.some(t => /jad\s*se\s*khatam/i.test(t)));
check('Preset 3 flags "100% asar" clinical exaggeration', resPreset3.findings.some(f => f.rule_id === 'HINGLISH-CLINICAL-EXAGGERATION-05' || /100%\s*asar/i.test(f.highlighted_text)));
check('Preset 3 has #vigyapan so no missing disclosure finding', !resPreset3.findings.some(f => f.rule_id === 'HINGLISH-DISCLOSURE-04'));

// -------------------------------------------------------------
// SUITE 2: EDGE CASES & ADVERSARIAL INPUTS
// -------------------------------------------------------------
console.log('\n--- SUITE 2: Edge Cases & Adversarial Inputs ---');

// Empty string
console.log('\nTesting Empty string:');
const resEmpty = simulateHinglishCompliance('', 'hinglish_instagram');
check('Empty string returns 0 findings', resEmpty.findings.length === 0);
check('Empty string score is 100', resEmpty.compliance_score === 100);
check('Empty string is_compliant is true', resEmpty.summary.is_compliant === true);

// Whitespace string
console.log('\nTesting Whitespace string:');
const resWhitespace = simulateHinglishCompliance('   \t\n\r   ', 'hinglish_instagram');
check('Whitespace string returns 0 findings', resWhitespace.findings.length === 0);
check('Whitespace string score is 100', resWhitespace.compliance_score === 100);
check('Whitespace string is_compliant is true', resWhitespace.summary.is_compliant === true);

// Non-string / null / undefined inputs
console.log('\nTesting Non-string / null / undefined inputs:');
const resNull = simulateHinglishCompliance(null, 'hinglish_instagram');
check('null input returns 0 findings safely', resNull.findings.length === 0 && resNull.compliance_score === 100);

const resUndef = simulateHinglishCompliance(undefined, 'hinglish_instagram');
check('undefined input returns 0 findings safely', resUndef.findings.length === 0 && resUndef.compliance_score === 100);

const resNum = simulateHinglishCompliance(12345, 'hinglish_instagram');
check('number input returns 0 findings safely', resNum.findings.length === 0 && resNum.compliance_score === 100);

const resObj = simulateHinglishCompliance({}, 'hinglish_instagram');
check('object input returns 0 findings safely', resObj.findings.length === 0 && resObj.compliance_score === 100);

// Commercial Discounts Edge Cases
console.log('\nTesting Commercial Discounts:');
const discountSamples = [
  "Abhi order karein aur paayein flat 50% discount hamari website par! #vigyapan",
  "Special festival deal: 20% off on all sunscreen products #ad",
  "Use code BEAUTY30 to get 30% cashback on your first purchase #sponsored",
  "Heavy monsoon 40% sale live now! #vigyapan",
  "Flat 15% chhoot sabhi products par #prayasit"
];

for (const sample of discountSamples) {
  const res = simulateHinglishCompliance(sample, 'hinglish_instagram');
  const clinicalFindings = res.findings.filter(f => f.rule_id === 'HINGLISH-CLINICAL-EXAGGERATION-05' || f.rule_id === 'HINGLISH-CLINICAL-BORDERLINE-06');
  check(`Commercial discount not flagged as clinical: "${sample.substring(0, 40)}..."`, clinicalFindings.length === 0);
  check(`Discount sample score is 100: "${sample.substring(0, 40)}..."`, res.compliance_score === 100);
}

// Genuine Clinical vs Commercial Disambiguation
console.log('\nTesting Genuine Clinical vs Commercial Disambiguation:');
const genuineClinical = "Clinical study CS-2026-88 mein 98% asar dekha gaya #ad";
const resGenClin = simulateHinglishCompliance(genuineClinical, 'hinglish_instagram');
check('Clinical 98% asar flagged as clinical exaggeration', resGenClin.findings.some(f => f.rule_id === 'HINGLISH-CLINICAL-EXAGGERATION-05'));

const borderlineClinical = "Clinical study CS-2026-88 mein 94% asar dekha gaya #ad";
const resBorderClin = simulateHinglishCompliance(borderlineClinical, 'hinglish_instagram');
check('Clinical 94% asar flagged as borderline rounding', resBorderClin.findings.some(f => f.rule_id === 'HINGLISH-CLINICAL-BORDERLINE-06'));

// Unicode & Devanagari Script Tests
console.log('\nTesting Unicode & Devanagari Inputs:');
const devanagariClean = "यह एक प्राकृतिक क्रीम है जो त्वचा को नमी प्रदान करती है। #vigyapan";
const resDevClean = simulateHinglishCompliance(devanagariClean, 'hinglish_instagram');
check('Pure Devanagari clean copy parses safely with 0 errors', resDevClean.status === 'success' && resDevClean.compliance_score === 100);

const mixedDevanagariHinglish = "Ye formula त्वचा ko chamatkari hydration deta hai aur gora rang banata hai #ad";
const resMixed = simulateHinglishCompliance(mixedDevanagariHinglish, 'hinglish_instagram');
check('Mixed Devanagari-Hinglish detects "chamatkari"', resMixed.findings.some(f => /chamatkari/i.test(f.highlighted_text)));
check('Mixed Devanagari-Hinglish detects "gora rang"', resMixed.findings.some(f => /gora\s*rang/i.test(f.highlighted_text)));

// 50,000 Characters Stress Test (Clean copy performance)
console.log('\nTesting 50,000 Characters Stress Test (Clean text):');
const safeChunk = "DermaCare daily moisturizer skin barrier support karta hai aur hydration deta hai. ";
const bigSafeText = safeChunk.repeat(Math.ceil(50000 / safeChunk.length)).slice(0, 50000) + " #vigyapan #ad";
const tStart1 = performance.now();
const resBigSafe = simulateHinglishCompliance(bigSafeText, 'hinglish_instagram');
const tEnd1 = performance.now();
const elapsed1 = tEnd1 - tStart1;
console.log(`  50,000 clean chars executed in ${elapsed1.toFixed(2)} ms`);
check('50,000 clean chars executes within 500ms', elapsed1 < 500);
check('50,000 clean chars score is 100', resBigSafe.compliance_score === 100);
check('50,000 clean chars findings count is 0', resBigSafe.findings.length === 0);

// 50,000 Characters Stress Test with Hundreds of Violations (Score floor & performance)
console.log('\nTesting 50,000 Characters with Multiple Violations:');
const violationChunk = "DermaCare leke aaya chamatkari 100% asar gora rang ramban ilaj bilkul theek! ";
const bigViolText = violationChunk.repeat(Math.ceil(50000 / violationChunk.length)).slice(0, 50000);
const tStart2 = performance.now();
const resBigViol = simulateHinglishCompliance(bigViolText, 'hinglish_instagram');
const tEnd2 = performance.now();
const elapsed2 = tEnd2 - tStart2;
console.log(`  50,000 violation chars executed in ${elapsed2.toFixed(2)} ms with ${resBigViol.findings.length} findings`);
check('50,000 chars with violations executes within 1000ms', elapsed2 < 1000);
check('Score is clamped at minimum 0 (NEVER drops below 0)', resBigViol.compliance_score === 0);
check('Summary reports correct total findings', resBigViol.summary.total_findings === resBigViol.findings.length);

// -------------------------------------------------------------
// SUITE 3: SCORE BOUNDARY RIGOROUS INVARIANTS [0, 100]
// -------------------------------------------------------------
console.log('\n--- SUITE 3: Score Boundary Invariants [0, 100] ---');

// Test monotonic deduction and clamping
const incrementalTests = [
  { desc: "0 violations", text: "Clean skin care product #vigyapan", expectedMin: 100, expectedMax: 100 },
  { desc: "1 high violation (-20)", text: "Ye formula chamatkari hai #vigyapan", expectedMin: 80, expectedMax: 80 },
  { desc: "2 high violations (-40)", text: "Ye chamatkari formula deta hai gora rang #vigyapan", expectedMin: 60, expectedMax: 60 },
  { desc: "3 high violations (-60)", text: "Ye chamatkari formula deta hai gora rang ramban ilaj #vigyapan", expectedMin: 40, expectedMax: 40 },
  { desc: "4 high violations (-80)", text: "Ye chamatkari formula deta hai gora rang ramban ilaj pakka ilaj #vigyapan", expectedMin: 20, expectedMax: 20 },
  { desc: "5 high violations (-100)", text: "Ye chamatkari formula deta hai gora rang ramban ilaj pakka ilaj bilkul theek #vigyapan", expectedMin: 0, expectedMax: 0 },
  { desc: "6 high violations (-120 clamped)", text: "Ye chamatkari formula deta hai gora rang ramban ilaj pakka ilaj bilkul theek shat pratishat #vigyapan", expectedMin: 0, expectedMax: 0 },
  { desc: "10 high violations (-200 clamped)", text: "chamatkari gora rang ramban ilaj pakka ilaj bilkul theek shat pratishat jad se khatam hamesha ke liye ek jhatke mein fairness guarantee #vigyapan", expectedMin: 0, expectedMax: 0 }
];

for (const t of incrementalTests) {
  const r = simulateHinglishCompliance(t.text, 'hinglish_instagram');
  check(`Score for [${t.desc}] is within [${t.expectedMin}, ${t.expectedMax}]: actual ${r.compliance_score}`,
    r.compliance_score >= t.expectedMin && r.compliance_score <= t.expectedMax);
  check(`Score is always >= 0 for [${t.desc}]`, r.compliance_score >= 0);
  check(`Score is always <= 100 for [${t.desc}]`, r.compliance_score <= 100);
}

// -------------------------------------------------------------
// SUITE 4: ALL 18 SPECIFIED PATTERNS EMPIRICAL COVERAGE
// -------------------------------------------------------------
console.log('\n--- SUITE 4: All Prohibited Patterns & Rules Verification ---');

const patternTestCases = [
  // Superlatives
  { pattern: "100% asar", input: "Ye cream 100% asar dikhayegi #vigyapan", rule: "HINGLISH-SUPERLATIVE-01" },
  { pattern: "100% asardaar", input: "Ye formula 100% asardaar hai #vigyapan", rule: "HINGLISH-SUPERLATIVE-01" },
  { pattern: "chamatkari", input: "Chamatkari serum se glowing skin #vigyapan", rule: "HINGLISH-SUPERLATIVE-01" },
  { pattern: "jad se khatam", input: "Acne ko jad se khatam karein #vigyapan", rule: "HINGLISH-SUPERLATIVE-01" },
  { pattern: "hamesha ke liye", input: "Dark spots hamesha ke liye gayab #vigyapan", rule: "HINGLISH-SUPERLATIVE-01" },
  { pattern: "shat pratishat", input: "Shat pratishat guarantee ke saath #vigyapan", rule: "HINGLISH-SUPERLATIVE-01" },
  { pattern: "shat-pratishat", input: "Shat-pratishat result #vigyapan", rule: "HINGLISH-SUPERLATIVE-01" },
  { pattern: "ek jhatke mein", input: "Ek jhatke mein acne gayab #vigyapan", rule: "HINGLISH-SUPERLATIVE-01" },
  { pattern: "ramban ilaj", input: "Acne ka ramban ilaj #vigyapan", rule: "HINGLISH-AYUSH-03" },
  { pattern: "pakka ilaj", input: "Pimples ka pakka ilaj #vigyapan", rule: "HINGLISH-AYUSH-03" },
  { pattern: "bilkul theek", input: "Skin ko bilkul theek kare #vigyapan", rule: "HINGLISH-AYUSH-03" },

  // Colorist claims
  { pattern: "gora rang", input: "Payein gora rang 10 dinon mein #vigyapan", rule: "HINGLISH-COLORIST-02" },
  { pattern: "gore rang", input: "Gore rang ke liye best cream #vigyapan", rule: "HINGLISH-COLORIST-02" },
  { pattern: "rang gora", input: "Rang gora karne ka natural tarika #vigyapan", rule: "HINGLISH-COLORIST-02" },
  { pattern: "fairness guarantee", input: "Fairness guarantee formula #vigyapan", rule: "HINGLISH-COLORIST-02" },
  { pattern: "ek hafte mein gora", input: "Ek hafte mein gora chehra #vigyapan", rule: "HINGLISH-COLORIST-02" },
  { pattern: "rang nikhare", input: "Ye serum aapka rang nikhare #vigyapan", rule: "HINGLISH-COLORIST-02" },
  { pattern: "gorapan", input: "Instant gorapan paane ka tarika #vigyapan", rule: "HINGLISH-COLORIST-02" },

  // Missing disclosure triggers
  { pattern: "discount trigger missing tag", input: "Aaj hi khareedo aur 20% discount pao link bio mein", rule: "HINGLISH-DISCLOSURE-04" },
  { pattern: "loot lo trigger missing tag", input: "Loot lo ye offer abhi order karein", rule: "HINGLISH-DISCLOSURE-04" },
  { pattern: "code lagao trigger missing tag", input: "Code lagao SAVE20 aur buy now", rule: "HINGLISH-DISCLOSURE-04" }
];

for (const pt of patternTestCases) {
  const r = simulateHinglishCompliance(pt.input, 'hinglish_instagram');
  const matched = r.findings.some(f => f.rule_id === pt.rule || (f.highlighted_text && f.highlighted_text.toLowerCase().includes(pt.pattern.toLowerCase())));
  check(`Rule match for [${pt.pattern}]: detected properly`, matched);
}

// -------------------------------------------------------------
// SUITE 5: CULTURALLY RESONANT HINGLISH SUGGESTED FIXES
// -------------------------------------------------------------
console.log('\n--- SUITE 5: Culturally Resonant Hinglish Suggested Fixes ---');

// Hinglish indicator terms
const hinglishMarkers = [
  'se', 'mein', 'me', 'karein', 'kare', 'aur', 'ke', 'saath', 'gaya', 'banaya',
  'madad', 'behtar', 'dinon', 'up to', '#vigyapan', '#ad', 'shuru', 'jodein',
  'dekha', 'anusaar', 'sahayak', 'badlein'
];

// Test all findings generated across all patterns
let totalFindingsTested = 0;
let hinglishFixesVerified = 0;

for (const pt of patternTestCases) {
  const r = simulateHinglishCompliance(pt.input, 'hinglish_instagram');
  for (const f of r.findings) {
    totalFindingsTested++;
    check(`Finding has suggested_fix: [${f.rule_id}]`, !!f.suggested_fix && typeof f.suggested_fix === 'string' && f.suggested_fix.trim().length > 0);
    check(`Finding has suggestedFix identical to suggested_fix: [${f.rule_id}]`, f.suggestedFix === f.suggested_fix);
    check(`Suggested fix differs from highlighted text: [${f.rule_id}]`, f.suggested_fix.toLowerCase() !== f.highlighted_text.toLowerCase());

    const lowerFix = f.suggested_fix.toLowerCase();
    const hasHinglishMarker = hinglishMarkers.some(m => lowerFix.includes(m.toLowerCase())) ||
      /radiance|regimen|dermatologist|clinically|botanical/i.test(lowerFix);
    check(`Suggested fix is culturally resonant Hinglish / Indian ad rewrite ("${f.suggested_fix}")`, hasHinglishMarker);
    if (hasHinglishMarker) hinglishFixesVerified++;
  }
}

console.log(`  Tested ${totalFindingsTested} findings, ${hinglishFixesVerified} verified as culturally resonant Hinglish.`);

// -------------------------------------------------------------
// SUITE 6: FRONTEND CHANNEL CONFIGURATIONS INTEGRITY
// -------------------------------------------------------------
console.log('\n--- SUITE 6: Frontend Channel Configurations Integrity ---');

check('Instagram Caption (Hinglish) channel exists in HTML',
  htmlContent.includes("'Instagram Caption (Hinglish)': {") && htmlContent.includes("id: 'hinglish_instagram'"));

check('Influencer Video Script (Hinglish) channel exists in HTML',
  htmlContent.includes("'Influencer Video Script (Hinglish)': {") && htmlContent.includes("id: 'hinglish_influencer'"));

check('ASCI Vernacular Guidelines 2025 §2.4 cited in channel rules',
  htmlContent.includes("ASCI Vernacular Guidelines 2025 §2.4"));

check('Drugs & Magic Remedies Act 1954 §3 cited in channel rules',
  htmlContent.includes("Drugs & Magic Remedies Act 1954 §3"));

check('AYUSH Advertising Guidelines §3.1 cited in channel rules',
  htmlContent.includes("AYUSH Advertising Guidelines §3.1"));

check('CDSCO Cosmetics Rules 2020 §14 cited in channel rules',
  htmlContent.includes("CDSCO Cosmetics Rules 2020 §14"));

// -------------------------------------------------------------
// SUITE 7: ADVANCED ADVERSARIAL BOUNDARY & STRESS INVARIANTS
// -------------------------------------------------------------
console.log('\n--- SUITE 7: Advanced Adversarial Boundary & Stress Invariants ---');

// 1. Clinical Threshold Boundaries against CS-2026-88 (target: 94.2%)
console.log('\nTesting Clinical Threshold Boundaries:');
// Exact match: 94.2%
const rExact = simulateHinglishCompliance("Clinical study CS-2026-88 mein 94.2% hydration dekha gaya #ad", 'hinglish_instagram');
check('Exact 94.2% clinical study is NOT flagged as exaggeration or borderline',
  !rExact.findings.some(f => f.rule_id === 'HINGLISH-CLINICAL-EXAGGERATION-05' || f.rule_id === 'HINGLISH-CLINICAL-BORDERLINE-06'));
check('Exact 94.2% score is 100', rExact.compliance_score === 100);

// Slightly higher: 94.3% -> exaggeration
const rHigher = simulateHinglishCompliance("Clinical study CS-2026-88 mein 94.3% hydration dekha gaya #ad", 'hinglish_instagram');
check('94.3% (> 94.2%) is flagged as clinical exaggeration',
  rHigher.findings.some(f => f.rule_id === 'HINGLISH-CLINICAL-EXAGGERATION-05'));
check('94.3% score drops by 20 (high severity)', rHigher.compliance_score === 80);

// Borderline rounding: 94% (delta 0.2 <= 1.0)
const rRound = simulateHinglishCompliance("Clinical study CS-2026-88 mein 94% asar dekha gaya #ad", 'hinglish_instagram');
check('94% rounding is flagged as borderline (medium severity)',
  rRound.findings.some(f => f.rule_id === 'HINGLISH-CLINICAL-BORDERLINE-06'));
check('94% score drops by 10 (medium severity)', rRound.compliance_score === 90);

// Far below target: 50% asar (not near 94.2, not commercial)
const rLowClin = simulateHinglishCompliance("Study shows 50% hydration improvement #ad", 'hinglish_instagram');
check('50% hydration (< target and > 1.0 away) is not flagged as exaggeration or borderline',
  !rLowClin.findings.some(f => f.rule_id === 'HINGLISH-CLINICAL-EXAGGERATION-05' || f.rule_id === 'HINGLISH-CLINICAL-BORDERLINE-06'));

// 2. Timeline Compression Boundaries (target: 14 days)
console.log('\nTesting Timeline Compression Boundaries:');
const rTime13 = simulateHinglishCompliance("Sirf 13 din mein acne theek karein #vigyapan", 'hinglish_instagram');
check('13 days (< 14 days) is flagged as timeline compression',
  rTime13.findings.some(f => f.rule_id === 'HINGLISH-CLINICAL-TIMELINE-07'));

const rTime14 = simulateHinglishCompliance("14 din mein acne theek karein #vigyapan", 'hinglish_instagram');
check('14 days (>= 14 days) is NOT flagged as timeline compression',
  !rTime14.findings.some(f => f.rule_id === 'HINGLISH-CLINICAL-TIMELINE-07'));

const rTime21 = simulateHinglishCompliance("21 din mein acne theek karein #vigyapan", 'hinglish_instagram');
check('21 days (> 14 days) is NOT flagged as timeline compression',
  !rTime21.findings.some(f => f.rule_id === 'HINGLISH-CLINICAL-TIMELINE-07'));

// 3. Deduplication of Overlapping Spans (100% asar)
console.log('\nTesting Overlapping Span Deduplication:');
const rOverlap = simulateHinglishCompliance("Ye formula deta hai 100% asar acne par #vigyapan", 'hinglish_instagram');
const asarFindings = rOverlap.findings.filter(f => /100%\s*asar/i.test(f.highlighted_text));
console.log(`  Overlapping '100% asar' findings count: ${asarFindings.length}`);
check('Overlapping "100% asar" is consolidated into exactly 1 finding card (no duplicate spam)', asarFindings.length === 1);
check('Consolidated finding carries clinical exaggeration rule', asarFindings[0].rule_id === 'HINGLISH-CLINICAL-EXAGGERATION-05');

// 4. All Vernacular Hashtag Variations Acceptance
console.log('\nTesting All Vernacular Hashtag Variations:');
const validTags = ['#vigyapan', '#VIGYAPAN', '#prayasit', '#Prayasit', '#sahyog', '#Sahyog', '#ad', '#AD', '#sponsored', '#SPONSORED'];
for (const tag of validTags) {
  const rTag = simulateHinglishCompliance(`Aaj hi order karein aur 20% discount paayein link bio mein ${tag}`, 'hinglish_instagram');
  const promoMissing = rTag.findings.some(f => f.rule_id === 'HINGLISH-DISCLOSURE-04');
  check(`Tag variation "${tag}" satisfies disclosure requirement`, !promoMissing);
}

// 5. Injection & Special Character Resilience
console.log('\nTesting Injection & Special Character Resilience:');
const injections = [
  "<script>alert('xss')</script> chamatkari cream #vigyapan",
  "' OR '1'='1' -- gora rang #ad",
  "🌸✨💖 Chamatkari glow up 🌺 100% asar 🔥 #vigyapan",
  "Regex torture: ((((a+)+)+)+) [a-z]*? \\d{5,10} \\b\\w+\\b #ad"
];

for (const inj of injections) {
  const rInj = simulateHinglishCompliance(inj, 'hinglish_instagram');
  check(`Simulation does not throw or crash on injection: "${inj.substring(0, 30)}..."`, rInj.status === 'success');
  check(`Score remains bounded [0, 100] on injection: "${inj.substring(0, 30)}..."`, rInj.compliance_score >= 0 && rInj.compliance_score <= 100);
}

// -------------------------------------------------------------
// FINAL SUMMARY
// -------------------------------------------------------------
console.log('\n================================================================');
console.log(`TOTAL ASSERTIONS: ${totalAssertions}`);
console.log(`PASSED: ${passedAssertions}`);
console.log(`FAILED: ${failedAssertions}`);
console.log('================================================================');

if (failedAssertions === 0) {
  console.log('\n>>> VERDICT: ALL EMPIRICAL CHALLENGER TESTS PASSED (APPROVE) <<<\n');
  process.exit(0);
} else {
  console.log('\n>>> VERDICT: FAILURES DETECTED (REJECT) <<<\n');
  process.exit(1);
}
