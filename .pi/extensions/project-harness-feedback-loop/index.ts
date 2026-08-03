import { spawn } from "node:child_process";
import { createHash, randomUUID } from "node:crypto";
import { existsSync } from "node:fs";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { basename, join, relative, resolve } from "node:path";

import { CONFIG_DIR_NAME, type ExtensionAPI } from "@earendil-works/pi-coding-agent";

const EXTENSION_FOLDER = "project-harness-feedback-loop";

type HarnessConfig = {
  schemaVersion: number;
  projectId: string;
  projectMarker: { path: string; contains: string };
  requireCleanWorktree: boolean;
  requirementFiles: string[];
  audit: { thinkingLevel: string; timeoutSeconds: number; interfaceChanges: string };
  limits: { maxDiffBytes: number; maxUntrackedFileBytes: number };
};

type ActiveTask = {
  id: string;
  runDirectory: string;
  runDirectoryRelative: string;
  startHead: string;
  config: HarnessConfig;
  interfacePrompt: string;
  input: Record<string, unknown>;
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
  return `${new Date().toISOString().replace(/[:.]/g, "-")}_${randomUUID().slice(0, 8)}`;
}

function truncateUtf8(value: string, maxBytes: number): string {
  if (Buffer.byteLength(value, "utf8") <= maxBytes) return value;
  let end = Math.min(value.length, maxBytes);
  while (Buffer.byteLength(value.slice(0, end), "utf8") > maxBytes) end -= 1;
  return `${value.slice(0, end)}\n\n[truncated by project harness]`;
}

async function loadConfig(cwd: string): Promise<HarnessConfig> {
  const config = JSON.parse(await readFile(join(extensionDirectory(cwd), "config.json"), "utf8")) as HarnessConfig;
  if (config.schemaVersion !== 1) throw new Error(`Unsupported harness config schema: ${config.schemaVersion}.`);
  return config;
}

