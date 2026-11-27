# Roadmap

## Shipped Milestones

### v1.0.0 — Foundation & PyPI CLI
- `src/`-layout PyPI package (`ty-zombies` / `tyzombie` CLI & `python -m tyzombie`)
- 8-level Campaign, Endless Survival, Daily Challenge, Seeded Sandbox & Mutators
- Zero-dependency cross-platform synthesized audio (`winsound` / PCM WAV)
- 4 color themes, accessibility toggles, Top-10 leaderboard, and mid-run auto-save/resume

### v2.0.0 — Sentence Siege
- **Sentence Siege** mode (`--mode sentence`) with Everyday, Horror, Coder, and Mixed sentence packs
- Boss Paragraphs, Word Streak multipliers, and `+250` Perfect Sentence bonuses
- Wrapped multi-line `TARGET` cockpit and 3 new achievements (`Sentence Master`, `Flawless Prose`, `Supersonic Typist`)

### v3.0.0 — Non-Repeating Pools & Space Cues
- `seen_words` and `seen_sentences` tracking so words/sentences never repeat until exhausted
- Scrollable Main Menu for compact `80x24` terminals
- Visible `SPACE> ` indicator and `_` highlight in `TARGET` for multi-word typing

### v4.0.0 — Cockpit Redesign, PB Ghost & Custom Packs
- 2-column Main Menu dashboard (`OPERATIONS` + `FIELD STATUS` panel) on wide terminals
- Danger-lane `!` warning markers, live `WAV` progress bar, and Personal-Best WPM Ghost delta (`PB`)
- Custom user word/sentence pack loader (`~/.tyzombie/packs/*.txt`)

---

## Planned Milestones

### v5.0.0 — Replay System, Pack Browser & New Hazards
- **Interactive Custom Pack Selector:** Browse and toggle `~/.tyzombie/packs/*.txt` directly inside Options without editing config files
- **Keystroke Replay & Ghost Racing:** Record timestamped run timelines (`~/.tyzombie/replays/`) and race your personal-best ghost in real time
- **New Zombie Archetypes & Hazards:**
  - *Shielded `[#]`*: Requires two quick words or a power-up to crack
  - *Splitter `[%]`*: Splits into two fast mini-words when defeated unless killed during Combo Fever
  - *EMP Storm Event*: Temporarily scrambles lane positions and rewards rapid target switching
- **Exportable HTML/SVG Run Reports:** Generate shareable visual match summaries via `tyzombie --export`

### v6.0.0 — Multiplayer Co-Op & Versus Arena
- **Local Split-Barricade Co-Op:** Two-player local/LAN defense sharing a combined barricade with lane handoffs
- **LAN / Socket Versus Mode:** Send defeated words/sentences as bonus zombies into your opponent's lanes
- **Deterministic Tournament Brackets:** Seeded best-of-3 sprint rulesets with standardized mutator presets

### v7.0.0 — Adaptive AI Director & Plugin Ecosystem
- **Adaptive Weakness Trainer:** Tracks per-character and bigram typo rates to dynamically bias spawned words toward keys you miss most
- **Campaign Act II ("Quarantine Zero"):** 8 new stages with multi-phase Boss encounters, environmental hazards, and branching route choices
- **Community Pack Registry & Validator:** `tyzombie pack validate <file>` CLI tool to lint, balance-check, and package community word/sentence packs

### v8.0.0 — Room-Based Asymmetric Co-Op ("Defender vs. Director")
- **Room Code Lobbies:** Host or join a match with a short room code (`tyzombie --host` / `tyzombie --join <CODE>`) over LAN or lightweight relay
- **Asymmetric Stress Rounds:**
  - **Player 1 (Defender):** Types words and sentences to hold the barricade and build combos
  - **Player 2 (Director):** Spends regenerating Stress Energy to spawn fast Runners, Brutes, Fog, Blood Moons, or long sentences to pressure the Defender
- **Role-Swap Rounds & Scoring:** Players swap roles every round; whoever survives longer or scores higher as Defender wins the match

