import assert from "node:assert/strict";
import { afterEach, mock, test } from "node:test";
import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";
import { registerCompletionSound } from "../extensions/agent-sound-notifier.js";

type PiHandler = (event: unknown, ctx: ExtensionContext) => void;

function fakePi() {
  const registrations: string[] = [];
  const handlers = new Map<string, PiHandler>();
  const pi = {
    on(event: string, handler: unknown) {
      registrations.push(event);
      handlers.set(event, handler as PiHandler);
      return () => {};
    },
  } as unknown as Pick<ExtensionAPI, "on">;

  return {
    pi,
    registrations,
    fire(event: string, ctx: ExtensionContext) {
      const handler = handlers.get(event);
      assert.ok(handler, `${event} handler should be registered`);
      handler({ type: event }, ctx);
    },
  };
}

function fakeContext(mode: "tui" | "rpc" = "tui", cwd = "/work/demo") {
  const titles: string[] = [];
  const ctx = {
    mode,
    cwd,
    ui: { setTitle: (title: string) => titles.push(title) },
  } as unknown as ExtensionContext;
  return { ctx, titles };
}

afterEach(() => mock.reset());

test("marks the terminal tab yellow only after the agent settles", () => {
  const { pi, registrations, fire } = fakePi();
  const { ctx, titles } = fakeContext();
  let playCount = 0;

  registerCompletionSound(pi, () => playCount++);

  assert.deepEqual(registrations, ["agent_start", "agent_settled"]);
  fire("agent_start", ctx);
  assert.deepEqual(titles, ["⚪ demo · Pi"]);
  assert.equal(playCount, 0);

  fire("agent_settled", ctx);
  assert.deepEqual(titles, ["⚪ demo · Pi", "🟡 demo · Pi"]);
  assert.equal(playCount, 1);
});

test("does not change terminal titles in non-TUI modes", () => {
  const { pi, fire } = fakePi();
  const { ctx, titles } = fakeContext("rpc");

  registerCompletionSound(pi, () => {});
  fire("agent_start", ctx);

  assert.deepEqual(titles, []);
});

test("does not let terminal-title failures interrupt agent events", () => {
  const { pi, fire } = fakePi();
  const warning = mock.method(console, "warn", () => {});
  const ctx = {
    mode: "tui",
    cwd: "/work/demo",
    ui: { setTitle: () => { throw new Error("terminal title unavailable"); } },
  } as unknown as ExtensionContext;
  let playCount = 0;

  registerCompletionSound(pi, () => playCount++);

  assert.doesNotThrow(() => fire("agent_start", ctx));
  assert.doesNotThrow(() => fire("agent_settled", ctx));
  assert.equal(playCount, 1);
  assert.equal(warning.mock.callCount(), 2);
});

test("does not let a sound failure interrupt the settled event", () => {
  const { pi, fire } = fakePi();
  const { ctx, titles } = fakeContext();
  const warning = mock.method(console, "warn", () => {});

  registerCompletionSound(pi, () => {
    throw new Error("audio unavailable");
  });

  assert.doesNotThrow(() => fire("agent_settled", ctx));
  assert.equal(warning.mock.callCount(), 1);
  assert.deepEqual(titles, ["🟡 demo · Pi"]);
});
