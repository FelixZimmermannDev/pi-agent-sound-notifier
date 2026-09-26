import { spawn } from "node:child_process";
import { basename } from "node:path";
import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";

const COMPLETION_SOUND = "/System/Library/Sounds/Pop.aiff";
const AFPLAY = "/usr/bin/afplay";

function playCompletionSound(): void {
  try {
    const player = spawn(AFPLAY, ["-v", "0.5", COMPLETION_SOUND], {
      stdio: "ignore",
    });

    player.on("error", (error) => {
      console.warn(`[pi-agent-sound-notifier] Could not play completion sound: ${error.message}`);
    });
    player.on("exit", (code) => {
      if (code !== 0) {
        console.warn(`[pi-agent-sound-notifier] Audio player exited with code ${code}.`);
      }
    });
  } catch (error) {
    console.warn("[pi-agent-sound-notifier] Could not start the audio player.", error);
  }
}

function setTerminalTabStatus(ctx: ExtensionContext, completed: boolean): void {
  if (ctx.mode !== "tui") return;

  const projectName = basename(ctx.cwd) || "project";
  const marker = completed ? "🟡" : "⚪";
  try {
    ctx.ui.setTitle(`${marker} ${projectName} · Pi`);
  } catch (error) {
    console.warn("[pi-agent-sound-notifier] Could not update the terminal tab title.", error);
  }
}

export function registerCompletionSound(
  pi: Pick<ExtensionAPI, "on">,
  playSound: () => void = playCompletionSound,
): void {
  pi.on("agent_start", (_event, ctx) => {
    setTerminalTabStatus(ctx, false);
  });

  pi.on("agent_settled", (_event, ctx) => {
    try {
      playSound();
    } catch (error) {
      console.warn("[pi-agent-sound-notifier] Completion sound failed.", error);
    }
    setTerminalTabStatus(ctx, true);
  });
}

export default function (pi: ExtensionAPI): void {
  registerCompletionSound(pi);
}
