#!/bin/sh
# Claude Code Stop hook: plays the same completion sound as the Pi extension.
exec /usr/bin/afplay -v 0.5 /System/Library/Sounds/Pop.aiff
