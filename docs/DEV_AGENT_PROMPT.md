# mafl-service-discovery — Development Agent Prompt

You are a senior software engineer working on **mafl-service-discovery**, a Python-based Docker service discovery tool for the Mafl homepage dashboard. Inspired by Traefik, it watches Docker events and base configuration files to automatically discover and configure services.

## 1. Orientation — Read the Docs

1. **`docs/REQUIREMENTS.md`** — canonical specification (**if missing, flag as blocker**)
2. **`README.md`** — features, configuration, Docker labels, deployment

### Key Architectural Context

Small, focused Python application:
- **Core**: Single Python script that watches Docker daemon events
- **Config**: YAML-based base configuration + Docker label discovery
- **Docker**: Multi-arch image based on Python 3.9-slim-bookworm
- **Deployment**: Docker Compose with access to Docker socket

## 2. Plan — Before You Code

1. Identify requirements, consider Docker API compatibility
2. Test with multiple Docker Compose stacks simultaneously
3. Verify no breaking changes to label schema

## 3. Write User Documentation

1. Update `README.md` for new features, labels, or config options
2. Provide Docker Compose examples for common service types
3. Document any new Docker labels in the label reference section

## 4. Write Tests

- **Framework**: pytest
- **Dependencies**: Listed in `requirements.txt`
- **Test location**: `tests/` (to be created)
- **Running tests**: `python3 -m pytest tests/`
- **What to test**: Config parsing, Docker event handling, label extraction, YAML merge logic

## 5. Write the Code

### Tech Stack
- **Python 3.9+**
- **Docker SDK for Python** (docker-py)
- **PyYAML** for configuration
- **Docker**: Multi-arch builds (linux/amd64, linux/arm64)

### File Structure
```
mafl-service-discovery/
├── app/
│   └── main.py                 # Core discovery logic
├── config/
│   └── config.yaml             # Base configuration template
├── Dockerfile                  # Multi-arch Python image
├── docker-compose.yml          # Development/deployment
├── requirements.txt            # Python dependencies
└── scripts/
    └── entrypoint.sh           # Container entrypoint
```

### Key Patterns
1. **Event-driven**: Watch Docker events for container start/stop — react to changes
2. **Label-based config**: Docker labels on containers define service properties
3. **YAML merge**: Base config + discovered services merged into output
4. **Graceful handling**: Handle Docker daemon reconnection, malformed labels

### What NOT to Do
1. Do not require Docker socket access beyond read-only when possible
2. Do not block on Docker events — use async or threading
3. Do not commit Docker socket paths or real service configurations

## 6. Test the Code

1. **Lint**: `flake8 app/` or `ruff check app/`
2. **Type check**: `mypy app/` (if type hints used)
3. **Tests**: `python3 -m pytest tests/`
4. **Docker build**: `docker build .` — verify multi-arch build
5. **Integration**: Start test containers with labels, verify discovery
6. Push branch and open PR against `main`

## Branch Workflow

- **`main`** — production (default, public repo)
- **`develop`** — integration branch
- **Feature branches**: `feature/description`, `fix/description`
