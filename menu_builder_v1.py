# menu_builder_v1.py

from dataclasses import dataclass
from typing import Dict, List, Any

@dataclass
class Tile:
    opcode: str
    args: Dict[str, Any]
    color_role: str

@dataclass
class PXLIR:
    width: int
    height: int
    tiles: List[Tile]
    complexity: float = 0.0

default_palette = {
    "logic": "#FF6B6B",
    "memory": "#4ECDC4",
    "learn": "#45B7D1",
    "act": "#96CEB4",
    "meta": "#FFEAA7",
    "io": "#C7CEEA"
}

default_captests = {
    "version": 1,
    "tests": [
        {"name": "has_label_resolution", "expect": True},
        {"name": "has_click_if", "expect": True}
    ]
}

def build_menu_ir():
    tiles = [
        Tile("RECT", {"x": 0, "y": 0, "w": 128, "h": 16}, "logic"),
        Tile("WRITE_TEXT", {"x": 4, "y": 4, "text": "File", "font": "5x7"}, "meta"),
        Tile("IF_CLICK_AT", {"x": 0, "y": 0, "w": 30, "h": 16, "target_true": "menu_open", "target_false": "loop"}, "act"),
        Tile("LABEL", {"name": "loop"}, "memory"),
        Tile("JUMP", {"target": "loop"}, "logic")
    ]
    return PXLIR(width=128, height=64, tiles=tiles, complexity=len(tiles) * 1.5)
