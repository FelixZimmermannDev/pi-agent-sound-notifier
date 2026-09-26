# Pi Agent Sound Notifier

A small [Pi coding-agent](https://github.com/earendil-works/pi) extension that plays a short sound when an agent run is fully complete. Designed for using Pi from PyCharm's integrated terminal.

**GitHub:** [FelixZimmermannDev/pi-agent-sound-notifier](https://github.com/FelixZimmermannDev/pi-agent-sound-notifier)

## First milestone

- Listen for Pi's `agent_settled` lifecycle event.
- Play a short local sound on macOS.
- Keep audio failures from interrupting the agent session.

This is a Pi extension, not a PyCharm plugin. The first version targets the macOS machine running Pi; cross-platform audio, remote audio relays, custom settings, and sounds for other events are out of scope.

## Status

Project initialized; implementation and installation instructions are not yet available. See [`agentic-harness/harness/project.md`](agentic-harness/harness/project.md) for the current scope and next step.
