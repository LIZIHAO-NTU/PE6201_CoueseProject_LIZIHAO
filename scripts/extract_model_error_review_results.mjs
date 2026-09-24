import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const root = path.resolve(import.meta.dirname, "..");
const workbookPath = path.join(
  root,
  "outputs",
  "019ff04b-cd46-7592-878a-23b1747c508d",
  "model_evaluation_review_v0.1.xlsx",
);
const resultPath = path.join(root, "outputs", "evaluation", "model_error_review_results_v0.1.json");
const allowedAssessments = new Set(["acceptable_tradeoff", "needs_mitigation", "critical_issue"]);

const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(workbookPath));
const sheet = workbook.worksheets.getItem("Predictions");
const values = sheet.getRange("A1:S31").values;
const headers = values[0].map((value) => String(value ?? "").replace(/^\uFEFF/, ""));
const records = values.slice(1).map((row) =>
  Object.fromEntries(headers.map((header, index) => [header, row[index] ?? ""])),
);

if (records.length !== 30) throw new Error(`Expected 30 records, found ${records.length}`);
const ids = records.map((record) => String(record.id));
if (new Set(ids).size !== ids.length) throw new Error("Duplicate record IDs found");

for (const record of records) {
  const priority = String(record.review_priority).trim();
  const assessment = String(record.student_assessment).trim();
  const notes = String(record.review_notes).trim();
  if (priority === "correct") {
    if (assessment || notes) throw new Error(`Correct row should be blank: ${record.id}`);
  } else {
    if (!allowedAssessments.has(assessment)) throw new Error(`Invalid or missing assessment for ${record.id}`);
    if (!notes) throw new Error(`Missing review notes for ${record.id}`);
  }
}

function countBy(field, fallback = "blank") {
  return records.reduce((counts, record) => {
    const value = String(record[field] ?? "").trim() || fallback;
    counts[value] = (counts[value] ?? 0) + 1;
    return counts;
  }, {});
}

const assessmentCounts = countBy("student_assessment");
const priorityCounts = countBy("review_priority");
const reviewed = records.filter((record) => record.review_priority !== "correct");
if (reviewed.length !== 17 || assessmentCounts.blank !== 13) {
  throw new Error(`Unexpected review totals: reviewed=${reviewed.length}, blank=${assessmentCounts.blank}`);
}

const payload = {
  review_version: "model-error-review-0.1",
  reviewed_on: "2026-08-12",
  source_workbook: path.relative(root, workbookPath).replaceAll("\\", "/"),
  policy: {
    priority_order: [
      "critical_false_reassurance",
      "false_positive_review",
      "ambiguous_case_miss",
      "type_error",
      "conservative_abstention",
    ],
    assessments: [...allowedAssessments],
    correct_rows_require_review: false,
  },
  summary: {
    records: records.length,
    reviewed_non_correct: reviewed.length,
    correct_unreviewed: assessmentCounts.blank,
    priority_counts: priorityCounts,
    assessment_counts: assessmentCounts,
  },
  records,
};

console.log((await workbook.inspect({
  kind: "region",
  sheetId: "Predictions",
  range: "Q1:S31",
  maxChars: 6500,
})).ndjson);
await fs.writeFile(resultPath, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
console.log(JSON.stringify({ saved: resultPath, summary: payload.summary }, null, 2));
