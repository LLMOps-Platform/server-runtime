import json
import logging
import os
import subprocess
from abc import ABC, abstractmethod

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("server-runtime")

class ServerType(ABC):
    """Base class for all server types"""

    def __init__(self, config_path, app_dir):
        """
        Initialize server with configuration and application directory

        Args:
            config_path (str): Path to server configuration file
            app_dir (str): Path to application directory in shared NFS
        """
        self.config_path = config_path
        self.app_dir = app_dir
        self.config = self._load_config()
        self.server_name = self.__class__.__name__

    def _load_config(self):
        """Load configuration from JSON file"""
        try:
            with open(self.config_path, "r") as config_file:
                return json.load(config_file)
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            return {}

    def verify_app_directory(self):
        """Verify that the application directory exists and has required files"""
        if not os.path.exists(self.app_dir):
            logger.error(f"Application directory {self.app_dir} does not exist")
            return False

        # Check for descriptor.json
        descriptor_path = os.path.join(self.app_dir, "descriptor.json")
        if not os.path.exists(descriptor_path):
            logger.error(f"Application descriptor not found at {descriptor_path}")
            return False

        return True

    def setup_environment(self):
        """Set up environment variables and dependencies"""
        logger.info(f"Setting up environment for {self.server_name}")

        # Set environment variables from config
        for key, value in self.config.get("environment", {}).items():
            os.environ[key] = value

        # Install dependencies if specified
        dependencies = self.config.get("dependencies", [])
        if dependencies:
            logger.info(f"Installing dependencies: {', '.join(dependencies)}")
            try:
                subprocess.run(["pip", "install", "-q"] + dependencies, check=True)
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to install dependencies: {e}")
                return False

        return True

    @abstractmethod
    def start(self) -> bool:
        """Start the server (to be implemented by subclasses)"""
        pass

    def stop(self):
        """Stop the server"""
        logger.info(f"Stopping {self.server_name}")
        # Default implementation - override in subclasses if needed

    def status(self):
        """Check server status"""
        logger.info(f"Checking status of {self.server_name}")
        # Default implementation - override in subclasses if needed
