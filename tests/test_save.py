"""Tests for SaveManager persistence, isolation, corruption recovery, and stats."""

import json
import os

from tyzombie.models import LEVELS, Siege
from tyzombie.save import DEFAULT_SETTINGS, SaveManager


def test_save_manager_isolation_and_deepcopy(tmp_path, monkeypatch):
    dir_a = tmp_path / "a"
    dir_b = tmp_path / "b"
    monkeypatch.setenv("TYZOMBIE_DATA_DIR", str(dir_a))

    mgr_a = SaveManager()
    mgr_a.data["settings"]["difficulty"] = 3
    mgr_a.data["settings"]["mutators"].append("hyper_horde")
    mgr_a.save()

    mgr_b = SaveManager(data_dir=dir_b)
    assert mgr_b.data["settings"]["difficulty"] == DEFAULT_SETTINGS["difficulty"]
    assert mgr_b.data["settings"]["mutators"] == []


def test_corrupt_json_recovery(tmp_path):
    save_file = tmp_path / "data.json"
    save_file.write_text("{not valid json!!!", encoding="utf-8")

    mgr = SaveManager(data_dir=tmp_path)
    assert mgr.data["unlocked"] == 1
    assert mgr.data["scores"] == []


def test_leaderboard_sorting_and_top_10(tmp_path):
    mgr = SaveManager(data_dir=tmp_path)
    for i in range(15):
        mgr.record_score(100 * (i + 1), f"Level {i + 1}", "CAMPAIGN", "NORMAL", wpm=40 + i, acc=95.0)

    reloaded = SaveManager(data_dir=tmp_path)
    assert len(reloaded.data["scores"]) == 10
    assert reloaded.data["scores"][0]["score"] == 1500
    assert reloaded.data["scores"][-1]["score"] == 600


def test_achievements_stats_and_active_run(tmp_path):
    mgr = SaveManager(data_dir=tmp_path)
    sh = Siege(LEVELS[0], "LEVEL 1", DEFAULT_SETTINGS, seed=5)
    sh.kills = 12
    sh.correct = 60
    sh.typos = 1
    sh.best_combo = 26
    sh.bombs_used = 10
    sh.bosses_slain = 1
    sh.active_time = 10.0

    newly = mgr.record_level_stats(sh, {"stars": 3, "wpm": 75.0, "acc": 98.5}, mode="CAMPAIGN", wave=5)
    for expected in ("first_blood", "untouchable", "speed_demon", "combo_master", "boss_slayer", "survivor_5", "sharpshooter", "pyromaniac"):
        assert expected in newly

    mgr.save_active_run({"mode": "CAMPAIGN", "stage": 2, "total": 900, "siege": sh.to_dict()})
    reloaded = SaveManager(data_dir=tmp_path)
    assert reloaded.data["active_run"]["stage"] == 2
    reloaded.clear_active_run()
    assert reloaded.data["active_run"] is None

    card = mgr.format_run_card({"mode": "CAMPAIGN", "where": "Level 1", "diff": "NORMAL", "score": 1234, "wpm": 62.0, "acc": 97.5, "date": "2026-11-27"})
    assert "TY-ZOMBIES RUN CARD" in card
    assert "1234" in card


def test_discover_custom_packs(tmp_path):
    packs_dir = tmp_path / "packs"
    packs_dir.mkdir()
    (packs_dir / "scifi.txt").write_text("# comment\nnebula\nstarship\n", encoding="utf-8")

    mgr = SaveManager(data_dir=tmp_path)
    custom = mgr.discover_custom_packs()
    assert "SCIFI" in custom
    assert custom["SCIFI"] == ["nebula", "starship"]

    sh = Siege(LEVELS[0], "LEVEL 1", DEFAULT_SETTINGS, seed=1)
    sh.apply_custom_words("SCIFI", custom["SCIFI"])
    assert sh.pack_name == "SCIFI"
    assert sh.pick_word(6, 8) in ("nebula", "starship")
