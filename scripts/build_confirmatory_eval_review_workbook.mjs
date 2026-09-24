import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = path.resolve(import.meta.dirname, "..");
const csvPath = path.join(root, "data", "eval", "message_confirmatory_review_v0.2.csv");
const outputDir = path.join(root, "outputs", "019ff04b-cd46-7592-878a-23b1747c508d");
const outputPath = path.join(outputDir, "message_confirmatory_review_v0.2.xlsx");
const csvText = (await fs.readFile(csvPath, "utf8")).replace(/^\uFEFF/, "");
const workbook = await Workbook.fromCSV(csvText, { sheetName: "Review Queue" });
const queue = workbook.worksheets.getItem("Review Queue");
const instructions = workbook.worksheets.add("Instructions");
const summary = workbook.worksheets.add("Summary");

const navy = "#002D72";
const blue = "#0050B5";
const cyan = "#00A6D6";
const paleBlue = "#EAF3FF";
const paleCyan = "#E7F8FC";
const ink = "#17233C";
const muted = "#516079";
const line = "#D5DEEA";
const green = "#DCFCE7";
const amber = "#FEF3C7";
const red = "#FEE2E2";
const white = "#FFFFFF";

function addTitle(sheet, range, text) {
  const target = sheet.getRange(range);
  target.merge();
  target.values = [[text]];
  target.format = {
    fill: navy,
    font: { name: "Aptos Display", size: 20, bold: true, color: white },
    verticalAlignment: "center",
  };
  target.format.rowHeight = 34;
}

// Review queue
queue.showGridLines = false;
queue.freezePanes.freezeRows(1);
queue.freezePanes.freezeColumns(2);
queue.getRange("A1:M21").format = { font: { name: "Aptos", size: 10, color: ink }, verticalAlignment: "top" };
queue.getRange("A1:M1").format = {
  fill: navy,
  font: { name: "Aptos", size: 10, bold: true, color: white },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  wrapText: true,
};
queue.getRange("A1:M1").format.rowHeight = 42;
queue.getRange("A2:M21").format = {
  wrapText: true,
  verticalAlignment: "top",
  borders: { insideHorizontal: { style: "thin", color: line } },
};
queue.getRange("A2:M21").format.rowHeight = 76;
queue.getRange("I2:M21").format = { fill: paleBlue, wrapText: true };
queue.getRange("I1:M1").format = {
  fill: blue,
  font: { name: "Aptos", size: 10, bold: true, color: white },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  wrapText: true,
};
queue.getRange("I2:I21").dataValidation = {
  rule: { type: "list", values: ["accept", "edit", "reject"] },
};
queue.getRange("J2:J21").dataValidation = {
  rule: { type: "list", values: ["scam", "legitimate", "ambiguous"] },
};
queue.getRange("K2:K21").dataValidation = {
  rule: { type: "list", values: ["government_impersonation", "investment", "job", "e_commerce", "uncertain", "not_applicable"] },
};
for (const [text, fill, color] of [
  ["accept", green, "#166534"],
  ["edit", amber, "#92400E"],
  ["reject", red, "#991B1B"],
]) {
  queue.getRange("I2:I21").conditionalFormats.add("containsText", {
    text,
    format: { fill, font: { bold: true, color } },
  });
}
for (const [text, fill, color] of [
  ["scam", red, "#991B1B"],
  ["legitimate", green, "#166534"],
  ["ambiguous", amber, "#92400E"],
]) {
  queue.getRange("C2:C21").conditionalFormats.add("containsText", {
    text,
    format: { fill, font: { bold: true, color } },
  });
}
const widths = { A: 23, B: 58, C: 18, D: 27, E: 38, F: 40, G: 48, H: 31, I: 18, J: 20, K: 28, L: 38, M: 44 };
for (const [column, width] of Object.entries(widths)) queue.getRange(`${column}:${column}`).format.columnWidth = width;
const table = queue.tables.add("A1:M21", true, "ConfirmatoryEvaluationReviewTable");
table.style = "TableStyleMedium2";
table.showBandedRows = true;
table.showFilterButton = true;

