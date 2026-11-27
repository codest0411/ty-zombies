# Security Policy

## Supported Versions

| Version | Supported |
| ------- | --------- |
| 1.0.x   | Yes       |

## Security Design

- **Zero network / zero telemetry**: `ty-zombies` runs 100% locally in your terminal and never sends data over the network.
- **Safe persistence**: Player progress is stored as plain JSON in `~/.tyzombie/data.json` (or `TYZOMBIE_DATA_DIR`). No `pickle` or `eval` is ever used.

## Reporting a Vulnerability

If you discover a security issue, please open a private security advisory on GitHub at:
https://github.com/codest0411/ty-zombies/security/advisories
