"""Curses application controller and game loops for ty-zombies."""

import curses
import datetime
import random
import time

from tyzombie.audio import AudioEngine
from tyzombie.models import (
    DIFFS,
    KINDS,
    LEVELS,
    MUTATORS,
    PACK_NAMES,
    SentenceSiege,
    Siege,
    daily_cfg,
    sentence_cfg,
    survival_cfg,
)
from tyzombie.save import ACHIEVEMENTS, SaveManager
from tyzombie.themes import GREEN, RED, THEMES, WHITE, YELLOW, get_theme
from tyzombie.ui import (
    HOW_TO,
    OPTION_INFO,
    CursesCanvas,
    draw_achievements,
    draw_debrief,
    draw_lines,
    draw_menu,
    draw_options,
    draw_sandbox,
    draw_scores,
    draw_siege,
)

CURSES_COLOR_MAP = {
    "green": curses.COLOR_GREEN,
    "yellow": curses.COLOR_YELLOW,
    "red": curses.COLOR_RED,
    "cyan": curses.COLOR_CYAN,
    "blue": curses.COLOR_BLUE,
    "white": curses.COLOR_WHITE,
    "magenta": curses.COLOR_MAGENTA,
}


class App:
    """Main curses application managing menus, game modes, audio, and persistence."""

    def __init__(self, stdscr, data_dir=None, start_mode=None, start_seed=None):
        self.s = stdscr
        self.cv = CursesCanvas(stdscr)
        self.save_mgr = SaveManager(data_dir=data_dir)
        self.data = self.save_mgr.data
        self.audio = AudioEngine(enabled=self.data["settings"].get("sound", True))
        self.start_mode = start_mode
        self.start_seed = start_seed
        self._ach_names = {aid: name for aid, name, _ in ACHIEVEMENTS}

    def apply_theme(self):
        st = self.data["settings"]
        theme = get_theme(st.get("theme", 0), colorblind=st.get("colorblind", False))
        for pair_id, cname in theme["curses_pairs"].items():
            curses.init_pair(pair_id, CURSES_COLOR_MAP.get(cname, curses.COLOR_WHITE), curses.COLOR_BLACK)

    def key(self):
        self.s.nodelay(False)
        while True:
            ch = self.s.getch()
            if ch == curses.KEY_RESIZE:
                continue
            return ch

    def show(self, lines):
        self.s.erase()
        draw_lines(self.cv, lines)
        self.s.refresh()
        self.key()
        curses.flushinp()

    def show_debrief(self, title, col, lines, newly_unlocked=None):
        names = [self._ach_names.get(a, a) for a in (newly_unlocked or [])]
        self.s.erase()
        draw_debrief(self.cv, title, col, lines, newly_unlocked=names)
        self.s.refresh()
        self.key()
        curses.flushinp()

    def menu(self, items, sel=0, **kw):
        while True:
            self.s.erase()
            draw_menu(self.cv, items, sel, **kw)
            self.s.refresh()
            ch = self.s.getch()
            if ch == curses.KEY_RESIZE:
                continue
            if ch in (curses.KEY_UP, ord("w"), ord("k")):
                sel = (sel - 1) % len(items)
            elif ch in (curses.KEY_DOWN, ord("s"), ord("j")):
                sel = (sel + 1) % len(items)
            elif ch in (10, 13, curses.KEY_ENTER, ord(" ")):
                return sel
            elif ch in (27, ord("q"), ord("Q")):
                return -1

    def options(self):
        st = self.data["settings"]
        keys = [
            "difficulty",
            "pack",
            "hints",
            "jam",
            "sound",
            "theme",
            "colorblind",
            "reduced_flash",
            "large_ui",
        ]
        sel = 0
        onoff = lambda v: "ON" if v else "OFF"
        while True:
            rows = [
                ("DIFFICULTY", DIFFS[st["difficulty"]][0]),
                ("WORD PACK", PACK_NAMES[st["pack"]]),
                ("ASSIST HINTS", onoff(st["hints"])),
                ("TYPO JAM", onoff(st["jam"])),
                ("SOUND", onoff(st["sound"])),
                ("THEME", THEMES[st["theme"] % len(THEMES)]["name"]),
                ("COLORBLIND", onoff(st["colorblind"])),
                ("REDUCED FLASH", onoff(st["reduced_flash"])),
                ("LARGE UI", onoff(st["large_ui"])),
            ]
            self.s.erase()
            draw_options(self.cv, rows, sel, OPTION_INFO[keys[sel]])
            self.s.refresh()
            ch = self.s.getch()
            if ch == curses.KEY_RESIZE:
                continue
            k = keys[sel]
            if ch in (curses.KEY_UP, ord("w"), ord("k")):
                sel = (sel - 1) % len(keys)
            elif ch in (curses.KEY_DOWN, ord("s"), ord("j")):
                sel = (sel + 1) % len(keys)
            elif ch in (curses.KEY_RIGHT, curses.KEY_LEFT, 10, 13, ord(" "), ord("d"), ord("a")):
                step = -1 if ch in (curses.KEY_LEFT, ord("a")) else 1
                if k == "difficulty":
                    st[k] = (st[k] + step) % len(DIFFS)
                elif k == "pack":
                    st[k] = (st[k] + step) % len(PACK_NAMES)
                elif k == "theme":
                    st[k] = (st[k] + step) % len(THEMES)
                    self.apply_theme()
                else:
                    st[k] = not st[k]
                    if k == "sound":
                        self.audio.set_enabled(st[k])
                    elif k == "colorblind":
                        self.apply_theme()
            elif ch in (27, ord("q"), ord("Q")):
                self.save_mgr.save()
                return

    def howto(self):
        for page in HOW_TO:
            self.show(page)

    def scores(self):
        self.s.erase()
        draw_scores(self.cv, self.save_mgr)
        self.s.refresh()
        self.key()
        curses.flushinp()

    def achievements(self):
        self.s.erase()
        draw_achievements(self.cv, self.data["achievements"])
        self.s.refresh()
        self.key()
        curses.flushinp()

    def level_select(self):
        n = self.data["unlocked"]
        names = []
        for i in range(min(n, len(LEVELS))):
            stars = self.data["stars"].get(str(i + 1), 0)
            names.append(f"{i + 1}  {LEVELS[i]['name']:<18} " + "*" * stars + "-" * (3 - stars))
        pick = self.menu(names, footer="Pick where to start   Q back", sub="Unlocked levels")
        if pick >= 0:
            self.campaign(pick)

    def _save_run_snapshot(self, sh, mode, idx_or_wave, total, seed=None):
        self.save_mgr.save_active_run({
            "mode": mode,
            "stage": idx_or_wave,
            "total": total,
            "seed": seed,
            "settings": dict(self.data["settings"]),
            "siege": sh.to_dict(),
        })

    def run_level(self, sh, mode="CAMPAIGN", stage=0, total=0, seed=None):
        st = self.data["settings"]
        self.s.nodelay(True)
        paused = False
        last = time.time()
        last_autosave = last
        while True:
            now = time.time()
            dt = min(0.1, now - last)
            last = now
            while True:
                ch = self.s.getch()
                if ch == -1:
                    break
                if ch == curses.KEY_RESIZE:
                    continue
                if paused:
                    if ch in (27, 10, 13):
                        paused = False
                    elif ch in (ord("m"), ord("M")):
                        st["sound"] = not st["sound"]
                        self.audio.set_enabled(st["sound"])
                    elif ch in (ord("q"), ord("Q")):
                        self._save_run_snapshot(sh, mode, stage, total, seed)
                        return "quit"
                    continue
                if ch == 27:
                    paused = True
                elif ch == 9:
                    sh.tab()
                elif ch in (8, 127, curses.KEY_BACKSPACE):
                    sh.drop()
                elif ch in (ord("1"), ord("2"), ord("3")):
                    sh.power(ch - ord("0"))
                elif ch == ord("/"):
                    sh.hint()
                elif 32 <= ch < 127:
                    sh.type_char(chr(ch).lower())

            if not paused:
                sh.update(dt)
                while sh.sound_events:
                    cue = sh.sound_events.pop(0)
                    self.audio.play(cue)
                sh.beep = False
                if now - last_autosave >= 15.0:
                    self._save_run_snapshot(sh, mode, stage, total, seed)
                    last_autosave = now

            result = sh.status()
            if result:
                return result

            self.s.erase()
            draw_siege(
                self.cv,
                sh,
                paused=paused,
                reduced_flash=st.get("reduced_flash", False),
                large_ui=st.get("large_ui", False),
            )
            self.s.refresh()
            time.sleep(0.02)

    def briefing(self, label, cfg, settings=None):
        st = settings or self.data["settings"]
        kinds = "   ".join(f"{KINDS[k]['sprite']} {KINDS[k]['label']}" for k in cfg["kinds"])
        extra = "  + BOSS" if cfg["boss"] else ""
        mode = DIFFS[st["difficulty"]][0]
        self.show([
            (label, RED, True),
            (cfg["name"], YELLOW, True),
            "",
            cfg["blurb"],
            "",
            f"{cfg['quota']} zombies{extra}   mode {mode}   words: {PACK_NAMES[st['pack']]}",
            "",
            kinds,
            "",
            ("Press any key to start. Hands on the keyboard.", WHITE, True),
        ])

    def finish(self, total, where, mode, sh, seed=None):
        self.save_mgr.clear_active_run()
        self.save_mgr.record_score(
            total,
            where=where,
            mode=mode,
            diff_name=sh.diff_name,
            wpm=sh.overall_wpm(),
            acc=sh.accuracy(),
            seed=seed,
        )

    def level_cleared(self, sh, total, mode="CAMPAIGN", wave=0):
        info = sh.summary()
        total += sh.score + info["bonus"]
        newly = self.save_mgr.record_level_stats(sh, info, mode=mode, wave=wave)
        return total, info, newly

    def campaign(self, start=0, total=0, resume_siege=None):
        idx = start
        sh = None
        while idx < len(LEVELS):
            cfg = LEVELS[idx]
            if resume_siege is not None:
                sh = resume_siege
                resume_siege = None
            else:
                self.briefing(f"LEVEL {idx + 1}", cfg)
                sh = Siege(cfg, f"LEVEL {idx + 1}", self.data["settings"], tier=idx + 1)
            result = self.run_level(sh, mode="CAMPAIGN", stage=idx, total=total)
            if result == "quit":
                return
            if result == "dead":
                self.audio.play("gameover")
                total += sh.score
                self.show_debrief(
                    "THE BARRICADE FELL",
                    RED,
                    [
                        f"Killed {sh.kills} zombies on Level {idx + 1}.",
                        f"Speed {sh.overall_wpm():.0f} WPM   Accuracy {sh.accuracy():.0f}%   Best combo x{sh.best_combo}",
                        "",
                        (f"Final Run Score: {total}", YELLOW, True),
                    ],
                )
                self.finish(total, f"Level {idx + 1}", "CAMPAIGN", sh)
                return
            self.audio.play("clear")
            total, info, newly = self.level_cleared(sh, total, mode="CAMPAIGN")
            key = str(idx + 1)
            self.data["stars"][key] = max(self.data["stars"].get(key, 0), info["stars"])
            self.data["unlocked"] = max(self.data["unlocked"], idx + 2)
            self.save_mgr.clear_active_run()
            self.save_mgr.save()
            self.show_debrief(
                "LEVEL CLEARED",
                GREEN,
                [
                    "STARS  " + "*" * info["stars"] + "-" * (3 - info["stars"]),
                    "",
                    f"Speed {info['wpm']:.0f} WPM   Accuracy {info['acc']:.0f}%   Best combo x{sh.best_combo}",
                    f"Barricade {sh.hp}/{sh.max_hp}",
                    f"Level score {sh.score}   Bonus +{info['bonus']}",
                    (f"Run score: {total}", YELLOW, True),
                ],
                newly_unlocked=newly,
            )
            idx += 1

        self.save_mgr.unlock_achievement("apocalypse")
        self.save_mgr.save()
        self.show_debrief(
            "YOU SURVIVED THE APOCALYPSE",
            GREEN,
            [
                (f"Final score: {total}", YELLOW, True),
                "",
                "Try SURVIVAL or DAILY CHALLENGE next!",
            ],
            newly_unlocked=["apocalypse"],
        )
        if sh is not None:
            self.finish(total, "Victory", "CAMPAIGN", sh)

    def survival(self, start_wave=1, total=0, resume_siege=None):
        wave = start_wave
        while True:
            cfg = survival_cfg(wave)
            if resume_siege is not None:
                sh = resume_siege
                resume_siege = None
            else:
                self.briefing("SURVIVAL", cfg)
                sh = Siege(cfg, "SURVIVAL", self.data["settings"], tier=wave + 2)
                sh.name = f"WAVE {wave}"
            result = self.run_level(sh, mode="SURVIVAL", stage=wave, total=total)
            if result == "quit":
                return
            if result == "dead":
                self.audio.play("gameover")
                total += sh.score
                self.show_debrief(
                    "OVERRUN",
                    RED,
                    [
                        f"You reached Wave {wave}.",
                        f"Speed {sh.overall_wpm():.0f} WPM   Accuracy {sh.accuracy():.0f}%",
                        (f"Final Score: {total}", YELLOW, True),
                    ],
                )
                self.finish(total, f"Wave {wave}", "SURVIVAL", sh)
                return
            self.audio.play("clear")
            total, info, newly = self.level_cleared(sh, total, mode="SURVIVAL", wave=wave)
            self.save_mgr.clear_active_run()
            self.show_debrief(
                f"WAVE {wave} SURVIVED",
                GREEN,
                [
                    f"Speed {info['wpm']:.0f} WPM   Accuracy {info['acc']:.0f}%",
                    (f"Score so far: {total}", YELLOW, True),
                ],
                newly_unlocked=newly,
            )
            wave += 1

    def sentence_siege(self, start_wave=1, total=0):
        wave = start_wave
        while True:
            cfg = sentence_cfg(wave)
            self.briefing("SENTENCE SIEGE", cfg)
            sh = SentenceSiege(cfg, "SENTENCE", self.data["settings"], tier=wave)
            sh.name = f"WAVE {wave}"
            result = self.run_level(sh, mode="SENTENCE", stage=wave, total=total)
            if result == "quit":
                return
            if result == "dead":
                self.audio.play("gameover")
                total += sh.score
                self.show_debrief(
                    "SENTENCE SIEGE ENDED",
                    RED,
                    [
                        f"Reached Wave {wave}   Sentences cleared: {sh.sentences_cleared}",
                        f"Peak WPM {sh.peak_wpm:.0f}   Best Word Streak x{sh.best_word_streak}",
                        f"Perfect Sentences: {sh.perfect_sentences}   Accuracy: {sh.accuracy():.0f}%",
                        (f"Final Score: {total}", YELLOW, True),
                    ],
                )
                self.finish(total, f"Sentence W{wave}", "SENTENCE", sh)
                return
            self.audio.play("clear")
            total, info, newly = self.level_cleared(sh, total, mode="SENTENCE", wave=wave)
            self.save_mgr.clear_active_run()
            self.show_debrief(
                f"SENTENCE WAVE {wave} CLEARED",
                GREEN,
                [
                    f"Speed {info['wpm']:.0f} WPM (Peak {sh.peak_wpm:.0f})   Accuracy {info['acc']:.0f}%",
                    f"Word Streak x{sh.best_word_streak}   Perfect Sentences: {sh.perfect_sentences}",
                    (f"Score so far: {total}", YELLOW, True),
                ],
                newly_unlocked=newly,
            )
            wave += 1

    def daily_challenge(self):
        day = datetime.date.today().isoformat()
        cfg, seed, pack_idx, muts = daily_cfg(day)
        st = dict(self.data["settings"])
        st["pack"] = pack_idx
        self.briefing("DAILY CHALLENGE", cfg, settings=st)
        sh = Siege(cfg, "DAILY", st, tier=4, seed=seed, mutators=muts)
        result = self.run_level(sh, mode="DAILY", stage=1, total=0, seed=str(seed))
        if result == "quit":
            return
        if result == "dead":
            self.audio.play("gameover")
            self.show_debrief(
                "DAILY FAILED",
                RED,
                [f"Kills: {sh.kills}   Score: {sh.score}", f"Seed: {seed}"],
            )
            self.finish(sh.score, f"Daily {day}", "DAILY", sh, seed=seed)
            return
        self.audio.play("clear")
        total, info, newly = self.level_cleared(sh, 0, mode="DAILY")
        if day not in self.data["stats"]["daily_completed"]:
            self.data["stats"]["daily_completed"].append(day)
        self.save_mgr.save()
        self.show_debrief(
            "DAILY CHALLENGE COMPLETE",
            GREEN,
            [
                f"Speed {info['wpm']:.0f} WPM   Accuracy {info['acc']:.0f}%",
                (f"Final Score: {total}", YELLOW, True),
                f"Seed: {seed}",
            ],
            newly_unlocked=newly,
        )
        self.finish(total, f"Daily {day}", "DAILY", sh, seed=seed)

    def sandbox(self, seed_override=None):
        seed_str = seed_override or str(random.randint(1000, 99999))
        mutators = list(self.data["settings"].get("mutators", []))
        mut_ids = list(MUTATORS.keys())
        sel = 0
        total_rows = len(mut_ids) + 2
        while True:
            self.s.erase()
            draw_sandbox(self.cv, seed_str, mutators, sel)
            self.s.refresh()
            ch = self.s.getch()
            if ch == curses.KEY_RESIZE:
                continue
            if ch in (curses.KEY_UP, ord("w"), ord("k")):
                sel = (sel - 1) % total_rows
            elif ch in (curses.KEY_DOWN, ord("s"), ord("j")):
                sel = (sel + 1) % total_rows
            elif ch in (27, ord("q"), ord("Q")):
                return
            elif ch in (10, 13, curses.KEY_ENTER, ord(" ")):
                if sel == 0:
                    seed_str = str(random.randint(1000, 99999))
                elif 1 <= sel <= len(mut_ids):
                    mid = mut_ids[sel - 1]
                    if mid in mutators:
                        mutators.remove(mid)
                    else:
                        mutators.append(mid)
                else:
                    cfg = dict(LEVELS[3])
                    cfg["name"] = f"SANDBOX #{seed_str}"
                    cfg["blurb"] = "Custom seeded run with selected mutators."
                    self.briefing("SANDBOX", cfg)
                    sh = Siege(cfg, "SANDBOX", self.data["settings"], tier=4, seed=seed_str, mutators=mutators)
                    res = self.run_level(sh, mode="SANDBOX", stage=1, total=0, seed=seed_str)
                    if res == "dead":
                        self.audio.play("gameover")
                        self.show_debrief("SANDBOX ENDED", RED, [f"Score: {sh.score}", f"Seed: {seed_str}"])
                    elif res == "done":
                        self.audio.play("clear")
                        total, info, newly = self.level_cleared(sh, 0, mode="SANDBOX")
                        self.show_debrief("SANDBOX CLEARED", GREEN, [f"Score: {total}", f"Seed: {seed_str}"], newly)
                    self.save_mgr.clear_active_run()
                    return

    def resume_saved_run(self):
        run = self.data.get("active_run")
        if not run:
            return
        mode = run.get("mode", "CAMPAIGN")
        stage = int(run.get("stage", 0))
        total = int(run.get("total", 0))
        settings = run.get("settings", self.data["settings"])
        if mode == "CAMPAIGN" and 0 <= stage < len(LEVELS):
            cfg = LEVELS[stage]
            sh = Siege(cfg, f"LEVEL {stage + 1}", settings, tier=stage + 1)
            sh.restore_dict(run.get("siege", {}))
            self.campaign(start=stage, total=total, resume_siege=sh)
        elif mode == "SURVIVAL":
            wave = max(1, stage)
            cfg = survival_cfg(wave)
            sh = Siege(cfg, "SURVIVAL", settings, tier=wave + 2)
            sh.name = f"WAVE {wave}"
            sh.restore_dict(run.get("siege", {}))
            self.survival(start_wave=wave, total=total, resume_siege=sh)

    def main(self):
        try:
            curses.curs_set(0)
        except curses.error:
            pass
        self.s.keypad(True)
        if curses.has_colors():
            curses.start_color()
            self.apply_theme()

        try:
            if self.start_mode == "survival":
                self.survival()
                return
            if self.start_mode == "sentence":
                self.sentence_siege()
                return
            if self.start_mode == "daily":
                self.daily_challenge()
                return
            if self.start_mode == "sandbox":
                self.sandbox(seed_override=self.start_seed)
                return
            if self.start_mode == "campaign":
                self.campaign(0)
                return

            sel = 0
            while True:
                has_resume = bool(self.data.get("active_run"))
                items = (["RESUME RUN"] if has_resume else []) + [
                    "CAMPAIGN",
                    "SURVIVAL",
                    "SENTENCE SIEGE",
                    "DAILY CHALLENGE",
                    "SANDBOX & MUTATORS",
                    "LEVEL SELECT",
                    "ACHIEVEMENTS",
                    "HIGH SCORES",
                    "OPTIONS",
                    "HOW TO PLAY",
                    "QUIT",
                ]
                sel = self.menu(items, sel, stats=self.data["stats"])
                if sel == -1:
                    return
                choice = items[sel]
                if choice == "RESUME RUN":
                    self.resume_saved_run()
                elif choice == "CAMPAIGN":
                    self.campaign(0)
                elif choice == "SURVIVAL":
                    self.survival()
                elif choice == "SENTENCE SIEGE":
                    self.sentence_siege()
                elif choice == "DAILY CHALLENGE":
                    self.daily_challenge()
                elif choice == "SANDBOX & MUTATORS":
                    self.sandbox()
                elif choice == "LEVEL SELECT":
                    self.level_select()
                elif choice == "ACHIEVEMENTS":
                    self.achievements()
                elif choice == "HIGH SCORES":
                    self.scores()
                elif choice == "OPTIONS":
                    self.options()
                elif choice == "HOW TO PLAY":
                    self.howto()
                elif choice == "QUIT":
                    return
        finally:
            self.audio.close()
