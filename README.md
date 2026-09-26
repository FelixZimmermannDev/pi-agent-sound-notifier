# Pi Agent Sound Notifier

A small [Pi coding-agent](https://github.com/earendil-works/pi) extension for PyCharm users. It plays a short macOS sound when a Pi agent run is fully finished.

**GitHub:** [FelixZimmermannDev/pi-agent-sound-notifier](https://github.com/FelixZimmermannDev/pi-agent-sound-notifier)

## What it does

- Listens for Pi's final `agent_settled` event—not intermediate turns that may continue automatically.
- Plays the macOS `Pop` alert sound at reduced volume.
- Does not inspect prompts or transcripts and does not depend on the selected model/provider.
- Keeps audio-player failures from interrupting the Pi session.

This is a Pi extension, not a PyCharm plugin. It works when Pi is run from PyCharm's integrated terminal, as well as from other terminals. The first version targets macOS only; pop-up notifications, remote audio relays, custom settings, and other sounds are out of scope.

## Install for your Pi sessions

From this repository root, install the local package into your personal Pi settings:

```sh
pi install "$(pwd)"
```

Restart Pi after installing. Check the package is listed with `pi list`. Personal installation makes it available to Pi in any project, including PyCharm. To remove it later, run `pi remove "$(pwd)"` from this repository.

## Development checks

```sh
npm install
npm test
npm run typecheck
```

## Project status

The extension is implemented and installed locally for the current Pi user. Automated checks pass; a live completion run in PyCharm remains the final manual smoke test. See [`agentic-harness/harness/project.md`](agentic-harness/harness/project.md) and [`agentic-harness/specs/S001-pi-agent-completion-sound.md`](agentic-harness/specs/S001-pi-agent-completion-sound.md) for scope and verification status.
