import { spawn } from "node:child_process";
import { createHash, randomUUID } from "node:crypto";
import { existsSync } from "node:fs";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { basename, join, relative, resolve } from "node:path";

import { CONFIG_DIR_NAME, type ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";

import {
  extractFinalAssistantText,
  extractJsonObject,
  formatAuditReport,
  normalizeAuditReport,
  truncateUtf8,
} from "./core.mjs";

const EXTENSION_FOLDER = "project-harness-feedback-loop";
const CONTRACT_TOOL = "record_task_contract";

type HarnessConfig = {
  schemaVersion: number;
  name: string;
  projectId: string;
  projectMarker: { path: string; contains: string };
  requireCleanWorktree: boolean;
  requirementFiles: string[];
  checks: Array<{ name: string; program: string; args: string[]; timeoutSeconds: number }>;
  audit: { thinkingLevel: string; timeoutSeconds: number; interfaceChanges: string };
  limits: { maxDiffBytes: number; maxCommandOutputBytes: number; maxUntrackedFileBytes: number };
};

type RequirementReference = { id: string; source: string; reason: string };

type TaskContract = {
  goal: string;
  scope: string[];
  doneWhen: string[];
  mustRemainUnchanged: string[];
  requirements: RequirementReference[];
  verification: string[];
  assumptions: string[];
};

type ActiveTask = {
  id: string;
  userPrompt: string;
  runDirectory: string;
  runDirectoryRelative: string;
  startHead: string;
  config: HarnessConfig;
  taskCompilerPrompt: string;
  contract?: TaskContract;
  mutationObserved: boolean;
  auditing: boolean;
};

type PiProcessResult = { code: number; stdout: string; stderr: string; timedOut: boolean };

function extensionDirectory(cwd: string): string {
  return join(cwd, CONFIG_DIR_NAME, "extensions", EXTENSION_FOLDER);
}

function samePath(left: string, right: string): boolean {
  return resolve(left).toLowerCase() === resolve(right).toLowerCase();
}

function sha256(value: string): string {
  return createHash("sha256").update(value, "utf8").digest("hex");
}

function createRunId(): string {
  const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
  return `${timestamp}_${randomUUID().slice(0, 8)}`;
}

async function loadConfig(cwd: string): Promise<HarnessConfig> {
  const path = join(extensionDirectory(cwd), "config.json");
  const parsed = JSON.parse(await readFile(path, "utf8")) as HarnessConfig;
  if (parsed.schemaVersion !== 1) throw new Error(`Unsupported harness config schema: ${parsed.schemaVersion}.`);
  return parsed;
}

async function verifyProject(pi: ExtensionAPI, cwd: string, config: HarnessConfig): Promise<void> {
  const markerPath = join(cwd, config.projectMarker.path);
  const marker = await readFile(markerPath, "utf8");
  if (!marker.includes(config.projectMarker.contains)) {
    throw new Error(`Project marker did not match ${config.projectId}: ${config.projectMarker.path}`);
  }

  const rootResult = await pi.exec("git", ["rev-parse", "--show-toplevel"], { timeout: 10000 });
  if (rootResult.code !== 0 || !samePath(rootResult.stdout.trim(), cwd)) {
    throw new Error("Run /guarded from the chess-analysis-coach Git root.");
  }

  if (config.requireCleanWorktree) {
    const status = await pi.exec("git", ["status", "--porcelain", "--untracked-files=all"], { timeout: 10000 });
    if (status.code !== 0) throw new Error("Could not inspect Git worktree status.");
    if (status.stdout.trim()) {
      throw new Error(
        "Guarded tasks require a clean worktree so the audit can attribute one diff to one request. Commit, stash, or use a separate worktree first.",
      );
    }
  }
}

async function snapshotRequirements(
  cwd: string,
  config: HarnessConfig,
  contextFiles: Array<{ path: string; content: string }>,
  runDirectory: string,
): Promise<Array<{ path: string; sha256: string }>> {
  const sources = new Map<string, string>();
  for (const contextFile of contextFiles) {
    if (contextFile?.path && typeof contextFile.content === "string") {
      sources.set(resolve(contextFile.path), contextFile.content);
    }
  }
  for (const configuredPath of config.requirementFiles) {
    const absolutePath = resolve(cwd, configuredPath);
    sources.set(absolutePath, await readFile(absolutePath, "utf8"));
  }

  const metadata: Array<{ path: string; sha256: string }> = [];
  const sections: string[] = [];
  for (const [absolutePath, content] of sources) {
    const displayPath = absolutePath.toLowerCase().startsWith(resolve(cwd).toLowerCase())
      ? relative(cwd, absolutePath).replaceAll("\\", "/")
      : absolutePath;
    metadata.push({ path: displayPath, sha256: sha256(content) });
    sections.push(`\n\n---\n\n# Requirement source: ${displayPath}\n\n${content.trim()}\n`);
  }

  await writeFile(join(runDirectory, "requirements-snapshot.md"), sections.join(""), "utf8");
  return metadata;
}

function setContractToolActive(pi: ExtensionAPI, enabled: boolean): void {
  const current = pi.getActiveTools().filter((name) => name !== CONTRACT_TOOL);
  pi.setActiveTools(enabled ? [...current, CONTRACT_TOOL] : current);
}

async function collectChanges(pi: ExtensionAPI, cwd: string, task: ActiveTask): Promise<string> {
  const tracked = await pi.exec("git", ["diff", "--binary", "--no-ext-diff", task.startHead, "--", "."], {
    timeout: 30000,
  });
  if (tracked.code !== 0) throw new Error(`Could not create task diff: ${tracked.stderr || tracked.stdout}`);

  const untrackedResult = await pi.exec("git", ["ls-files", "--others", "--exclude-standard"], { timeout: 10000 });
  if (untrackedResult.code !== 0) throw new Error("Could not list untracked files for the task diff.");

  const additions: string[] = [];
  for (const filePath of untrackedResult.stdout.split(/\r?\n/).filter(Boolean)) {
    const absolutePath = resolve(cwd, filePath);
    let content: Buffer;
    try {
      content = await readFile(absolutePath);
    } catch {
      continue;
    }
    if (content.includes(0)) {
      additions.push(`\n--- /dev/null\n+++ b/${filePath}\n[untracked binary file omitted]\n`);
      continue;
    }
    const text = truncateUtf8(content.toString("utf8"), task.config.limits.maxUntrackedFileBytes);
    const prefixed = text
      .split("\n")
      .map((line) => `+${line}`)
      .join("\n");
    additions.push(`\n--- /dev/null\n+++ b/${filePath.replaceAll("\\", "/")}\n@@ new file @@\n${prefixed}\n`);
  }

  return truncateUtf8(`${tracked.stdout}${additions.join("")}`, task.config.limits.maxDiffBytes);
}

async function runChecks(pi: ExtensionAPI, task: ActiveTask): Promise<Array<Record<string, unknown>>> {
  const results: Array<Record<string, unknown>> = [];
  for (const check of task.config.checks) {
    const startedAt = Date.now();
    try {
      const result = await pi.exec(check.program, check.args, { timeout: check.timeoutSeconds * 1000 });
      results.push({
        name: check.name,
        command: [check.program, ...check.args],
        exitCode: result.code,
        durationMs: Date.now() - startedAt,
        stdout: truncateUtf8(result.stdout, task.config.limits.maxCommandOutputBytes),
        stderr: truncateUtf8(result.stderr, task.config.limits.maxCommandOutputBytes),
      });
    } catch (error) {
      results.push({
        name: check.name,
        command: [check.program, ...check.args],
        exitCode: null,
        durationMs: Date.now() - startedAt,
        error: error instanceof Error ? error.message : String(error),
      });
    }
  }
  return results;
}

function getPiInvocation(args: string[]): { command: string; args: string[] } {
  const currentScript = process.argv[1];
  const isBunVirtualScript = currentScript?.startsWith("/$bunfs/root/");
  if (currentScript && !isBunVirtualScript && existsSync(currentScript)) {
    return { command: process.execPath, args: [currentScript, ...args] };
  }

  const executable = basename(process.execPath).toLowerCase();
  const genericRuntime = /^(node|bun)(\.exe)?$/.test(executable);
  return genericRuntime ? { command: "pi", args } : { command: process.execPath, args };
}

async function runPiProcess(cwd: string, args: string[], timeoutMs: number): Promise<PiProcessResult> {
  const invocation = getPiInvocation(args);
  return new Promise((resolvePromise) => {
    const child = spawn(invocation.command, invocation.args, {
      cwd,
      env: process.env,
      shell: false,
      windowsHide: true,
      stdio: ["ignore", "pipe", "pipe"],
    });
    let stdout = "";
    let stderr = "";
    let timedOut = false;
    const timer = setTimeout(() => {
      timedOut = true;
      child.kill("SIGTERM");
      setTimeout(() => child.kill("SIGKILL"), 5000).unref();
    }, timeoutMs);

    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });
    child.on("error", (error) => {
      stderr += `\n${error.message}`;
    });
    child.on("close", (code) => {
      clearTimeout(timer);
      resolvePromise({ code: code ?? 1, stdout, stderr, timedOut });
    });
  });
}

