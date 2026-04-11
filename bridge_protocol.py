from bridge_config import MAX_LINE_LENGTH


def sanitize_line(value):
    return str(value or '').replace('|', '/').replace('\n', ' ')[:MAX_LINE_LENGTH]


def extract_lines(payload):
    if isinstance(payload.get('lines'), list):
        lines = payload['lines']
    elif isinstance(payload.get('screen'), dict) and isinstance(payload['screen'].get('lines'), list):
        lines = payload['screen']['lines']
    else:
        named = [payload.get(f'line{i}') for i in range(1, 5)]
        if not any(value is not None for value in named):
            return None
        lines = named

    normalized = [sanitize_line(value) for value in lines[:4]]
    while len(normalized) < 4:
        normalized.append('')
    return normalized


def build_serial_payload(lines):
    normalized = [sanitize_line(value) for value in lines[:4]]
    while len(normalized) < 4:
        normalized.append('')
    return 'SCREEN|' + '|'.join(normalized) + '\n'
