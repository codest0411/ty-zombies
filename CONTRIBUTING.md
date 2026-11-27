# Contributing to ty-zombies

Thank you for your interest in contributing to **ty-zombies**!

## Development Setup

```bash
git clone https://github.com/codest0411/ty-zombies.git
cd ty-zombies
python -m venv .venv
# Activate .venv, then:
pip install -e ".[dev]"
```

## Running Tests

```bash
pytest -v
```

## Guidelines

- Keep gameplay simulation (`src/tyzombie/models.py`) decoupled from `curses` so all mechanics remain unit-testable.
- Use `encoding="utf-8"` for all file I/O.
- Add or update tests in `tests/` for any bug fix or new feature.
- Keep zero external runtime dependencies beyond `windows-curses` on Windows.
