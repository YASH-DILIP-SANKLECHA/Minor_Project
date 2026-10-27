const byId = (id) => document.getElementById(id);
const form = byId("question-form");
const button = byId("ask-button");
const refinementForm = byId("refinement-form");
const refineButton = byId("refine-button");
const error = byId("error");

function setAnswer(id, text, placeholder = false) {
  const element = byId(id);
  element.textContent = text;
  element.classList.toggle("placeholder", placeholder);
}

function updateRefinementState(refinement = {}) {
  const state = refinement.state || "idle";
  const message = refinement.error || refinement.message || "Ready for a raw dataset.";
  const status = byId("refinement-status");
  status.textContent = message;
  status.dataset.state = state;
  const active = state === "queued" || state === "running";
  refineButton.disabled = active;
  byId("dataset-text").disabled = active;
}

function updateReport(report = {}, rawLineCount, refinedLineCount) {
  byId("report-original-lines").textContent = (report.original_dataset_lines ?? rawLineCount).toLocaleString();
  byId("report-refined-lines").textContent = (report.refined_dataset_lines ?? refinedLineCount).toLocaleString();
  byId("report-reduction").textContent = report.reduction_percentage !== undefined ? `${Number(report.reduction_percentage).toFixed(2)}%` : "—";
  byId("report-similarities").textContent = (report.semantic_duplicates_removed ?? "—").toLocaleString();
  byId("report-contradictions").textContent = (report.contradictions_resolved_automatically ?? "—").toLocaleString();
  byId("report-manual").textContent = (report.manual_intervention_required ?? "—").toLocaleString();
  const refinedDatasetLink = byId("refined-dataset-link");
  refinedDatasetLink.href = "/api/datasets/refined";
  refinedDatasetLink.target = "_blank";
  refinedDatasetLink.rel = "noopener";
  refinedDatasetLink.classList.remove("disabled");
  refinedDatasetLink.removeAttribute("aria-disabled");
}

async function loadStatus() {
  try {
    const response = await fetch("/api/status");
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Unable to load dataset status.");
    const report = data.final_report || {};
    updateRefinementState(data.refinement);
    const active = ["queued", "running"].includes(data.refinement?.state);
    if (!active && data.refinement?.state === "complete") {
      updateReport(report, data.raw_line_count, data.refined_line_count);
    }
    if (active) setTimeout(loadStatus, 3000);
  } catch (err) { error.textContent = err.message; }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault(); error.textContent = "";
  const question = byId("question").value.trim();
  button.disabled = true; button.textContent = "Querying local models…";
  setAnswer("raw-answer", "Analyzing the raw dataset…", true);
  setAnswer("refined-answer", "Analyzing the refined dataset…", true);
  try {
    const response = await fetch("/api/compare", { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({question}) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Comparison failed.");
    setAnswer("raw-answer", data.raw.answer);
    setAnswer("refined-answer", data.refined.answer);
    byId("raw-context").textContent = `${data.raw.context_line_count} relevant dataset lines supplied`;
    byId("refined-context").textContent = `${data.refined.context_line_count} relevant dataset lines supplied`;
  } catch (err) {
    error.textContent = err.message;
    setAnswer("raw-answer", "No answer available.", true);
    setAnswer("refined-answer", "No answer available.", true);
  } finally { button.disabled = false; button.innerHTML = "Run comparison <span>→</span>"; }
});

refinementForm.addEventListener("submit", async (event) => {
  event.preventDefault(); error.textContent = "";
  const datasetText = byId("dataset-text").value.trim();
  refineButton.disabled = true;
  try {
    const response = await fetch("/api/refine", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({dataset_text: datasetText}),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Unable to start refinement.");
    byId("refinement-status").textContent = "Refinement queued. The dashboard will refresh when it completes.";
    byId("refinement-status").dataset.state = "queued";
    byId("dataset-text").disabled = true;
    setTimeout(loadStatus, 1000);
  } catch (err) {
    error.textContent = err.message;
    refineButton.disabled = false;
  }
});
