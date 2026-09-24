import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = path.resolve(import.meta.dirname, "..");
const inputPath = path.join(root, "outputs", "evaluation", "deployed_predictions_review_v0.1.csv");
const outputDir = path.join(root, "outputs", "019ff04b-cd46-7592-878a-23b1747c508d");
const outputPath = path.join(outputDir, "model_evaluation_review_v0.1.xlsx");
const csvText = (await fs.readFile(inputPath, "utf8")).replace(/^\uFEFF/, "");
const workbook = await Workbook.fromCSV(csvText, { sheetName: "Predictions" });
const predictions = workbook.worksheets.getItem("Predictions");
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

// Predictions sheet
predictions.showGridLines = false;
predictions.freezePanes.freezeRows(1);
predictions.freezePanes.freezeColumns(2);
predictions.getRange("A1:S31").format = { font: { name: "Aptos", size: 10, color: ink }, verticalAlignment: "top" };
predictions.getRange("A1:S1").format = {
  fill: navy,
  font: { name: "Aptos", size: 10, bold: true, color: white },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  wrapText: true,
};
predictions.getRange("A1:S1").format.rowHeight = 42;
predictions.getRange("A2:S31").format = {
  wrapText: true,
  verticalAlignment: "top",
  borders: { insideHorizontal: { style: "thin", color: line } },
};
predictions.getRange("A2:S31").format.rowHeight = 68;
predictions.getRange("K2").formulas = [["=G2=C2"]];
predictions.getRange("K2:K31").fillDown();
predictions.getRange("L2").formulas = [["=IF(C2=\"scam\",J2=H2,\"\")"]];
predictions.getRange("L2:L31").fillDown();
predictions.getRange("R2:S31").format = { fill: paleBlue, font: { name: "Aptos", size: 10, color: ink }, wrapText: true };
predictions.getRange("R1:S1").format = {
  fill: blue,
  font: { name: "Aptos", size: 10, bold: true, color: white },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  wrapText: true,
};
predictions.getRange("R2:R31").dataValidation = {
  rule: { type: "list", values: ["acceptable_tradeoff", "needs_mitigation", "critical_issue"] },
};
for (const [text, fill, color] of [
  ["correct", green, greenInk],
  ["conservative_abstention", paleBlue, blue],
  ["type_error", amber, amberInk],
  ["false_positive_review", amber, amberInk],
  ["ambiguous_case_miss", amber, amberInk],
  ["critical_false_reassurance", red, redInk],
]) {
  predictions.getRange("Q2:Q31").conditionalFormats.add("containsText", {
    text,
    format: { fill, font: { bold: true, color } },
  });
}
for (const [text, fill, color] of [
  ["acceptable_tradeoff", green, greenInk],
  ["needs_mitigation", amber, amberInk],
  ["critical_issue", red, redInk],
]) {
  predictions.getRange("R2:R31").conditionalFormats.add("containsText", {
    text,
    format: { fill, font: { bold: true, color } },
  });
}
const widths = { A: 22, B: 56, C: 15, D: 15, E: 16, F: 13, G: 17, H: 25, I: 25, J: 25, K: 12, L: 12, M: 16, N: 16, O: 14, P: 11, Q: 27, R: 23, S: 42 };
for (const [column, width] of Object.entries(widths)) predictions.getRange(`${column}:${column}`).format.columnWidth = width;
predictions.getRange("F2:F31").format.numberFormat = "0.0%";
predictions.getRange("M2:O31").format.numberFormat = "0.0%";
const predictionTable = predictions.tables.add("A1:S31", true, "ModelPredictionReviewTable");
predictionTable.style = "TableStyleMedium2";
predictionTable.showBandedRows = true;
predictionTable.showFilterButton = true;

