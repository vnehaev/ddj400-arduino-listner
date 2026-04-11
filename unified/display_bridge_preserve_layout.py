import json, logging, os, socket, threading, time
from pathlib import Path

try:
    import serial
    from serial.tools import list_ports
except Exception:
    serial = None
    list_ports = None

try:
    from smbus2 import SMBus
except Exception:
    SMBus = None

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('display-bridge')

UDP_HOST = os.getenv('UDP_HOST', '127.0.0.1')
UDP_PORT = int(os.getenv('UDP_PORT', '5005'))
OLED_I2C_PORT = int(os.getenv('OLED_I2C_PORT', '1'))
SERIAL_BAUDRATE = int(os.getenv('SERIAL_BAUDRATE', '115200'))
MAX_LINE_LENGTH = int(os.getenv('MAX_LINE_LENGTH', '21'))
PREFERRED_OUTPUT = os.getenv('PREFERRED_OUTPUT', 'auto').strip().lower()

class RaspberryBackend:
    name = 'raspberry'
    def __init__(self, address):
        from luma.core.interface.serial import i2c
        from luma.oled.device import ssd1306
        from PIL import Image, ImageDraw, ImageFont
        self.Image = Image
        self.ImageDraw = ImageDraw
        self.font = ImageFont.load_default()
        self.device = ssd1306(i2c(port=OLED_I2C_PORT, address=address))
    def render(self, lines):
        image = self.Image.new('1', (self.device.width, self.device.height))
        draw = self.ImageDraw.Draw(image)
        draw.rectangle((0, 0, self.device.width, self.device.height), outline=0, fill=0)
        visible = lines[:2] if self.device.height <= 32 else lines[:4]
        for i, line in enumerate(visible):
            draw.text((0, i * 16), line[:MAX_LINE_LENGTH], font=self.font, fill=255)
        self.device.display(image)
    def close(self):
        try:
            self.device.clear()
        except Exception:
            pass

class ArduinoBackend:
    name = 'arduino'
    def __init__(self, port):
        self.ser = serial.Serial(port=port, baudrate=SERIAL_BAUDRATE, timeout=1, write_timeout=1)
        time.sleep(2)
        self.ser.reset_input_buffer(); self.ser.reset_output_buffer()
        self.ser.write(b'PING\n'); self.ser.flush()
        if not self.ser.readline().decode('utf-8', 'ignore').strip().startswith('PONG'):
            self.ser.close(); raise RuntimeError('Handshake failed')
    def render(self, lines):
        lines = [str(x or '').replace('|', '/').replace('\n', ' ')[:MAX_LINE_LENGTH] for x in lines[:4]]
        while len(lines) < 4: lines.append('')
        self.ser.write(('SCREEN|' + '|'.join(lines) + '\n').encode('utf-8')); self.ser.flush()
    def close(self):
        try:
            self.ser.close()
        except Exception:
            pass

def detect_backend():
    order = [PREFERRED_OUTPUT] if PREFERRED_OUTPUT in {'raspberry', 'arduino'} else ['raspberry', 'arduino']
    for output in order:
        if output == 'raspberry' and SMBus and Path(f'/dev/i2c-{OLED_I2C_PORT}').exists():
            try:
                with SMBus(OLED_I2C_PORT) as bus:
                    for address in (0x3C, 0x3D):
                        try:
                            bus.read_byte(address)
                            return RaspberryBackend(address)
                        except OSError:
                            pass
            except Exception as exc:
                log.warning('I2C scan failed: %s', exc)
        if output == 'arduino' and serial and list_ports:
            for port in list_ports.comports():
                text = ' '.join(filter(None, [port.device, port.description, port.manufacturer or ''])).lower()
                if any(k in text for k in ('arduino', 'ch340', 'usb serial', 'cp210', 'ttyacm', 'ttyusb')):
                    try:
                        return ArduinoBackend(port.device)
                    except Exception:
                        pass
    return None

class App:
    def __init__(self):
        self.lines = ['', '', '', '']
        self.lock = threading.Lock()
        self.backend = None
        self.last = None
        self.last_try = 0
    def update(self, payload):
        if isinstance(payload.get('lines'), list):
            lines = payload['lines']
        elif isinstance(payload.get('screen'), dict) and isinstance(payload['screen'].get('lines'), list):
            lines = payload['screen']['lines']
        else:
            lines = [payload.get(f'line{i}') for i in range(1, 5)]
            if not any(x is not None for x in lines):
                return
        lines = [str(x or '')[:MAX_LINE_LENGTH] for x in lines[:4]]
        while len(lines) < 4: lines.append('')
        with self.lock: self.lines = lines
    def listen(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((UDP_HOST, UDP_PORT))
        while True:
            data, _ = sock.recvfrom(4096)
            try: self.update(json.loads(data.decode('utf-8')))
            except Exception as exc: log.warning('Bad packet: %s', exc)
    def run(self):
        threading.Thread(target=self.listen, daemon=True).start()
        while True:
            if self.backend is None and time.monotonic() - self.last_try > 3:
                self.last_try = time.monotonic(); self.backend = detect_backend()
            with self.lock: lines = list(self.lines)
            sig = tuple(lines)
            if self.backend and sig != self.last:
                try:
                    self.backend.render(lines); self.last = sig
                except Exception:
                    self.backend = None; self.last = None
            time.sleep(0.2)

if __name__ == '__main__':
    App().run()
