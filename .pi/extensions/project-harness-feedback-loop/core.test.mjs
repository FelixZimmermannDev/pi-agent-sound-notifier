import assert from "node:assert/strict";
import test from "node:test";

import {
  extractFinalAssistantText,
  extractJsonObject,
  formatAuditReport,
  normalizeAuditReport,
  truncateUtf8,
} from "./core.mjs";

test("extractFinalAssistantText returns the last completed assistant text", () => {
  const stream = [
    JSON.stringify({ type: "message_end", message: { role: "assistant", content: [{ type: "text", text: "first" }] } }),
    JSON.stringify({ type: "message_end", message: { role: "toolResult", content: [{ type: "text", text: "ignored" }] } }),
    JSON.stringify({ type: "message_end", message: { role: "assistant", content: [{ type: "text", text: "final" }] } }),
  ].join("\n");

  assert.equal(extractFinalAssistantText(stream), "final");
});

test("extractJsonObject handles prose and braces inside strings", () => {
  const parsed = extractJsonObject('result: {"summary":"value with } brace","rootCause":"PASS"} trailing');

  assert.equal(parsed.summary, "value with } brace");
  assert.equal(parsed.rootCause, "PASS");
});

test("extractJsonObject handles fenced JSON", () => {
  assert.deepEqual(extractJsonObject('```json\n{"rootCause":"CODE"}\n```'), { rootCause: "CODE" });
});

test("normalizeAuditReport validates classifications and fills section defaults", () => {
  const report = normalizeAuditReport({
    rootCause: "harness",
    summary: "A required invariant was omitted.",
    translation: { verdict: "fail", findings: [{ requirementId: "ARCH-007", problem: "Missing revision handling." }] },
    implementation: { verdict: "unclear" },
    interfaceImprovement: {
      problem: "Concurrency requirements were not selected.",
      promptSection: "contract requirements",
      proposedChange: "Require revision handling for live background work.",
      evalCase: { input: "Add background analysis", requiredContractElements: ["revision", "stale result handling"] },
    },
  });

  assert.equal(report.rootCause, "HARNESS");
  assert.equal(report.translation.findings[0].requirementId, "ARCH-007");
  assert.deepEqual(report.implementation.findings, []);
  assert.equal(report.interfaceImprovement.evalCase.requiredContractElements.length, 2);
});

test("normalizeAuditReport rejects unknown root causes", () => {
  assert.throws(() => normalizeAuditReport({ rootCause: "STYLE" }), /Invalid evaluator root cause/);
});

test("formatAuditReport marks interface proposals as not applied", () => {
  const report = normalizeAuditReport({
    rootCause: "HARNESS",
    summary: "Translation gap.",
    translation: { verdict: "fail" },
    implementation: { verdict: "pass" },
    interfaceImprovement: {
      problem: "Missing rule.",
      promptSection: "requirements",
      proposedChange: "Select the rule.",
      evalCase: { input: "task", requiredContractElements: [] },
    },
  });

  assert.match(formatAuditReport(report, "output/run"), /not applied/);
  assert.match(formatAuditReport(report, "output/run"), /Evidence: output\/run/);
});

test("truncateUtf8 respects a byte limit for multibyte text", () => {
  const result = truncateUtf8("ä".repeat(20), 10);
  const prefix = result.split("\n\n")[0];

  assert.ok(Buffer.byteLength(prefix, "utf8") <= 10);
  assert.match(result, /truncated/);
});
