"""Core game data, levels, mutators, zombie entities, and Siege simulation."""

import datetime
import hashlib
import random

from tyzombie.themes import BLUE, CYAN, GREEN, MAGENTA, RED, WHITE, YELLOW

LANES = 8
FIELD_W = 66          # zombies spawn at x = FIELD_W and die/hit when x <= 0
FX0 = 8               # screen column where x = 0 is drawn
MAX_ON_SCREEN = 10
VIS_W = 70            # columns of the field that fit on an 80-column screen
POWERS = ["freeze", "bomb", "repair"]

KINDS = {
    "W": {"label": "Walker", "speed": 1.0,  "dmg": 1, "mult": 1.0,  "sprite": "[Z]",    "col": GREEN},
    "R": {"label": "Runner", "speed": 1.9,  "dmg": 1, "mult": 1.5,  "sprite": "[R]",    "col": YELLOW},
    "B": {"label": "Brute",  "speed": 0.7,  "dmg": 2, "mult": 2.0,  "sprite": "[B]",    "col": RED},
    "M": {"label": "Medic",  "speed": 1.0,  "dmg": 1, "mult": 1.5,  "sprite": "[+]",    "col": CYAN},
    "F": {"label": "Frost",  "speed": 1.2,  "dmg": 1, "mult": 1.5,  "sprite": "[*]",    "col": BLUE},
    "X": {"label": "Bomber",   "speed": 1.0,  "dmg": 1, "mult": 1.5,  "sprite": "[X]",    "col": MAGENTA},
    "S": {"label": "Sentence", "speed": 0.38, "dmg": 2, "mult": 3.0,  "sprite": "[S]",    "col": CYAN},
    "K": {"label": "BOSS",     "speed": 0.45, "dmg": 6, "mult": 10.0, "sprite": "[BOSS]", "col": RED},
}

KIND_NOTE = {
    "W": "normal",
    "R": "fast, short words",
    "B": "slow, long words, hits hard",
    "M": "drops a REPAIR charge",
    "F": "drops a FREEZE charge",
    "X": "drops a BOMB charge",
    "S": "carries a full sentence",
    "K": "type a whole sentence",
}
DROPS = {"M": "repair", "F": "freeze", "X": "bomb"}

# (name, speed_mult, spawn_delay_mult, barricade_hp, assists_per_level, start_charges, forced_jam)
DIFFS = [
    ("EASY",      0.80, 1.25, 12, 5, (1, 1, 1), False),
    ("NORMAL",    1.00, 1.00,  8, 3, (1, 1, 0), False),
    ("HARD",      1.20, 0.85,  6, 2, (1, 0, 0), False),
    ("NIGHTMARE", 1.40, 0.70,  4, 1, (0, 0, 0), True),
]

MUTATORS = {
    "hyper_horde": ("Hyper Horde", "Zombies move 25% faster; +25% score bonus."),
    "glass_wall":  ("Glass Barricade", "Barricade starts at 3 HP; +35% score bonus."),
    "dense_mist":  ("Dense Mist", "Permanent fog hides distant words."),
    "pure_typing": ("Pure Typing", "No power-up charges or assists; +30% score bonus."),
}

PACK_NAMES = ["EVERYDAY", "HORROR", "CODER", "MIXED"]

WORDS = {
    "EVERYDAY": """sun cat run map pen cup hat bus car key box dog egg ice jar
        door tree road book lamp city wind rain fish cake bird farm gold hand jump kite lake moon nest play ship song
        house water green plant river chair bread light phone cloud earth fruit glass happy money music paper table
        window garden market pocket bridge silver orange yellow coffee school family button candle dinner flower
        kitchen morning country picture station weather balance holiday blanket journey monster teacher mailbox
        mountain computer vacation sandwich umbrella birthday question hospital elephant treasure festival lantern
        breakfast adventure chocolate afternoon invention telephone president wonderful fireworks community
        restaurant photograph television basketball understand playground strawberry adventurer""",
    "HORROR": """boo rot bat bog fog axe
        dark moon fear bone grim crow tomb howl rage claw dead evil mist rust
        ghost blood skull grave witch curse ghoul night spook scare cabin fangs gloom
        zombie coffin spirit cursed shadow horror gloomy undead sinister
        phantom vampire haunted ghastly cadaver grisly shiver cobweb whisper
        werewolf skeleton creeping darkness terrible haunting scarecrow poltergeist
        nightmare graveyard moonlight tombstone chainsaw trembling bloodbath
        apocalypse undertaker necromancer abandoned screaming slaughterhouse""",
    "CODER": """for int var def map set key git tab bit tcp api
        loop list dict bool null void code byte file push pull bash node tree hash
        array class print float stack queue merge debug build shell regex token fetch
        python string import return module commit branch syntax kernel socket buffer script server thread
        boolean integer pointer compile runtime network package inherit iterate lambda closure payload
        function variable database iterator frontend backend terminal compiler template protocol
        algorithm recursion interface framework developer exception constants parameter
        javascript repository dictionary middleware singleton encryption concurrency""",
}
WORDS["MIXED"] = " ".join(WORDS[k] for k in ("EVERYDAY", "HORROR", "CODER"))

