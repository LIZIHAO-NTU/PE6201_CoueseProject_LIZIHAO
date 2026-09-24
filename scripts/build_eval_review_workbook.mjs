import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const projectRoot = path.resolve(import.meta.dirname, "..");
const csvPath = path.join(projectRoot, "data", "eval", "message_eval_review_v0.1.csv");
const outputDir = path.join(
  projectRoot,
  "outputs",
  "019ff04b-cd46-7592-878a-23b1747c508d",
);

const csvText = (await fs.readFile(csvPath, "utf8")).replace(/^\uFEFF/, "");
const workbook = await Workbook.fromCSV(csvText, { sheetName: "Review Queue" });
const review = workbook.worksheets.getItem("Review Queue");
const instructions = workbook.worksheets.add("Instructions");
const summary = workbook.worksheets.add("Summary");

const navy = "#002D72";
const ntuBlue = "#0050B5";
const cyan = "#00A6D6";
const paleBlue = "#EAF3FF";
const paleCyan = "#E7F8FC";
const ink = "#17233C";
const muted = "#5C6B82";
const line = "#D5DEEA";
const green = "#DCFCE7";
const greenInk = "#166534";
const amber = "#FEF3C7";
const amberInk = "#92400E";
const red = "#FEE2E2";
const redInk = "#991B1B";
const white = "#FFFFFF";

function styleTitle(sheet, rangeAddress, title) {
  const range = sheet.getRange(rangeAddress);
  range.merge();
  range.values = [[title]];
  range.format = {
    fill: navy,
    font: { name: "Aptos Display", size: 20, bold: true, color: white },
    verticalAlignment: "center",
    horizontalAlignment: "left",
  };
  range.format.rowHeight = 34;
}

// Instructions sheet
instructions.showGridLines = false;
styleTitle(instructions, "A1:H2", "ScamLens SG — Evaluation Candidate Review");
instructions.getRange("A4:H4").merge();
instructions.getRange("A4:H4").values = [[
  "Purpose: create a model-independent gold test set before measuring the current system.",
]];
instructions.getRange("A4:H4").format = {
  fill: paleCyan,
  font: { name: "Aptos", size: 12, bold: true, color: navy },
  wrapText: true,
  verticalAlignment: "center",
  borders: { preset: "outside", style: "thin", color: cyan },
};
instructions.getRange("A4:H4").format.rowHeight = 38;

instructions.getRange("A6:B6").values = [["Step", "What to do"]];
instructions.getRange("A7:B11").values = [
  ["1", "Read each message without checking the current model output."],
  ["2", "For scam candidates, open the cited SPF source and check that the scenario is supported."],
  ["3", "Choose accept, edit or reject in Student Decision."],
  ["4", "If you choose edit, complete the corrected label, type and mechanisms."],
  ["5", "Use Review Notes for unnatural wording, duplicate scenarios or clues that are too obvious."],
];
instructions.getRange("A6:B11").format = {
  font: { name: "Aptos", size: 11, color: ink },
  wrapText: true,
  verticalAlignment: "center",
  borders: {
    insideHorizontal: { style: "thin", color: line },
    bottom: { style: "thin", color: line },
  },
};
instructions.getRange("A6:B6").format = {
  fill: ntuBlue,
  font: { name: "Aptos", size: 11, bold: true, color: white },
};
instructions.getRange("A7:A11").format = {
  fill: paleBlue,
  font: { name: "Aptos", size: 12, bold: true, color: ntuBlue },
  horizontalAlignment: "center",
  verticalAlignment: "center",
};
instructions.getRange("A7:B11").format.rowHeight = 42;
instructions.getRange("A13:D13").values = [["Decision", "Meaning", "Corrected fields", "Gold-set outcome"]];
instructions.getRange("A14:D16").values = [
  ["accept", "Proposed annotation is correct", "Leave blank", "Eligible for gold test set"],
  ["edit", "Candidate is useful but needs correction", "Complete corrected fields", "Eligible after correction"],
  ["reject", "Unusable, duplicated or unsupported", "Leave blank; explain why", "Exclude and replace"],
];
instructions.getRange("A13:D16").format = {
  font: { name: "Aptos", size: 11, color: ink },
  wrapText: true,
  verticalAlignment: "center",
  borders: {
    insideHorizontal: { style: "thin", color: line },
    bottom: { style: "thin", color: line },
  },
};
instructions.getRange("A13:D13").format = {
  fill: ntuBlue,
  font: { name: "Aptos", size: 11, bold: true, color: white },
};
instructions.getRange("A14:A14").format = { fill: green, font: { bold: true, color: greenInk } };
instructions.getRange("A15:A15").format = { fill: amber, font: { bold: true, color: amberInk } };
instructions.getRange("A16:A16").format = { fill: red, font: { bold: true, color: redInk } };
instructions.getRange("A14:D16").format.rowHeight = 38;
instructions.getRange("A18:H19").merge();
instructions.getRange("A18:H19").values = [[
  "Important: do not run the current classifier on individual candidates while deciding gold labels. The evaluation target must be independent of the system being tested.",
]];
instructions.getRange("A18:H19").format = {
  fill: amber,
  font: { name: "Aptos", size: 11, bold: true, color: amberInk },
  wrapText: true,
  verticalAlignment: "center",
  borders: { preset: "outside", style: "thin", color: "#F59E0B" },
};
instructions.getRange("A:A").format.columnWidth = 13;
instructions.getRange("B:B").format.columnWidth = 62;
instructions.getRange("C:D").format.columnWidth = 25;
instructions.getRange("E:H").format.columnWidth = 14;
instructions.freezePanes.freezeRows(2);

