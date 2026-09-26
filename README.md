# Pi Agent Sound Notifier

A lightweight [Pi coding-agent](https://github.com/earendil-works/pi) extension that plays a short macOS sound when an agent run finishes. Works from PyCharm's integrated terminal and is independent of the model/provider.

## Install

From the repository root, install it for your Pi sessions:

```sh
pi install "$(pwd)"
```

Restart Pi, then confirm the package is listed with `pi list`. It will be available in any project. Remove it with `pi remove "$(pwd)"` from this repository.

Requires Pi and macOS (`afplay`). For development, run `npm install`, `npm test`, and `npm run typecheck`.
