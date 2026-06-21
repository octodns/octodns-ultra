# Developer Agent Guide for octoDNS UltraDNS Provider

This repository contains the UltraDNS provider for octoDNS. It enables planning, syncing, and applying DNS record states directly to the UltraDNS platform using its REST API.

> [!IMPORTANT]
> **Core Workflow and Guidelines**
>
> All agents working on this repository must read and follow the general instructions and workflow guidelines defined in the core octoDNS `AGENTS.md` file.
> - **Local check**: Look for the file at `../octodns/AGENTS.md`.
> - **Remote check**: If the local file is not available, fetch it from GitHub: [octoDNS Core AGENTS.md](https://github.com/octodns/octodns/raw/refs/heads/main/AGENTS.md).
>
> You must align your code structure, style, pull request guidelines, and overall development workflows with the instructions specified there.

## Repository & Module Information

### Key Components

- **Provider Class**: [UltraProvider](file:///home/ross/octodns/octodns-ultra/octodns_ultra/__init__.py#L48-L550) (defined in [octodns_ultra/__init__.py](file:///home/ross/octodns/octodns-ultra/octodns_ultra/__init__.py)). This is the core provider implementing record and zone synchronization.
- **REST Client & Authentication**: The provider handles token authentication natively by logging in to `/v2/authorization/token` with `username` and `password` to obtain a Bearer token, which it caches in its request headers. It targets the base URI `https://restapi.ultradns.com`.
- **Special Conditions**:
  - [UltraNoZonesExistException](file:///home/ross/octodns/octodns-ultra/octodns_ultra/__init__.py#L28-L37): Handles cases where no zones are defined under the account, preventing API error codes (70002) from breaking standard sync runs.

### Key Workflows & Features

1. **Supported Record Types**: `A`, `AAAA`, `ALIAS` (mapped to UltraDNS `APEXALIAS`), `CAA`, `CNAME`, `MX`, `NS`, `PTR`, `SRV`, `TXT`.
2. **Zone Types**: The provider filters and operates only on PRIMARY zones (`PRIMARY` query query parameter on `/v3/zones`).
3. **Paging limits**: Configures limit options `ZONE_REQUEST_LIMIT = 1000` and `RRSET_REQUEST_LIMIT = 1000` to page through large accounts and zone sets.
4. **Root Name Server Support**: Fully supported (`SUPPORTS_ROOT_NS=True`).
5. **Dynamic Routing**: Not supported (`SUPPORTS_DYNAMIC=False`, `SUPPORTS_GEO=False`).
6. **Dynamic Subnets**: Not supported (`SUPPORTS_DYNAMIC_SUBNETS=False`).
7. **Pool Value Status**: Not supported (`SUPPORTS_POOL_VALUE_STATUS=False`).

## Development & Testing

- **Setup Script**: Run `./script/bootstrap` to create a virtual environment, install runtime and development dependencies (including `black`, `isort`, `pyflakes`, and `pytest`), and configure pre-commit hooks.
- **Test Suite**: Run unit tests using `pytest` via `./script/test` (or `pytest tests/`). Test files are located in [tests/](file:///home/ross/octodns/octodns-ultra/tests).
- **Code Coverage**: Verify code coverage using `./script/coverage`.

## Key Constraints & Behaviors

- **Python Version**: Targets Python `>=3.9`.
- **Formatting**: Code formatting is enforced via `black` (version `>=26.0.0,<27.0.0`) and `isort`.
