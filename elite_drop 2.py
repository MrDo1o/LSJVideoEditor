#!/bin/bash
osascript <<EOF
tell application "Terminal"
    activate
    do script "python3 /Users/lsjsystemsconsulting/LSJ-Video-Editor-Swift/LSJVideoEditor/elite_drop.py"
end tell
EOF
