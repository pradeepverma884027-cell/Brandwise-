import os

FRONTEND_PATH = 'codex/frontend/index.html'

with open(FRONTEND_PATH, 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Enhance Clinical Upload Modal with [Download Sample Dossier PDF] and [Load Sample Study #CS-2026-88]
old_quick_header = '<div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">\n                    Or Quick Load Synthetic Fixture:\n                  </div>'
new_quick_header = '''<div className="flex items-center justify-between pt-1">
                    <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                      Or Quick Load / Download Synthetic Fixture:
                    </span>
                    <a
                      href="/api/clinical/sample-pdf"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[11px] text-emerald-600 dark:text-emerald-400 hover:underline flex items-center space-x-1"
                      title="Download raw multi-page Study_CS-2026-88.pdf to test drag & drop"
                    >
                      <span>📥</span>
                      <span>Download Sample Study PDF</span>
                    </a>
                  </div>'''

if old_quick_header in html:
    html = html.replace(old_quick_header, new_quick_header, 1)
    print('[+] Enhanced Clinical Upload Modal with direct sample download link')

# 2. Add [Load Sample Signed Brand Waiver (#BW-2026-09)] and [Download Sample Waiver PDF] to Counter-Evidence Modal
target_counter_form = '<form onSubmit={handleCounterEvidenceSubmit} className="space-y-3.5 text-xs">'
counter_sample_bar = '''{/* Quick-Preload Sample Waiver Toolbar for Judges */}
                <div className={`p-3 rounded-xl border space-y-2 ${
                  isDark ? 'bg-slate-800/80 border-slate-700' : 'bg-slate-100 border-slate-200'
                }`}>
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="font-semibold text-slate-700 dark:text-slate-300 flex items-center space-x-1">
                      <span>⚡</span>
                      <span>Judge Quick-Fill Counter Evidence:</span>
                    </span>
                    <a
                      href="/api/clinical/sample-waiver"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-purple-600 dark:text-purple-400 hover:underline flex items-center space-x-1 text-[10px]"
                      title="Download official signed Brand_Design_Waiver_BW-2026-09.pdf"
                    >
                      <span>📥</span>
                      <span>Download Sample Waiver PDF</span>
                    </a>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setCounterForm({
                        evidence_type: 'legal_waiver_signoff',
                        reference_id: 'BW-2026-09',
                        justification: 'Approved dark-mode campaign contrast exception signed by Brand Creative Director (Marcus Vance) & Chief Governance Officer.',
                        document_ref: 'Brand_Design_Waiver_BW-2026-09.pdf'
                      });
                      triggerNotification("⚡ Preloaded Signed Waiver #BW-2026-09. Click 'Submit Counter-Evidence' to adjudicate!");
                    }}
                    className="w-full py-2 px-2.5 rounded-lg border text-left text-xs bg-purple-500/10 hover:bg-purple-500/20 text-purple-700 dark:text-purple-300 border-purple-300 dark:border-purple-800/60 font-medium transition cursor-pointer flex items-center justify-between"
                  >
                    <div className="flex items-center space-x-1.5">
                      <span>📑</span>
                      <span>Load Sample Signed Brand Waiver (#BW-2026-09)</span>
                    </div>
                    <span className="text-[10px] font-mono opacity-80">1-Click Preload &rarr;</span>
                  </button>
                </div>

                <form onSubmit={handleCounterEvidenceSubmit} className="space-y-3.5 text-xs">'''

if 'Judge Quick-Fill Counter Evidence' not in html and target_counter_form in html:
    html = html.replace(target_counter_form, counter_sample_bar, 1)
    print('[+] Added Sample Waiver quick-fill and download button into Counter-Evidence Modal')

with open(FRONTEND_PATH, 'w', encoding='utf-8') as f:
    f.write(html)
print('Saved Stage 3 updates to codex/frontend/index.html!')