// Instructions
instructions.showGridLines = false;
title(instructions, "A1:H2", "ScamLens SG — Model Error Review");
instructions.getRange("A4:H4").merge();
instructions.getRange("A4:H4").values = [[
  "This review judges system behaviour, not the gold labels. Filter out 'correct' rows and assess whether each remaining error is acceptable, needs mitigation or is critical.",
]];
instructions.getRange("A4:H4").format = {
  fill: paleCyan,
  font: { name: "Aptos", size: 12, bold: true, color: navy },
  wrapText: true,
  verticalAlignment: "center",
  borders: { preset: "outside", style: "thin", color: cyan },
};
instructions.getRange("A4:H4").format.rowHeight = 46;
instructions.getRange("A6:B6").values = [["Priority", "How to interpret it"]];
instructions.getRange("A7:B12").values = [
  ["critical_false_reassurance", "A real scam received a low-risk result. Review this first because it may delay protective action."],
  ["false_positive_review", "A legitimate message was flagged. Decide whether a conservative verification prompt is tolerable."],
  ["ambiguous_case_miss", "An insufficient-information case did not trigger the intended medium-risk abstention."],
  ["type_error", "Scam risk may be detected, but the category-specific explanation or intervention could be wrong."],
  ["conservative_abstention", "The system avoided a definitive answer and asked for verification. This is often acceptable in a safety-focused assistant."],
  ["correct", "Risk label and, for scams, category were both correct. No review is required unless the explanation seems unsafe."],
];
instructions.getRange("A6:B12").format = {
  font: { name: "Aptos", size: 11, color: ink },
  wrapText: true,
  verticalAlignment: "center",
  borders: { insideHorizontal: { style: "thin", color: line } },
};
instructions.getRange("A6:B6").format = { fill: blue, font: { size: 11, bold: true, color: white } };
instructions.getRange("A7:A7").format = { fill: red, font: { bold: true, color: redInk } };
instructions.getRange("A8:A10").format = { fill: amber, font: { bold: true, color: amberInk } };
instructions.getRange("A11:A11").format = { fill: paleBlue, font: { bold: true, color: blue } };
instructions.getRange("A12:A12").format = { fill: green, font: { bold: true, color: greenInk } };
instructions.getRange("A7:B12").format.rowHeight = 48;
instructions.getRange("A14:D14").values = [["Assessment", "Meaning", "Expected response", "Example"]];
instructions.getRange("A15:D17").values = [
  ["acceptable_tradeoff", "Behaviour is conservative but defensible", "Document the trade-off", "Medium risk on a plausible scam"],
  ["needs_mitigation", "Could confuse users or weaken intervention", "Improve explanation, data or category handling", "Wrong scam category"],
  ["critical_issue", "Could create meaningful safety harm", "Do not present as final without fixing", "Low risk on a clear scam"],
];
instructions.getRange("A14:D17").format = {
  font: { name: "Aptos", size: 11, color: ink }, wrapText: true, verticalAlignment: "center",
  borders: { insideHorizontal: { style: "thin", color: line } },
};
instructions.getRange("A14:D14").format = { fill: blue, font: { size: 11, bold: true, color: white } };
instructions.getRange("A15:A15").format = { fill: green, font: { bold: true, color: greenInk } };
instructions.getRange("A16:A16").format = { fill: amber, font: { bold: true, color: amberInk } };
instructions.getRange("A17:A17").format = { fill: red, font: { bold: true, color: redInk } };
instructions.getRange("A15:D17").format.rowHeight = 42;
instructions.getRange("A19:H20").merge();
instructions.getRange("A19:H20").values = [[
  "Important finding: validation selected a text weight of 100%. The URL analyser remains visible and useful for explanation, but it did not improve validation risk decisions in this small dataset. Treat this as a result, not as proof that URL signals are unimportant.",
]];
instructions.getRange("A19:H20").format = {
  fill: amber,
  font: { name: "Aptos", size: 11, bold: true, color: amberInk },
  wrapText: true,
  verticalAlignment: "center",
  borders: { preset: "outside", style: "thin", color: "#F59E0B" },
};
instructions.getRange("A:A").format.columnWidth = 31;
instructions.getRange("B:B").format.columnWidth = 72;
instructions.getRange("C:D").format.columnWidth = 29;
instructions.getRange("E:H").format.columnWidth = 14;
instructions.freezePanes.freezeRows(2);

