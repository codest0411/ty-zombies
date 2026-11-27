"""Persistent save management, stats, achievements, mid-run resume, and run cards."""

from __future__ import annotations

import copy
import datetime
import json
import os
from typing import Any

DATA_DIR_ENV = "TYZOMBIE_DATA_DIR"

DEFAULT_SETTINGS = {
    "difficulty": 1,       # 0=EASY, 1=NORMAL, 2=HARD, 3=NIGHTMARE
    "pack": 0,             # 0=EVERYDAY, 1=HORROR, 2=CODER, 3=MIXED
    "hints": True,
    "jam": False,
    "sound": True,
    "theme": 0,            # 0=OUTBREAK, 1=NEON, 2=AMBER, 3=COLORBLIND
    "colorblind": False,
    "reduced_flash": False,
    "large_ui": False,
    "mutators": [],        # list of active mutator IDs
}

DEFAULT_STATS = {
    "runs_played": 0,
    "total_kills": 0,
    "total_chars": 0,
    "total_typos": 0,
    "bosses_slain": 0,
    "bombs_used": 0,
    "levels_cleared": 0,
    "best_combo": 0,
    "best_wpm": 0,
    "best_wave": 0,
    "daily_completed": [],
}

ACHIEVEMENTS = [
    ("first_blood", "First Blood", "Kill your first zombie."),
    ("untouchable", "Untouchable", "Earn 3 stars on any campaign level."),
    ("speed_demon", "Speed Demon", "Reach 70+ WPM in a completed level or wave."),
    ("combo_master", "Combo Master", "Reach a 25x typing combo."),
    ("boss_slayer", "Boss Slayer", "Defeat a sentence-carrying Boss."),
    ("survivor_5", "Wave Rider", "Survive to Wave 5 in Survival mode."),
    ("apocalypse", "Apocalypse Survivor", "Complete all 8 Campaign levels."),
    ("sharpshooter", "Sharpshooter", "Finish a level with 98%+ accuracy."),
    ("pyromaniac", "Pyromaniac", "Detonate 10 Bomb power-ups."),
    ("daily_contender", "Daily Contender", "Complete a Daily Challenge run."),
]

DEFAULT_DATA: dict[str, Any] = {
    "version": 2,
    "settings": DEFAULT_SETTINGS,
    "unlocked": 1,
    "stars": {},
    "scores": [],
    "best_wpm": 0,
    "stats": DEFAULT_STATS,
    "achievements": [],
    "active_run": None,
    "best_run_card": None,
    "last_run_card": None,
}


def resolve_data_dir(data_dir=None):
    """Return the directory for save data, honoring TYZOMBIE_DATA_DIR."""
    if data_dir:
        return os.path.abspath(str(data_dir))
    env_dir = os.environ.get(DATA_DIR_ENV, "").strip()
    if env_dir:
        return os.path.abspath(os.path.expanduser(env_dir))
    return os.path.join(os.path.expanduser("~"), ".tyzombie")


