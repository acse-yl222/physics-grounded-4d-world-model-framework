#!/usr/bin/env bash
# Start (or restart) the visualiser on a workstation, detached from the terminal.
#   ./start_server.sh            # listen on 0.0.0.0:8787
#   ./start_server.sh 9000       # custom port
# Logs: server.log  ·  stop: kill $(cat server.pid)
cd "$(dirname "$0")"
PORT="${1:-8787}"
if [ -f server.pid ] && kill -0 "$(cat server.pid)" 2>/dev/null; then
  echo "stopping old server pid $(cat server.pid)"; kill "$(cat server.pid)"; sleep 1
fi
setsid nohup python3 serve.py "$PORT" --host 0.0.0.0 --no-browser > server.log 2>&1 &
echo $! > server.pid
sleep 1
echo "started pid $(cat server.pid); $(head -1 server.log)"
echo "local:     http://localhost:$PORT/viewer/3d/"
echo "tailscale: http://$(tailscale ip -4 2>/dev/null || hostname -I | awk '{print $1}'):$PORT/viewer/3d/"
