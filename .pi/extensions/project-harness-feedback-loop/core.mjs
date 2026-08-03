const ROOT_CAUSES = new Set(["PASS", "CODE", "CHECKER", "HARNESS", "SPEC", "MIXED"]);
const VERDICTS = new Set(["pass", "fail", "unclear"]);

export function truncateUtf8(value, maxBytes) {
  const text = String(value ?? "");
  if (Buffer.byteLength(text, "utf8") <= maxBytes) return text;

  let end = Math.min(text.length, maxBytes);
  let truncated = text.slice(0, end);
  while (Buffer.byteLength(truncated, "utf8") > maxBytes) {
    end -= Math.max(1, Math.ceil((Buffer.byteLength(truncated, "utf8") - maxBytes) / 2));
    truncated = text.slice(0, end);
  }
  return `${truncated}\n\n[truncated by project harness]`;
}

export function extractFinalAssistantText(jsonLines) {
  let finalText = "";
  for (const line of String(jsonLines ?? "").split(/\r?\n/)) {
    if (!line.trim()) continue;
    let event;
    try {
      event = JSON.parse(line);
    } catch {
      continue;
    }
    if (event.type !== "message_end" || event.message?.role !== "assistant") continue;
    const text = (event.message.content ?? [])
      .filter((part) => part?.type === "text")
      .map((part) => part.text)
      .join("\n")
      .trim();
    if (text) finalText = text;
  }
  return finalText;
}

export function extractJsonObject(value) {
  const text = String(value ?? "").trim();
  const fenced = text.match(/```(?:json)?\s*([\s\S]*?)```/i);
  if (fenced) return JSON.parse(fenced[1].trim());

  const start = text.indexOf("{");
  if (start < 0) throw new Error("Evaluator returned no JSON object.");

  let depth = 0;
  let inString = false;
  let escaped = false;
  for (let index = start; index < text.length; index += 1) {
    const character = text[index];
    if (inString) {
      if (escaped) escaped = false;
      else if (character === "\\") escaped = true;
      else if (character === '"') inString = false;
      continue;
    }
    if (character === '"') inString = true;
    else if (character === "{") depth += 1;
    else if (character === "}") {
      depth -= 1;
      if (depth === 0) return JSON.parse(text.slice(start, index + 1));
    }
  }
  throw new Error("Evaluator returned an incomplete JSON object.");
}

function normalizeSection(value) {
  const section = value && typeof value === "object" ? value : {};
  const verdict = VERDICTS.has(section.verdict) ? section.verdict : "unclear";
  const findings = Array.isArray(section.findings)
    ? section.findings.map((finding) => ({
        requirementId: String(finding?.requirementId ?? "UNSPECIFIED"),
        evidence: Array.isArray(finding?.evidence) ? finding.evidence.map(String) : [],
        problem: String(finding?.problem ?? "Unspecified finding."),
      }))
    : [];
  return { verdict, findings };
}

export function normalizeAuditReport(value) {
  if (!value || typeof value !== "object") throw new Error("Evaluator report must be an object.");
  const rootCause = String(value.rootCause ?? "").toUpperCase();
  if (!ROOT_CAUSES.has(rootCause)) throw new Error(`Invalid evaluator root cause: ${rootCause || "missing"}.`);

  return {
    translation: normalizeSection(value.translation),
    implementation: normalizeSection(value.implementation),
    rootCause,
    summary: String(value.summary ?? "No evaluator summary supplied."),
    interfaceImprovement:
      value.interfaceImprovement && typeof value.interfaceImprovement === "object"
        ? {
            problem: String(value.interfaceImprovement.problem ?? ""),
            promptSection: String(value.interfaceImprovement.promptSection ?? ""),
            proposedChange: String(value.interfaceImprovement.proposedChange ?? ""),
            evalCase: {
              input: String(value.interfaceImprovement.evalCase?.input ?? ""),
              requiredContractElements: Array.isArray(value.interfaceImprovement.evalCase?.requiredContractElements)
                ? value.interfaceImprovement.evalCase.requiredContractElements.map(String)
                : [],
            },
          }
        : null,
  };
}

export function formatAuditReport(report, runPath) {
  const lines = [
    `Project Harness Feedback Loop: ${report.rootCause}`,
    `Translation: ${report.translation.verdict}`,
    `Implementation: ${report.implementation.verdict}`,
    "",
    report.summary,
  ];

  const findings = [...report.translation.findings, ...report.implementation.findings];
  if (findings.length > 0) {
    lines.push("", "Findings:");
    for (const finding of findings) {
      lines.push(`- ${finding.requirementId}: ${finding.problem}`);
      for (const evidence of finding.evidence) lines.push(`  - ${evidence}`);
    }
  }

  if (report.interfaceImprovement) {
    lines.push(
      "",
      "Proposed project-local interface improvement (not applied):",
      `- Problem: ${report.interfaceImprovement.problem}`,
      `- Prompt section: ${report.interfaceImprovement.promptSection}`,
      `- Change: ${report.interfaceImprovement.proposedChange}`,
      `- Eval input: ${report.interfaceImprovement.evalCase.input}`,
    );
  }

  lines.push("", `Evidence: ${runPath}`);
  return lines.join("\n");
}
