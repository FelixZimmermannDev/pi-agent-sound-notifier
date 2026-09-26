import assert from "node:assert/strict";
import { afterEach, mock, test } from "node:test";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { registerCompletionSound } from "../extensions/agent-sound-notifier.js";

type PiHandler = () => void;

function fakePi() {
  const registrations: string[] = [];
  let settledHandler: PiHandler | undefined;
  const pi = {
    on(event: string, handler: PiHandler) {
      registrations.push(event);
      if (event === "agent_settled") settledHandler = handler;
      return () => {};
    },
  } as unknown as Pick<ExtensionAPI, "on">;

  return {
    pi,
    registrations,
    settle() {
      assert.ok(settledHandler, "agent_settled handler should be registered");
      settledHandler();
    },
  };
}

afterEach(() => mock.reset());

test("plays one sound only after the agent fully settles", () => {
  const { pi, registrations, settle } = fakePi();
  let playCount = 0;

  registerCompletionSound(pi, () => playCount++);

  assert.deepEqual(registrations, ["agent_settled"]);
  assert.equal(playCount, 0);
  settle();
  assert.equal(playCount, 1);
});

test("does not let a sound failure interrupt the settled event", () => {
  const { pi, settle } = fakePi();
  const warning = mock.method(console, "warn", () => {});

  registerCompletionSound(pi, () => {
    throw new Error("audio unavailable");
  });

  assert.doesNotThrow(settle);
  assert.equal(warning.mock.callCount(), 1);
});
