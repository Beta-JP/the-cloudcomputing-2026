#!/bin/bash
set -euo pipefail

if [[ -n "${PYTHON_BIN:-}" ]]; then
	PYTHON_CMD="${PYTHON_BIN}"
elif [[ -x "./antenv/bin/python" ]]; then
	PYTHON_CMD="./antenv/bin/python"
elif [[ -x "./venv/bin/python" ]]; then
	PYTHON_CMD="./venv/bin/python"
else
	PYTHON_CMD="python"
fi

if [[ "${FORCE_PIP_INSTALL:-0}" == "1" ]]; then
	"${PYTHON_CMD}" -m pip install --disable-pip-version-check --no-cache-dir -r requirements.txt
elif [[ "${SKIP_PIP_INSTALL:-0}" == "1" ]]; then
	:
elif [[ -n "${WEBSITE_SITE_NAME:-}" && "${SCM_DO_BUILD_DURING_DEPLOYMENT:-false}" == "true" ]]; then
	:
else
	"${PYTHON_CMD}" -m pip install --disable-pip-version-check --no-cache-dir -r requirements.txt
fi

API_PORT="${API_PORT:-8000}"
DASHBOARD_PORT="${PORT:-${WEBSITES_PORT:-8501}}"
APP_MODE="${APP_MODE:-both}"

if [[ "${APP_MODE}" != "api" && "${API_PORT}" == "${DASHBOARD_PORT}" ]]; then
	API_PORT="8001"
fi

export API_URL="http://127.0.0.1:${API_PORT}"

case "${APP_MODE}" in
	api)
		exec "${PYTHON_CMD}" -m uvicorn app.main:app --host 0.0.0.0 --port "${API_PORT}"
		;;
	dashboard|both)
		"${PYTHON_CMD}" -m uvicorn app.main:app --host 0.0.0.0 --port "${API_PORT}" &
		API_PID=$!
		trap 'kill "${API_PID}"' EXIT
		exec "${PYTHON_CMD}" -m streamlit run dashboard.py --server.address 0.0.0.0 --server.port "${DASHBOARD_PORT}" --server.headless true
		;;
	*)
		echo "Unknown APP_MODE: ${APP_MODE}. Use 'api' or 'dashboard'." >&2
		exit 1
		;;
esac
