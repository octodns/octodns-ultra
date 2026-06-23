## 1.1.1 - 2026-06-23

Patch:
* Update API base URL and pin UltraDNS API version - [#79](https://github.com/octodns/octodns-ultra/pull/79)

## 1.1.0 - 2026-06-22

Minor:
* Migrate to the UltraDNS v3 REST API (v2 URL prefix deprecated) - [#74](https://github.com/octodns/octodns-ultra/pull/74)
* ValiMonitor as a configurable provider parameter, disabled by default, ignore related records when enabled - [#73](https://github.com/octodns/octodns-ultra/pull/73)

## v1.0.0 - 2025-05-04 - Long overdue 1.0

### Notedworthy Changes:

* `SPF` record support removed, records should be migrated to `TXT` before
  upgrading.
* Requires octoDNS >= 1.5.0

## v0.0.3 - 2024-02-26 - A long overdue one

* Enable support for root level NS records (`SUPPORTS_ROOT_NS=true`)
* Enable support for wildcard zone lookups (list_zones())
* Skip unsupported dynamic record type "Directional Pool"

## v0.0.2 - 2022-10-10 - APIs gonna break

* Update zone metadata API call to v3 as v2 no longer works

## v0.0.1 - 2022-01-17 - Moving

#### Nothworthy Changes

* Initial extraction of UltraProvider from octoDNS core

#### Stuff

Nothing
