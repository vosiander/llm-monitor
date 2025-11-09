# LLM Monitor 🔍

A monitoring and management system for Large Language Models (LLMs) with a modern web interface.

## 🌟 Features

- 🔍 **Automatic Network Discovery**: Automatically discovers Ollama instances on your network
- 🚀 Real-time LLM monitoring with live updates
- 🎯 Plugin system for different LLM providers
- 🖥️ Modern Vue.js UI interface
- 🐍 Fast Python API with FastAPI
- 🛠️ Kubernetes-ready with Helm charts
- 🔌 Built-in Ollama integration
- 🌐 CIDR range scanning for multi-host environments
- 🔒 Security-focused design with proper CORS and host validation
- ⚡ Asynchronous network scanning with configurable parallelism

## 🏗️ Architecture

The project consists of three main components:

- **UI**: Vue.js application with a modern UI
- **API**: Python-based FastAPI server with plugin support
- **Helm Charts**: Kubernetes deployment configuration

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for local UI development)
- Python 3.8+ (for local API development)
- An LLM provider (e.g., Ollama) running locally or remotely

### Local Development

1. **Clone the repository**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/llm-monitor.git
   cd llm-monitor
   ```

2. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your network configuration
   ```
   
   **Required**: Set your network CIDR range:
   ```bash
   DISCOVERY_CIDR_RANGES=192.168.1.0/24
   ```

3. **Start the development environment**:
   ```bash
   docker-compose up
   ```

5. **Access the application**:
   - UI: http://localhost:3000
   - API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Production Deployment

Deploy to Kubernetes using Helm:

```bash
helm install llm-monitor ./helm
```

For production deployment, ensure you:
- Configure proper CORS origins in `ALLOWED_ORIGINS`
- Set up HTTPS with valid certificates
- Configure `TRUSTED_HOSTS` for your domain
- Use secure configuration management for secrets

## ⚙️ Configuration

### Network Discovery Configuration

LLM Monitor automatically discovers Ollama instances on your network using CIDR range scanning.

#### Required Environment Variables

```bash
# Comma-separated CIDR ranges to scan
DISCOVERY_CIDR_RANGES=192.168.1.0/24,10.0.0.0/16
```

#### Optional Environment Variables

```bash
# Discovery interval in seconds (default: 60)
DISCOVERY_INTERVAL_SECONDS=60

# Maximum parallel connections during scanning (default: 10)
DISCOVERY_MAX_PARALLEL=10

# Connection timeout in seconds (default: 2.0)
DISCOVERY_TIMEOUT_SECONDS=2.0

# Port to scan for Ollama (default: 11434)
DISCOVERY_PORT=11434
```

#### CIDR Range Examples

- **Single network**: `192.168.1.0/24` (scans 192.168.1.1-254)
- **Multiple networks**: `192.168.1.0/24,10.0.0.0/16` (scans both ranges)
- **Small subnet**: `192.168.1.0/28` (scans 192.168.1.1-14)
- **Large network**: `10.0.0.0/8` (scans millions of IPs - use with caution!)

### Other Environment Variables

- `ALLOWED_ORIGINS`: Comma-separated list of allowed CORS origins
- `TRUSTED_HOSTS`: Comma-separated list of trusted host headers
- `VITE_LLMMONITOR_URL`: API URL for the UI

### How Network Discovery Works

1. **Scanning**: Every 60 seconds (configurable), the system scans all configured CIDR ranges
2. **Detection**: For each IP, it checks if port 11434 is open and validates the Ollama API
3. **Registration**: Valid Ollama hosts are automatically added to the monitoring dashboard
4. **Updates**: Host status is refreshed on each scan cycle
5. **Removal**: Hosts that go offline are automatically marked as unavailable

### Performance Considerations

- **Network Size**: Scanning a /24 network (254 hosts) takes ~5-10 seconds with default settings
- **Parallel Connections**: Increase `DISCOVERY_MAX_PARALLEL` for faster scanning of large networks
- **Timeout**: Lower `DISCOVERY_TIMEOUT_SECONDS` for faster scanning but may miss slow hosts
- **Interval**: Reduce `DISCOVERY_INTERVAL_SECONDS` for more frequent updates (increases network load)
