"""Unit tests for core game logic, difficulty scaling, mutators, and simulation."""

from tyzombie.models import (
    DIFFS,
    LEVELS,
    SentenceSiege,
    Siege,
    Zombie,
    daily_cfg,
    seed_to_int,
    sentence_cfg,
    survival_cfg,
)
from tyzombie.save import DEFAULT_SETTINGS


def make_settings(**overrides):
    st = dict(DEFAULT_SETTINGS)
    st.update(overrides)
    return st


def test_siege_lock_on_and_kill():
    cfg = LEVELS[0]
    sh = Siege(cfg, "LEVEL 1", make_settings(), seed=42)
    z1 = sh.add("W", 0, word="brain")
    z2 = sh.add("W", 1, word="bone")
    z1.x = 20.0
    z2.x = 30.0

    # First 'b' locks onto closest matching zombie (z1)
    assert sh.type_char("b") == "hit"
    assert sh.target is z1
    for ch in "rai":
        assert sh.type_char(ch) == "hit"
    assert sh.type_char("n") == "kill"
    assert sh.kills == 1
    assert sh.combo == 1
    assert sh.score > 0
    assert z1 not in sh.zombies


def test_typo_breaks_combo_and_jams():
    sh = Siege(LEVELS[0], "LEVEL 1", make_settings(jam=True), seed=1)
    sh.add("W", 0, word="cat")
    sh.type_char("c")
    assert sh.combo == 0
    assert sh.type_char("z") == "miss"
    assert sh.typos == 1
    assert sh.combo == 0
    assert sh.type_char("a") == "jam"


def test_tab_drop_and_hint():
    sh = Siege(LEVELS[0], "LEVEL 1", make_settings(), seed=7)
    z1 = sh.add("W", 0, word="alpha")
    z2 = sh.add("W", 1, word="bravo")
    z1.x = 15.0
    z2.x = 25.0

    sh.hint()
    assert sh.target is z1
    assert sh.hints_left == DIFFS[1][4] - 1

    sh.tab()
    assert sh.target is z2
    sh.drop()
    assert sh.target is None


def test_powers_freeze_bomb_repair():
    sh = Siege(LEVELS[2], "LEVEL 3", make_settings(difficulty=0), seed=10)
    sh.hp = 8
    sh.power(3)  # repair (+2)
    assert sh.hp == 10

    sh.power(1)  # freeze
    assert sh.freeze_left == 5.0
    z = sh.add("W", 0, word="walk")
    x_before = z.x
    sh.update(0.5)
    assert z.x == x_before

    for lane in range(5):
        sh.add("W", lane, word=f"word{lane}")
    boss = sh.add("K", 6, word="the big boss")
    sh.power(2)  # bomb kills up to 4 non-boss zombies
    assert sh.bombs_used == 1
    assert boss in sh.zombies


def test_mutators_and_score_multiplier():
    sh = Siege(
        LEVELS[0],
        "SANDBOX",
        make_settings(),
        seed="muttest",
        mutators=["hyper_horde", "glass_wall", "dense_mist", "pure_typing"],
    )
    assert sh.max_hp == 3
    assert sh.fog_active() is True
    assert sh.charges == {"freeze": 0, "bomb": 0, "repair": 0}
    assert sh.hints_left == 0
    assert sh.score_mult > 1.5


def test_survival_and_daily_deterministic():
    w1 = survival_cfg(1)
    w5 = survival_cfg(5)
    assert w5["quota"] > w1["quota"]
    assert w5["speed"] > w1["speed"]

    d1 = daily_cfg("2026-11-27")
    d2 = daily_cfg("2026-11-27")
    assert d1 == d2
    assert seed_to_int("hello") == seed_to_int("hello")


def test_summary_stars_and_serialization():
    sh = Siege(LEVELS[0], "LEVEL 1", make_settings(), seed=99)
    sh.correct = 100
    sh.typos = 2
    sh.active_time = 20.0
    info = sh.summary()
    assert info["stars"] == 3
    assert info["acc"] > 95

    sh.add("W", 2, word="zombie")
    snap = sh.to_dict()
    sh2 = Siege(LEVELS[0], "LEVEL 1", make_settings(), seed=99)
    sh2.restore_dict(snap)
    assert len(sh2.zombies) == 1
    assert sh2.zombies[0].word == "zombie"
    assert sh2.correct == 100


def test_sentence_siege_word_streak_and_perfect_bonus():
    cfg = sentence_cfg(1)
    sh = SentenceSiege(cfg, "SENTENCE", make_settings(difficulty=1), tier=1, seed=11)
    sh.charges = {"freeze": 0, "bomb": 0, "repair": 0}
    for i in range(3):
        sentence = f"hold fast lane {i}"
        sh.add("S", i, word=sentence)
        res = None
        for ch in sentence:
            res = sh.type_char(ch)
        assert res == "kill"
    assert sh.sentences_cleared == 3
    assert sh.perfect_sentences == 3
    assert sh.best_word_streak >= 12
    assert sum(sh.charges.values()) == 1  # bonus charge on 3rd perfect sentence
    assert sh.score > 500


def test_no_repeated_words_or_sentences_until_exhausted():
    sh = Siege(LEVELS[0], "LEVEL 1", make_settings(), tier=1, seed=101)
    picked = [sh.pick_word(3, 3) for _ in range(8)]
    assert len(set(picked)) == len(picked)

    ssh = SentenceSiege(sentence_cfg(1), "SENTENCE", make_settings(), tier=1, seed=202)
    sentences = [ssh.pick_sentence() for _ in range(4)]
    assert len(set(sentences)) == len(sentences)
