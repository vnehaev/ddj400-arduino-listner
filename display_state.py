import threading


class DisplayState:
    def __init__(self):
        self._lines = ['', '', '', '']
        self._lock = threading.Lock()

    def update(self, lines):
        with self._lock:
            self._lines = list(lines[:4])
            while len(self._lines) < 4:
                self._lines.append('')

    def get_lines(self):
        with self._lock:
            return list(self._lines)