async function verifyProject(pi: ExtensionAPI, cwd: string, config: HarnessConfig): Promise<void> {
  const marker = await readFile(join(cwd, config.projectMarker.path), "utf8");
  if (!marker.includes(config.projectMarker.contains)) {
    throw new Error(`Project marker did not match ${config.projectId}.`);
  }

  const root = await pi.exec("git", ["rev-parse", "--show-toplevel"], { timeout: 10000 });
  if (root.code !== 0 || !samePath(root.stdout.trim(), cwd)) {
    throw new Error("Run /guarded from the chess-analysis-coach Git root.");
  }

  if (config.requireCleanWorktree) {
    const status = await pi.exec("git", ["status", "--porcelain", "--untracked-files=all"], { timeout: 10000 });
    if (status.code !== 0) throw new Error("Could not inspect Git worktree status.");
    if (status.stdout.trim()) {
      throw new Error("/guarded requires a clean worktree. Commit, stash, or use a separate worktree first.");
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
  for (const file of contextFiles) {
    if (file?.path && typeof file.content === "string") sources.set(resolve(file.path), file.content);
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

async function collectChanges(pi: ExtensionAPI, cwd: string, task: ActiveTask): Promise<string> {
  const tracked = await pi.exec("git", ["diff", "--binary", "--no-ext-diff", task.startHead, "--", "."], {
    timeout: 30000,
  });
  if (tracked.code !== 0) throw new Error(`Could not create task diff: ${tracked.stderr || tracked.stdout}`);

  const untracked = await pi.exec("git", ["ls-files", "--others", "--exclude-standard"], { timeout: 10000 });
  if (untracked.code !== 0) throw new Error("Could not list untracked files.");

  const additions: string[] = [];
  for (const filePath of untracked.stdout.split(/\r?\n/).filter(Boolean)) {
    let content: Buffer;
    try {
      content = await readFile(resolve(cwd, filePath));
    } catch {
      continue;
    }
    if (content.includes(0)) {
      additions.push(`\n--- /dev/null\n+++ b/${filePath}\n[untracked binary file omitted]\n`);
      continue;
    }
    const text = truncateUtf8(content.toString("utf8"), task.config.limits.maxUntrackedFileBytes);
    additions.push(
      `\n--- /dev/null\n+++ b/${filePath.replaceAll("\\", "/")}\n@@ new file @@\n${text
        .split("\n")
        .map((line) => `+${line}`)
        .join("\n")}\n`,
    );
  }
  return truncateUtf8(`${tracked.stdout}${additions.join("")}`, task.config.limits.maxDiffBytes);
}

function latestAssistantText(ctx: { sessionManager: { getBranch(): any[] } }): string {
  const entries = ctx.sessionManager.getBranch();
  for (let index = entries.length - 1; index >= 0; index -= 1) {
    const entry = entries[index];
    if (entry.type !== "message" || entry.message?.role !== "assistant") continue;
    return (entry.message.content ?? [])
      .filter((part: any) => part?.type === "text")
      .map((part: any) => part.text)
      .join("\n")
      .trim();
  }
  return "[No final implementation summary was recorded.]";
}

function getPiInvocation(args: string[]): { command: string; args: string[] } {
  const currentScript = process.argv[1];
  if (currentScript && !currentScript.startsWith("/$bunfs/root/") && existsSync(currentScript)) {
    return { command: process.execPath, args: [currentScript, ...args] };
  }
  const genericRuntime = /^(node|bun)(\.exe)?$/.test(basename(process.execPath).toLowerCase());
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
    child.stdout.on("data", (chunk) => (stdout += chunk.toString()));
    child.stderr.on("data", (chunk) => (stderr += chunk.toString()));
    child.on("error", (error) => (stderr += `\n${error.message}`));
    child.on("close", (code) => {
      clearTimeout(timer);
      resolvePromise({ code: code ?? 1, stdout, stderr, timedOut });
    });
  });
}

async function evaluateTask(cwd: string, task: ActiveTask): Promise<string> {
  const auditorPrompt = await readFile(join(extensionDirectory(cwd), "prompts", "auditor.md"), "utf8");
  const modelArgs: string[] = [];
  if (process.env.PI_PROVIDER && process.env.PI_MODEL) {
    modelArgs.push("--provider", process.env.PI_PROVIDER, "--model", process.env.PI_MODEL);
  }
  const taskPrompt = [
    `Evaluate the guarded run in ${task.runDirectoryRelative.replaceAll("\\", "/")}.`,
    "Read input.json, effective-system-prompt.md, requirements-snapshot.md, changes.patch, and implementation-summary.md.",
    "Inspect only directly relevant current source and test files when confirmation is needed.",
  ].join("\n");
  const result = await runPiProcess(
    cwd,
    [
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
    ],
    task.config.audit.timeoutSeconds * 1000,
  );
  await writeFile(
    join(task.runDirectory, "audit-process.json"),
    JSON.stringify({ code: result.code, stderr: result.stderr, timedOut: result.timedOut }, null, 2),
    "utf8",
  );
  if (result.code !== 0 || result.timedOut || !result.stdout.trim()) {
    throw new Error(result.timedOut ? "Evaluator timed out." : result.stderr.trim() || "Evaluator returned no report.");
  }
  return result.stdout.trim();
}

export default function projectHarnessFeedbackLoop(pi: ExtensionAPI) {
  let activeTask: ActiveTask | undefined;

  pi.on("session_start", () => {
    activeTask = undefined;
  });

  pi.on("resources_discover", (event) => ({
    promptPaths: [join(extensionDirectory(event.cwd), "commands")],
  }));

  pi.on("before_agent_start", async (event) => {
    if (!activeTask || activeTask.auditing) return;
    const contextFiles = (event.systemPromptOptions.contextFiles ?? []) as Array<{ path: string; content: string }>;
    activeTask.input.requirementSources = await snapshotRequirements(
      event.systemPromptOptions.cwd,
      activeTask.config,
      contextFiles,
      activeTask.runDirectory,
    );
    await writeFile(join(activeTask.runDirectory, "input.json"), JSON.stringify(activeTask.input, null, 2), "utf8");
    const effectivePrompt = `${event.systemPrompt}\n\n${activeTask.interfacePrompt}`;
    await writeFile(join(activeTask.runDirectory, "effective-system-prompt.md"), effectivePrompt, "utf8");
    return { systemPrompt: effectivePrompt };
  });

  pi.on("agent_settled", async (_event, ctx) => {
    if (!activeTask || activeTask.auditing) return;
    const task = activeTask;
    task.auditing = true;
    ctx.ui.setStatus(EXTENSION_FOLDER, "double-checking requirements…");
    try {
      const changes = await collectChanges(pi, ctx.cwd, task);
      await writeFile(join(task.runDirectory, "changes.patch"), changes || "[no project changes detected]\n", "utf8");
      await writeFile(join(task.runDirectory, "implementation-summary.md"), latestAssistantText(ctx), "utf8");
      let report: string;
      try {
        report = await evaluateTask(ctx.cwd, task);
      } catch (error) {
        report = `Verdict: CHECKER\n\nReflection check:\n- Independent evaluator failed: ${
          error instanceof Error ? error.message : String(error)
        }\n\nCorrection:\n- None`;
      }
      await writeFile(join(task.runDirectory, "audit.md"), report, "utf8");
      activeTask = undefined;
      pi.sendMessage({
        customType: "project-harness-audit",
        content: `${report}\n\nEvidence: ${task.runDirectoryRelative.replaceAll("\\", "/")}`,
        display: true,
        details: { taskId: task.id, evidencePath: task.runDirectoryRelative },
      });
      const verdict = report.match(/^Verdict:\s*([A-Z]+)/m)?.[1] ?? "CHECKER";
      ctx.ui.notify(`Guarded double-check completed: ${verdict}`, verdict === "PASS" ? "info" : "warning");
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      await writeFile(join(task.runDirectory, "harness-error.txt"), message, "utf8").catch(() => undefined);
      activeTask = undefined;
      ctx.ui.notify(`Project harness failed: ${message}`, "error");
    } finally {
      ctx.ui.setStatus(EXTENSION_FOLDER, undefined);
    }
  });

  pi.on("session_shutdown", () => {
    activeTask = undefined;
  });

  pi.on("input", async (event, ctx) => {
    const match = event.text.match(/^\/guarded(?:\s+([\s\S]*))?$/);
    if (!match) return { action: "continue" };
    const userPrompt = (match[1] ?? "").trim();
    if (!userPrompt) {
      ctx.ui.notify("Usage: /guarded <implementation request>", "warning");
      return { action: "handled" };
    }
    if (!ctx.isIdle() || activeTask) {
      ctx.ui.notify("Wait for the current guarded task to settle first.", "warning");
      return { action: "handled" };
    }
    if (!ctx.isProjectTrusted()) {
      ctx.ui.notify("The project-local harness requires this repository to be trusted by Pi.", "error");
      return { action: "handled" };
    }

    try {
      const config = await loadConfig(ctx.cwd);
      await verifyProject(pi, ctx.cwd, config);
      const head = await pi.exec("git", ["rev-parse", "HEAD"], { timeout: 10000 });
      if (head.code !== 0) throw new Error("Could not capture the starting Git revision.");
      const id = createRunId();
      const runDirectory = join(ctx.cwd, "output", EXTENSION_FOLDER, "runs", id);
      await mkdir(runDirectory, { recursive: true });
      const input: Record<string, unknown> = {
        schemaVersion: 1,
        taskId: id,
        projectId: config.projectId,
        originalUserPrompt: userPrompt,
        startedAt: new Date().toISOString(),
        startHead: head.stdout.trim(),
        model: ctx.model ? { provider: ctx.model.provider, id: ctx.model.id } : null,
        requirementSources: [],
        interfaceChanges: config.audit.interfaceChanges,
      };
      activeTask = {
        id,
        runDirectory,
        runDirectoryRelative: relative(ctx.cwd, runDirectory),
        startHead: head.stdout.trim(),
        config,
        interfacePrompt: await readFile(join(extensionDirectory(ctx.cwd), "prompts", "interface.md"), "utf8"),
        input,
        auditing: false,
      };
      await writeFile(join(runDirectory, "input.json"), JSON.stringify(input, null, 2), "utf8");
      ctx.ui.notify(`Started guarded task ${id}.`, "info");
      return { action: "transform", text: userPrompt };
    } catch (error) {
      activeTask = undefined;
      ctx.ui.notify(error instanceof Error ? error.message : String(error), "error");
      return { action: "handled" };
    }
  });
}
