import json
import logging
import os
import subprocess


class RegistryServer:
    def __init__(self, app_dir):
        self.server_name = self.__class__.__name__
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(self.server_name)
        self.app_dir = app_dir
        self.config = self._load_config()

    def _load_config(self):
        """Load configuration from JSON file"""
        config_path = os.path.join(self.app_dir, "descriptor.json")
        try:
            with open(config_path, "r") as config_file:
                return json.load(config_file)
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            return {}

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

    def start(self):
        self.logger.info("Starting Registry Server")

        if not self._setup_environment():
            return -1

        port = self.config.get("port", 8080)

        try:
            app_module = self.config.get("app_module", "app:app")
            cmd = ["gunicorn", "-b", f"0.0.0.0:{port}", app_module]

            # Start the server as a subprocess
            self.logger.info(f"Executing: {' '.join(cmd)}")
            proc = subprocess.Popen(
                cmd,
                cwd=self.app_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            self.logger.info(f"Registry Server started on port {port}")
            return proc.pid

        except Exception as e:
            self.logger.error(f"Failed to start Registry Server: {e}")
            return -1
