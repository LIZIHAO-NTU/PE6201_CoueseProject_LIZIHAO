document.querySelectorAll(".example").forEach((button) => {
  button.addEventListener("click", () => {
    const textarea = document.querySelector("#message");
    textarea.value = button.dataset.example;
    textarea.focus();
  });
});

const llmToggle = document.querySelector("#use_llm");
const providerNote = document.querySelector("#provider-note");
llmToggle?.addEventListener("change", () => {
  providerNote.textContent = llmToggle.checked
    ? "The redacted message and compact analysis context will be sent to the configured LLM via OpenRouter."
    : "No message content will be sent to an external AI provider.";
});

if (window.location.hash === "#results") {
  document.querySelector("#results")?.scrollIntoView({ behavior: "smooth", block: "start" });
}

if (document.querySelector(".benchmark-history tr.benchmark-running")) {
  window.setTimeout(() => window.location.reload(), 3000);
}

const benchmarkForm = document.querySelector(".benchmark-form");
const benchmarkEstimate = document.querySelector("#benchmark-estimate");
const updateBenchmarkEstimate = () => {
  if (!benchmarkForm || !benchmarkEstimate) return;
  const cases = Number(benchmarkForm.querySelector('[name="case_limit"]')?.value || 0);
  const inputTokens = Number(benchmarkForm.dataset.assumedInputTokens || 1800);
  const outputTokens = Number(benchmarkForm.dataset.maxOutputTokens || 400);
  const selected = [...benchmarkForm.querySelectorAll('[name="models"]:checked')];
  const perCase = selected.reduce((sum, item) => {
    const inputRate = Number(item.dataset.inputRate || 0);
    const outputRate = Number(item.dataset.outputRate || 0);
    return sum + inputTokens / 1_000_000 * inputRate + outputTokens / 1_000_000 * outputRate;
  }, 0);
  benchmarkEstimate.textContent = `Estimated maximum: US$${(cases * perCase).toFixed(4)} · ${cases * selected.length} paid calls`;
};
benchmarkForm?.addEventListener("input", updateBenchmarkEstimate);
updateBenchmarkEstimate();
