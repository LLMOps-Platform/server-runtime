"""
Server Runtime Types for LLM Ops Platform
This module defines the different server types and their startup processes.
"""

import argparse
import json
import logging
import os
import shutil
import subprocess
from abc import ABC, abstractmethod

# Configure logging
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


class WebAppServer(ServerType):
    """Server type for hosting the web application frontend"""

    def start(self):
        """Start the web application server"""
        logger.info("Starting Web Application Server")

        if not self.verify_app_directory() or not self.setup_environment():
            return False

        # Load web app configuration
        app_config_path = os.path.join(self.app_dir, "descriptor.json")
        with open(app_config_path, "r") as config_file:
            app_config = json.load(config_file)

        # Determine web server type (defaults to Flask)
        web_server = app_config.get("web_server", "flask")
        port = self.config.get("port", 8080)

        try:
            if web_server.lower() == "flask":
                app_module = app_config.get("app_module", "app:app")
                cmd = ["gunicorn", "-b", f"0.0.0.0:{port}", app_module]

                # Start the server as a subprocess
                logger.info(f"Executing: {' '.join(cmd)}")
                proc = subprocess.Popen(
                    cmd,
                    cwd=self.app_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )

                # Write PID to file for later management
                with open(os.path.join(self.app_dir, "web_server.pid"), "w") as f:
                    f.write(str(proc.pid))

                logger.info(f"Web Application Server started on port {port}")
                return True

            elif web_server.lower() == "streamlit":
                app_file = app_config.get("app_file", "app.py")
                app_path = os.path.join(self.app_dir, app_file)
                cmd = ["streamlit", "run", app_path, "--server.port", str(port)]

                # Start the server as a subprocess
                logger.info(f"Executing: {' '.join(cmd)}")
                proc = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )

                # Write PID to file for later management
                with open(os.path.join(self.app_dir, "web_server.pid"), "w") as f:
                    f.write(str(proc.pid))

                logger.info(f"Streamlit Web Application Server started on port {port}")
                return True

            else:
                logger.error(f"Unsupported web server type: {web_server}")
                return False

        except Exception as e:
            logger.error(f"Failed to start Web Application Server: {e}")
            return False


class InferenceAPIServer(ServerType):
    """Server type for hosting the model inference API"""

    def start(self):
        """Start the inference API server"""
        logger.info("Starting Inference API Server")

        if not self.verify_app_directory() or not self.setup_environment():
            return False

        # Load API configuration
        app_config_path = os.path.join(self.app_dir, "descriptor.json")
        with open(app_config_path, "r") as config_file:
            app_config = json.load(config_file)

        # Set up model path and server configuration
        model_path = os.path.join(self.app_dir, app_config.get("model_path", "model"))
        api_module = app_config.get("api_module", "api:app")
        port = self.config.get("port", 8000)
        workers = self.config.get("workers", 2)

        try:
            # Export model path as environment variable for the API
            os.environ["MODEL_PATH"] = model_path

            # Start the API server with gunicorn for production or uvicorn for FastAPI
            if "fastapi" in api_module.lower():
                cmd = [
                    "uvicorn",
                    api_module,
                    "--host",
                    "0.0.0.0",
                    "--port",
                    str(port),
                    "--workers",
                    str(workers),
                ]
            else:
                cmd = [
                    "gunicorn",
                    "-b",
                    f"0.0.0.0:{port}",
                    "-w",
                    str(workers),
                    api_module,
                ]

            # Start the server as a subprocess
            logger.info(f"Executing: {' '.join(cmd)}")
            proc = subprocess.Popen(
                cmd, cwd=self.app_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )

            # Write PID to file for later management
            with open(os.path.join(self.app_dir, "api_server.pid"), "w") as f:
                f.write(str(proc.pid))

            logger.info(f"Inference API Server started on port {port}")
            return True

        except Exception as e:
            logger.error(f"Failed to start Inference API Server: {e}")
            return False


