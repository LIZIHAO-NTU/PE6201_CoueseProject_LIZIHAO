import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = path.resolve(import.meta.dirname, "..");
const sourcePath = path.join(root, "data", "training", "message_training_review_v0.1.csv");
const outputDir = path.join(root, "outputs", "019ff04b-cd46-7592-878a-23b1747c508d");
const outputPath = path.join(outputDir, "message_training_review_v0.1.xlsx");
const csvText = (await fs.readFile(sourcePath, "utf8")).replace(/^\uFEFF/, "");
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
const line = "#D5DEEA";
const green = "#DCFCE7";
const greenInk = "#166534";
const amber = "#FEF3C7";
const amberInk = "#92400E";
const red = "#FEE2E2";
const redInk = "#991B1B";
const white = "#FFFFFF";

function title(sheet, range, text) {
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
queue.getRange("A1:M61").format = {
  font: { name: "Aptos", size: 10, color: ink },
  verticalAlignment: "top",
};
queue.getRange("A1:M1").format = {
  fill: navy,
  font: { name: "Aptos", size: 10, bold: true, color: white },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  wrapText: true,
};
queue.getRange("A1:M1").format.rowHeight = 40;
queue.getRange("A2:M61").format = {
  wrapText: true,
  verticalAlignment: "top",
  borders: { insideHorizontal: { style: "thin", color: line } },
};
queue.getRange("A2:M61").format.rowHeight = 70;
queue.getRange("I2:M61").format = {
  fill: paleBlue,
  font: { name: "Aptos", size: 10, color: ink },
  wrapText: true,
  verticalAlignment: "top",
};
queue.getRange("I1:M1").format = {
  fill: blue,
  font: { name: "Aptos", size: 10, bold: true, color: white },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  wrapText: true,
};
queue.getRange("I2:I61").dataValidation = {
  rule: { type: "list", values: ["accept", "edit", "reject"] },
};
queue.getRange("J2:J61").dataValidation = {
  rule: { type: "list", values: ["scam", "legitimate", "ambiguous"] },
};
queue.getRange("K2:K61").dataValidation = {
  rule: {
    type: "list",
    values: ["government_impersonation", "investment", "job", "e_commerce", "not_applicable", "uncertain"],
  },
};
for (const [text, fill, color] of [
  ["accept", green, greenInk],
  ["edit", amber, amberInk],
  ["reject", red, redInk],
]) {
  queue.getRange("I2:I61").conditionalFormats.add("containsText", {
    text,
    format: { fill, font: { bold: true, color } },
  });
}
for (const [text, fill, color] of [
  ["scam", red, redInk],
  ["legitimate", green, greenInk],
  ["ambiguous", amber, amberInk],
]) {
  queue.getRange("C2:C61").conditionalFormats.add("containsText", {
    text,
    format: { fill, font: { bold: true, color } },
  });
}
const widths = { A: 23, B: 57, C: 16, D: 27, E: 47, F: 39, G: 46, H: 31, I: 18, J: 19, K: 27, L: 47, M: 42 };
for (const [column, width] of Object.entries(widths)) {
  queue.getRange(`${column}:${column}`).format.columnWidth = width;
}
const table = queue.tables.add("A1:M61", true, "TrainingReviewTable");
table.style = "TableStyleMedium2";
table.showBandedRows = true;
table.showFilterButton = true;

// Instructions
instructions.showGridLines = false;
title(instructions, "A1:H2", "ScamLens SG — Training Candidate Review");
instructions.getRange("A4:H4").merge();
instructions.getRange("A4:H4").values = [[
  "Goal: approve a separate pool for model training and validation. These records will never be added to the fixed gold test set.",
]];
instructions.getRange("A4:H4").format = {
  fill: paleCyan,
  font: { name: "Aptos", size: 12, bold: true, color: navy },
  wrapText: true,
  verticalAlignment: "center",
  borders: { preset: "outside", style: "thin", color: cyan },
};
instructions.getRange("A4:H4").format.rowHeight = 42;
instructions.getRange("A6:B6").values = [["Step", "What to check"]];
instructions.getRange("A7:B12").values = [
  ["1", "Judge whether the wording sounds like a plausible message seen in Singapore."],
  ["2", "Check the risk label: scam, legitimate or ambiguous."],
  ["3", "For scam records, verify the primary type and cited SPF modus operandi."],
  ["4", "Check that the listed mechanisms are actually present in the message."],
  ["5", "Choose accept, edit or reject. Complete corrected fields only when editing."],
  ["6", "Reject overly artificial, duplicated or unsupported examples and explain briefly in Review Notes."],
];
instructions.getRange("A6:B12").format = {
  font: { name: "Aptos", size: 11, color: ink },
  wrapText: true,
  verticalAlignment: "center",
  borders: { insideHorizontal: { style: "thin", color: line } },
};
instructions.getRange("A6:B6").format = {
  fill: blue,
  font: { name: "Aptos", size: 11, bold: true, color: white },
};
instructions.getRange("A7:A12").format = {
  fill: paleBlue,
  font: { name: "Aptos", size: 12, bold: true, color: blue },
  horizontalAlignment: "center",
};
instructions.getRange("A7:B12").format.rowHeight = 42;
instructions.getRange("A14:D14").values = [["Decision", "Use when", "Corrected fields", "Outcome"]];
instructions.getRange("A15:D17").values = [
  ["accept", "Message and annotation are usable", "Leave blank", "Eligible for train/validation split"],
  ["edit", "Useful after a label or mechanism correction", "Complete corrected columns", "Eligible after correction"],
  ["reject", "Artificial, duplicate, unsupported or unsafe", "Leave blank; explain why", "Excluded and replaced"],
];
instructions.getRange("A14:D17").format = {
  font: { name: "Aptos", size: 11, color: ink },
  wrapText: true,
  verticalAlignment: "center",
  borders: { insideHorizontal: { style: "thin", color: line } },
};
instructions.getRange("A14:D14").format = {
  fill: blue,
  font: { name: "Aptos", size: 11, bold: true, color: white },
};
instructions.getRange("A15:A15").format = { fill: green, font: { bold: true, color: greenInk } };
instructions.getRange("A16:A16").format = { fill: amber, font: { bold: true, color: amberInk } };
instructions.getRange("A17:A17").format = { fill: red, font: { bold: true, color: redInk } };
instructions.getRange("A15:D17").format.rowHeight = 38;
instructions.getRange("A19:H20").merge();
instructions.getRange("A19:H20").values = [[
  "Data separation rule: these candidates may become training or validation data only. The 30-record gold test set remains untouched for final comparison.",
]];
instructions.getRange("A19:H20").format = {
  fill: amber,
  font: { name: "Aptos", size: 11, bold: true, color: amberInk },
  wrapText: true,
  verticalAlignment: "center",
  borders: { preset: "outside", style: "thin", color: "#F59E0B" },
};
instructions.getRange("A:A").format.columnWidth = 13;
instructions.getRange("B:B").format.columnWidth = 65;
instructions.getRange("C:D").format.columnWidth = 26;
instructions.getRange("E:H").format.columnWidth = 14;
instructions.freezePanes.freezeRows(2);

// Summary
summary.showGridLines = false;
title(summary, "A1:H2", "Training Review Progress");
for (const [labelRange, valueRange, label, formula] of [
  ["A4:B4", "A5:B6", "Reviewed", "=60-COUNTBLANK('Review Queue'!I2:I61)"],
  ["D4:E4", "D5:E6", "Accepted / edited", "=COUNTIF('Review Queue'!I2:I61,\"accept\")+COUNTIF('Review Queue'!I2:I61,\"edit\")"],
  ["G4:H4", "G5:H6", "Pending", "=COUNTBLANK('Review Queue'!I2:I61)"],
]) {
  summary.getRange(labelRange).merge();
  summary.getRange(valueRange).merge();
  summary.getRange(labelRange).values = [[label]];
  summary.getRange(valueRange).formulas = [[formula]];
  summary.getRange(labelRange).format = {
    fill: paleBlue,
    font: { name: "Aptos", size: 11, bold: true, color: blue },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    borders: { preset: "outside", style: "thin", color: line },
  };
  summary.getRange(valueRange).format = {
    fill: white,
    font: { name: "Aptos Display", size: 24, bold: true, color: navy },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    borders: { preset: "outside", style: "thin", color: line },
  };
}
summary.getRange("A9:C9").values = [["Decision", "Count", "% of 60"]];
summary.getRange("A10:A13").values = [["accept"], ["edit"], ["reject"], ["pending"]];
summary.getRange("B10:B13").formulas = [
  ["=COUNTIF('Review Queue'!I2:I61,A10)"],
  ["=COUNTIF('Review Queue'!I2:I61,A11)"],
  ["=COUNTIF('Review Queue'!I2:I61,A12)"],
  ["=COUNTBLANK('Review Queue'!I2:I61)"],
];
summary.getRange("C10:C13").formulas = [["=B10/60"], ["=B11/60"], ["=B12/60"], ["=B13/60"]];
summary.getRange("E9:F9").values = [["Candidate group", "Count"]];
summary.getRange("E10:E15").values = [
  ["Government impersonation"], ["Investment"], ["Job"], ["E-commerce"], ["Legitimate hard negatives"], ["Ambiguous"],
];
summary.getRange("F10:F15").formulas = [
  ["=COUNTIF('Review Queue'!D2:D61,\"government_impersonation\")"],
  ["=COUNTIF('Review Queue'!D2:D61,\"investment\")"],
  ["=COUNTIF('Review Queue'!D2:D61,\"job\")"],
  ["=COUNTIF('Review Queue'!D2:D61,\"e_commerce\")"],
  ["=COUNTIF('Review Queue'!C2:C61,\"legitimate\")"],
  ["=COUNTIF('Review Queue'!C2:C61,\"ambiguous\")"],
];
for (const range of ["A9:C13", "E9:F15"]) {
  summary.getRange(range).format = {
    font: { name: "Aptos", size: 11, color: ink },
    verticalAlignment: "center",
    borders: { insideHorizontal: { style: "thin", color: line } },
  };
}
summary.getRange("A9:C9").format = { fill: blue, font: { size: 11, bold: true, color: white }, horizontalAlignment: "center" };
summary.getRange("E9:F9").format = { fill: blue, font: { size: 11, bold: true, color: white }, horizontalAlignment: "center" };
summary.getRange("C10:C13").format.numberFormat = "0%";
summary.getRange("A10:A10").format = { fill: green, font: { bold: true, color: greenInk } };
summary.getRange("A11:A11").format = { fill: amber, font: { bold: true, color: amberInk } };
summary.getRange("A12:A12").format = { fill: red, font: { bold: true, color: redInk } };
summary.getRange("A13:A13").format = { fill: paleBlue, font: { bold: true, color: blue } };
summary.getRange("A17:H18").merge();
summary.getRange("A17:H18").values = [[
  "Open Review Queue and fill the blue columns. The dataset has already passed schema and train/test leakage checks.",
]];
summary.getRange("A17:H18").format = {
  fill: paleCyan,
  font: { name: "Aptos", size: 11, bold: true, color: navy },
  wrapText: true,
  verticalAlignment: "center",
  borders: { preset: "outside", style: "thin", color: cyan },
};
summary.getRange("A:H").format.columnWidth = 15;
summary.getRange("A:A").format.columnWidth = 25;
summary.getRange("E:E").format.columnWidth = 30;
summary.getRange("A9:F15").format.rowHeight = 27;
summary.freezePanes.freezeRows(2);

await fs.mkdir(outputDir, { recursive: true });
for (const [sheetName, fileName, options] of [
  ["Summary", "training_review_summary_v0.1.png", { autoCrop: "all", scale: 1 }],
  ["Instructions", "training_review_instructions_v0.1.png", { autoCrop: "all", scale: 1 }],
  ["Review Queue", "training_review_queue_v0.1.png", { range: "A1:M18", scale: 0.8 }],
]) {
  const preview = await workbook.render({ sheetName, ...options, format: "png" });
  await fs.writeFile(path.join(outputDir, fileName), new Uint8Array(await preview.arrayBuffer()));
}

const keyCheck = await workbook.inspect({
  kind: "region",
  sheetId: "Summary",
  range: "A4:H15",
  maxChars: 5000,
});
console.log(keyCheck.ndjson);
const errorCheck = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  summary: "final formula error scan",
  maxChars: 3000,
});
console.log(errorCheck.ndjson);
const xlsx = await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(outputPath);
console.log(`Saved ${outputPath}`);
