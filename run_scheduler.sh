#!/bin/bash
# 📄 run_scheduler.sh

cd /home/mcd/email-platform
source venv/bin/activate
python3 -c "from app.main import run_scheduler; run_scheduler()" >> logs/scheduler.log 2>&1

