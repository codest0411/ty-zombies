"""Responsive terminal UI, box-drawn cockpit, and headless BufferCanvas."""

import curses

from tyzombie.models import FIELD_W, FX0, KINDS, LANES, MUTATORS, POWERS
from tyzombie.save import ACHIEVEMENTS
from tyzombie.themes import (
    BLUE,
    CYAN,
    GREEN,
    MAGENTA,
    RED,
    WHITE,
    YELLOW,
    get_glyphs,
    progress_bar,
)


class CursesCanvas:
    """Thin wrapper over a curses window."""

    def __init__(self, stdscr):
        self.s = stdscr

    def size(self):
        return self.s.getmaxyx()

    def put(self, y, x, text, col=0, bold=False, rev=False, dim=False):
        h, w = self.size()
        if not (0 <= y < h) or x >= w or not text:
            return
        if x < 0:
            text = text[-x:]
            x = 0
        if not text:
            return
        attr = curses.color_pair(col) if col else 0
        if bold:
            attr |= curses.A_BOLD
        if rev:
            attr |= curses.A_REVERSE
        if dim:
            attr |= curses.A_DIM
        try:
            self.s.addstr(y, x, text[: max(0, w - x - 1)], attr)
        except curses.error:
            pass


class BufferCanvas:
    """In-memory canvas used for unit tests and PNG screenshot rendering."""

    def __init__(self, rows=24, cols=80):
        self.rows = rows
        self.cols = cols
        self.ops = []
        self.grid = [[(" ", 0, False, False, False) for _ in range(cols)] for _ in range(rows)]

    def size(self):
        return self.rows, self.cols

    def clear(self):
        self.ops.clear()
        self.grid = [[(" ", 0, False, False, False) for _ in range(self.cols)] for _ in range(self.rows)]

    def put(self, y, x, text, col=0, bold=False, rev=False, dim=False):
        if not (0 <= y < self.rows) or x >= self.cols or not text:
            return
        if x < 0:
            text = text[-x:]
            x = 0
        clipped = text[: max(0, self.cols - x - 1)]
        if not clipped:
            return
        self.ops.append((y, x, clipped, col, bold, rev, dim))
        for i, ch in enumerate(clipped):
            if x + i < self.cols:
                self.grid[y][x + i] = (ch, col, bold, rev, dim)

    def text_lines(self):
        return ["".join(cell[0] for cell in row).rstrip() for row in self.grid]

    def full_text(self):
        return "\n".join(self.text_lines())