async function evaluateTask(cwd: string, task: ActiveTask): Promise<Record<string, unknown>> {
  const auditorPrompt = await readFile(join(extensionDirectory(cwd), "prompts", "auditor.md"), "utf8");
  const modelArgs: string[] = [];
  if (process.env.PI_PROVIDER && process.env.PI_MODEL) {
    modelArgs.push("--provider", process.env.PI_PROVIDER, "--model", process.env.PI_MODEL);
  }

  const taskPrompt = [
    `Audit the guarded run stored in ${task.runDirectoryRelative.replaceAll("\\", "/")}.`,
    "Read input.json, effective-system-prompt.md, requirements-snapshot.md, task-contract.json, changes.patch, and checks.json.",
    "Then inspect only directly relevant source and test files when evidence needs confirmation.",
    "Return exactly the JSON object required by your evaluator instructions.",
  ].join("\n");

  const args = [
    "--mode",
    "json",
    "-p",
    "--no-session",
    "--no-extensions",
    "--no-skills",
    "--no-prompt-templates",
    "--no-context-files",
    "--tools",
    "read,grep,find,ls",
    "--thinking",
    task.config.audit.thinkingLevel,
    "--append-system-prompt",
    auditorPrompt,
    ...modelArgs,
    taskPrompt,
  ];

  const result = await runPiProcess(cwd, args, task.config.audit.timeoutSeconds * 1000);
  await writeFile(join(task.runDirectory, "audit-process.json"), JSON.stringify(result, null, 2), "utf8");
  if (result.code !== 0 || result.timedOut) {
    throw new Error(
      result.timedOut
        ? "Harness evaluator timed out."
        : `Harness evaluator exited with code ${result.code}: ${result.stderr.trim() || "no stderr"}`,
    );
  }

  const finalText = extractFinalAssistantText(result.stdout);
  await writeFile(join(task.runDirectory, "audit-raw.txt"), finalText || result.stdout, "utf8");
  return normalizeAuditReport(extractJsonObject(finalText));
}

