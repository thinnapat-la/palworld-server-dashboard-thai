#!/bin/sh
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
"$SCRIPT_DIR/palworld.command" "$1"
rc=$?
if [ "$rc" -ne 0 ]; then
  printf '\nกด Enter เพื่อปิดหน้าต่าง...'
  read answer
fi
exit "$rc"
