#!/usr/bin/env python3
"""
Testing script for LLM Ops Platform server types
This script validates that each server type can be started and functions correctly
"""

import os
import sys
import json
import time
import argparse
import subprocess
import requests

# Test configuration
DEFAULT_TEST_DIR = "/tmp/llm-platform-test"
TEST_TIMEOUT = 60  # seconds


def setup_test_environment(test_dir):
    """Set up test environment with sample application"""
    print(f"Setting up test environment in {test_dir}")
    os.makedirs(test_dir, exist_ok=True)

    # Create sample descriptor.json
    descriptor = {
        "name": "Test OCR App",
        "version": "0.1.0",
        "components": {
            "web": {"web_server": "flask", "app_module": "app:app"},
            "api": {"api_module": "api:app", "framework": "flask"},
            "model": {"model_path": "model/test_model.pt"},
        },
    }

    with open(os.path.join(test_dir, "descriptor.json"), "w") as f:
        json.dump(descriptor, f, indent=2)

    # Create simple Flask app for testing
    with open(os.path.join(test_dir, "app.py"), "w") as f:
        f.write(
            """
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    return jsonify({"status": "ok", "message": "Web server is running"})

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
"""
        )

    # Create simple API for testing
    with open(os.path.join(test_dir, "api.py"), "w") as f:
        f.write(
            """
from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route('/api/predict', methods=['POST'])
def predict():
    return jsonify({
        "result": "5",
        "confidence": 0.98,
        "processing_time": 0.05
    })

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
"""
        )

    # Create model directory with dummy model
    model_dir = os.path.join(test_dir, "model")
    os.makedirs(model_dir, exist_ok=True)

    with open(os.path.join(model_dir, "test_model.pt"), "wb") as f:
        f.write(b"DUMMY MODEL CONTENT")

    # Create requirements.txt
    with open(os.path.join(test_dir, "requirements.txt"), "w") as f:
        f.write("flask==2.0.1\nrequests==2.26.0\ngunicorn==20.1.0\n")

    print("Test environment setup complete")
    return True


def create_test_configs(config_dir):
    """Create test configuration files for each server type"""
    print(f"Creating test configurations in {config_dir}")
    os.makedirs(config_dir, exist_ok=True)

    # Web server config
    web_config = {
        "server_type": "web",
        "port": 8080,
        "environment": {"FLASK_ENV": "development", "FLASK_DEBUG": "1"},
        "dependencies": ["flask", "gunicorn"],
    }

    with open(os.path.join(config_dir, "web_server.json"), "w") as f:
        json.dump(web_config, f, indent=2)

    # API server config
    api_config = {
        "server_type": "api",
        "port": 8000,
        "workers": 1,
        "environment": {"FLASK_ENV": "development", "FLASK_DEBUG": "1"},
        "dependencies": ["flask", "gunicorn"],
    }

    with open(os.path.join(config_dir, "api_server.json"), "w") as f:
        json.dump(api_config, f, indent=2)

    # Load balancer config
    lb_config = {
        "server_type": "loadbalancer",
        "port": 8081,  # Different port for testing
        "backend_servers": ["localhost:8080", "localhost:8000"],
    }

    with open(os.path.join(config_dir, "loadbalancer_server.json"), "w") as f:
        json.dump(lb_config, f, indent=2)

    # Database server config
    db_config = {
        "server_type": "database",
        "db_type": "sqlite",
        "environment": {"DATABASE_PATH": "/tmp/llm-platform-test/database"},
    }

    with open(os.path.join(config_dir, "database_server.json"), "w") as f:
        json.dump(db_config, f, indent=2)

    # Monitoring server config
    monitoring_config = {
        "server_type": "monitoring",
        "monitoring_type": "prometheus",
        "port": 9090,
        "start_grafana": False,
        "targets": ["localhost:8080", "localhost:8000"],
    }

    with open(os.path.join(config_dir, "monitoring_server.json"), "w") as f:
        json.dump(monitoring_config, f, indent=2)

    print("Test configurations created")
    return True


