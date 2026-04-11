from bridge_config import (
    DISPLAY_BPM_PLACEHOLDER,
    DISPLAY_KEY_PLACEHOLDER,
    DISPLAY_MANUFACTURER_ID,
)


def set_recording_state(display_state, enabled, now):
    if enabled and not display_state.rec_enabled:
        display_state.rec_started_at = now
    elif not enabled:
        display_state.rec_started_at = None

    display_state.rec_enabled = enabled


def update_display_state(display_state, payload, now):
    name, separator, raw_value = payload.partition(":")
    if not separator:
        return

    value = raw_value.strip()

    if name == "REC_STATUS":
        set_recording_state(display_state, value not in {"", "0", "false", "False"}, now)
        return

    deck_name, separator, field_name = name.partition("_")
    if not separator or deck_name not in display_state.decks:
        return

    deck_state = display_state.decks[deck_name]
    if field_name == "BPM":
        deck_state.bpm = value or DISPLAY_BPM_PLACEHOLDER
    elif field_name == "KEY":
        deck_state.key = value or DISPLAY_KEY_PLACEHOLDER
    elif field_name == "TITLE":
        deck_state.title = value
    elif field_name == "ARTIST":
        deck_state.artist = value
    elif field_name == "PLAY":
        deck_state.play = value == "1"
    elif field_name == "LOADED":
        deck_state.loaded = value == "1"
    elif field_name == "LOOP":
        deck_state.loop = value == "1"
    elif field_name == "ELAPSED":
        deck_state.elapsed = int(float(value or 0))
    elif field_name == "DURATION":
        deck_state.duration = int(float(value or 0))


def transform_mixxx_to_ddj(msg, display_serial, display_state, now):
    if msg.type == "sysex" and msg.data and msg.data[0] == DISPLAY_MANUFACTURER_ID:
        payload = bytes(msg.data[1:]).decode("ascii", errors="ignore")
        update_display_state(display_state, payload, now)
        return None

    return msg


def transform_ddj_to_mixxx(msg):
    return msg