// Instructions
instructions.showGridLines = false;
addTitle(instructions, "A1:H2", "ScamLens SG — Confirmatory Evaluation Review v0.2");
instructions.getRange("A4:H5").merge();
instructions.getRange("A4:H5").values = [[
  "These 20 messages have not been run through the model. Review naturalness and labels first so the batch remains an untouched confirmation set.",
]];
instructions.getRange("A4:H5").format = {
  fill: paleCyan,
  font: { name: "Aptos", size: 12, bold: true, color: navy },
  wrapText: true,
  verticalAlignment: "center",
  borders: { preset: "outside", style: "thin", color: cyan },
};
instructions.getRange("A7:D7").values = [["Decision", "When to use it", "What else to fill", "Example"]];
instructions.getRange("A8:D10").values = [
  ["accept", "Message and proposed labels are suitable", "Nothing else is required", "Natural message with correct label"],
  ["edit", "Message is usable after correction", "Fill corrected fields and explain the change", "Wrong type or unnatural wording"],
  ["reject", "Case should not enter the confirmatory set", "Explain why in review_notes", "Duplicate, implausible or unsafe provenance"],
];
instructions.getRange("A7:D10").format = {
  font: { name: "Aptos", size: 11, color: ink },
  wrapText: true,
  verticalAlignment: "center",
  borders: { insideHorizontal: { style: "thin", color: line } },
};
instructions.getRange("A7:D7").format = { fill: blue, font: { size: 11, bold: true, color: white } };
instructions.getRange("A8:A8").format = { fill: green, font: { bold: true, color: "#166534" } };
instructions.getRange("A9:A9").format = { fill: amber, font: { bold: true, color: "#92400E" } };
instructions.getRange("A10:A10").format = { fill: red, font: { bold: true, color: "#991B1B" } };
instructions.getRange("A8:D10").format.rowHeight = 46;
instructions.getRange("A12:H14").merge();
instructions.getRange("A12:H14").values = [[
  "Review order: (1) read the message without looking at the proposed label, (2) decide scam / legitimate / ambiguous, (3) check the scam type only if scam, (4) check whether the wording is plausible for Singapore, and (5) record corrections. Do not test these messages in the Flask app yet.",
]];
instructions.getRange("A12:H14").format = {
  fill: amber,
  font: { name: "Aptos", size: 11, bold: true, color: "#92400E" },
  wrapText: true,
  verticalAlignment: "center",
  borders: { preset: "outside", style: "thin", color: "#F59E0B" },
};
instructions.getRange("A:A").format.columnWidth = 25;
instructions.getRange("B:D").format.columnWidth = 38;
instructions.getRange("E:H").format.columnWidth = 18;
instructions.freezePanes.freezeRows(2);