// Review queue
review.showGridLines = false;
review.freezePanes.freezeRows(1);
review.freezePanes.freezeColumns(2);
review.getRange("A1:M31").format = {
  font: { name: "Aptos", size: 10, color: ink },
  verticalAlignment: "top",
};
review.getRange("A1:M1").format = {
  fill: navy,
  font: { name: "Aptos", size: 10, bold: true, color: white },
  wrapText: true,
  verticalAlignment: "center",
  horizontalAlignment: "center",
  borders: { preset: "outside", style: "thin", color: navy },
};
review.getRange("A1:M1").format.rowHeight = 40;
review.getRange("A2:M31").format = {
  wrapText: true,
  verticalAlignment: "top",
  borders: { insideHorizontal: { style: "thin", color: line } },
};
review.getRange("A2:M31").format.rowHeight = 72;
review.getRange("I2:M31").format = {
  fill: paleBlue,
  font: { name: "Aptos", size: 10, color: ink },
  wrapText: true,
  verticalAlignment: "top",
};
review.getRange("I1:M1").format = {
  fill: ntuBlue,
  font: { name: "Aptos", size: 10, bold: true, color: white },
  wrapText: true,
  verticalAlignment: "center",
  horizontalAlignment: "center",
};

review.getRange("I2:I31").dataValidation = {
  rule: { type: "list", values: ["accept", "edit", "reject"] },
};
review.getRange("J2:J31").dataValidation = {
  rule: { type: "list", values: ["scam", "legitimate", "ambiguous"] },
};
review.getRange("K2:K31").dataValidation = {
  rule: {
    type: "list",
    values: [
      "government_impersonation",
      "investment",
      "job",
      "e_commerce",
      "not_applicable",
      "uncertain",
    ],
  },
};

for (const [text, fill, color] of [
  ["accept", green, greenInk],
  ["edit", amber, amberInk],
  ["reject", red, redInk],
]) {
  review.getRange("I2:I31").conditionalFormats.add("containsText", {
    text,
    format: { fill, font: { bold: true, color } },
  });
}
for (const [text, fill, color] of [
  ["scam", red, redInk],
  ["legitimate", green, greenInk],
  ["ambiguous", amber, amberInk],
]) {
  review.getRange("C2:C31").conditionalFormats.add("containsText", {
    text,
    format: { fill, font: { bold: true, color } },
  });
}

const widths = {
  A: 23,
  B: 58,
  C: 16,
  D: 27,
  E: 48,
  F: 38,
  G: 48,
  H: 31,
  I: 18,
  J: 19,
  K: 27,
  L: 48,
  M: 42,
};
for (const [column, width] of Object.entries(widths)) {
  review.getRange(`${column}:${column}`).format.columnWidth = width;
}
const reviewTable = review.tables.add("A1:M31", true, "EvaluationReviewTable");
reviewTable.style = "TableStyleMedium2";
reviewTable.showBandedRows = true;
reviewTable.showFilterButton = true;

// Summary sheet: all counts are formulas linked to the editable review queue.
summary.showGridLines = false;
styleTitle(summary, "A1:H2", "Review Progress Dashboard");
summary.getRange("A4:B4").merge();
summary.getRange("D4:E4").merge();
summary.getRange("G4:H4").merge();
summary.getRange("A5:B6").merge();
summary.getRange("D5:E6").merge();
summary.getRange("G5:H6").merge();
summary.getRange("A4:B4").values = [["Reviewed"]];
summary.getRange("D4:E4").values = [["Gold-ready"]];
summary.getRange("G4:H4").values = [["Pending"]];
summary.getRange("A5:B6").formulas = [["=30-COUNTBLANK('Review Queue'!I2:I31)"]];
summary.getRange("D5:E6").formulas = [["=COUNTIF('Review Queue'!I2:I31,\"accept\")+COUNTIF('Review Queue'!I2:I31,\"edit\")"]];
summary.getRange("G5:H6").formulas = [["=COUNTBLANK('Review Queue'!I2:I31)"]];

