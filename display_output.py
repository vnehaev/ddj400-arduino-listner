from datetime import datetime
import time

from bridge_config import DISPLAY_BAUDRATE, DISPLAY_KEY_PLACEHOLDER, DISPLAY_PORT

try:
    import serial
except ImportError:
    serial = None


def open_display_serial():
    if serial is None:
        print("Display serial disabled: pyserial is not installed")
        return None

    try:
        display_serial = serial.Serial(DISPLAY_PORT, DISPLAY_BAUDRATE, timeout=1)
        time.sleep(2)
        print(f"Display serial opened     : {DISPLAY_PORT} @ {DISPLAY_BAUDRATE}")
        return display_serial
    except Exception as exc:
        print(f"Display serial disabled   : {exc}")
        return None


def send_display_line(display_serial, line):
    if not line:
        return

    if display_serial is None:
        print("DISPLAY (dry-run):", line)
        return

    display_serial.write((line + "\n").encode("utf-8"))
    print("DISPLAY:", line)


def clean_display_text(value, max_length=32):
    return " ".join(str(value).split())[:max_length]


def format_clock(seconds):
    seconds = max(0, int(seconds))
    minutes, seconds = divmod(seconds, 60)
    return f"{minutes:02d}:{seconds:02d}"


def send_cached_line(display_serial, display_state, key, line, force=False):
    if not force and display_state.last_lines.get(key) == line:
        return

    send_display_line(display_serial, line)
    display_state.last_lines[key] = line


def emit_display_state(display_serial, display_state, now):
    send_cached_line(display_serial, display_state, "TIME", f"TIME:{datetime.now().strftime('%H:%M')}")
    send_cached_line(display_serial, display_state, "REC", f"REC:{1 if display_state.rec_enabled else 0}")

    record_elapsed = 0
    if display_state.rec_enabled and display_state.rec_started_at is not None:
        record_elapsed = now - display_state.rec_started_at
    send_cached_line(
        display_serial,
        display_state,
        "REC_TIME",
        f"REC_TIME:{format_clock(record_elapsed)}",
        force=display_state.rec_enabled,
    )

    for deck_name, deck_state in display_state.decks.items():
        key = clean_display_text(deck_state.key or DISPLAY_KEY_PLACEHOLDER, max_length=8) or DISPLAY_KEY_PLACEHOLDER
        send_cached_line(
            display_serial,
            display_state,
            f"{deck_name}_MAIN",
            f"{deck_name}:{deck_state.bpm}:{key}",
        )
        send_cached_line(
            display_serial,
            display_state,
            f"{deck_name}_TITLE",
            f"{deck_name}_TITLE:{clean_display_text(deck_state.title)}",
        )
        send_cached_line(
            display_serial,
            display_state,
            f"{deck_name}_ARTIST",
            f"{deck_name}_ARTIST:{clean_display_text(deck_state.artist)}",
        )
        send_cached_line(
            display_serial,
            display_state,
            f"{deck_name}_ELAPSED",
            f"{deck_name}_ELAPSED:{format_clock(deck_state.elapsed)}",
        )
        send_cached_line(
            display_serial,
            display_state,
            f"{deck_name}_STATE",
            f"{deck_name}_STATE:{'PLAY' if deck_state.play else 'PAUSE'}",
        )
        send_cached_line(
            display_serial,
            display_state,
            f"{deck_name}_LOADED",
            f"{deck_name}_LOADED:{1 if deck_state.loaded else 0}",
        )
        send_cached_line(
            display_serial,
            display_state,
            f"{deck_name}_LOOP",
            f"{deck_name}_LOOP:{1 if deck_state.loop else 0}",
        )