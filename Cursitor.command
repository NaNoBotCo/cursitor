#!/bin/bash
# Double-click in Finder to open the Cursitor desk in your browser.
# To show a matter's dates too, write its folder after MATTER= below, in quotes.
cd "$(dirname "$0")" || exit 1
MATTER="${CURSITOR_MATTER:-}"   # e.g. MATTER="$HOME/Matters/doe-v-roe"
if [ -n "$MATTER" ]; then
  exec /usr/bin/env python3 -m cursitor desk --matter "$MATTER"
else
  exec /usr/bin/env python3 -m cursitor desk
fi
