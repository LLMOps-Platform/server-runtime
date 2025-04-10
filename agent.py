import json
import logging
import os
import shutil
import subprocess

import requests
from flask import Flask, jsonify, request

from inference_server import InferenceAPIServer
from webapp_server import WebAppServer

REGISTRY_URL = "localhost:5002"
REPOSITORY_URL = "localhost:5001"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("agent")


def run_inference_server(name, version, port, workers):
    try:
        dir = requests.get(f"{REPOSITORY_URL}/get_version_files/{name}/{version}")
    except requests.RequestException as e:
        logger.error(f"Could not get files: {e}")
        return

    data = json.loads(dir.json())
    app_nfs_path = data["app"]
    inference_nfs_path = os.path.join(app_nfs_path, "inference")
    model_nfs_path = data["model"]

    # Copy files from NFS share to local directories
    app_dir = f"{name}_{version}"

    os.makedirs(app_dir, exist_ok=True)
    model_path = os.path.join(app_dir, "model.pt")

    shutil.copytree(inference_nfs_path, app_dir, dirs_exist_ok=True)
    shutil.copy(model_nfs_path, model_path)

    server = InferenceAPIServer(app_dir, model_path, port, workers)
    pid = server.start()
    if pid == -1:
        logger.error(f"Could not start inference server: {name}:{version}")
        return
    data = {name: name, version: version, pid: pid, port: port}
    try:
        response = requests.post(
            f"{REGISTRY_URL}/register_application", json=json.dumps(data)
        )
        if response.status_code == 200:
            logger.info("Registered application succesfully")
        else:
            logger.error(f"Application registration failed: {response.json()}")
            stop_service(pid)
    except requests.RequestException as e:
        logger.error(f"Failed to register application: {e}")
        stop_service(pid)


def get_application_url(name, version):
    try:
        response = requests.get(
            f"{REGISTRY_URL}/get_application_url",
            params={"name": name, "version": version},
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("port")
        elif response.status_code == 404:
            print("Application not found.")
        else:
            print(f"Error: {response.json().get('error', 'Unknown error')}")
    except requests.RequestException as e:
        print(f"Request failed: {e}")
    return None


def run_webapp_server(name, version, port):
    try:
        dir = requests.get(f"{REPOSITORY_URL}/get_version_files/{name}/{version}")
    except requests.RequestException as e:
        logger.error(f"Could not get files: {e}")
        return

    # TODO: adjust accordingly later
    data = json.loads(dir.json())
    app_nfs_path = data["app"]
    webapp_nfs_path = os.path.join(app_nfs_path, "webapp")

    # Copy files from NFS share to local directories
    app_dir = f"{name}_{version}"

    os.makedirs(app_dir, exist_ok=True)

    shutil.copytree(webapp_nfs_path, app_dir, dirs_exist_ok=True)

    inference_url = get_application_url(name, version)
    server = WebAppServer(app_dir, port, inference_url)
    pid = server.start()
    data = {name: name, version: version, pid: pid, port: port}
    try:
        response = requests.post("/register_application", json=json.dumps(data))
        if response.status_code == 200:
            logger.info("Registered application succesfully")
        else:
            logger.error(f"Application registration failed: {response.json()}")
            stop_service(pid)
    except requests.RequestException as e:
        logger.error(f"Failed to register application: {e}")
        stop_service(pid)


def stop_service(pid):
    cmd = ["kill", str(pid)]
    try:
        subprocess.run(cmd, check=True)
        logger.info(f"Process with pid ${pid} succesfully stoped")
    except subprocess.CalledProcessError:
        logger.info(f"Could not found process with pid {pid}")


app = Flask(__name__)


@app.route("/run_inference_server", methods=["POST"])
def api_run_inference_server():
    try:
        data = request.get_json()
        name = data.get("name")
        version = data.get("version")
        port = data.get("port")
        workers = data.get("workers")

        if not all([name, version, port, workers]):
            return jsonify({"error": "Missing required parameters"}), 400

        run_inference_server(name, version, port, workers)
        return jsonify({"message": "Inference server started successfully"}), 200
    except Exception as e:
        logger.error(f"Error starting inference server: {e}")
        return jsonify({"error": "Failed to start inference server"}), 500


@app.route("/run_webapp_server", methods=["POST"])
def api_run_webapp_server():
    try:
        data = request.get_json()
        name = data.get("name")
        version = data.get("version")
        port = data.get("port")

        if not all([name, version, port]):
            return jsonify({"error": "Missing required parameters"}), 400

        run_webapp_server(name, version, port)
        return jsonify({"message": "WebApp server started successfully"}), 200
    except Exception as e:
        logger.error(f"Error starting WebApp server: {e}")
        return jsonify({"error": "Failed to start WebApp server"}), 500


@app.route("/stop_service", methods=["POST"])
def api_stop_service():
    try:
        data = request.get_json()
        pid = data.get("pid")

        if not pid:
            return jsonify({"error": "Missing required parameter: pid"}), 400

        stop_service(pid)
        return jsonify({"message": f"Service with PID {pid} stopped successfully"}), 200
    except Exception as e:
        logger.error(f"Error stopping service: {e}")
        return jsonify({"error": "Failed to stop service"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