for (const range of ["A4:B4", "D4:E4", "G4:H4"]) {
  summary.getRange(range).format = {
    fill: paleBlue,
    font: { name: "Aptos", size: 11, bold: true, color: ntuBlue },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    borders: { preset: "outside", style: "thin", color: line },
  };
}
for (const range of ["A5:B6", "D5:E6", "G5:H6"]) {
  summary.getRange(range).format = {
    fill: white,
    font: { name: "Aptos Display", size: 24, bold: true, color: navy },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    borders: { preset: "outside", style: "thin", color: line },
  };
}

summary.getRange("A9:C9").values = [["Decision", "Count", "% of 30"]];
summary.getRange("A10:A13").values = [["accept"], ["edit"], ["reject"], ["pending"]];
summary.getRange("B10:B13").formulas = [
  ["=COUNTIF('Review Queue'!I2:I31,A10)"],
  ["=COUNTIF('Review Queue'!I2:I31,A11)"],
  ["=COUNTIF('Review Queue'!I2:I31,A12)"],
  ["=COUNTBLANK('Review Queue'!I2:I31)"],
];
summary.getRange("C10:C13").formulas = [
  ["=B10/30"],
  ["=B11/30"],
  ["=B12/30"],
  ["=B13/30"],
];
summary.getRange("A9:C13").format = {
  font: { name: "Aptos", size: 11, color: ink },
  borders: { insideHorizontal: { style: "thin", color: line } },
  verticalAlignment: "center",
};
summary.getRange("A9:C9").format = {
  fill: ntuBlue,
  font: { name: "Aptos", size: 11, bold: true, color: white },
  horizontalAlignment: "center",
};
summary.getRange("C10:C13").format.numberFormat = "0%";
summary.getRange("A10:A10").format = { fill: green, font: { bold: true, color: greenInk } };
summary.getRange("A11:A11").format = { fill: amber, font: { bold: true, color: amberInk } };
summary.getRange("A12:A12").format = { fill: red, font: { bold: true, color: redInk } };
summary.getRange("A13:A13").format = { fill: paleBlue, font: { bold: true, color: ntuBlue } };

summary.getRange("E9:F9").values = [["Candidate group", "Count"]];
summary.getRange("E10:E15").values = [
  ["Government impersonation"],
  ["Investment"],
  ["Job"],
  ["E-commerce"],
  ["Legitimate hard negatives"],
  ["Ambiguous / abstention"],
];
summary.getRange("F10:F15").formulas = [
  ["=COUNTIF('Review Queue'!D2:D31,\"government_impersonation\")"],
  ["=COUNTIF('Review Queue'!D2:D31,\"investment\")"],
  ["=COUNTIF('Review Queue'!D2:D31,\"job\")"],
  ["=COUNTIF('Review Queue'!D2:D31,\"e_commerce\")"],
  ["=COUNTIF('Review Queue'!C2:C31,\"legitimate\")"],
  ["=COUNTIF('Review Queue'!C2:C31,\"ambiguous\")"],
];
summary.getRange("E9:F15").format = {
  font: { name: "Aptos", size: 11, color: ink },
  borders: { insideHorizontal: { style: "thin", color: line } },
  verticalAlignment: "center",
};
summary.getRange("E9:F9").format = {
  fill: ntuBlue,
  font: { name: "Aptos", size: 11, bold: true, color: white },
  horizontalAlignment: "center",
};

summary.getRange("A17:H18").merge();
summary.getRange("A17:H18").values = [[
  "Start in the Review Queue sheet. Blue input columns are yours to edit; dropdowns are available for decisions and corrected labels.",
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

const workbookInspection = await workbook.inspect({
  kind: "workbook,sheet,table",
  maxChars: 8000,
  tableMaxRows: 4,
  tableMaxCols: 8,
  tableMaxCellChars: 60,
});
console.log(workbookInspection.ndjson);

const formulaInspection = await workbook.inspect({
  kind: "formula",
  sheetId: "Summary",
  range: "A1:H18",
  maxChars: 6000,
  options: { maxResults: 40 },
});
console.log(formulaInspection.ndjson);

const preview = await workbook.render({
  sheetName: "Summary",
  autoCrop: "all",
  scale: 1,
  format: "png",
});
await fs.writeFile(
  path.join(outputDir, "message_eval_review_summary_v0.1.png"),
  new Uint8Array(await preview.arrayBuffer()),
);

const reviewPreview = await workbook.render({
  sheetName: "Review Queue",
  autoCrop: "all",
  scale: 0.55,
  format: "png",
});
await fs.writeFile(
  path.join(outputDir, "message_eval_review_queue_v0.1.png"),
  new Uint8Array(await reviewPreview.arrayBuffer()),
);

const xlsx = await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(path.join(outputDir, "message_eval_review_v0.1.xlsx"));
console.log(`Saved workbook to ${path.join(outputDir, "message_eval_review_v0.1.xlsx")}`);
