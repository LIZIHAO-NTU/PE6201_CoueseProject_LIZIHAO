import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const root = path.resolve(import.meta.dirname, "..");
const workbookPath = path.join(root, "outputs", "019ff04b-cd46-7592-878a-23b1747c508d", "message_confirmatory_review_v0.2.xlsx");
const resultPath = path.join(root, "data", "eval", "message_confirmatory_review_results_v0.2.json");
const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(workbookPath));
const queue = workbook.worksheets.getItem("Review Queue");
const values = queue.getRange("A1:M21").values;
const headers = values[0].map((value) => String(value ?? "").replace(/^\uFEFF/, ""));
const records = values.slice(1).map((row) =>
  Object.fromEntries(headers.map((header, index) => [header, row[index] ?? ""])),
);

const counts = records.reduce((acc, record) => {
  const decision = String(record.student_decision || "").trim().toLowerCase() || "blank";
  acc[decision] = (acc[decision] || 0) + 1;
  return acc;
}, {});
if (records.length !== 20 || counts.accept !== 20) {
  throw new Error(`Expected 20 accepted records, found ${JSON.stringify(counts)}`);
}

await fs.writeFile(resultPath, JSON.stringify({
  review_version: "ai-assisted-sanity-review-0.2",
  reviewer: "AI-assisted content audit",
  independent_human_review: false,
  counts,
  records,
}, null, 2) + "\n");
console.log(JSON.stringify({ saved: resultPath, counts }, null, 2));
