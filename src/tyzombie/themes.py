"""Color themes, accessibility palettes, and box-drawing glyphs."""

import sys

# Color pair IDs used across canvases
GREEN, YELLOW, RED, CYAN, BLUE, WHITE, MAGENTA = 1, 2, 3, 4, 5, 6, 7

THEMES = [
    {
        "id": "outbreak",
        "name": "OUTBREAK",
        "desc": "Classic quarantine green, blood red, and hazard yellow.",
        "curses_pairs": {
            GREEN: "green",
            YELLOW: "yellow",
            RED: "red",
            CYAN: "cyan",
            BLUE: "blue",
            WHITE: "white",
            MAGENTA: "magenta",
        },
        "hex": {
            0: "#c9d1d9",
            GREEN: "#3fb950",
            YELLOW: "#d29922",
            RED: "#f85149",
            CYAN: "#39c5cf",
            BLUE: "#58a6ff",
            WHITE: "#e6edf3",
            MAGENTA: "#bc8cff",
        },
    },
    {
        "id": "neon",
        "name": "NEON CYBER",
        "desc": "Synthwave cyan, electric magenta, and bright white.",
        "curses_pairs": {
            GREEN: "cyan",
            YELLOW: "magenta",
            RED: "red",
            CYAN: "blue",
            BLUE: "cyan",
            WHITE: "white",
            MAGENTA: "yellow",
        },
        "hex": {
            0: "#cbd5e1",
            GREEN: "#22d3ee",
            YELLOW: "#f472b6",
            RED: "#fb7185",
            CYAN: "#38bdf8",
            BLUE: "#818cf8",
            WHITE: "#f8fafc",
            MAGENTA: "#e879f9",
        },
    },
    {
        "id": "amber",
        "name": "AMBER CRT",
        "desc": "Retro phosphor amber terminal with high-visibility alerts.",
        "curses_pairs": {
            GREEN: "yellow",
            YELLOW: "white",
            RED: "red",
            CYAN: "yellow",
            BLUE: "white",
            WHITE: "yellow",
            MAGENTA: "red",
        },
        "hex": {
            0: "#fbbf24",
            GREEN: "#f59e0b",
            YELLOW: "#fef3c7",
            RED: "#ef4444",
            CYAN: "#fcd34d",
            BLUE: "#fde68a",
            WHITE: "#fffbeb",
            MAGENTA: "#fb923c",
        },
    },
    {
        "id": "colorblind",
        "name": "COLORBLIND",
        "desc": "High-contrast blue/orange/cyan palette avoiding red-green ambiguity.",
        "curses_pairs": {
            GREEN: "cyan",
            YELLOW: "yellow",
            RED: "magenta",
            CYAN: "blue",
            BLUE: "cyan",
            WHITE: "white",
            MAGENTA: "yellow",
        },
        "hex": {
            0: "#e2e8f0",
            GREEN: "#009e73",
            YELLOW: "#f0e442",
            RED: "#d55e00",
            CYAN: "#56b4e9",
            BLUE: "#0072b2",
            WHITE: "#ffffff",
            MAGENTA: "#cc79a7",
        },
    },
]


def get_theme(index_or_id, colorblind=False):
    """Return the active theme dictionary, respecting colorblind override."""
    if colorblind:
        return THEMES[3]
    if isinstance(index_or_id, int):
        return THEMES[index_or_id % len(THEMES)]
    for t in THEMES:
        if t["id"] == index_or_id:
            return t
    return THEMES[0]


def supports_unicode():
    """Return True if stdout encoding appears to support Unicode box drawing."""
    enc = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        "╔═╗║╚╝┌─┐│└┘█░".encode(enc)
        return True
    except (UnicodeEncodeError, LookupError):
        return False


def get_glyphs(force_ascii=False):
    """Return box-drawing and bar glyphs with automatic ASCII fallback."""
    if not force_ascii and supports_unicode():
        return {
            "tl": "╔", "tr": "╗", "bl": "╚", "br": "╝", "h": "═", "v": "║",
            "stl": "┌", "str": "┐", "sbl": "└", "sbr": "┘", "sh": "─", "sv": "│",
            "full": "█", "empty": "░", "bullet": "•", "arrow": "▸",
            "star_on": "★", "star_off": "☆",
        }
    return {
        "tl": "+", "tr": "+", "bl": "+", "br": "+", "h": "=", "v": "|",
        "stl": "+", "str": "+", "sbl": "+", "sbr": "+", "sh": "-", "sv": "|",
        "full": "#", "empty": "-", "bullet": "*", "arrow": ">",
        "star_on": "*", "star_off": "-",
    }


def progress_bar(ratio, width, glyphs=None):
    """Render a smooth progress bar string of exact width."""
    g = glyphs or get_glyphs()
    clamped = max(0.0, min(1.0, float(ratio)))
    filled = int(round(clamped * width))
    return g["full"] * filled + g["empty"] * (width - filled)
