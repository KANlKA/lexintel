import json
import matplotlib.pyplot as plt
import numpy as np

# Load your results
with open('research_results_for_paper.json') as f:
    results = json.load(f)

# Figure 1: Precision by Confidence Level
fig1, ax1 = plt.subplots(figsize=(8, 6))
confidence_levels = ['High\n(≥0.8)', 'Medium\n(0.6-0.8)', 'Low\n(<0.6)']
precisions = [100.0, 93.1, 0.0]
counts = [34, 649, 25]

bars = ax1.bar(confidence_levels, precisions, color=['#2ecc71', '#f39c12', '#e74c3c'])
ax1.set_ylabel('Precision (%)', fontsize=12)
ax1.set_xlabel('Confidence Level', fontsize=12)
ax1.set_title('Event Extraction Precision by LLM Confidence', fontsize=14)
ax1.set_ylim(0, 110)

# Add count labels on bars
for bar, count in zip(bars, counts):
    ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2, 
             f'n={count}', ha='center', va='bottom', fontsize=10)

plt.tight_layout()
plt.savefig('figure_precision_by_confidence.png', dpi=300, bbox_inches='tight')
print("✅ Saved: figure_precision_by_confidence.png")

# Figure 2: Distribution of Events by Confidence
fig2, ax2 = plt.subplots(figsize=(8, 6))
colors = ['#2ecc71', '#f39c12', '#e74c3c']
wedges, texts, autotexts = ax2.pie(counts, labels=confidence_levels, 
                                    autopct='%1.1f%%', colors=colors,
                                    explode=(0.05, 0, 0))
ax2.set_title('Distribution of Extracted Events by Confidence Level', fontsize=14)
plt.tight_layout()
plt.savefig('figure_confidence_distribution.png', dpi=300, bbox_inches='tight')
print("✅ Saved: figure_confidence_distribution.png")

print("\n📊 Figures saved! These are ready for your paper.")
