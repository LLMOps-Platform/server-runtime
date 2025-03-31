# Server Runtime Types

This document describes the server runtime types component of the LLM Ops Platform, which defines different types of servers and their startup processes.

## Overview

The Server Runtime Types component provides:

1. Definitions of five server types for different roles in the LLM Ops platform
2. Initialization and startup processes for each server type
3. Configuration templates for each server type
4. Testing framework to validate server functionality

## Server Types

The platform includes the following server types:

### 1. Web Application Server

**Purpose**: Serves the OCR web interface to end users.

**Key Features**:
- Hosts the user-facing web application
- Handles user authentication and session management
- Renders UI and manages user interactions
- Communicates with the Inference API server

**Technologies**:
- Flask/Streamlit for web framework
- Gunicorn for production deployment

### 2. Inference API Server

**Purpose**: Hosts the OCR model and provides inference endpoints.

**Key Features**:
- Loads and manages PyTorch models in memory
- Preprocesses input images
- Performs inference
- Returns recognition results
- Handles model versioning

**Technologies**:
- Flask/FastAPI for API framework
- PyTorch for model inference
- Gunicorn/Uvicorn for production deployment

### 3. Load Balancer Server

**Purpose**: Distributes traffic across multiple servers.

**Key Features**:
- Routes requests to appropriate backend servers
- Performs health checks on backend services
- Handles SSL termination
- Manages traffic distribution based on load

**Technologies**:
- Nginx for HTTP load balancing
- Configuration templates for different deployment scenarios

### 4. Database Server

**Purpose**: Manages data persistence for the platform.

**Key Features**:
- Stores model metadata
- Tracks request history
- Manages user data if applicable
- Handles backup and recovery

**Technologies**:
- SQLite for simple deployments
- PostgreSQL for production deployments

### 5. Monitoring/Logging Server

**Purpose**: Collects metrics and provides visibility into system health.

**Key Features**:
- Gathers logs from all services
- Tracks server performance metrics
- Provides dashboards for visualization
- Generates alerts based on thresholds

**Technologies**:
- Prometheus for metrics collection
- Grafana for visualization (optional)

## Implementation

The server runtime types are implemented as Python classes that inherit from a common base class:

```
ServerType (Base Class)
  ├── WebAppServer
  ├── InferenceAPIServer
  ├── LoadBalancerServer
  ├── DatabaseServer
  └── MonitoringServer
```

Each server type handles its own:
- Configuration loading
- Environment setup
- Application verification
- Server startup process
- Status monitoring
- Shutdown procedure

## Configuration

Each server type is configured using a JSON configuration file with the following structure:

```json
{
  "server_type": "web",
  "port": 8080,
  "environment": {
    "ENV_VAR1": "value1",
    "ENV_VAR2": "value2"
  },
  "dependencies": [
    "package1>=1.0.0",
    "package2>=2.0.0"
  ],
  // Other server-specific configuration
}
```

Configuration templates for all server types are provided in the `configs` directory.

## Application Structure

Each application deployed on the platform is expected to have a `descriptor.json` file in its root directory that describes the application components and requirements. The server runtime uses this descriptor to properly start and configure the application.

## Usage

### Starting a Server

To start a server, use the provided startup script:

```bash
./start_server.sh [OPTIONS] SERVER_TYPE

# Example: Start a web server
./start_server.sh web

# Example: Start an API server with custom config and app directory
./start_server.sh --config-dir /etc/llm-platform/configs --app-dir /mnt/apps/ocr-v2 api
```

### Testing a Server

To test server functionality, use the provided testing script:

```bash
./test_servers.py [OPTIONS]

# Example: Test all server types
./test_servers.py

# Example: Test only the API server
./test_servers.py --server-type api
```

## Integration with Other Components

### Application Development (Component 1)

The Server Runtime Types component uses the application packages created by the Application Development component. The OCR model, API, and web application are deployed using our server types.

### Server Lifecycle Management (Component 2)

Our server types are deployed on the Linux machines provisioned by the Server Lifecycle Management component. The lifecycle manager interacts with our server programs to start and monitor applications.

### Registry/Repository Management (Component 3)

The deployment packages and configurations stored in the registry/repository are used by our server types. Our component reads from and writes status information back to the registry.

## Deployment Recommendations

1. **Development Environment**:
   - Use SQLite for the database
   - Run all server types on a single machine
   - Use Flask debug mode for easier development

2. **Production Environment**:
   - Distribute server types across multiple machines
   - Use PostgreSQL for the database
   - Enable monitoring and configure proper alerts
   - Set up high availability for critical servers

## Security Considerations

1. **Authentication**: Configure proper authentication between services
2. **Network Security**: Use internal networks for server-to-server communication
3. **Configuration Security**: Avoid storing secrets in configuration files
4. **Access Control**: Implement proper access control for each server type

## Future Enhancements

1. **Auto-scaling**: Add capability to automatically scale server instances based on load
2. **Container Support**: Enhance support for containerized deployments
3. **Advanced Monitoring**: Implement more sophisticated monitoring and alerting
4. **High Availability**: Add support for high availability configurations
5. **Resource Optimization**: Implement dynamic resource allocation based on workload

## Troubleshooting

Common issues and their solutions:

1. **Server won't start**:
   - Check if the application directory exists and has a valid descriptor.json
   - Verify that all dependencies are installed
   - Check for port conflicts

2. **Application errors**:
   - Check server logs (typically in /var/log or application directory)
   - Verify that the model file exists and is accessible
   - Ensure the app has necessary permissions

3. **Performance issues**:
   - Check resource utilization (CPU, memory, disk)
   - Verify that the server configuration matches resource availability
   - Consider increasing worker count for API and web servers
