#!/bin/sh
# Claude Code hook: mirrors the Pi extension.
#   start (UserPromptSubmit) -> tab title "⚪ <project> · Claude"
#   stop  (Stop)             -> tab title "🟡 <project> · Claude" + completion sound
# Hooks run without a controlling terminal, so the title is written to the
# terminal device of the nearest ancestor process that has one.

find_tty() {
  pid=$PPID
  while [ -n "$pid" ] && [ "$pid" -gt 1 ]; do
    tty=$(ps -o tty= -p "$pid" | tr -d ' ')
    case "$tty" in
      ""|"??") pid=$(ps -o ppid= -p "$pid" | tr -d ' ') ;;
      *) echo "/dev/$tty"; return 0 ;;
    esac
  done
  return 1
}

set_title() {
  device=$(find_tty) || return 0
  [ -w "$device" ] || return 0
  project=$(basename "${CLAUDE_PROJECT_DIR:-$PWD}")
  printf '\033]0;%s %s · Claude\007' "$1" "$project" > "$device"
}

case "$1" in
  start) set_title "⚪" ;;
  stop)
    set_title "🟡"
    /usr/bin/afplay -v 0.5 /System/Library/Sounds/Pop.aiff
    ;;
esac
exit 0
