# E2E Test Infra: Brandwise Improvement 2

## Test Philosophy
- Deterministic, cloud-free, requirement-driven tests.
- Execution via standard library `unittest` (`python -m unittest discover -s codex/tests`).
- In-memory `HTTPTestClient` with `MockSocket` for rapid, port-conflict-free server testing.
- Methodology: Category-Partition + Boundary Value Analysis (BVA) + Pairwise Combinations + Real-World Workloads.

## Feature Inventory & Test Coverage
| # | Feature | Source | Tier 1 (Equivalence) | Tier 2 (Boundary) | Tier 3 (Cross-Feature) | Tier 4 (Workload) |
|---|---------|--------|:--------------------:|:-----------------:|:----------------------:|:-----------------:|
| 1 | Logo Geometry Distortion | R1 | 5 | 5 (2.0% boundary) | ✓ | ✓ |
| 2 | Brand Palette Colour Drift (ΔE) | R1 | 5 | 5 (15 & 65 thresholds) | ✓ | ✓ |
| 3 | Disclaimer Contrast Ratio | R1 | 5 | 5 (4.5:1 boundary) | ✓ | ✓ |
| 4 | Missing Alt-Text Detection | R1 | 5 | 5 (None, empty, spaces) | ✓ | ✓ |
| 5 | Counter-Evidence Adjudication | R2 | 6 (all types) | 5 (10-char boundary) | ✓ | ✓ |
| 6 | Visual Inspect Endpoint | R4 | 5 | 5 | ✓ | ✓ |
| 7 | Adjudication Submit Endpoint | R4 | 5 | 5 | ✓ | ✓ |
| 8 | Score Restoration & Audit Log | R2 | 5 | 5 (+15 score deltas) | ✓ | ✓ |

## Test Architecture
- Unit test files:
  - `codex/tests/test_visual_compliance.py`: Tests for R1 and `/api/visual/inspect`.
  - `codex/tests/test_adjudication.py`: Tests for R2, R4, and `/api/adjudication/submit`.
- Test runners:
  - `python codex/tests/test_visual_compliance.py`
  - `python codex/tests/test_adjudication.py`
  - `python -m unittest discover -s codex/tests`

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Expected Outcome |
|---|----------|--------------------|------------------|
| 1 | Multi-violation visual asset | Logo distortion + palette drift + contrast failure + missing alt | All 4 violations caught, is_compliant=False |
| 2 | End-to-end adjudication cycle | Asset inspected -> violation flagged -> counter-evidence submitted -> allegation dismissed -> score restored by +15 -> audit log verified | Score restored, audit log appended with SHA256 hash |
| 3 | Invalid counter-evidence rejection | Invalid type, empty ref ID, or justification < 10 chars | REJECTED_INSUFFICIENT_EVIDENCE returned, score unchanged |
| 4 | Dual-server parity | SHA256 of `server.py` and `codex/server.py` | Hashes match identically |
| 5 | Tri-HTML parity | SHA256 of `codex/frontend/index.html`, `index.html`, `docs/index.html` | Hashes match identically |
