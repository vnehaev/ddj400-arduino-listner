import json
import logging
import socket
import threading
import time

from bridge_config import UDP_HOST, UDP_PORT, REFRESH_INTERVAL, REDISCOVERY_INTERVAL
from bridge_protocol import extract_lines
from display_output import detect_display_backend
from display_state import DisplayState

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('midi-bridge')


class MidiBridge:
    def __init__(self):
        self.state = DisplayState()
        self.backend = None
        self.last_render_signature = None
        self.last_detection_attempt = 0.0

    def listen_udp(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((UDP_HOST, UDP_PORT))
        log.info('Listening for screen updates on %s:%s', UDP_HOST, UDP_PORT)
        while True:
            data, _ = sock.recvfrom(4096)
            try:
                payload = json.loads(data.decode('utf-8'))
                lines = extract_lines(payload)
                if lines is not None:
                    self.state.update(lines)
            except Exception as exc:
                log.warning('Bad packet: %s', exc)

    def ensure_backend(self):
        now = time.monotonic()
        if self.backend is not None:
            return
        if now - self.last_detection_attempt < REDISCOVERY_INTERVAL:
            return
        self.last_detection_attempt = now
        self.backend = detect_display_backend()
        if self.backend is None:
            log.warning('No display backend detected yet')

    def render_loop(self):
        while True:
            self.ensure_backend()
            lines = self.state.get_lines()
            signature = tuple(lines)
            if self.backend is not None and signature != self.last_render_signature:
                try:
                    self.backend.render(lines)
                    self.last_render_signature = signature
                except Exception as exc:
                    log.error('Backend failed: %s', exc)
                    try:
                        self.backend.close()
                    except Exception:
                        pass
                    self.backend = None
                    self.last_render_signature = None
            time.sleep(REFRESH_INTERVAL)

    def run(self):
        threading.Thread(target=self.listen_udp, daemon=True).start()
        self.render_loop()


if __name__ == '__main__':
    MidiBridge().run()
