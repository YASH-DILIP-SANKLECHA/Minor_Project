export function downloadTextFile(filename, content) {
  const url = URL.createObjectURL(new Blob([content], { type: 'text/plain;charset=utf-8' }));
  const link = document.createElement('a'); link.href = url; link.download = filename; link.click(); URL.revokeObjectURL(url);
}
export function downloadJsonFile(filename, value) {
  downloadTextFile(filename, JSON.stringify(value, null, 2));
}
export function generateFullReportText({ rawText, optimizedText, stats, prompt, rawAnswer, optimizedAnswer }) {
  return `DATASET REFINEMENT RESULTS
Generated: ${new Date().toLocaleString()}

RESULTS
Original lines: ${stats?.originalRecords ?? 0}
Refined lines: ${stats?.optimizedRecords ?? 0}
Lines reduced: ${(stats?.originalRecords ?? 0) - (stats?.optimizedRecords ?? 0)}
Reduction: ${stats?.reductionPercentage ?? 0}%
Similar statements removed: ${stats?.semanticDuplicatesRemoved ?? 0}
Conflicts resolved: ${stats?.contradictionsResolved ?? 0}
Items needing review: ${stats?.manualReview ?? 0}

QUESTION
${prompt || 'No question was asked.'}

ORIGINAL DATASET ANSWER
${rawAnswer || 'No answer recorded.'}

REFINED DATASET ANSWER
${optimizedAnswer || 'No answer recorded.'}

ORIGINAL DATASET
${rawText || ''}

REFINED DATASET
${optimizedText || ''}
`;
}