export default function projectHarnessFeedbackLoop(pi: ExtensionAPI) {
  let activeTask: ActiveTask | undefined;

  pi.registerTool({
    name: CONTRACT_TOOL,
    label: "Record Task Contract",
    description: "Record the explicit requirement-grounded contract for the active project-local guarded task before editing files.",
    parameters: Type.Object({
      goal: Type.String({ description: "Single concrete goal" }),
      scope: Type.Array(Type.String(), { description: "Bounded implementation scope" }),
      doneWhen: Type.Array(Type.String(), { description: "Observable completion conditions" }),
      mustRemainUnchanged: Type.Array(Type.String(), { description: "Behavior, state, and boundaries that must remain unchanged" }),
      requirements: Type.Array(
        Type.Object({
          id: Type.String({ description: "Stable requirement ID" }),
          source: Type.String({ description: "Canonical source path or section" }),
          reason: Type.String({ description: "Why this requirement constrains the task" }),
        }),
      ),
      verification: Type.Array(Type.String(), { description: "Focused, full-suite, and real-boundary checks as applicable" }),
      assumptions: Type.Array(Type.String(), { description: "Low-risk assumptions used by the implementation" }),
    }),
    async execute(_toolCallId, params) {
      if (!activeTask) throw new Error("No active /guarded task.");
      if (activeTask.mutationObserved) throw new Error("Record the task contract before modifying project files.");

      const contract: TaskContract = {
        goal: params.goal,
        scope: [...params.scope],
        doneWhen: [...params.doneWhen],
        mustRemainUnchanged: [...params.mustRemainUnchanged],
        requirements: params.requirements.map((requirement) => ({ ...requirement })),
        verification: [...params.verification],
        assumptions: [...params.assumptions],
      };
      activeTask.contract = contract;
      await writeFile(join(activeTask.runDirectory, "task-contract.json"), JSON.stringify(contract, null, 2), "utf8");
      return {
        content: [{ type: "text", text: `Recorded guarded task contract ${activeTask.id}.` }],
        details: { taskId: activeTask.id, contract },
      };
    },
  });

  pi.on("session_start", () => {
    activeTask = undefined;
    setContractToolActive(pi, false);
  });

  pi.on("tool_call", (event) => {
    if (!activeTask || activeTask.auditing) return;
    if (event.toolName !== "edit" && event.toolName !== "write") return;
    if (!activeTask.contract) {
      return {
        block: true,
        reason: "The active /guarded task requires record_task_contract before edit or write.",
      };
    }
    activeTask.mutationObserved = true;
  });

  pi.on("before_agent_start", async (event) => {
    if (!activeTask || activeTask.auditing) return;
    const requirementList = activeTask.config.requirementFiles.map((path) => `- ${path}`).join("\n");
    const addition = [
      activeTask.taskCompilerPrompt,
      `\n## Active guarded run\n\nRun ID: ${activeTask.id}\n\nRequirement files:\n${requirementList}`,
    ].join("\n");
    const effectivePrompt = `${event.systemPrompt}\n\n${addition}`;
    await writeFile(join(activeTask.runDirectory, "effective-system-prompt.md"), effectivePrompt, "utf8");
    return { systemPrompt: effectivePrompt };
  });

  pi.on("agent_settled", async (_event, ctx) => {
    if (!activeTask || activeTask.auditing) return;
    const task = activeTask;
    task.auditing = true;
    ctx.ui.setStatus("project-harness-feedback-loop", "auditing guarded task…");

    try {
      if (!task.contract) {
        await writeFile(
          join(task.runDirectory, "task-contract.json"),
          JSON.stringify({ error: "Coding agent did not record a task contract." }, null, 2),
          "utf8",
        );
      }

      const changes = await collectChanges(pi, ctx.cwd, task);
      await writeFile(join(task.runDirectory, "changes.patch"), changes || "[no project changes detected]\n", "utf8");
      const checks = await runChecks(pi, task);
      await writeFile(join(task.runDirectory, "checks.json"), JSON.stringify(checks, null, 2), "utf8");

      let report: ReturnType<typeof normalizeAuditReport>;
      try {
        report = (await evaluateTask(ctx.cwd, task)) as ReturnType<typeof normalizeAuditReport>;
      } catch (error) {
        report = normalizeAuditReport({
          translation: { verdict: "unclear", findings: [] },
          implementation: { verdict: "unclear", findings: [] },
          rootCause: "CHECKER",
          summary: `The independent evaluator could not complete: ${error instanceof Error ? error.message : String(error)}`,
          interfaceImprovement: null,
        });
      }
      await writeFile(join(task.runDirectory, "audit.json"), JSON.stringify(report, null, 2), "utf8");

      const display = formatAuditReport(report, task.runDirectoryRelative.replaceAll("\\", "/"));
      activeTask = undefined;
      setContractToolActive(pi, false);
      pi.sendMessage({
        customType: "project-harness-audit",
        content: display,
        display: true,
        details: { taskId: task.id, report, evidencePath: task.runDirectoryRelative },
      });
      ctx.ui.notify(`Guarded audit completed: ${report.rootCause}`, report.rootCause === "PASS" ? "info" : "warning");
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      await writeFile(join(task.runDirectory, "harness-error.txt"), message, "utf8").catch(() => undefined);
      activeTask = undefined;
      setContractToolActive(pi, false);
      ctx.ui.notify(`Project harness failed: ${message}`, "error");
    } finally {
      ctx.ui.setStatus("project-harness-feedback-loop", undefined);
    }
  });

  pi.on("session_shutdown", () => {
    activeTask = undefined;
    setContractToolActive(pi, false);
  });

  pi.registerCommand("guarded", {
    description: "Run one implementation task through the project-local harness feedback loop",
    handler: async (args, ctx) => {
      const userPrompt = args.trim();
      if (!userPrompt) {
        ctx.ui.notify("Usage: /guarded <implementation request>", "warning");
        return;
      }
      if (!ctx.isIdle()) {
        ctx.ui.notify("Wait for the current agent run to settle before starting /guarded.", "warning");
        return;
      }
      if (activeTask) {
        ctx.ui.notify(`Guarded task ${activeTask.id} is already active.`, "warning");
        return;
      }
      if (!ctx.isProjectTrusted()) {
        ctx.ui.notify("The project-local harness requires this repository to be trusted by Pi.", "error");
        return;
      }

      try {
        const config = await loadConfig(ctx.cwd);
        await verifyProject(pi, ctx.cwd, config);
        const startHeadResult = await pi.exec("git", ["rev-parse", "HEAD"], { timeout: 10000 });
        if (startHeadResult.code !== 0) throw new Error("Could not capture the starting Git revision.");

        const id = createRunId();
        const runDirectory = join(ctx.cwd, "output", "project-harness-feedback-loop", "runs", id);
        await mkdir(runDirectory, { recursive: true });
        const taskCompilerPrompt = await readFile(join(extensionDirectory(ctx.cwd), "prompts", "task-compiler.md"), "utf8");
        const systemOptions = ctx.getSystemPromptOptions();
        const contextFiles = (systemOptions.contextFiles ?? []) as Array<{ path: string; content: string }>;
        const requirementSources = await snapshotRequirements(ctx.cwd, config, contextFiles, runDirectory);

        const input = {
          schemaVersion: 1,
          taskId: id,
          projectId: config.projectId,
          originalUserPrompt: userPrompt,
          startedAt: new Date().toISOString(),
          startHead: startHeadResult.stdout.trim(),
          model: ctx.model ? { provider: ctx.model.provider, id: ctx.model.id } : null,
          thinkingLevel: ctx.thinkingLevel,
          requirementSources,
          correctionPolicy: config.audit.interfaceChanges,
        };
        await writeFile(join(runDirectory, "input.json"), JSON.stringify(input, null, 2), "utf8");

        activeTask = {
          id,
          userPrompt,
          runDirectory,
          runDirectoryRelative: relative(ctx.cwd, runDirectory),
          startHead: startHeadResult.stdout.trim(),
          config,
          taskCompilerPrompt,
          mutationObserved: false,
          auditing: false,
        };
        setContractToolActive(pi, true);
        ctx.ui.notify(`Started guarded task ${id}.`, "info");
        pi.sendUserMessage(userPrompt);
      } catch (error) {
        activeTask = undefined;
        setContractToolActive(pi, false);
        ctx.ui.notify(error instanceof Error ? error.message : String(error), "error");
      }
    },
  });
}
