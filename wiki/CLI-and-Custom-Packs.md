# ⚙️ CLI & Custom Packs

## CLI Flags

```bash
tyzombie                          # Launch interactive menu
tyzombie --mode sentence          # Jump into Sentence Siege
tyzombie --mode daily             # Play today's Daily Challenge
tyzombie --mode sandbox --seed 42 # Seeded Sandbox run
tyzombie --record                 # Print latest / best ASCII run card
tyzombie setup-shell              # Add PowerShell / Bash / Zsh alias
tyzombie --version                # Show installed version
```

## Save Data & Environment Variables

Progress, Top-10 scores, lifetime stats, and 13 achievements are stored in:
- `~/.tyzombie/data.json`

Override the directory with:
```bash
export TYZOMBIE_DATA_DIR=/path/to/data
```

## Custom Word & Sentence Packs

Drop `.txt` files (one word or sentence per line, `#` for comments) into:
- `~/.tyzombie/packs/` (or `$TYZOMBIE_DATA_DIR/packs/`)

`SaveManager.discover_custom_packs()` automatically detects them.
