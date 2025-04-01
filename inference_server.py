import json
import os
import subprocess
import logging


class InferenceAPIServer:
    def __init__(self, app_dir, model_path, port, workers):
        self.app_dir = app_dir
        self.config = self._load_config()
        self.server_name = self.__class__.__name__
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(self.server_name)
        self.model_path = model_path
        self.port = port
        self.workers = workers

    def _verify_app_directory(self):
        """Verify that the application directory exists and has required files"""
        if not os.path.exists(self.app_dir):
            self.logger.error(f"Application directory {self.app_dir} does not exist")
            return False
        return True

    def _setup_environment(self):
        """Set up environment variables and dependencies"""
        self.logger.info(f"Setting up environment for {self.server_name}")

        # Set environment variables from config
        for key, value in self.config.get("environment", {}).items():
            os.environ[key] = value

        # Install dependencies if specified
        dependencies = self.config.get("dependencies", [])
        if dependencies:
            self.logger.info(f"Installing dependencies: {', '.join(dependencies)}")
            try:
                subprocess.run(["pip", "install", "-q"] + dependencies, check=True)
            except subprocess.CalledProcessError as e:
                self.logger.error(f"Failed to install dependencies: {e}")
                return False

        return True

    def _load_config(self):
        """Load configuration from JSON file"""
        config_path = os.path.join(self.app_dir, "descriptor.json")
        try:
            with open(config_path, "r") as config_file:
                return json.load(config_file)
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            return {}

    def start(self):
        """Start the inference API server"""
        self.logger.info("Starting Inference API Server")

        if not self._verify_app_directory() or not self._setup_environment():
            return -1

        # Set up model path and server configuration
        api_module = self.config.get("api_module", "api:app")

        try:
            # Export model path as environment variable for the API
            os.environ["MODEL_PATH"] = self.model_path

            # Start the API server with gunicorn for production or uvicorn for FastAPI
            if "fastapi" in api_module.lower():
                cmd = [
                    "uvicorn",
                    api_module,
                    "--host",
                    "0.0.0.0",
                    "--port",
                    str(self.port),
                    "--workers",
                    str(self.workers),
                ]
            else:
                cmd = [
                    "gunicorn",
                    "-b",
                    f"0.0.0.0:{self.port}",
                    "-w",
                    str(self.workers),
                    api_module,
                ]

            # Start the server as a subprocess
            self.logger.info(f"Executing: {' '.join(cmd)}")
            proc = subprocess.Popen(
                cmd, cwd=self.app_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )

            self.logger.info(f"Inference API Server started on port {self.port}")
            return proc.pid

        except Exception as e:
            self.logger.error(f"Failed to start Inference API Server: {e}")
            return -1
