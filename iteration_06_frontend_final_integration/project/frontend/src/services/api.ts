/** Bridge the imported UI to this project's local FastAPI backend. */
const API = import.meta.env.VITE_API_BASE_URL || "/api";
const pause = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

function textMetrics(text) {
  const bytes = new Blob([text]).size;
  const words = text.trim() ? text.trim().split(/\s+/).length : 0;
  return { bytes, characters: text.length, words, tokens: Math.ceil(text.length / 4) };
}

function statistics(report, rawText, optimizedText) {
  const raw = textMetrics(rawText); const optimized = textMetrics(optimizedText);
  return {
    originalRecords: report.original_dataset_lines ?? 0,
    originalInformationUnits: report.original_information_units ?? 0,
    refinedInformationUnits: report.refined_information_units ?? 0,
    removalsMade: report.reductions_made ?? 0,
    exactDuplicatesRemoved: 0,
    semanticDuplicatesRemoved: report.semantic_duplicates_removed ?? 0,
    optimizedRecords: report.refined_dataset_lines ?? 0,
    reductionPercentage: report.reduction_percentage ?? 0,
    originalTokens: raw.tokens, optimizedTokens: optimized.tokens,
    tokenReductionPercentage: raw.tokens ? Number((((raw.tokens - optimized.tokens) / raw.tokens) * 100).toFixed(2)) : 0,
    originalSizeBytes: raw.bytes, optimizedSizeBytes: optimized.bytes,
    originalCharCount: raw.characters, optimizedCharCount: optimized.characters,
    originalWordCount: raw.words, optimizedWordCount: optimized.words,
    contradictionsResolvedAutomatically: report.contradictions_resolved_automatically ?? 0,
    contradictionsResolvedManually: report.contradictions_resolved_manually ?? 0,
    contradictionsResolved: (report.contradictions_resolved_automatically ?? 0) + (report.contradictions_resolved_manually ?? 0),
    manualReview: report.manual_intervention_required ?? 0,
  };
}

async function responseJson(response) {
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.detail || "The local backend could not complete this request.");
  return payload;
}

async function localRequest(path, options) {
  try {
    return await fetch(`${API}${path}`, options);
  } catch (error) {
    throw new Error(
      "Cannot reach the local server. Start FastAPI with: python run_backend.py"
    );
  }
}

export async function getRefinementStatus() {
  return responseJson(await localRequest('/status'));
}

export async function getManualVerification() {
  return responseJson(await localRequest('/manual-verification'));
}

export async function submitManualVerification(caseNumber, decision) {
  return responseJson(await localRequest(`/manual-verification/${caseNumber}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ decision }),
  }));
}

export async function getSavedDatasetsAndStats() {
  const status = await getRefinementStatus();
  const [rawText, optimizedText] = await Promise.all([
    (await localRequest('/datasets/raw')).text(),
    (await localRequest('/datasets/refined')).text(),
  ]);
  return {
    status,
    rawText,
    optimizedText,
    stats: statistics(status.final_report || {}, rawText, optimizedText),
  };
}

export async function optimizeDataset(rawText, onStatus) {
  const started = await responseJson(await localRequest('/refine', {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ dataset_text: rawText }),
  }));
  onStatus?.({ state: 'queued', message: started.message, progress: 0, error: null });
  for (;;) {
    await pause(1500);
    const status = await getRefinementStatus();
    onStatus?.(status.refinement);
    if (status.refinement.state === "idle") {
      throw new Error(
        "The backend restarted while refining the dataset. Start the backend with 'python run_backend.py' (without --reload), then submit the dataset again."
      );
    }
    if (status.refinement.state === "failed") throw new Error(status.refinement.error || "Refinement failed.");
    if (status.refinement.state !== "complete") continue;
    return getSavedDatasetsAndStats();
  }
}

export async function getModelComparison(prompt) {
  const result = await responseJson(await localRequest('/compare', {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question: prompt }),
  }));
  return {
    rawModelResponse: result.raw.answer,
    optimizedModelResponse: result.refined.answer,
    rawContextLines: result.raw.context_line_count,
    optimizedContextLines: result.refined.context_line_count,
  };
}
