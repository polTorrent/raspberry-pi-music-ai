#!/bin/bash
cd /home/pi/.picoclaw/workspace/raspberry-pi-music-ai
rm -f dopush*.sh
echo "dopush*.sh" >> .gitignore
git add -A
git commit -m "Remove temp push scripts and add to .gitignore"
git push origin master 2>&1
echo "===DONE==="
git status