class LoadBalancerServer(ServerType):
    """Server type for load balancing requests across multiple servers"""

    def start(self):
        """Start the load balancer server"""
        logger.info("Starting Load Balancer Server")

        if not self.verify_app_directory() or not self.setup_environment():
            return False

        # Get server list and configuration
        backend_servers = self.config.get("backend_servers", [])
        if not backend_servers:
            logger.error("No backend servers configured for load balancer")
            return False

        port = self.config.get("port", 80)

        try:
            # Create nginx configuration
            nginx_config = self._generate_nginx_config(backend_servers, port)
            nginx_conf_path = os.path.join(self.app_dir, "nginx.conf")

            with open(nginx_conf_path, "w") as f:
                f.write(nginx_config)

            # Create sites-available directory if it doesn't exist
            nginx_sites_dir = "/etc/nginx/sites-available"
            os.makedirs(nginx_sites_dir, exist_ok=True)

            # Copy configuration to nginx
            shutil.copy(nginx_conf_path, os.path.join(nginx_sites_dir, "llm_platform"))

            # Create symbolic link in sites-enabled
            nginx_enabled_dir = "/etc/nginx/sites-enabled"
            os.makedirs(nginx_enabled_dir, exist_ok=True)

            enabled_link = os.path.join(nginx_enabled_dir, "llm_platform")
            if os.path.exists(enabled_link):
                os.remove(enabled_link)

            os.symlink(os.path.join(nginx_sites_dir, "llm_platform"), enabled_link)

            # Restart nginx
            subprocess.run(["systemctl", "restart", "nginx"], check=True)

            logger.info(f"Load Balancer started on port {port}")
            return True

        except Exception as e:
            logger.error(f"Failed to start Load Balancer: {e}")
            return False

    def _generate_nginx_config(self, backend_servers, port):
        """Generate nginx configuration for load balancing"""
        upstream_block = "upstream backend {\n"
        for server in backend_servers:
            upstream_block += f"    server {server};\n"
        upstream_block += "}\n\n"

        server_block = f"""
server {{
    listen {port};

    location /api/ {{
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}

    location / {{
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}
"""
        return upstream_block + server_block


class DatabaseServer(ServerType):
    """Server type for database operations"""

    def start(self):
        """Start the database server"""
        logger.info("Starting Database Server")

        if not self.verify_app_directory() or not self.setup_environment():
            return False

        # Determine database type
        db_type = self.config.get("db_type", "sqlite").lower()

        try:
            if db_type == "sqlite":
                # For SQLite, just ensure the database directory exists
                db_dir = os.path.join(self.app_dir, "database")
                os.makedirs(db_dir, exist_ok=True)
                db_path = os.path.join(db_dir, "app.db")

                # Export database path as environment variable
                os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

                logger.info(f"SQLite Database configured at {db_path}")
                return True

            elif db_type == "postgres":
                # For PostgreSQL, we need to start the service if not already running
                try:
                    # Check if PostgreSQL is running
                    subprocess.run(["systemctl", "is-active", "--quiet", "postgresql"])
                except subprocess.CalledProcessError:
                    # Start PostgreSQL if not running
                    logger.info("Starting PostgreSQL service")
                    subprocess.run(["systemctl", "start", "postgresql"], check=True)

                # Set up PostgreSQL configuration
                db_name = self.config.get("db_name", "llm_platform")
                db_user = self.config.get("db_user", "postgres")
                db_password = self.config.get("db_password", "postgres")

                # Export database connection string as environment variable
                os.environ["DATABASE_URL"] = (
                    f"postgresql://{db_user}:{db_password}@localhost/{db_name}"
                )

                logger.info(f"PostgreSQL Database configured: {db_name}")
                return True

            else:
                logger.error(f"Unsupported database type: {db_type}")
                return False

        except Exception as e:
            logger.error(f"Failed to start Database Server: {e}")
            return False


