import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const projectRoot = path.resolve(import.meta.dirname, "..");
const workbookPath = path.join(
  projectRoot,
  "outputs",
  "019ff04b-cd46-7592-878a-23b1747c508d",
  "message_eval_review_v0.1.xlsx",
);
const resultPath = path.join(projectRoot, "data", "eval", "message_eval_review_results_v0.1.json");
const previewPath = path.join(
  projectRoot,
  "outputs",
  "019ff04b-cd46-7592-878a-23b1747c508d",
  "message_eval_review_completed_v0.1.png",
);

const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(workbookPath));
const sheet = workbook.worksheets.getItem("Review Queue");
const values = sheet.getRange("A1:M31").values;
const headers = values[0].map((value) => String(value ?? "").replace(/^\uFEFF/, ""));
const records = values.slice(1).map((row) =>
  Object.fromEntries(headers.map((header, index) => [header, row[index] ?? ""])),
);

const counts = records.reduce(
  (acc, record) => {
    const decision = String(record.student_decision || "").trim().toLowerCase() || "blank";
    acc[decision] = (acc[decision] || 0) + 1;
    return acc;
  },
  {},
);

const inspection = await workbook.inspect({
  kind: "region",
  sheetId: "Review Queue",
  range: "A1:M31",
  maxChars: 5000,
});
console.log(inspection.ndjson);
console.log(JSON.stringify({ counts }, null, 2));

const preview = await workbook.render({
  sheetName: "Review Queue",
  range: "H1:M31",
  scale: 0.9,
  format: "png",
});
await fs.writeFile(previewPath, new Uint8Array(await preview.arrayBuffer()));
await fs.writeFile(resultPath, JSON.stringify({ workbookPath, counts, records }, null, 2) + "\n");
console.log(`Saved ${resultPath}`);