// Summary
summary.showGridLines = false;
addTitle(summary, "A1:H2", "Confirmatory Review Dashboard");
for (const [labelRange, valueRange, label, formula] of [
  ["A4:B4", "A5:B6", "Reviewed", "=20-COUNTBLANK('Review Queue'!I2:I21)"],
  ["D4:E4", "D5:E6", "Edits or rejects", "=COUNTIF('Review Queue'!I2:I21,\"edit\")+COUNTIF('Review Queue'!I2:I21,\"reject\")"],
  ["G4:H4", "G5:H6", "Pending", "=COUNTBLANK('Review Queue'!I2:I21)"],
]) {
  summary.getRange(labelRange).merge();
  summary.getRange(valueRange).merge();
  summary.getRange(labelRange).values = [[label]];
  summary.getRange(valueRange).formulas = [[formula]];
  summary.getRange(labelRange).format = { fill: paleBlue, font: { size: 11, bold: true, color: blue }, horizontalAlignment: "center", verticalAlignment: "center", borders: { preset: "outside", style: "thin", color: line } };
  summary.getRange(valueRange).format = { fill: white, font: { name: "Aptos Display", size: 24, bold: true, color: navy }, horizontalAlignment: "center", verticalAlignment: "center", borders: { preset: "outside", style: "thin", color: line } };
}
summary.getRange("A9:B9").values = [["Proposed risk label", "Count"]];
summary.getRange("A10:A12").values = [["Scam"], ["Legitimate"], ["Ambiguous"]];
summary.getRange("B10:B12").formulas = [
  ["=COUNTIF('Review Queue'!C2:C21,\"scam\")"],
  ["=COUNTIF('Review Queue'!C2:C21,\"legitimate\")"],
  ["=COUNTIF('Review Queue'!C2:C21,\"ambiguous\")"],
];
summary.getRange("D9:E9").values = [["Proposed scam type", "Count"]];
summary.getRange("D10:D13").values = [["Government impersonation"], ["Investment"], ["Job"], ["E-commerce"]];
summary.getRange("E10:E13").formulas = [
  ["=COUNTIF('Review Queue'!D2:D21,\"government_impersonation\")"],
  ["=COUNTIF('Review Queue'!D2:D21,\"investment\")"],
  ["=COUNTIF('Review Queue'!D2:D21,\"job\")"],
  ["=COUNTIF('Review Queue'!D2:D21,\"e_commerce\")"],
];
summary.getRange("A9:B12").format = { font: { name: "Aptos", size: 11, color: ink }, borders: { insideHorizontal: { style: "thin", color: line } }, verticalAlignment: "center" };
summary.getRange("D9:E13").format = { font: { name: "Aptos", size: 11, color: ink }, borders: { insideHorizontal: { style: "thin", color: line } }, verticalAlignment: "center" };
summary.getRange("A9:B9").format = { fill: blue, font: { bold: true, color: white }, horizontalAlignment: "center" };
summary.getRange("D9:E9").format = { fill: blue, font: { bold: true, color: white }, horizontalAlignment: "center" };
summary.getRange("A15:H17").merge();
summary.getRange("A15:H17").values = [[
  "Stop before running model predictions. After all 20 decisions are complete, extract accepted/corrected records, lock them as a new confirmatory test set, then run the v0.2 deployment exactly once.",
]];
summary.getRange("A15:H17").format = { fill: paleCyan, font: { name: "Aptos", size: 11, bold: true, color: navy }, wrapText: true, verticalAlignment: "center", borders: { preset: "outside", style: "thin", color: cyan } };
summary.getRange("A:H").format.columnWidth = 16;
summary.getRange("A:A").format.columnWidth = 29;
summary.getRange("D:D").format.columnWidth = 31;
summary.getRange("A9:E13").format.rowHeight = 28;
summary.freezePanes.freezeRows(2);

await fs.mkdir(outputDir, { recursive: true });
for (const [sheetName, fileName, options] of [
  ["Summary", "confirmatory_review_summary_v0.2.png", { autoCrop: "all", scale: 1 }],
  ["Instructions", "confirmatory_review_instructions_v0.2.png", { autoCrop: "all", scale: 1 }],
  ["Review Queue", "confirmatory_review_queue_v0.2.png", { range: "A1:M21", scale: 0.72 }],
]) {
  const preview = await workbook.render({ sheetName, ...options, format: "png" });
  await fs.writeFile(path.join(outputDir, fileName), new Uint8Array(await preview.arrayBuffer()));
}
console.log((await workbook.inspect({ kind: "table", range: "Summary!A4:H17", include: "values,formulas", tableMaxRows: 14, tableMaxCols: 8, maxChars: 7000 })).ndjson);
console.log((await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 100 }, summary: "formula error scan", maxChars: 2500 })).ndjson);
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(`Saved ${outputPath}`);
