# Changelog

All notable changes to **ty-zombies** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-11-27

### Added
- **Sentence Siege Mode (`SENTENCE SIEGE` in menu / `tyzombie --mode sentence`)**: Full-sentence typing survival mode with Everyday, Horror, Coder, and Mixed sentence packs, escalating waves, and Boss Paragraphs.
- **Word Streak & Perfect Sentence Bonuses**: Consecutive typo-free words build a Word Streak multiplier, and 0-typo sentences award `+250` bonus points plus a free power-up charge every 3 perfect sentences.
- **Wrapped Active Sentence Cockpit**: Compact `[S]` lane previews paired with a multi-line character-highlighted `TARGET` console and live `STRK` / `PERF` telemetry.
- **New Achievements**: `Sentence Master`, `Flawless Prose`, and `Supersonic Typist` (90+ WPM).

## [1.0.0] - 2026-11-27

### Added
- Packaged as a `src/`-layout PyPI CLI application (`ty-zombies` / `tyzombie` command and `python -m tyzombie`).
- **New Game Modes**: Deterministic Daily Challenge (`--mode daily`) and Seeded Sandbox with 4 gameplay mutators (`Hyper Horde`, `Glass Barricade`, `Dense Mist`, `Pure Typing`).
- **Combo Fever**: 10x+ typing combos grant a +25% score bonus.
- **Persistent Systems** (`~/.tyzombie/data.json`, overridable via `TYZOMBIE_DATA_DIR`): Top-10 leaderboard, lifetime stats, 10 unlockable achievements, mid-run auto-save & resume, and shareable ASCII/Markdown run cards (`tyzombie --record`).
- **Cross-Platform Synthesized Audio**: Non-blocking `winsound.Beep` on Windows and synthesized PCM WAV cues via `afplay`/`paplay`/`aplay` on macOS/Linux.
- **Terminal UI/UX Overhaul**: Unicode box-drawn cockpit with automatic ASCII fallback, wide 2-column telemetry layout (`>=96` cols), 4 color themes (`OUTBREAK`, `NEON CYBER`, `AMBER CRT`, `COLORBLIND`), accessibility toggles (`Colorblind Mode`, `Reduced Flash`, `Large UI`), `KEY_RESIZE` handling, and Mission Debrief screens.
- **CLI & Tooling**: `--version`, `--mode`, `--seed`, `--record`, `setup-shell` subcommand, full `pytest` suite, and GitHub Actions CI/CD.
