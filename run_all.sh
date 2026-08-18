#!/bin/bash

# Kill background processes on exit
trap 'kill 0' SIGINT

export PYTHONUNBUFFERED=1
export PYTHONPATH=".:$PYTHONPATH"

echo "Starting Person 2: Voice Intake API (Port 5000)..."
python -m voice_intake.app.main &
PID_VOICE=$!

echo "Starting Person 3: Decision Engine API (Port 8000)..."
python -m uvicorn decision_engine.app.main:app --host 127.0.0.1 --port 8000 &
PID_DECISION=$!

sleep 2

echo "Starting Person 4: Dashboard UI (Port 5173)..."
cd dashboard/app
npm run dev &
PID_VITE=$!
cd ../..


echo "All services started. Press Ctrl+C to stop."
wait