class SaveManager:
    """Manages loading, migrating, and persisting player progress safely."""

    def __init__(self, data_dir=None):
        self.data_dir = resolve_data_dir(data_dir)
        self.path = os.path.join(self.data_dir, "data.json")
        self.data = self.load()

    @staticmethod
    def default_data():
        return copy.deepcopy(DEFAULT_DATA)

    def load(self):
        """Load JSON save data, recovering cleanly from missing or corrupt files."""
        d = self.default_data()
        if not os.path.isfile(self.path):
            return d
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if not isinstance(raw, dict):
                return d
            if isinstance(raw.get("settings"), dict):
                for k, v in raw["settings"].items():
                    if k in d["settings"]:
                        d["settings"][k] = copy.deepcopy(v)
            d["unlocked"] = max(1, int(raw.get("unlocked", 1)))
            if isinstance(raw.get("stars"), dict):
                d["stars"] = {str(k): int(v) for k, v in raw["stars"].items()}
            if isinstance(raw.get("scores"), list):
                valid_scores = [e for e in raw["scores"] if isinstance(e, dict) and "score" in e]
                d["scores"] = sorted(valid_scores, key=lambda e: -int(e.get("score", 0)))[:10]
            d["best_wpm"] = max(0, round(float(raw.get("best_wpm", 0))))
            if isinstance(raw.get("stats"), dict):
                for k in d["stats"]:
                    if k in raw["stats"]:
                        d["stats"][k] = copy.deepcopy(raw["stats"][k])
            d["stats"]["best_wpm"] = max(d["stats"]["best_wpm"], d["best_wpm"])
            if isinstance(raw.get("achievements"), list):
                known = {a[0] for a in ACHIEVEMENTS}
                d["achievements"] = [a for a in raw["achievements"] if a in known]
            if isinstance(raw.get("active_run"), dict):
                d["active_run"] = copy.deepcopy(raw["active_run"])
            if isinstance(raw.get("best_run_card"), dict):
                d["best_run_card"] = copy.deepcopy(raw["best_run_card"])
            if isinstance(raw.get("last_run_card"), dict):
                d["last_run_card"] = copy.deepcopy(raw["last_run_card"])
        except Exception:
            return self.default_data()
        return d

    def save(self):
        """Persist current save data to disk using UTF-8."""
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            tmp_path = self.path + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
            os.replace(tmp_path, self.path)
            return True
        except Exception:
            return False

    def unlock_achievement(self, ach_id):
        """Unlock an achievement ID if valid and not already unlocked."""
        known = {a[0] for a in ACHIEVEMENTS}
        if ach_id in known and ach_id not in self.data["achievements"]:
            self.data["achievements"].append(ach_id)
            return True
        return False

    def record_score(self, score, where, mode, diff_name, wpm=0.0, acc=100.0, seed=None):
        """Record a run on the Top-10 leaderboard and update run cards."""
        entry = {
            "score": int(score),
            "where": str(where),
            "mode": str(mode),
            "diff": str(diff_name),
            "wpm": round(float(wpm), 1),
            "acc": round(float(acc), 1),
            "date": datetime.date.today().isoformat(),
        }
        if seed is not None:
            entry["seed"] = str(seed)
        self.data["last_run_card"] = copy.deepcopy(entry)
        best = self.data.get("best_run_card")
        if best is None or entry["score"] >= int(best.get("score", 0)):
            self.data["best_run_card"] = copy.deepcopy(entry)

        if score > 0:
            self.data["scores"].append(entry)
            self.data["scores"] = sorted(
                self.data["scores"],
                key=lambda e: (-int(e.get("score", 0)), -float(e.get("wpm", 0))),
            )[:10]
        self.data["stats"]["runs_played"] += 1
        self.save()
        return entry

    def record_level_stats(self, siege, info, mode="CAMPAIGN", wave=0):
        """Update lifetime stats and unlock any earned achievements."""
        st = self.data["stats"]
        st["total_kills"] += siege.kills
        st["total_chars"] += siege.correct
        st["total_typos"] += siege.typos
        st["bosses_slain"] += siege.bosses_slain
        st["bombs_used"] += siege.bombs_used
        st["levels_cleared"] += 1
        st["best_combo"] = max(st["best_combo"], siege.best_combo)
        rounded_wpm = int(round(info["wpm"]))
        st["best_wpm"] = max(st["best_wpm"], rounded_wpm)
        self.data["best_wpm"] = max(self.data["best_wpm"], rounded_wpm)
        if wave > 0:
            st["best_wave"] = max(st["best_wave"], wave)

        newly_unlocked = []
        checks = [
            ("first_blood", st["total_kills"] >= 1),
            ("untouchable", info.get("stars", 0) == 3),
            ("speed_demon", info.get("wpm", 0) >= 70),
            ("combo_master", siege.best_combo >= 25),
            ("boss_slayer", st["bosses_slain"] >= 1),
            ("survivor_5", wave >= 5),
            ("sharpshooter", info.get("acc", 0) >= 98 and siege.kills > 0),
            ("pyromaniac", st["bombs_used"] >= 10),
            ("daily_contender", mode == "DAILY"),
        ]
        for ach_id, cond in checks:
            if cond and self.unlock_achievement(ach_id):
                newly_unlocked.append(ach_id)
        self.save()
        return newly_unlocked

    def save_active_run(self, run_state):
        """Persist mid-run state for later resume."""
        self.data["active_run"] = copy.deepcopy(run_state)
        self.save()

    def clear_active_run(self):
        """Clear saved mid-run state."""
        self.data["active_run"] = None
        self.save()

    @staticmethod
    def format_run_card(card):
        """Format a shareable ASCII/Markdown run card."""
        if not card:
            return "No runs recorded yet. Play a game of tyzombie first!"
        seed_line = f"Seed : {card['seed']}\n" if card.get("seed") else ""
        return (
            "```text\n"
            "+--------------------------------------+\n"
            "|        TY-ZOMBIES RUN CARD           |\n"
            "+--------------------------------------+\n"
            f"| Mode  : {card.get('mode', 'CAMPAIGN'):<28} |\n"
            f"| Stage : {card.get('where', '-'):<28} |\n"
            f"| Diff  : {card.get('diff', 'NORMAL'):<28} |\n"
            f"| Score : {card.get('score', 0):<28} |\n"
            f"| Speed : {card.get('wpm', 0):.1f} WPM   Acc: {card.get('acc', 0):.1f}%{' ' * 7}|\n"
            f"| Date  : {card.get('date', ''):<28} |\n"
            "+--------------------------------------+\n"
            f"{seed_line}"
            "```"
        )