def test_web_server(app_dir, config_dir):
    """Test the web application server"""
    print("\n=== Testing Web Application Server ===")

    # Start the web server
    cmd = [
        "python",
        "-m",
        "server_runtime",
        "web",
        "--config",
        os.path.join(config_dir, "web_server.json"),
        "--app-dir",
        app_dir,
        "--action",
        "start",
    ]

    try:
        print(f"Starting web server: {' '.join(cmd)}")
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Give it time to start
        print("Waiting for web server to start...")
        time.sleep(5)

        # Test if the server is running
        response = requests.get("http://localhost:8080/health", timeout=5)

        if response.status_code == 200 and response.json().get("status") == "healthy":
            print("✅ Web Server test passed: Server is running and responding")
            return True
        else:
            print("❌ Web Server test failed: Server responded with unexpected data")
            print(f"Response: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ Web Server test failed: Could not connect to server: {e}")
        return False
    except Exception as e:
        print(f"❌ Web Server test failed with exception: {e}")
        return False
    finally:
        # Stop the web server
        stop_cmd = [
            "python",
            "-m",
            "server_runtime",
            "web",
            "--config",
            os.path.join(config_dir, "web_server.json"),
            "--app-dir",
            app_dir,
            "--action",
            "stop",
        ]
        subprocess.run(stop_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Kill any remaining processes (force cleanup)
        try:
            with open(os.path.join(app_dir, "web_server.pid"), "r") as f:
                pid = int(f.read().strip())
                os.kill(pid, 9)
        except:
            pass


def test_api_server(app_dir, config_dir):
    """Test the inference API server"""
    print("\n=== Testing Inference API Server ===")

    # Start the API server
    cmd = [
        "python",
        "-m",
        "server_runtime",
        "api",
        "--config",
        os.path.join(config_dir, "api_server.json"),
        "--app-dir",
        app_dir,
        "--action",
        "start",
    ]

    try:
        print(f"Starting API server: {' '.join(cmd)}")
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Give it time to start
        print("Waiting for API server to start...")
        time.sleep(5)

        # Test if the server is running
        health_response = requests.get("http://localhost:8000/health", timeout=5)

        if health_response.status_code != 200:
            print("❌ API Server test failed: Health check failed")
            return False

        # Test prediction endpoint
        test_image = {"image": "dummy_base64_data"}
        predict_response = requests.post(
            "http://localhost:8000/api/predict", json=test_image, timeout=5
        )

        if predict_response.status_code == 200 and "result" in predict_response.json():
            print(
                "✅ API Server test passed: Server is running and responding to inference requests"
            )
            return True
        else:
            print(
                "❌ API Server test failed: Prediction endpoint returned unexpected data"
            )
            print(f"Response: {predict_response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ API Server test failed: Could not connect to server: {e}")
        return False
    except Exception as e:
        print(f"❌ API Server test failed with exception: {e}")
        return False
    finally:
        # Stop the API server
        stop_cmd = [
            "python",
            "-m",
            "server_runtime",
            "api",
            "--config",
            os.path.join(config_dir, "api_server.json"),
            "--app-dir",
            app_dir,
            "--action",
            "stop",
        ]
        subprocess.run(stop_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Kill any remaining processes (force cleanup)
        try:
            with open(os.path.join(app_dir, "api_server.pid"), "r") as f:
                pid = int(f.read().strip())
                os.kill(pid, 9)
        except:
            pass


def test_database_server(app_dir, config_dir):
    """Test the database server"""
    print("\n=== Testing Database Server ===")

    # Start the database server
    cmd = [
        "python",
        "-m",
        "server_runtime",
        "database",
        "--config",
        os.path.join(config_dir, "database_server.json"),
        "--app-dir",
        app_dir,
        "--action",
        "start",
    ]

    try:
        print(f"Starting database server: {' '.join(cmd)}")
        process = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
        )

        # SQLite database should be created
        db_path = os.path.join(app_dir, "database", "app.db")
        db_dir = os.path.dirname(db_path)

        if os.path.exists(db_dir):
            print("✅ Database Server test passed: Database directory created")
            return True
        else:
            print("❌ Database Server test failed: Database directory not created")
            return False

    except subprocess.CalledProcessError as e:
        print(f"❌ Database Server test failed: Process error: {e}")
        return False
    except Exception as e:
        print(f"❌ Database Server test failed with exception: {e}")
        return False


def test_all_servers(app_dir, config_dir):
    """Run tests for all server types"""
    results = {}

    # Test web server
    results["web"] = test_web_server(app_dir, config_dir)

    # Test API server
    results["api"] = test_api_server(app_dir, config_dir)

    # Test database server (simpler test)
    results["database"] = test_database_server(app_dir, config_dir)

    # Skip load balancer and monitoring tests in basic mode
    # These might require additional system setup

    # Print summary
    print("\n=== Test Summary ===")
    for server, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{server.upper()} Server: {status}")

    # Overall result
    if all(results.values()):
        print("\n✅ All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed. See above for details.")
        return 1


def main():
    """Main entry point for the testing script"""
    parser = argparse.ArgumentParser(description="Test LLM Ops Platform server types")
    parser.add_argument(
        "--test-dir",
        default=DEFAULT_TEST_DIR,
        help=f"Directory for test application (default: {DEFAULT_TEST_DIR})",
    )
    parser.add_argument(
        "--config-dir",
        default=None,
        help="Directory for test configurations (default: test_dir/configs)",
    )
    parser.add_argument(
        "--skip-setup",
        action="store_true",
        help="Skip test environment setup (use existing)",
    )
    parser.add_argument(
        "--server-type",
        choices=["web", "api", "loadbalancer", "database", "monitoring", "all"],
        default="all",
        help="Specific server type to test (default: all)",
    )

    args = parser.parse_args()

    # Set up config directory if not specified
    if args.config_dir is None:
        args.config_dir = os.path.join(args.test_dir, "configs")

    try:
        # Set up test environment if needed
        if not args.skip_setup:
            setup_test_environment(args.test_dir)
            create_test_configs(args.config_dir)

        # Run requested tests
        if args.server_type == "all":
            return test_all_servers(args.test_dir, args.config_dir)
        elif args.server_type == "web":
            return 0 if test_web_server(args.test_dir, args.config_dir) else 1
        elif args.server_type == "api":
            return 0 if test_api_server(args.test_dir, args.config_dir) else 1
        elif args.server_type == "database":
            return 0 if test_database_server(args.test_dir, args.config_dir) else 1
        else:
            print(f"Test for {args.server_type} not implemented in basic mode")
            return 0

    except Exception as e:
        print(f"Error during testing: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
