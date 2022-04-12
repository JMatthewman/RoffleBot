#!/bin/bash
echo $(date) " ## Pulling from Git ##"
echo
git pull
echo

echo $(date) " ## Launching roffle-bot.py ##"
echo
python roffle-bot.py
echo $(date) " ## roffle-bot.py exited ##"
echo
./loop.sh