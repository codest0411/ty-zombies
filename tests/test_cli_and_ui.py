"""Tests for CLI entry points, headless UI rendering, and audio synthesis."""

import os
import subprocess
import sys
import wave

from tyzombie import __version__
from tyzombie.audio import AudioEngine, _synthesize_wav
from tyzombie.cli import main as cli_main
from tyzombie.models import LEVELS, SentenceSiege, Siege, sentence_cfg
from tyzombie.save import DEFAULT_SETTINGS, SaveManager
from tyzombie.ui import (
    BufferCanvas,
    draw_achievements,
    draw_debrief,
    draw_menu,
    draw_options,
    draw_sandbox,
    draw_scores,
    draw_siege,
)


def test_cli_version_and_help(capsys):
    try:
        cli_main(["--version"])
    except SystemExit as exc:
        assert exc.code == 0
    out = capsys.readouterr().out
    assert __version__ in out

    try:
        cli_main(["--help"])
    except SystemExit as exc:
        assert exc.code == 0
    help_out = capsys.readouterr().out
    assert "setup-shell" in help_out
    assert "--record" in help_out


def test_cli_record_flag(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TYZOMBIE_DATA_DIR", str(tmp_path))
    mgr = SaveManager()
    mgr.record_score(2500, "Level 3", "CAMPAIGN", "HARD", wpm=65.0, acc=96.0)
    rc = cli_main(["--record"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "2500" in out
    assert "TY-ZOMBIES RUN CARD" in out


def test_python_m_tyzombie_from_temp_dir(tmp_path):
    env = dict(os.environ)
    src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
    env["PYTHONPATH"] = src_dir + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    proc = subprocess.run(
        [sys.executable, "-m", "tyzombie", "--version"],
        cwd=str(tmp_path),
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert __version__ in proc.stdout


def test_ui_screens_render_without_error(tmp_path):
    sh = Siege(LEVELS[3], "LEVEL 4", DEFAULT_SETTINGS, tier=4, seed=123)
    sh.add("W", 1, word="zombie")
    sh.add("K", 3, word="the big boss")
    sh.type_char("z")

    # Wide telemetry layout (>= 96 cols)
    wide_cv = BufferCanvas(rows=26, cols=104)
    draw_siege(wide_cv, sh)
    wide_text = wide_cv.full_text()
    assert "TELEMETRY" in wide_text
    assert "THE HOSPITAL" in wide_text

    # Compact 80x24 layout
    compact_cv = BufferCanvas(rows=24, cols=80)
    draw_siege(compact_cv, sh, paused=True)
    compact_text = compact_cv.full_text()
    assert "PAUSED" in compact_text
    assert "TELEMETRY" not in compact_text

    # Too-small terminal overlay
    tiny_cv = BufferCanvas(rows=14, cols=50)
    draw_siege(tiny_cv, sh)
    assert "Terminal too small" in tiny_cv.full_text()

    # Other screens
    cv = BufferCanvas(rows=26, cols=90)
    draw_menu(cv, ["CAMPAIGN", "SURVIVAL", "QUIT"], 0, stats={"best_wpm": 60, "total_kills": 50, "best_combo": 12})
    assert "T Y - Z O M B I E S" in cv.full_text()

    cv.clear()
    draw_options(cv, [("DIFFICULTY", "NORMAL"), ("THEME", "OUTBREAK")], 0, "Test description")
    assert "OPTIONS" in cv.full_text()

    cv.clear()
    mgr = SaveManager(data_dir=tmp_path)
    mgr.record_score(900, "Level 2", "CAMPAIGN", "NORMAL", wpm=55, acc=94)
    draw_scores(cv, mgr)
    assert "HIGH SCORES" in cv.full_text()

    cv.clear()
    draw_achievements(cv, ["first_blood"])
    assert "First Blood" in cv.full_text()

    cv.clear()
    draw_debrief(cv, "LEVEL CLEARED", 1, ["Score 1000"], newly_unlocked=["First Blood"])
    assert "LEVEL CLEARED" in cv.full_text()

    cv.clear()
    draw_sandbox(cv, "42", ["hyper_horde"], 0)
    assert "SANDBOX" in cv.full_text()

    # Sentence Siege wrapped cockpit & telemetry
    scv = BufferCanvas(rows=26, cols=104)
    ssh = SentenceSiege(sentence_cfg(1), "SENTENCE", DEFAULT_SETTINGS, tier=1, seed=3)
    sz = ssh.add("S", 1, word="git commit your clean changes before the midnight deployment begins")
    ssh.type_char("g")
    ssh.type_char("i")
    ssh.type_char("t")
    draw_siege(scv, ssh)
    stext = scv.full_text()
    assert "STRK" in stext
    assert "PERF" in stext
    assert sz.word[:20] in stext or "commit" in stext


def test_audio_wav_synthesis_and_engine(tmp_path):
    wav_path = tmp_path / "cue.wav"
    _synthesize_wav(str(wav_path), [(440, 50), (660, 50)])
    assert wav_path.is_file()
    with wave.open(str(wav_path), "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getnframes() > 0

    eng = AudioEngine(enabled=False)
    eng.play("kill")
    eng.close()
