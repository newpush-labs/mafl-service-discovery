# mafl-service-discovery — Requirements

## 1. Project Overview

**mafl-service-discovery** is a Python-based Docker service discovery tool for the [Mafl](https://github.com/hywax/mafl) homepage dashboard. Inspired by Traefik's label-based approach, it watches Docker daemon events and base configuration files to automatically discover, configure, and register services on a Mafl dashboard.

### Goals

- Eliminate manual service registration by automatically detecting Docker containers with `mafl.*` labels.
- Keep the Mafl dashboard configuration (`config/config.yml`) always in sync with the running Docker environment.
- Support static configuration via YAML files in `config/conf.d/` that are merged with discovered services.
- Run as a lightweight sidecar container alongside the Mafl dashboard.

## 2. Core Functional Requirements

### FR-1: Docker Label Discovery

The application must scan all running Docker containers and extract service metadata from containers that have `mafl.enable=true` set as a label.

**Supported labels:**

| Label | Required | Default | Description |
|---|---|---|---|| `mafl.enable` | Yes | — | Must be `"true"` to opt in |
| `mafl.group` | No | `Miscellaneous` | Dashboard group/category |
| `mafl.title` | No | Container name | Display title |
| `mafl.description` | No | `""` | Short description |
| `mafl.link` | No | `""` | URL to access the service |
| `mafl.icon.name` | No | `""` | Icon identifier (e.g. `simple-icons:docker`) |
| `mafl.icon.url` | No | `""` | Custom icon URL |
| `mafl.icon.wrap` | No | `true` | Whether to wrap the icon |
| `mafl.icon.color` | No | — | Icon colour (hex, e.g. `#007acc`) |
| `mafl.status.enabled` | No | — | Enable health-status monitoring |
| `mafl.status.interval` | No | `60` | Status check interval in seconds |

**Acceptance criteria:**

- Only running containers are included.
- Containers without `mafl.enable=true` are ignored.
- Empty or missing optional labels are omitted from the generated configuration (no empty-string values).
- Services are grouped under their `mafl.group` value.

### FR-2: Docker Event Monitoring

The application must monitor Docker daemon events in real time and regenerate the configuration whenever a container starts or stops.

**Acceptance criteria:**

- Listens for `container` and `service` event types.
- Reacts to `start` and `die` actions.
- Regenerates `config/config.yml` after each relevant event.
- Runs in a dedicated background thread so it does not block other functionality.
### FR-3: Base Configuration Merging

The application must read a base configuration from `config/base.yml` and merge it with discovered services.

**Acceptance criteria:**

- `config/base.yml` is loaded on startup and on every regeneration cycle.
- Environment variable placeholders (`${VAR_NAME}`) in the base configuration are substituted with values from the runtime environment.
- Unresolvable variables are replaced with an empty string.
- The merge is recursive: nested dictionaries are deep-merged and lists are concatenated.

### FR-4: Drop-in Configuration Files

The application must support additional YAML files placed in `config/conf.d/`. These are merged (in filesystem order) on top of the base configuration.

**Acceptance criteria:**

- Only files ending in `.yml` are processed.
- Files in `conf.d/` are merged after `base.yml` but before Docker-discovered services.
- Changes to files in `config/conf.d/` trigger a configuration regeneration.

### FR-5: File Watching

The application must watch the `config/` directory (recursively) for changes and regenerate the configuration when `base.yml` or any `conf.d/*.yml` file is modified.

**Acceptance criteria:**

- Uses filesystem event notifications (not polling).
- Reacts only to `.yml` file modifications inside `config/`.
- Runs in a dedicated background thread.
### FR-6: Configuration Output

The application must write the merged and discovered configuration to `config/config.yml`.

**Acceptance criteria:**

- The output file is written only when the new configuration differs from the current one (avoid unnecessary writes).
- The YAML output preserves key order (`sort_keys=False`).
- The output file is readable by the Mafl dashboard container via a shared Docker volume.

## 3. Non-Functional Requirements

### NFR-1: Performance

- The application must not consume excessive CPU while idle. Event monitoring and file watching must be non-blocking.
- Configuration regeneration should complete within a few seconds even with hundreds of running containers.

### NFR-2: Reliability

- The application must handle Docker daemon disconnections gracefully and recover when the daemon becomes available again.
- Malformed Docker labels or YAML files must not crash the application; errors should be logged and the problematic input skipped.

### NFR-3: Security

- The Docker socket (`/var/run/docker.sock`) should be mounted read-only when possible.
- No secrets, credentials, or real hostnames should be committed to the repository.
### NFR-4: Portability

- The Docker image must support multiple architectures: `linux/amd64`, `linux/arm64`, and `linux/arm/v7`.
- The image is based on `python:3.9-slim-bookworm` and uses a multi-stage build to minimise size.

### NFR-5: Maintainability

- The codebase should follow standard Python conventions (PEP 8).
- All public functions should include docstrings.
- A `tests/` directory with pytest-based tests should exist for all core logic (config parsing, label extraction, YAML merging, environment variable substitution).

## 4. Integration Requirements

### Docker Daemon

- Connects via the Docker socket (default: `/var/run/docker.sock`).
- Uses the Docker SDK for Python (`docker` package) to list containers and subscribe to events.

### Mafl Dashboard

- The generated `config/config.yml` is consumed by the Mafl dashboard container (`hywax/mafl`).
- Both containers share the configuration file through a Docker volume mount.
- The Mafl dashboard runs on port 3000 by default.

### CI/CD

- On push to `main`, a GitHub Actions workflow builds and pushes a multi-arch Docker image to `ghcr.io`.
- PRs to `main` must originate from the `develop` branch (enforced by the `require-develop-source` workflow).
## 5. Current Status and Implementation Gaps

### Implemented

- Docker label discovery and service extraction (`get_mafl_services`).
- Docker event monitoring in a background thread (`monitor_docker_events`).
- Base configuration loading with environment variable substitution (`replace_env_variables`).
- Drop-in `conf.d/` file merging (`merge_dicts`).
- File watching for `config/` directory changes (`watch_base_yaml`).
- Configuration output with diff-based write guard (`update_config_yaml`).
- Multi-arch Docker image build (Dockerfile, Makefile, build.sh, GitHub Actions).
- Docker Compose deployment with Mafl dashboard.

### Gaps / Future Work

- **No test suite**: The `tests/` directory does not yet exist. Unit tests for `replace_env_variables`, `get_mafl_services`, `merge_dicts`, `update_config_yaml`, and label parsing are needed.
- **No structured logging**: The application uses `print()` statements; a proper logging framework (e.g. Python `logging` module) would improve observability.
- **No graceful shutdown**: The main loop and background threads do not handle `SIGTERM`/`SIGINT` for clean container stops.
- **No health check endpoint**: There is no HTTP health check for container orchestrators to probe.
- **No input validation**: Malformed labels (e.g. non-integer `mafl.status.interval`) could cause unhandled exceptions.
- **Docker socket typo in docker-compose.yaml**: The volume mount reads `/var/run/docker.sock:/var/run/docker.sockx` (trailing `x`), which would prevent Docker event monitoring from working.