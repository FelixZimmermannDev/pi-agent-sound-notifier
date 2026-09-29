# Pi Agent Sound Notifier — Version 1.0.0

A lightweight [Pi coding-agent](https://github.com/earendil-works/pi) extension that plays a short macOS sound and marks the PyCharm terminal tab with a yellow dot when an agent run finishes. It is independent of the model/provider.

## Install

From the repository root, install it for your Pi sessions:

```sh
pi install "$(pwd)"
```

Restart Pi, then confirm the package is listed with `pi list`. It will be available in any project. Remove it with `pi remove "$(pwd)"` from this repository.

## Notifications

- Listen for Pi's final `agent_settled` event and play the macOS `Pop` sound at reduced volume.
- Show a neutral dot while Pi is working and a yellow dot in the terminal-tab title when it settles.

This is a Pi extension, not a PyCharm plugin. It uses Pi's terminal-title API; [PyCharm supports programmatically renamed terminal tabs](https://www.jetbrains.com/help/pycharm/terminal-emulator.html). Version 1.0.0 targets macOS and does not depend on the selected model/provider. The full live smoke test in a PyCharm terminal is still pending.

## Claude Code

Claude Code does not load Pi extensions. The same behaviour is available there through two hooks that run `hooks/claude-notify.sh`: `UserPromptSubmit` sets a neutral dot in the terminal-tab title, `Stop` sets the yellow dot and plays the sound. Add them to `~/.claude/settings.json` (use the absolute path of your checkout):

```json
{
  "hooks": {
    "UserPromptSubmit": [
      { "hooks": [ { "type": "command", "command": "/path/to/pi-agent-sound-notifier/hooks/claude-notify.sh start 2>/dev/null || true", "async": true } ] }
    ],
    "Stop": [
      { "hooks": [ { "type": "command", "command": "/path/to/pi-agent-sound-notifier/hooks/claude-notify.sh stop 2>/dev/null || true", "async": true } ] }
    ]
  }
}
```

Start a new Claude Code session (or open `/hooks` once) to load them. Hooks have no controlling terminal, so the script writes the title to the terminal device of the nearest ancestor process (the `claude` CLI). In the Claude desktop app there is no terminal, so only the sound plays.

For development, run `npm install`, `npm test`, and `npm run typecheck`.
