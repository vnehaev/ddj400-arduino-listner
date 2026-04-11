from dataclasses import dataclass, field
from typing import Optional

from bridge_config import DISPLAY_BPM_PLACEHOLDER, DISPLAY_KEY_PLACEHOLDER


@dataclass
class DeckDisplayState:
    bpm: str = DISPLAY_BPM_PLACEHOLDER
    key: str = DISPLAY_KEY_PLACEHOLDER
    title: str = ""
    artist: str = ""
    play: bool = False
    loaded: bool = False
    loop: bool = False
    elapsed: int = 0
    duration: int = 0


@dataclass
class DisplayState:
    decks: dict = field(default_factory=lambda: {
        "D1": DeckDisplayState(),
        "D2": DeckDisplayState(),
    })
    rec_enabled: bool = False
    rec_started_at: Optional[float] = None
    last_lines: dict = field(default_factory=dict)