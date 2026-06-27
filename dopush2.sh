#!/bin/bash
cd /home/pi/.picoclaw/workspace/raspberry-pi-music-ai
rm dopush.sh
git add -A
git commit -m "Remove temp script"
git push origin master 2>&1
echo "===DONE==="