class MonitoringServer(ServerType):
    """Server type for monitoring and logging"""

    def start(self):
        """Start the monitoring server"""
        logger.info("Starting Monitoring Server")

        if not self.verify_app_directory() or not self.setup_environment():
            return False

        # Get monitoring configuration
        monitoring_type = self.config.get("monitoring_type", "prometheus").lower()
        port = self.config.get("port", 9090)

        try:
            if monitoring_type == "prometheus":
                # Create Prometheus configuration
                prometheus_config = self._generate_prometheus_config()
                prometheus_config_path = os.path.join(self.app_dir, "prometheus.yml")

                with open(prometheus_config_path, "w") as f:
                    f.write(prometheus_config)

                # Start Prometheus
                cmd = [
                    "prometheus",
                    "--config.file=" + prometheus_config_path,
                    "--storage.tsdb.path="
                    + os.path.join(self.app_dir, "prometheus_data"),
                    "--web.listen-address=0.0.0.0:" + str(port),
                ]

                # Start the server as a subprocess
                logger.info(f"Executing: {' '.join(cmd)}")
                proc = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )

                # Write PID to file for later management
                with open(
                    os.path.join(self.app_dir, "monitoring_server.pid"), "w"
                ) as f:
                    f.write(str(proc.pid))

                # Start Grafana if specified
                if self.config.get("start_grafana", False):
                    grafana_port = self.config.get("grafana_port", 3000)
                    logger.info(f"Starting Grafana on port {grafana_port}")
                    subprocess.run(["systemctl", "start", "grafana-server"], check=True)

                logger.info(f"Monitoring Server started on port {port}")
                return True

            else:
                logger.error(f"Unsupported monitoring type: {monitoring_type}")
                return False

        except Exception as e:
            logger.error(f"Failed to start Monitoring Server: {e}")
            return False

    def _generate_prometheus_config(self):
        """Generate Prometheus configuration"""
        targets = self.config.get("targets", [])
        if not targets:
            # Default to localhost if no targets specified
            targets = ["localhost:8080", "localhost:8000"]

        config = (
            """
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'llm_platform'
    static_configs:
      - targets: ["""
            + ", ".join([f"'{target}'" for target in targets])
            + """]
"""
        )
        return config


# Factory function to create server instances
def create_server(server_type, config_path, app_dir):
    """
    Factory function to create a server instance based on type

    Args:
        server_type (str): Type of server to create
        config_path (str): Path to server configuration
        app_dir (str): Path to application directory

    Returns:
        ServerType: Instance of the specified server type
    """
    server_types = {
        "web": WebAppServer,
        "api": InferenceAPIServer,
        "loadbalancer": LoadBalancerServer,
        "database": DatabaseServer,
        "monitoring": MonitoringServer,
    }

    if server_type.lower() not in server_types:
        raise ValueError(f"Unknown server type: {server_type}")

    return server_types[server_type.lower()](config_path, app_dir)


def main():
    """Main entry point for server startup"""
    parser = argparse.ArgumentParser(description="Start a server of the specified type")
    parser.add_argument(
        "server_type",
        choices=["web", "api", "loadbalancer", "database", "monitoring"],
        help="Type of server to start",
    )
    parser.add_argument(
        "--config", required=True, help="Path to server configuration file"
    )
    parser.add_argument(
        "--app-dir", required=True, help="Path to application directory in shared NFS"
    )
    parser.add_argument(
        "--action",
        choices=["start", "stop", "status"],
        default="start",
        help="Action to perform (default: start)",
    )

    args = parser.parse_args()

    try:
        # Create server instance
        server = create_server(args.server_type, args.config, args.app_dir)

        # Perform requested action
        if args.action == "start":
            success = server.start()
            return 0 if success else 1
        elif args.action == "stop":
            server.stop()
            return 0
        elif args.action == "status":
            server.status()
            return 0

    except Exception as e:
        logger.error(f"Error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