BUCKETS = {}
for _pack, _text in WORDS.items():
    _b = {}
    for _w in sorted(set(_text.split())):
        _b.setdefault(len(_w), []).append(_w)
    BUCKETS[_pack] = _b

LEVELS = [
    dict(name="THE QUIET STREET",  quota=12, speed=2.3, spawn=3.3, lens=(3, 4),  kinds={"W": 1},
         events=[], boss=False, blurb="Slow ones only. Find your rhythm."),
    dict(name="THE PARK",          quota=16, speed=2.8, spawn=2.8, lens=(3, 5),  kinds={"W": 3, "R": 1},
         events=[], boss=False, blurb="Runners are short and fast."),
    dict(name="THE SUPERMARKET",   quota=20, speed=3.3, spawn=2.4, lens=(4, 6),  kinds={"W": 4, "R": 2, "M": 1},
         events=["supply"], boss=False, blurb="Medics carry repair kits. Shoot them."),
    dict(name="THE HOSPITAL",      quota=24, speed=3.7, spawn=2.1, lens=(4, 7),  kinds={"W": 4, "R": 2, "B": 1, "M": 1, "F": 1},
         events=["horde", "supply"], boss=True, blurb="Brutes, hordes, and a boss with a sentence."),
    dict(name="THE SUBWAY",        quota=32, speed=4.4, spawn=1.7, lens=(5, 8),  kinds={"W": 4, "R": 3, "B": 2, "M": 1, "F": 1, "X": 1},
         events=["horde", "fog", "supply"], boss=False, blurb="Darkness falls. Words vanish into fog."),
    dict(name="THE CITY",          quota=38, speed=4.9, spawn=1.5, lens=(5, 9),  kinds={"W": 4, "R": 3, "B": 2, "M": 1, "F": 1, "X": 1},
         events=["horde", "fog", "moon", "supply"], boss=True, blurb="A blood moon rises. Everything speeds up."),
    dict(name="THE MILITARY BASE", quota=44, speed=5.4, spawn=1.3, lens=(6, 10), kinds={"W": 4, "R": 3, "B": 2, "M": 1, "F": 1, "X": 1},
         events=["horde", "fog", "moon", "supply"], boss=False, blurb="They have been waiting for you."),
    dict(name="ZOMBIE APOCALYPSE", quota=50, speed=5.9, spawn=1.15, lens=(7, 11), kinds={"W": 4, "R": 3, "B": 2, "M": 1, "F": 1, "X": 1},
         events=["horde", "fog", "moon", "supply"], boss=True, blurb="The last stand. Good luck."),
]