def center(cv, y, text, col=0, bold=False, rev=False, dim=False):
    _, w = cv.size()
    cv.put(y, max(0, (w - len(text)) // 2), text, col, bold, rev, dim)


def draw_box(cv, y, x, h, w, title="", col=WHITE, outer=True, glyphs=None):
    """Draw a clean Unicode (or ASCII fallback) box with optional title."""
    g = glyphs or get_glyphs()
    if h < 2 or w < 2:
        return
    tl, tr, bl, br, hh, vv = (
        (g["tl"], g["tr"], g["bl"], g["br"], g["h"], g["v"])
        if outer
        else (g["stl"], g["str"], g["sbl"], g["sbr"], g["sh"], g["sv"])
    )
    top = tl + hh * (w - 2) + tr
    if title and len(title) + 4 <= w:
        t_str = f" {title} "
        pos = max(1, (w - len(t_str)) // 2)
        top = top[:pos] + t_str + top[pos + len(t_str):]
    cv.put(y, x, top, col, bold=outer)
    for row in range(y + 1, y + h - 1):
        cv.put(row, x, vv, col, bold=outer)
        cv.put(row, x + w - 1, vv, col, bold=outer)
    cv.put(y + h - 1, x, bl + hh * (w - 2) + br, col, bold=outer)


def draw_lines(cv, lines):
    h, w = cv.size()
    g = get_glyphs()
    draw_box(cv, 0, 0, h, max(2, w - 1), title="TY-ZOMBIES", col=RED, outer=True, glyphs=g)
    top = max(2, (h - len(lines)) // 2)
    for i, ln in enumerate(lines):
        if top + i >= h - 1:
            break
        text, col, bold = (ln + (0, False))[:3] if isinstance(ln, tuple) else (ln, 0, False)
        center(cv, top + i, text, col, bold)


def banner(cv, y, glyphs=None):
    g = glyphs or get_glyphs()
    w_box = 47
    _, w = cv.size()
    x = max(0, (w - w_box) // 2)
    draw_box(cv, y, x, 3, w_box, col=RED, outer=True, glyphs=g)
    center(cv, y + 1, "T Y - Z O M B I E S   [Z]>>", RED, bold=True)


def draw_menu(cv, items, sel, footer="UP/DOWN move   ENTER select   Q quit", sub=None, stats=None):
    h, w = cv.size()
    g = get_glyphs()
    draw_box(cv, 0, 0, h, max(2, w - 1), col=WHITE, outer=True, glyphs=g)
    banner(cv, 1, g)
    center(cv, 4, sub or "They are coming. Every one of them carries a word.", dim=True)
    if stats:
        stat_line = (
            f"Best WPM: {stats.get('best_wpm', 0)}  {g['bullet']}  "
            f"Kills: {stats.get('total_kills', 0)}  {g['bullet']}  "
            f"Best Combo: x{stats.get('best_combo', 0)}"
        )
        center(cv, 5, stat_line, CYAN, dim=True)
    top = 7
    step = 2 if h >= 26 and len(items) <= 8 else 1
    for i, text in enumerate(items):
        row = top + i * step
        if row >= h - 2:
            break
        if i == sel:
            center(cv, row, f" {g['arrow']} {text} ", YELLOW, bold=True, rev=True)
        else:
            center(cv, row, f"   {text}   ", WHITE)
    center(cv, h - 2, footer, dim=True)


def draw_options(cv, rows, sel, desc):
    h, w = cv.size()
    g = get_glyphs()
    draw_box(cv, 0, 0, h, max(2, w - 1), title="OPTIONS & ACCESSIBILITY", col=CYAN, outer=True, glyphs=g)
    start_y = 3
    step = 2 if h >= 26 else 1
    for i, (name, value) in enumerate(rows):
        y = start_y + i * step
        if y >= h - 4:
            break
        line = f"{name:<18} < {value:^14} >"
        if i == sel:
            center(cv, y, line, YELLOW, bold=True, rev=True)
        else:
            center(cv, y, line, WHITE)
    center(cv, h - 3, desc[: max(10, w - 4)], CYAN, dim=True)
    center(cv, h - 2, "UP/DOWN pick   LEFT/RIGHT change   Q back", dim=True)


def draw_zombie(cv, y, z, sh):
    k = KINDS[z.kind]
    col0 = FX0 + int(z.x)
    danger = z.x < 14
    cv.put(y, col0, k["sprite"], k["col"], bold=True)
    x = col0 + len(k["sprite"]) + 1
    is_target = z is sh.target
    word = z.word
    if sh.fog_active() and not is_target and z.x > 22:
        word = word[0] + "?" * (len(word) - 1)
    base = RED if danger else WHITE
    if z.typed:
        cv.put(y, x, word[: z.typed], GREEN, bold=True)
    if z.typed < len(word):
        nxt = word[z.typed]
        if is_target:
            cv.put(y, x + z.typed, nxt, YELLOW, bold=True, rev=True)
        else:
            cv.put(y, x + z.typed, nxt, base, bold=True)
        if len(word) > z.typed + 1:
            cv.put(y, x + z.typed + 1, word[z.typed + 1:], base)


def draw_siege(cv, sh, paused=False, reduced_flash=False, large_ui=False):
    h, w = cv.size()
    g = get_glyphs()
    if h < LANES + 12 or w < 78:
        draw_box(cv, 0, 0, max(3, h), max(20, w - 1), title="RESIZE TERMINAL", col=RED, outer=True, glyphs=g)
        center(cv, max(1, h // 2 - 1), f"Terminal too small ({w}x{h}).", RED, bold=True)
        center(cv, max(2, h // 2), f"Need at least 78x{LANES + 12} (recommended 96x26).", YELLOW)
        return

    wide = w >= 96
    field_cols = 76 if wide else w - 1

    # Header bar
    hdr = f" TY-ZOMBIES {g['bullet']} {sh.label} {sh.name} ".ljust(w - 1)
    cv.put(0, 0, hdr, RED, bold=True, rev=True)

    total = sh.quota + (1 if sh.cfg["boss"] else 0)
    mins, secs = divmod(int(sh.t), 60)
    cv.put(
        1,
        0,
        f"SCORE {sh.score:<7} KILLS {sh.kills}/{total:<3} COMBO x{sh.combo:<3} "
        f"WPM {sh.wpm():>3.0f}  ACC {sh.accuracy():>3.0f}%  {sh.diff_name}",
        WHITE,
        bold=large_ui,
    )

    frac = max(0.0, sh.hp / max(1, sh.max_hp))
    bcol = GREEN if frac > 0.6 else YELLOW if frac > 0.3 else RED
    bar = progress_bar(frac, min(16, max(6, sh.max_hp)), g)
    cv.put(2, 0, "BARRICADE ", WHITE)
    cv.put(2, 10, f"[{bar}] {max(0, sh.hp)}/{sh.max_hp}", bcol, bold=True)
    cv.put(2, field_cols - 10, f"TIME {mins}:{secs:02d}", WHITE)

    x = 0
    for i, name in enumerate(POWERS, 1):
        n = sh.charges[name]
        label = f"[{i}] {name.upper()} x{n}"
        cv.put(3, x, label, [CYAN, MAGENTA, GREEN][i - 1], bold=n > 0, dim=n == 0)
        x += len(label) + 2
    cv.put(3, x, f"[/] ASSIST x{sh.hints_left}", YELLOW if sh.hints_on else WHITE, dim=not sh.hints_on)

    # Battlefield lanes
    flash = (not reduced_flash) and (sh.t < sh.flash_until)
    for lane in range(LANES):
        y = 4 + lane
        cv.put(y, 0, "@", GREEN, bold=True)
        cv.put(y, 2, f"{g['v']}#{g['v']}", RED if flash else bcol, bold=True, rev=flash)
        cv.put(y, FX0, " ." * (FIELD_W // 2), dim=True)

    for e in sh.effects:
        if e[0] == "tracer":
            _, lane, ex, _ = e
            n = max(0, int(ex) - 1)
            cv.put(4 + lane, 5, "-" * (FX0 - 5 + n), YELLOW, bold=True)
        elif e[0] == "pop":
            _, lane, ex, _ = e
            cv.put(4 + lane, FX0 + max(0, int(ex)), "*BOOM*", RED, bold=True)

    for z in sorted(sh.zombies, key=lambda q: -q.x):
        draw_zombie(cv, 4 + z.lane, z, sh)

    # Wide telemetry sidebar (>= 96 cols)
    if wide:
        sx = 77
        sw = w - sx - 1
        if sw >= 18:
            draw_box(cv, 1, sx, 12, sw, title="TELEMETRY", col=CYAN, outer=False, glyphs=g)
            wpm_bar = progress_bar(min(1.0, sh.wpm() / 90.0), max(4, sw - 10), g)
            acc_bar = progress_bar(sh.accuracy() / 100.0, max(4, sw - 10), g)
            cmb_bar = progress_bar(min(1.0, sh.combo / 20.0), max(4, sw - 10), g)
            cv.put(3, sx + 2, f"WPM {sh.wpm():>3.0f} {wpm_bar}", GREEN)
            cv.put(4, sx + 2, f"ACC {sh.accuracy():>3.0f}%{acc_bar}", CYAN)
            cv.put(5, sx + 2, f"CMB x{sh.combo:<2} {cmb_bar}", YELLOW)
            cv.put(7, sx + 2, f"PACK: {sh.pack_name}"[: sw - 4], WHITE)
            mut_str = ", ".join(sh.mutators) if sh.mutators else "none"
            cv.put(8, sx + 2, f"MUT: {mut_str}"[: sw - 4], MAGENTA if sh.mutators else WHITE, dim=not sh.mutators)
            if sh.combo >= 10:
                cv.put(10, sx + 2, "FEVER +25% PTS!", YELLOW, bold=True)
            else:
                cv.put(10, sx + 2, f"FEVER AT x10 ({sh.combo}/10)"[: sw - 4], dim=True)

    # Lower cockpit
    y = 4 + LANES
    cv.put(y, 0, g["h"] * (w - 1), dim=True)
    cv.put(y + 1, 0, "TARGET ", WHITE, bold=True)
    t = sh.target
    if t is None:
        cv.put(y + 1, 7, "(none)  type the first letter of any word", dim=True)
    else:
        label = KINDS[t.kind]["label"]
        cv.put(y + 1, 7, t.word[: t.typed], GREEN, bold=True)
        cv.put(y + 1, 7 + t.typed, t.word[t.typed:], YELLOW, bold=True)
        cv.put(y + 1, 7 + len(t.word) + 3, f"({label})", dim=True)

    status = []
    if sh.freeze_left > 0:
        status.append(f"FREEZE {sh.freeze_left:0.0f}s")
    if sh.moon_active():
        status.append(f"BLOOD MOON {sh.moon_until - sh.t:0.0f}s")
    if sh.fog_active():
        status.append("FOG" if "dense_mist" in sh.mutators else f"FOG {sh.fog_until - sh.t:0.0f}s")
    if sh.t < sh.jam_until:
        status.append("JAMMED")
    if status:
        cv.put(y + 2, 0, "STATUS ", WHITE, bold=True)
        cv.put(y + 2, 7, "   ".join(status), RED, bold=True)
    if sh.t - sh.msg_t < 4:
        cv.put(y + 3, 0, sh.msg, sh.msg_col, bold=True)
    if sh.t < sh.hint_until:
        cv.put(y + 4, 0, "ASSIST: " + sh.hint_text, YELLOW, bold=True)

    cv.put(
        h - 1,
        0,
        "type words  TAB switch  BKSP drop  1/2/3 powers  / assist  ESC pause",
        dim=True,
    )
    if paused:
        pw = 36
        px = max(0, (w - pw) // 2)
        py = max(1, h // 2 - 3)
        draw_box(cv, py, px, 6, pw, title="PAUSED", col=YELLOW, outer=True, glyphs=g)
        center(cv, py + 2, "ESC / ENTER : Resume", WHITE, bold=True)
        center(cv, py + 3, "M : Mute   Q : Save & Quit", YELLOW)


def draw_scores(cv, save_mgr):
    h, w = cv.size()
    g = get_glyphs()
    draw_box(cv, 0, 0, h, max(2, w - 1), title="HIGH SCORES & LIFETIME STATS", col=YELLOW, outer=True, glyphs=g)
    rows = save_mgr.data["scores"][:10]
    if not rows:
        center(cv, 4, "No scores recorded yet. Survive a siege first!", dim=True)
    else:
        center(cv, 2, "RANK   SCORE    STAGE            MODE      WPM   ACC", CYAN, bold=True)
        for i, e in enumerate(rows, 1):
            line = (
                f"#{i:<2}  {e.get('score', 0):>7}   {str(e.get('where', '-')):<16} "
                f"{str(e.get('mode', '-')):<8}  {e.get('wpm', 0):>4.0f}  {e.get('acc', 0):>4.0f}%"
            )
            center(cv, 3 + i, line, YELLOW if i == 1 else WHITE, bold=(i == 1))
    st = save_mgr.data["stats"]
    sy = min(h - 5, 15)
    cv.put(sy, 2, g["sh"] * max(10, w - 5), dim=True)
    center(
        cv,
        sy + 1,
        f"Runs: {st['runs_played']}  |  Kills: {st['total_kills']}  |  "
        f"Bosses: {st['bosses_slain']}  |  Best WPM: {st['best_wpm']}  |  Best Wave: {st['best_wave']}",
        GREEN,
    )
    center(cv, h - 2, "Press any key to go back", YELLOW)


def draw_achievements(cv, unlocked_ids):
    h, w = cv.size()
    g = get_glyphs()
    draw_box(cv, 0, 0, h, max(2, w - 1), title="ACHIEVEMENTS", col=MAGENTA, outer=True, glyphs=g)
    unlocked_set = set(unlocked_ids)
    center(cv, 2, f"Unlocked: {len(unlocked_set)} / {len(ACHIEVEMENTS)}", CYAN, bold=True)
    for i, (aid, name, desc) in enumerate(ACHIEVEMENTS):
        y = 4 + i
        if y >= h - 3:
            break
        done = aid in unlocked_set
        mark = g["star_on"] if done else g["star_off"]
        line = f"{mark} {name:<20} - {desc}"
        cv.put(y, 4, line[: max(10, w - 8)], GREEN if done else WHITE, bold=done, dim=not done)
    center(cv, h - 2, "Press any key to go back", YELLOW)


def draw_debrief(cv, title, col, lines, newly_unlocked=None):
    h, w = cv.size()
    g = get_glyphs()
    draw_box(cv, 0, 0, h, max(2, w - 1), title="MISSION DEBRIEF", col=col, outer=True, glyphs=g)
    center(cv, 2, title, col, bold=True)
    y = 4
    for ln in lines:
        if y >= h - 4:
            break
        text, c, b = (ln + (WHITE, False))[:3] if isinstance(ln, tuple) else (ln, WHITE, False)
        center(cv, y, text, c, bold=b)
        y += 1
    if newly_unlocked and y < h - 3:
        center(cv, y + 1, f"ACHIEVEMENT UNLOCKED: {', '.join(newly_unlocked)}", MAGENTA, bold=True)
    center(cv, h - 2, "Press any key to continue...", YELLOW)


def draw_sandbox(cv, seed_str, mutators, sel):
    h, w = cv.size()
    g = get_glyphs()
    draw_box(cv, 0, 0, h, max(2, w - 1), title="SANDBOX & MUTATORS", col=GREEN, outer=True, glyphs=g)
    center(cv, 2, "Configure a seeded run & toggle gameplay mutators.", dim=True)
    items = [("SEED", seed_str or "(random)")]
    for mid, (mname, mdesc) in MUTATORS.items():
        items.append((mname.upper(), "ON" if mid in mutators else "OFF"))
    items.append(("START SANDBOX", "GO"))
    for i, (k, v) in enumerate(items):
        y = 4 + i * 2
        if y >= h - 4:
            break
        line = f"{k:<20} [ {v:^12} ]"
        center(cv, y, line, YELLOW if i == sel else WHITE, bold=(i == sel), rev=(i == sel))
    center(cv, h - 2, "UP/DOWN move   ENTER/SPACE toggle or start   Q back", dim=True)


HOW_TO = [
    [
        ("FIELD MANUAL (1/3) - BASICS", RED, True),
        "",
        "Zombies crawl toward your barricade from the right.",
        "Each one carries a word. Type the word to shoot the zombie.",
        "",
        "   [Z] brain          <- a Walker carrying the word 'brain'",
        "",
        "Type the FIRST LETTER of any word to lock on (closest one wins).",
        "Keep typing the rest. A wrong key is a typo and breaks your combo.",
        "10x+ combo activates FEVER (+25% score bonus).",
        "Barricade at 0 = game over.",
        "",
        ("Press any key for the next page", YELLOW, False),
    ],
    [
        ("FIELD MANUAL (2/3) - THE DEAD & EVENTS", RED, True),
        "",
        "[Z] Walker   normal                          [R] Runner  fast, short words",
        "[B] Brute    slow, long words, hits hard     [BOSS] Boss  type a whole sentence",
        "[+] Medic    drops a REPAIR charge           [*] Frost   drops a FREEZE charge",
        "[X] Bomber   drops a BOMB charge",
        "",
        "EVENTS: hordes, blood moons (faster), fog (words hide), supply drops.",
        "MODES: Campaign, Endless Survival, Daily Challenge, and Seeded Sandbox.",
        "Clear a level with 3 stars: no barricade damage and 95% accuracy.",
        "",
        ("Press any key for the next page", YELLOW, False),
    ],
    [
        ("FIELD MANUAL (3/3) - CONTROLS", RED, True),
        "",
        "a-z / space   shoot",
        "TAB           switch target to the next zombie",
        "BACKSPACE     drop your current target",
        "1             FREEZE: everything stops for 5 seconds",
        "2             BOMB: blow up the 4 closest zombies (not the boss)",
        "3             REPAIR: +2 barricade",
        "/             ASSIST: lock on to the closest zombie",
        "M             toggle audio mute",
        "ESC           pause (saves progress if you quit)",
        "",
        ("Press any key to go back", YELLOW, False),
    ],
]

OPTION_INFO = {
    "difficulty": "EASY: 12 HP. NORMAL: 8 HP. HARD: 6 HP. NIGHTMARE: 4 HP + typo jam.",
    "pack": "Word pack carried by zombies: EVERYDAY, HORROR, CODER, or MIXED.",
    "hints": "ON: press / to lock onto the closest zombie (limited per level).",
    "jam": "ON: a typo jams your keyboard for 0.35s. Nightmare always enables this.",
    "sound": "ON: cross-platform synthesized audio cues (winsound / WAV).",
    "theme": "Visual color scheme: OUTBREAK, NEON CYBER, AMBER CRT, or COLORBLIND.",
    "colorblind": "ON: forces high-contrast colorblind-safe palette.",
    "reduced_flash": "ON: disables screen reverse-flash when barricade takes damage.",
    "large_ui": "ON: bold header telemetry for easier readability.",
}
