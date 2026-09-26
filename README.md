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

For development, run `npm install`, `npm test`, and `npm run typecheck`.
