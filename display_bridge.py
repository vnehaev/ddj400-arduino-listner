import json
import logging
import os
import socket
import threading
import time

from display_output_pi import detect_raspberry_backend
from display_output_arduino import detect_arduino_backend

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('display-bridge')

UDP_HOST = os.getenv('UDP_HOST', '127.0.0.1')
UDP_PORT = int(os.getenv('UDP_PORT', '5005'))
REFRESH_INTERVAL = float(os.getenv('REFRESH_INTERVAL', '0.20'))
REDISCOVERY_INTERVAL = float(os.getenv('REDISCOVERY_INTERVAL', '3.0'))
PREFERRED_OUTPUT = os.getenv('PREFERRED_OUTPUT', 'auto').strip().lower()
MAX_LINE_LENGTH = int(os.getenv('MAX_LINE_LENGTH', '21'))


class App:
    def __init__(self):
        self.lines = ['', '', '', '']
        self.lock = threading.Lock()
        self.backend = None
        self.last_render_signature = None
        self.last_detection_attempt = 0.0

    def update_lines(self, payload):
        lines = None
        if isinstance(payload.get('lines'), list):
            lines = payload['lines']
        elif isinstance(payload.get('screen'), dict) and isinstance(payload['screen'].get('lines'), list):
            lines = payload['screen']['lines']
        else:
            candidate = [payload.get(f'line{i}') for i in range(1, 5)]
            if any(value is not None for value in candidate):
                lines = candidate

        if lines is None:
            return

        normalized = [str(line or '')[:MAX_LINE_LENGTH] for line in lines[:4]]
        while len(normalized) < 4:
            normalized.append('')

        with self.lock:
            self.lines = normalized

    def listen(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((UDP_HOST, UDP_PORT))
        log.info('Listening for screen updates on %s:%s', UDP_HOST, UDP_PORT)
        while True:
            data, _ = sock.recvfrom(4096)
            try:
                self.update_lines(json.loads(data.decode('utf-8')))
            except Exception as exc:
                log.warning('Bad packet: %s', exc)

    def detect_backend(self):
        order = [PREFERRED_OUTPUT] if PREFERRED_OUTPUT in {'raspberry', 'arduino'} else ['raspberry', 'arduino']
        for output_type in order:
            if output_type == 'raspberry':
                backend = detect_raspberry_backend()
                if backend is not None:
                    log.info('Using Raspberry Pi OLED backend')
                    return backend
            if output_type == 'arduino':
                backend = detect_arduino_backend()
                if backend is not None:
                    log.info('Using Arduino serial backend')
                    return backend
        return None

    def render_loop(self):
        while True:
            now = time.monotonic()
            if self.backend is None and now - self.last_detection_attempt >= REDISCOVERY_INTERVAL:
                self.last_detection_attempt = now
                self.backend = self.detect_backend()
                if self.backend is None:
                    log.warning('No display backend detected yet')

            with self.lock:
                lines = list(self.lines)

            signature = tuple(lines)
            if self.backend is not None and signature != self.last_render_signature:
                try:
                    self.backend.render(lines)
                    self.last_render_signature = signature
                except Exception as exc:
                    log.error('Backend %s failed: %s', getattr(self.backend, 'name', 'unknown'), exc)
                    try:
                        self.backend.close()
                    except Exception:
                        pass
                    self.backend = None
                    self.last_render_signature = None

            time.sleep(REFRESH_INTERVAL)

    def run(self):
        threading.Thread(target=self.listen, daemon=True).start()
        self.render_loop()


if __name__ == '__main__':
    App().run()
