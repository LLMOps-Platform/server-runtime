#!/bin/bash

# Server Startup Script for LLM Ops Platform
# This script simplifies the process of starting different server types

# Default values
CONFIG_DIR="./configs"
APP_DIR="/mnt/nfs/apps/current"
ACTION="start"

# Display help information
show_help() {
  echo "Usage: $0 [OPTIONS] SERVER_TYPE"
  echo
  echo "Start a server of the specified type for the LLM Ops platform"
  echo
  echo "SERVER_TYPE can be one of: web, api, loadbalancer, database, monitoring"
  echo
  echo "Options:"
  echo "  -c, --config-dir DIR    Directory containing server configurations (default: ./configs)"
  echo "  -a, --app-dir DIR       Application directory in NFS (default: /mnt/nfs/apps/current)"
  echo "  -A, --action ACTION     Action to perform: start, stop, status (default: start)"
  echo "  -h, --help              Display this help message"
  echo
  echo "Example:"
  echo "  $0 --config-dir /etc/llm-platform/configs web"
  echo "  $0 --action stop api"
}

# Parse command line arguments
POSITIONAL=()
while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
  -c | --config-dir)
    CONFIG_DIR="$2"
    shift
    shift
    ;;
  -a | --app-dir)
    APP_DIR="$2"
    shift
    shift
    ;;
  -A | --action)
    ACTION="$2"
    shift
    shift
    ;;
  -h | --help)
    show_help
    exit 0
    ;;
  *)
    POSITIONAL+=("$1")
    shift
    ;;
  esac
done
set -- "${POSITIONAL[@]}"

# Check if server type is provided
if [ $# -lt 1 ]; then
  echo "Error: SERVER_TYPE is required"
  show_help
  exit 1
fi

SERVER_TYPE="$1"
CONFIG_FILE="${CONFIG_DIR}/${SERVER_TYPE}_server.json"

# Validate server type
case $SERVER_TYPE in
web | api | loadbalancer | database | monitoring) ;;
*)
  echo "Error: Invalid SERVER_TYPE: $SERVER_TYPE"
  show_help
  exit 1
  ;;
esac

# Validate action
case $ACTION in
start | stop | status) ;;
*)
  echo "Error: Invalid ACTION: $ACTION"
  show_help
  exit 1
  ;;
esac

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
  echo "Error: Configuration file not found: $CONFIG_FILE"
  exit 1
fi

# Check if application directory exists
if [ ! -d "$APP_DIR" ]; then
  echo "Error: Application directory not found: $APP_DIR"
  exit 1
fi

# Setup Python environment if needed
if [ -f "${APP_DIR}/requirements.txt" ]; then
  echo "Installing Python dependencies..."
  pip install -q -r "${APP_DIR}/requirements.txt"
fi

# Start the server
echo "Running ${ACTION} on ${SERVER_TYPE} server..."
python -m server_runtime ${SERVER_TYPE} --config "${CONFIG_FILE}" --app-dir "${APP_DIR}" --action "${ACTION}"

# Check if command executed successfully
if [ $? -eq 0 ]; then
  echo "${SERVER_TYPE} server ${ACTION} completed successfully"
  exit 0
else
  echo "Error ${ACTION}ing ${SERVER_TYPE} server"
  exit 1
fi
