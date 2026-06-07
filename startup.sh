#!/bin/bash
set -euo pipefail

python -m pip install --disable-pip-version-check --no-cache-dir -r requirements.txt

API_PORT="${API_PORT:-8000}"
DASHBOARD_PORT="${PORT:-${WEBSITES_PORT:-8501}}"
APP_MODE="${APP_MODE:-both}"

export API_URL="${API_URL:-http://127.0.0.1:${API_PORT}}"

case "${APP_MODE}" in
	api)
		exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${API_PORT}"
		;;
	dashboard|both)
		python -m uvicorn app.main:app --host 0.0.0.0 --port "${API_PORT}" &
		API_PID=$!
		trap 'kill "${API_PID}"' EXIT
		exec python -m streamlit run dashboard.py --server.address 0.0.0.0 --server.port "${DASHBOARD_PORT}" --server.headless true
		;;
	*)
		echo "Unknown APP_MODE: ${APP_MODE}. Use 'api' or 'dashboard'." >&2
		exit 1
		;;
esac
