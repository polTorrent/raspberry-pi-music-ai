#!/bin/bash
cd /home/pi/.picoclaw/workspace/raspberry-pi-music-ai
git add -A
git status --short
echo "===STATUS DONE==="
git commit -m "Make all stats and system state generic examples, not real data"
echo "===COMMIT DONE==="
git push origin master 2>&1
echo "===PUSH DONE==="