def survival_cfg(n):
    """Return configuration dict for endless Survival wave n."""
    return dict(
        name=f"WAVE {n}",
        quota=min(60, 14 + 4 * n),
        speed=min(9.0, 3.4 + 0.45 * n),
        spawn=max(0.8, 2.6 - 0.15 * n),
        lens=(4, min(11, 6 + n // 2)),
        kinds={"W": 4, "R": 3, "B": 2, "M": 1, "F": 1, "X": 1},
        events=["horde", "fog", "moon", "supply"],
        boss=(n % 3 == 0),
        blurb="Endless. Survive as long as you can.",
    )


def daily_cfg(date_str=None):
    """Return deterministic Daily Challenge config and seed for YYYY-MM-DD."""
    day = date_str or datetime.date.today().isoformat()
    digest = hashlib.sha256(f"tyzombie-daily-{day}".encode("utf-8")).hexdigest()
    seed = int(digest[:8], 16)
    rng = random.Random(seed)
    pack_idx = rng.randrange(len(PACK_NAMES))
    mutator = rng.choice(["hyper_horde", "dense_mist", None])
    cfg = dict(
        name=f"DAILY {day}",
        quota=28,
        speed=4.2,
        spawn=1.65,
        lens=(4, 9),
        kinds={"W": 4, "R": 3, "B": 2, "M": 1, "F": 1, "X": 1},
        events=["horde", "fog", "moon", "supply"],
        boss=True,
        blurb=f"Seeded Daily Challenge ({PACK_NAMES[pack_idx]} pack).",
    )
    return cfg, seed, pack_idx, ([mutator] if mutator else [])


def seed_to_int(seed_text):
    """Convert any user-supplied seed string into a deterministic integer."""
    if seed_text is None:
        return None
    s = str(seed_text).strip()
    if s.isdigit():
        return int(s)
    return int(hashlib.sha256(s.encode("utf-8")).hexdigest()[:8], 16)


class Zombie:
    """A single approaching zombie carrying a target word."""

    def __init__(self, kind, word, lane, speed, x=None, typed=0):
        self.kind = kind
        self.word = word
        self.lane = lane
        self.speed = speed
        self.x = float(FIELD_W) if x is None else float(x)
        self.typed = typed

    @property
    def width(self):
        return len(KINDS[self.kind]["sprite"]) + 1 + len(self.word)

    def to_dict(self):
        return {
            "kind": self.kind,
            "word": self.word,
            "lane": self.lane,
            "speed": self.speed,
            "x": self.x,
            "typed": self.typed,
        }

    @classmethod
    def from_dict(cls, raw):
        return cls(
            kind=raw["kind"],
            word=raw["word"],
            lane=int(raw["lane"]),
            speed=float(raw["speed"]),
            x=float(raw["x"]),
            typed=int(raw.get("typed", 0)),
        )


class Siege:
    """Core real-time typing siege simulation (no curses dependency)."""

    def __init__(self, cfg, label, settings, tier=1, seed=None, mutators=None):
        self.cfg = cfg
        self.label = label
        self.tier = tier
        self.seed = seed
        self.name = cfg["name"]
        self.quota = cfg["quota"]
        self.rng = random.Random(seed_to_int(seed))

        (
            self.diff_name,
            self.dspeed,
            self.dspawn,
            self.max_hp,
            hints,
            charges,
            forced_jam,
        ) = DIFFS[settings.get("difficulty", 1)]

        self.mutators = list(mutators if mutators is not None else settings.get("mutators", []))
        if "hyper_horde" in self.mutators:
            self.dspeed *= 1.25
        if "glass_wall" in self.mutators:
            self.max_hp = min(self.max_hp, 3)

        self.score_mult = 1.0
        if "hyper_horde" in self.mutators:
            self.score_mult += 0.25
        if "glass_wall" in self.mutators:
            self.score_mult += 0.35
        if "pure_typing" in self.mutators:
            self.score_mult += 0.30

        self.hints_on = bool(settings.get("hints", True)) and "pure_typing" not in self.mutators
        self.hints_left = 0 if "pure_typing" in self.mutators else hints
        self.jam_on = bool(settings.get("jam", False)) or forced_jam
        pack_idx = settings.get("pack", 0) % len(PACK_NAMES)
        self.pack_name = PACK_NAMES[pack_idx]
        self.bucket = BUCKETS[self.pack_name]

        if "pure_typing" in self.mutators:
            self.charges = {p: 0 for p in POWERS}
        else:
            self.charges = dict(zip(POWERS, charges))

        self.hp = self.max_hp
        self.t = 0.0
        self.zombies = []
        self.seen_words = set()
        self.effects = []
        self.stamps = []
        self.target = None
        self.spawned = 0
        self.kills = 0
        self.bosses_slain = 0
        self.bombs_used = 0
        self.score = 0
        self.combo = 0
        self.best_combo = 0
        self.correct = 0
        self.typos = 0
        self.active_time = 0.0
        self._last_char = -99.0
        self.damage_taken = 0
        self.boss_spawned = False
        self.next_spawn = 1.2
        self.next_event = 18.0 + self.rng.uniform(0, 6)
        self.freeze_left = 0.0
        self.moon_until = 0.0
        self.fog_until = 0.0
        self.flash_until = 0.0
        self.jam_until = 0.0
        self.msg, self.msg_col, self.msg_t = "", WHITE, -99.0
        self.hint_until, self.hint_text = -99.0, ""
        self.beep = False
        self.sound_events = []

    def _emit_sound(self, cue):
        self.sound_events.append(cue)
        if cue in ("bomb", "damage", "boss"):
            self.beep = True

    def say(self, text, col=WHITE):
        self.msg, self.msg_col, self.msg_t = text, col, self.t

    def fog_active(self):
        return "dense_mist" in self.mutators or self.t < self.fog_until

    def moon_active(self):
        return self.t < self.moon_until

    def closest(self):
        return min(self.zombies, key=lambda z: z.x) if self.zombies else None

    def accuracy(self):
        total = self.correct + self.typos
        return 100.0 if total == 0 else 100.0 * self.correct / total

    def wpm(self):
        """Live speed over the last 15 seconds."""
        window = min(15.0, max(self.t, 4.0))
        recent = sum(1 for s in self.stamps if s > self.t - window)
        return recent / 5.0 / (window / 60.0)

    def overall_wpm(self):
        return self.correct / 5.0 / (max(self.active_time, 5.0) / 60.0)

    def pick_word(self, lo, hi):
        lens = [n for n in sorted(self.bucket) if lo <= n <= hi]
        if not lens:
            lens = [min(self.bucket, key=lambda n: abs(n - lo))]
        pool = [w for n in lens for w in self.bucket[n]]
        used = {z.word for z in self.zombies} | self.seen_words
        firsts = {z.word[0] for z in self.zombies}
        fresh = [w for w in pool if w not in used and w[0] not in firsts]
        unseen = [w for w in pool if w not in used]
        if not fresh and not unseen:
            # All words in this length range were used; reset history except active zombies
            self.seen_words.clear()
            used = {z.word for z in self.zombies}
            fresh = [w for w in pool if w not in used and w[0] not in firsts]
            unseen = [w for w in pool if w not in used]
        choice_pool = fresh or unseen or [w for w in pool if w not in {z.word for z in self.zombies}] or pool
        picked = self.rng.choice(choice_pool)
        self.seen_words.add(picked)
        return picked

    def boss_phrase(self):
        n = 3 + (self.tier >= 5) + (self.tier >= 7)
        pool = [w for k in range(3, 7) for w in self.bucket.get(k, [])]
        return " ".join(self.rng.sample(pool, n))

    def lane_free(self, lane):
        edge = max((z.x + z.width for z in self.zombies if z.lane == lane), default=0)
        return edge <= FIELD_W - 2

    def add(self, kind, lane, word=None):
        lo, hi = self.cfg["lens"]
        if kind == "R":
            lo, hi = 3, max(3, min(hi, 5))
        elif kind == "B":
            lo = max(lo, 7)
            hi = max(hi, lo + 1)
        if word is None:
            word = self.boss_phrase() if kind == "K" else self.pick_word(lo, hi)
        z = Zombie(kind, word, lane, self.cfg["speed"] * KINDS[kind]["speed"] * self.dspeed)
        if kind == "K":
            z.x = float(min(FIELD_W, VIS_W - z.width))
        self.zombies.append(z)
        return z

    def pick_kind(self):
        kinds = self.cfg["kinds"]
        return self.rng.choices(list(kinds), weights=list(kinds.values()))[0]

    def _typo(self):
        self.typos += 1
        self.combo = 0
        if self.jam_on:
            self.jam_until = self.t + 0.35
        self._emit_sound("typo")
        self.say("TYPO!", RED)

    def type_char(self, ch):
        if self.t < self.jam_until:
            return "jam"
        z = self.target
        if z is not None and z not in self.zombies:
            z = self.target = None
        if z is None:
            if ch == " ":
                return "none"
            cands = [q for q in self.zombies if q.word[0] == ch]
            if not cands:
                self._typo()
                return "miss"
            z = self.target = min(cands, key=lambda q: q.x)
        if z.word[z.typed] != ch:
            self._typo()
            return "miss"
        z.typed += 1
        self.correct += 1
        self.stamps.append(self.t)
        if self.t - self._last_char < 2.0:
            self.active_time += self.t - self._last_char
        self._last_char = self.t
        self.effects.append(("tracer", z.lane, z.x, self.t + 0.1))
        if z.typed >= len(z.word):
            self._kill(z)
            return "kill"
        self._emit_sound("hit")
        return "hit"

    def tab(self):
        if not self.zombies:
            return
        ordered = sorted(self.zombies, key=lambda z: z.x)
        if self.target in ordered:
            nxt = ordered[(ordered.index(self.target) + 1) % len(ordered)]
        else:
            nxt = ordered[0]
        if self.target:
            self.target.typed = 0
        self.target = nxt
        nxt.typed = 0

    def drop(self):
        if self.target:
            self.target.typed = 0
            self.target = None

    def hint(self):
        if "pure_typing" in self.mutators:
            self.say("Assist disabled by Pure Typing mutator", YELLOW)
            return
        if not self.hints_on:
            self.say("Assist is turned off (see OPTIONS)", YELLOW)
            return
        if self.hints_left <= 0:
            self.say("No assists left this level", YELLOW)
            return
        z = self.closest()
        if z is None:
            self.say("No zombies yet. Breathe.", GREEN)
            return
        self.hints_left -= 1
        if self.target:
            self.target.typed = 0
        self.target = z
        z.typed = 0
        self.hint_until = self.t + 5
        self.hint_text = f"locked on the closest zombie: {z.word}"

    def power(self, n):
        if not 1 <= n <= 3:
            return
        if "pure_typing" in self.mutators:
            self.say("Powers disabled by Pure Typing mutator", YELLOW)
            return
        name = POWERS[n - 1]
        if self.charges[name] <= 0:
            self.say(f"No {name.upper()} charges. Kill medics, frost and bombers to earn them.", YELLOW)
            return
        if name == "repair" and self.hp >= self.max_hp:
            self.say("Barricade is already at full health", YELLOW)
            return
        self.charges[name] -= 1
        if name == "freeze":
            self.freeze_left = 5.0
            self._emit_sound("power")
            self.say("FREEZE! Everything stops for 5 seconds", CYAN)
        elif name == "repair":
            self.hp = min(self.max_hp, self.hp + 2)
            self._emit_sound("power")
            self.say("REPAIRED! +2 barricade", GREEN)
        else:
            self.bombs_used += 1
            gone = sorted((z for z in self.zombies if z.kind != "K"), key=lambda z: z.x)[:4]
            for z in gone:
                self._kill(z, bomb=True)
            self.say(f"BOMB! The {len(gone)} closest zombies are blown apart", MAGENTA)
            self._emit_sound("bomb")

    def _kill(self, z, bomb=False):
        if z in self.zombies:
            self.zombies.remove(z)
        if self.target is z:
            self.target = None
        self.kills += 1
        k = KINDS[z.kind]
        if bomb:
            self.score += int(len(z.word) * 5 * self.score_mult)
            self.effects.append(("pop", z.lane, z.x, self.t + 0.35))
            return
        self.combo += 1
        self.best_combo = max(self.best_combo, self.combo)
        fever = 1.25 if self.combo >= 10 else 1.0
        pts = int(
            len(z.word.replace(" ", ""))
            * 10
            * k["mult"]
            * (1 + min(self.combo, 20) * 0.1)
            * fever
            * self.score_mult
        )
        self.score += pts
        self.effects.append(("pop", z.lane, z.x, self.t + 0.35))
        text = f"+{pts}  {k['label']} down"
        if fever > 1.0:
            text += " [FEVER]"
        if z.kind in DROPS and "pure_typing" not in self.mutators:
            name = DROPS[z.kind]
            self.charges[name] = min(3, self.charges[name] + 1)
            text += f"   +1 {name.upper()}"
        if z.kind == "K":
            self.bosses_slain += 1
            text = f"BOSS DOWN! +{pts}"
            self._emit_sound("clear")
        else:
            self._emit_sound("kill")
        self.say(text, GREEN)

    def _hit_barricade(self, z):
        self.zombies.remove(z)
        if self.target is z:
            self.target = None
        dmg = KINDS[z.kind]["dmg"]
        self.hp -= dmg
        self.damage_taken += dmg
        self.combo = 0
        self.flash_until = self.t + 0.4
        self._emit_sound("damage")
        self.say(f"The {KINDS[z.kind]['label'].lower()} broke through! -{dmg} barricade", RED)

    def update(self, dt):
        self.t += dt
        self.freeze_left = max(0.0, self.freeze_left - dt)
        self.effects = [e for e in self.effects if e[-1] > self.t]
        self._move(dt)
        for z in [z for z in self.zombies if z.x <= 0]:
            self._hit_barricade(z)
        self._spawn()
        self._events()

    def _move(self, dt):
        if self.freeze_left > 0:
            return
        boost = 1.4 if self.moon_active() else 1.0
        for lane in range(LANES):
            row = sorted((z for z in self.zombies if z.lane == lane), key=lambda z: z.x)
            front = None
            for z in row:
                nx = z.x - z.speed * boost * dt
                if front is not None:
                    nx = max(nx, front.x + front.width + 1)
                z.x = nx
                front = z

    def _spawn(self):
        if self.t < self.next_spawn:
            return
        if self.spawned < self.quota:
            free = [l for l in range(LANES) if self.lane_free(l)]
            if len(self.zombies) >= MAX_ON_SCREEN or not free:
                self.next_spawn = self.t + 0.4
                return
            self.add(self.pick_kind(), self.rng.choice(free))
            self.spawned += 1
            self.next_spawn = self.t + self.cfg["spawn"] * self.dspawn * self.rng.uniform(0.75, 1.25)
        elif self.cfg["boss"] and not self.boss_spawned and len(self.zombies) <= 1:
            self.boss_spawned = True
            self.add("K", self.rng.choice([3, 4]) if self.lane_free(3) or self.lane_free(4) else 3)
            self.say("BOSS INCOMING! Type the whole sentence.", RED)
            self._emit_sound("boss")

    def _events(self):
        evs = self.cfg["events"]
        if not evs or self.t < self.next_event:
            return
        self.next_event = self.t + self.rng.uniform(15, 25)
        ev = self.rng.choice(evs)
        if ev == "horde":
            left = self.quota - self.spawned
            free = [l for l in range(LANES) if self.lane_free(l)]
            n = min(5, left, len(free))
            if n <= 0:
                return
            for lane in self.rng.sample(free, n):
                self.add(self.rng.choice("WWR"), lane)
                self.spawned += 1
            self.say("HORDE! A wave of zombies is arriving!", RED)
            self._emit_sound("boss")
        elif ev == "moon":
            self.moon_until = self.t + 10
            self.say("BLOOD MOON! Zombies are 40% faster for 10s", RED)
            self._emit_sound("boss")
        elif ev == "fog":
            self.fog_until = self.t + 8
            self.say("FOG! Words are hidden until they get close", YELLOW)
        elif ev == "supply":
            if "pure_typing" in self.mutators:
                return
            name = self.rng.choice(POWERS)
            self.charges[name] = min(3, self.charges[name] + 1)
            self.say(f"SUPPLY DROP! +1 {name.upper()}", CYAN)
            self._emit_sound("power")

    def status(self):
        if self.hp <= 0:
            return "dead"
        if (
            self.spawned >= self.quota
            and (not self.cfg["boss"] or self.boss_spawned)
            and not self.zombies
        ):
            return "done"
        return None

    def summary(self):
        acc, wpm = self.accuracy(), self.overall_wpm()
        if self.damage_taken == 0 and acc >= 95:
            stars = 3
        elif self.hp >= 0.6 * self.max_hp and acc >= 85:
            stars = 2
        else:
            stars = 1
        bonus = int((self.hp * 50 + (500 if acc >= 95 else 0) + int(wpm) * 5) * self.score_mult)
        return {"acc": acc, "wpm": wpm, "stars": stars, "bonus": bonus}

    def to_dict(self):
        """Serialize current Siege state for mid-run auto-save."""
        target_idx = self.zombies.index(self.target) if self.target in self.zombies else None
        return {
            "hp": self.hp,
            "t": self.t,
            "spawned": self.spawned,
            "kills": self.kills,
            "bosses_slain": self.bosses_slain,
            "bombs_used": self.bombs_used,
            "score": self.score,
            "combo": self.combo,
            "best_combo": self.best_combo,
            "correct": self.correct,
            "typos": self.typos,
            "active_time": self.active_time,
            "damage_taken": self.damage_taken,
            "boss_spawned": self.boss_spawned,
            "next_spawn": self.next_spawn,
            "next_event": self.next_event,
            "freeze_left": self.freeze_left,
            "moon_until": self.moon_until,
            "fog_until": self.fog_until,
            "charges": dict(self.charges),
            "hints_left": self.hints_left,
            "zombies": [z.to_dict() for z in self.zombies],
            "target_idx": target_idx,
        }

    def restore_dict(self, raw):
        """Restore mid-run Siege state from a saved dictionary."""
        self.hp = int(raw.get("hp", self.hp))
        self.t = float(raw.get("t", 0.0))
        self.spawned = int(raw.get("spawned", 0))
        self.kills = int(raw.get("kills", 0))
        self.bosses_slain = int(raw.get("bosses_slain", 0))
        self.bombs_used = int(raw.get("bombs_used", 0))
        self.score = int(raw.get("score", 0))
        self.combo = int(raw.get("combo", 0))
        self.best_combo = int(raw.get("best_combo", 0))
        self.correct = int(raw.get("correct", 0))
        self.typos = int(raw.get("typos", 0))
        self.active_time = float(raw.get("active_time", 0.0))
        self.damage_taken = int(raw.get("damage_taken", 0))
        self.boss_spawned = bool(raw.get("boss_spawned", False))
        self.next_spawn = float(raw.get("next_spawn", self.t + 1.2))
        self.next_event = float(raw.get("next_event", self.t + 15.0))
        self.freeze_left = float(raw.get("freeze_left", 0.0))
        self.moon_until = float(raw.get("moon_until", 0.0))
        self.fog_until = float(raw.get("fog_until", 0.0))
        if isinstance(raw.get("charges"), dict):
            for p in POWERS:
                if p in raw["charges"]:
                    self.charges[p] = int(raw["charges"][p])
        self.hints_left = int(raw.get("hints_left", self.hints_left))
        self.zombies = [Zombie.from_dict(z) for z in raw.get("zombies", [])]
        t_idx = raw.get("target_idx")
        self.target = self.zombies[t_idx] if isinstance(t_idx, int) and 0 <= t_idx < len(self.zombies) else None


SENTENCES = {
    "EVERYDAY": [
        "hold the wooden barricade before the dead break through",
        "every keystroke pushes the restless horde back into the dark",
        "keep your eyes on the closest lane and never panic",
        "quick fingers and steady breathing will save the city tonight",
        "the morning train arrives late while storm clouds gather overhead",
        "fresh coffee on the kitchen table cools beside an open notebook",
        "silver lanterns swing gently along the quiet harbor boardwalk",
        "we packed warm blankets and flashlights for the long mountain journey",
        "accurate typing beats frantic speed when the pressure rises fast",
        "count the seconds between each wave and prepare your next target",
        "the radio crackles with static as dawn breaks over the river",
        "bright fireworks echoed across the crowded town square at midnight",
    ],
    "HORROR": [
        "shadows creep across the abandoned subway platform in total silence",
        "something scratches violently against the reinforced iron cellar door",
        "a blood moon rises high above the crooked graveyard headstones",
        "cold mist swallows the streetlamps as hollow footsteps draw nearer",
        "ancient whispers echo from the darkened attic at the stroke of midnight",
        "the lantern flickered out just as pale hands reached through the fog",
        "cursed echoes linger inside the ruined hospital corridor after dark",
        "never look away when the closest silhouette steps out of the gloom",
        "the heavy iron gate groaned open beneath the howling winter wind",
        "trembling fingers reload the last flare while the undead close in",
        "broken glass crunches loudly along the deserted midnight highway",
        "the necromancer summoned a relentless swarm from the sunken crypt",
    ],
    "CODER": [
        "git commit your clean changes before the midnight deployment begins",
        "every failing unit test reveals an edge case waiting to be fixed",
        "refactor duplicated logic into a single well tested helper function",
        "async workers process incoming events without blocking the main loop",
        "never trust unvalidated user input anywhere near a system boundary",
        "clean architecture keeps simulation logic separate from terminal rendering",
        "binary search cuts the lookup time down to logarithmic complexity",
        "encrypted packets travel safely across the distributed server cluster",
        "check the stack trace carefully before restarting the production daemon",
        "strong typing catches subtle bugs long before the code ships to users",
        "automated pipelines build wheels and run tests on every pull request",
        "immutable snapshots make state serialization and debugging effortless",
    ],
}
SENTENCES["MIXED"] = SENTENCES["EVERYDAY"] + SENTENCES["HORROR"] + SENTENCES["CODER"]


def sentence_cfg(wave=1):
    """Return configuration dict for Sentence Siege wave n."""
    return dict(
        name=f"SENTENCE WAVE {wave}",
        quota=min(14, 5 + wave * 2),
        speed=min(4.2, 1.8 + 0.28 * wave),
        spawn=max(2.6, 5.2 - 0.3 * wave),
        lens=(6, 14),
        kinds={"S": 1},
        events=["supply", "fog"] if wave >= 2 else ["supply"],
        boss=(wave % 2 == 0),
        blurb="Type full sentences word by word. Perfect sentences earn bonus charges!",
    )


class SentenceSiege(Siege):
    """Big-sentence typing mode with word-streak multipliers and WPM bonuses."""

    def __init__(self, cfg, label, settings, tier=1, seed=None, mutators=None):
        super().__init__(cfg, label, settings, tier=tier, seed=seed, mutators=mutators)
        self.word_streak = 0
        self.best_word_streak = 0
        self.perfect_sentences = 0
        self.sentences_cleared = 0
        self.peak_wpm = 0.0
        self._sentence_typos = 0
        self._word_had_typo = False
        self.seen_sentences = set()

    def pick_sentence(self, boss=False):
        pool = SENTENCES[self.pack_name]
        active = {z.word for z in self.zombies}
        avail = [s for s in pool if s not in active and s not in self.seen_sentences]
        if not avail:
            self.seen_sentences.clear()
            avail = [s for s in pool if s not in active] or pool
        if boss:
            s1 = self.rng.choice(avail)
            rest = [s for s in avail if s != s1] or avail
            s2 = self.rng.choice(rest)
            self.seen_sentences.add(s1)
            self.seen_sentences.add(s2)
            return f"{s1} {s2}"
        # Prefer shorter sentences on early tiers, longer on later tiers
        ordered = sorted(avail, key=len)
        if self.tier <= 2:
            subset = ordered[: max(4, len(ordered) // 2)]
        elif self.tier >= 5:
            subset = ordered[len(ordered) // 3:]
        else:
            subset = ordered
        picked = self.rng.choice(subset)
        self.seen_sentences.add(picked)
        return picked

    def add(self, kind, lane, word=None):
        is_boss = kind == "K"
        actual_kind = "K" if is_boss else "S"
        if word is None:
            word = self.pick_sentence(boss=is_boss)
        speed = self.cfg["speed"] * KINDS[actual_kind]["speed"] * self.dspeed
        z = Zombie(actual_kind, word, lane, speed)
        z.x = float(FIELD_W - 4 if not is_boss else FIELD_W - 8)
        self.zombies.append(z)
        return z

    def _typo(self):
        super()._typo()
        self._sentence_typos += 1
        self._word_had_typo = True
        self.word_streak = 0

    def type_char(self, ch):
        if self.t < self.jam_until:
            return "jam"
        z = self.target
        if z is not None and z not in self.zombies:
            z = self.target = None
        if z is None:
            if ch == " ":
                return "none"
            cands = [q for q in self.zombies if q.word[0] == ch]
            if not cands:
                self._typo()
                return "miss"
            z = self.target = min(cands, key=lambda q: q.x)
            self._sentence_typos = 0
            self._word_had_typo = False
        if z.word[z.typed] != ch:
            self._typo()
            return "miss"

        z.typed += 1
        self.correct += 1
        self.stamps.append(self.t)
        if self.t - self._last_char < 2.0:
            self.active_time += self.t - self._last_char
        self._last_char = self.t
        self.peak_wpm = max(self.peak_wpm, self.wpm())
        self.effects.append(("tracer", z.lane, z.x, self.t + 0.1))

        if ch == " ":
            if not self._word_had_typo:
                self.word_streak += 1
                self.best_word_streak = max(self.best_word_streak, self.word_streak)
                self.score += 15 + min(self.word_streak, 15) * 3
            self._word_had_typo = False

        if z.typed >= len(z.word):
            if not self._word_had_typo:
                self.word_streak += 1
                self.best_word_streak = max(self.best_word_streak, self.word_streak)
            self._kill(z)
            return "kill"
        self._emit_sound("hit")
        return "hit"

    def _kill(self, z, bomb=False):
        if z in self.zombies:
            self.zombies.remove(z)
        if self.target is z:
            self.target = None
        self.kills += 1
        if bomb:
            self.score += int(len(z.word) * 4 * self.score_mult)
            self.effects.append(("pop", z.lane, z.x, self.t + 0.35))
            return

        self.sentences_cleared += 1
        self.combo += 1
        self.best_combo = max(self.best_combo, self.combo)
        streak_mult = 1.0 + min(self.word_streak, 20) * 0.05
        char_count = len(z.word.replace(" ", ""))
        wpm_bonus = int(self.wpm() * 3)
        perfect = self._sentence_typos == 0
        perfect_bonus = 250 if perfect else 0
        base = char_count * 12 * (1.5 if z.kind == "K" else 1.0)
        pts = int((base * streak_mult + wpm_bonus + perfect_bonus) * self.score_mult)
        self.score += pts
        self.effects.append(("pop", z.lane, z.x, self.t + 0.35))

        if perfect:
            self.perfect_sentences += 1
        msg = f"+{pts}  {'PERFECT! ' if perfect else ''}({len(z.word.split())} words)"
        if perfect and self.perfect_sentences % 3 == 0 and "pure_typing" not in self.mutators:
            bonus_power = self.rng.choice(POWERS)
            self.charges[bonus_power] = min(3, self.charges[bonus_power] + 1)
            msg += f"  +1 {bonus_power.upper()}"
        if z.kind == "K":
            self.bosses_slain += 1
            msg = f"BOSS PARAGRAPH CLEARED! +{pts}"
            self._emit_sound("clear")
        else:
            self._emit_sound("kill")
        self._sentence_typos = 0
        self._word_had_typo = False
        self.say(msg, GREEN)