// Summary
summary.showGridLines = false;
title(summary, "A1:H2", "Gold-Test Review Dashboard");
for (const [labelRange, valueRange, label, formula] of [
  ["A4:B4", "A5:B6", "Cases reviewed", "=30-COUNTBLANK('Predictions'!R2:R31)"],
  ["D4:E4", "D5:E6", "Critical false reassurance", "=COUNTIF('Predictions'!Q2:Q31,\"critical_false_reassurance\")"],
  ["G4:H4", "G5:H6", "Pending review", "=COUNTBLANK('Predictions'!R2:R31)"],
]) {
  summary.getRange(labelRange).merge(); summary.getRange(valueRange).merge();
  summary.getRange(labelRange).values = [[label]]; summary.getRange(valueRange).formulas = [[formula]];
  summary.getRange(labelRange).format = { fill: paleBlue, font: { size: 11, bold: true, color: blue }, horizontalAlignment: "center", verticalAlignment: "center", borders: { preset: "outside", style: "thin", color: line } };
  summary.getRange(valueRange).format = { fill: white, font: { name: "Aptos Display", size: 24, bold: true, color: navy }, horizontalAlignment: "center", verticalAlignment: "center", borders: { preset: "outside", style: "thin", color: line } };
}
summary.getRange("A9:C9").values = [["Metric", "Rules baseline", "Trained model"]];
summary.getRange("A10:A13").values = [["Three-way accuracy"], ["Operational scam recall"], ["Legitimate false-positive rate"], ["Scam-type accuracy"]];
summary.getRange("B10:B13").formulas = [
  ["=(COUNTIFS('Predictions'!C2:C31,\"scam\",'Predictions'!D2:D31,\"high\")+COUNTIFS('Predictions'!C2:C31,\"ambiguous\",'Predictions'!D2:D31,\"medium\")+COUNTIFS('Predictions'!C2:C31,\"legitimate\",'Predictions'!D2:D31,\"low\"))/30"],
  ["=(COUNTIFS('Predictions'!C2:C31,\"scam\",'Predictions'!D2:D31,\"high\")+COUNTIFS('Predictions'!C2:C31,\"scam\",'Predictions'!D2:D31,\"medium\"))/COUNTIF('Predictions'!C2:C31,\"scam\")"],
  ["=(COUNTIFS('Predictions'!C2:C31,\"legitimate\",'Predictions'!D2:D31,\"high\")+COUNTIFS('Predictions'!C2:C31,\"legitimate\",'Predictions'!D2:D31,\"medium\"))/COUNTIF('Predictions'!C2:C31,\"legitimate\")"],
  ["=SUMPRODUCT(--('Predictions'!C2:C31=\"scam\"),--('Predictions'!I2:I31='Predictions'!H2:H31))/COUNTIF('Predictions'!C2:C31,\"scam\")"],
];
summary.getRange("C10:C13").formulas = [
  ["=(COUNTIFS('Predictions'!C2:C31,\"scam\",'Predictions'!G2:G31,\"scam\")+COUNTIFS('Predictions'!C2:C31,\"ambiguous\",'Predictions'!G2:G31,\"ambiguous\")+COUNTIFS('Predictions'!C2:C31,\"legitimate\",'Predictions'!G2:G31,\"legitimate\"))/30"],
  ["=(COUNTIFS('Predictions'!C2:C31,\"scam\",'Predictions'!E2:E31,\"high\")+COUNTIFS('Predictions'!C2:C31,\"scam\",'Predictions'!E2:E31,\"medium\"))/COUNTIF('Predictions'!C2:C31,\"scam\")"],
  ["=(COUNTIFS('Predictions'!C2:C31,\"legitimate\",'Predictions'!E2:E31,\"high\")+COUNTIFS('Predictions'!C2:C31,\"legitimate\",'Predictions'!E2:E31,\"medium\"))/COUNTIF('Predictions'!C2:C31,\"legitimate\")"],
  ["=SUMPRODUCT(--('Predictions'!C2:C31=\"scam\"),--('Predictions'!J2:J31='Predictions'!H2:H31))/COUNTIF('Predictions'!C2:C31,\"scam\")"],
];
summary.getRange("A9:C13").format = { font: { name: "Aptos", size: 11, color: ink }, verticalAlignment: "center", borders: { insideHorizontal: { style: "thin", color: line } } };
summary.getRange("A9:C9").format = { fill: blue, font: { size: 11, bold: true, color: white }, horizontalAlignment: "center" };
summary.getRange("B10:C13").format.numberFormat = "0.0%";
summary.getRange("E9:F9").values = [["Review priority", "Count"]];
summary.getRange("E10:E15").values = [["Critical false reassurance"], ["False-positive review"], ["Ambiguous-case miss"], ["Type error"], ["Conservative abstention"], ["Correct"]];
summary.getRange("F10:F15").formulas = [
  ["=COUNTIF('Predictions'!Q2:Q31,\"critical_false_reassurance\")"],
  ["=COUNTIF('Predictions'!Q2:Q31,\"false_positive_review\")"],
  ["=COUNTIF('Predictions'!Q2:Q31,\"ambiguous_case_miss\")"],
  ["=COUNTIF('Predictions'!Q2:Q31,\"type_error\")"],
  ["=COUNTIF('Predictions'!Q2:Q31,\"conservative_abstention\")"],
  ["=COUNTIF('Predictions'!Q2:Q31,\"correct\")"],
];
summary.getRange("E9:F15").format = { font: { name: "Aptos", size: 11, color: ink }, verticalAlignment: "center", borders: { insideHorizontal: { style: "thin", color: line } } };
summary.getRange("E9:F9").format = { fill: blue, font: { size: 11, bold: true, color: white }, horizontalAlignment: "center" };
summary.getRange("E10:E10").format = { fill: red, font: { bold: true, color: redInk } };
summary.getRange("E11:E13").format = { fill: amber, font: { bold: true, color: amberInk } };
summary.getRange("E14:E14").format = { fill: paleBlue, font: { bold: true, color: blue } };
summary.getRange("E15:E15").format = { fill: green, font: { bold: true, color: greenInk } };
summary.getRange("A17:H18").merge();
summary.getRange("A17:H18").values = [["Start by filtering Predictions → review_priority = critical_false_reassurance. Then review the other non-correct rows and fill Student Assessment plus Review Notes."]];
summary.getRange("A17:H18").format = { fill: paleCyan, font: { size: 11, bold: true, color: navy }, wrapText: true, verticalAlignment: "center", borders: { preset: "outside", style: "thin", color: cyan } };
summary.getRange("A:H").format.columnWidth = 15;
summary.getRange("A:A").format.columnWidth = 29;
summary.getRange("E:E").format.columnWidth = 31;
summary.getRange("A9:F15").format.rowHeight = 28;
summary.freezePanes.freezeRows(2);

await fs.mkdir(outputDir, { recursive: true });
for (const [sheetName, fileName, options] of [
  ["Summary", "model_evaluation_summary_v0.1.png", { autoCrop: "all", scale: 1 }],
  ["Instructions", "model_evaluation_instructions_v0.1.png", { autoCrop: "all", scale: 1 }],
  ["Predictions", "model_evaluation_predictions_v0.1.png", { range: "A1:S12", scale: 0.72 }],
]) {
  const preview = await workbook.render({ sheetName, ...options, format: "png" });
  await fs.writeFile(path.join(outputDir, fileName), new Uint8Array(await preview.arrayBuffer()));
}
console.log((await workbook.inspect({ kind: "region", sheetId: "Summary", range: "A4:H18", maxChars: 6000 })).ndjson);
console.log((await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 100 }, summary: "final formula error scan", maxChars: 3000 })).ndjson);
const xlsx = await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(outputPath);
console.log(`Saved ${outputPath}`);
