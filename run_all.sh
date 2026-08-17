#!/bin/bash

# Kill background processes on exit
trap 'kill 0' SIGINT

echo "Starting Person 2: Voice Intake API (Port 5000)..."
cd voice_intake
# Ensure dependencies are installed or use existing env
# pip install -r requirements.txt
python -m app.main &
cd ..

echo "Starting Person 3: Decision Engine API (Port 8000)..."
cd decision_engine
# pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000 &
cd ..

echo "Starting Person 4: Dashboard UI (Port 5173)..."
cd dashboard/app
# npm install
npm run dev &
cd ../..

echo "All services started. Press Ctrl+C to stop."
wait
