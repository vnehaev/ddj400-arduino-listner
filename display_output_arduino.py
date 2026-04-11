import time

try:
    import serial
    from serial.tools import list_ports
except Exception:
    serial = None
    list_ports = None

SERIAL_BAUDRATE = 115200
MAX_LINE_LENGTH = 21
SERIAL_KEYWORDS = ('arduino', 'ch340', 'usb serial', 'cp210', 'ttyacm', 'ttyusb')


class ArduinoBackend:
    name = 'arduino'

    def __init__(self, port, baudrate=SERIAL_BAUDRATE):
        if serial is None:
            raise RuntimeError('pyserial is not installed')
        self.ser = serial.Serial(port=port, baudrate=baudrate, timeout=1, write_timeout=1)
        time.sleep(2)
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()
        self.ser.write(b'PING\n')
        self.ser.flush()
        reply = self.ser.readline().decode('utf-8', 'ignore').strip()
        if not reply.startswith('PONG'):
            self.ser.close()
            raise RuntimeError(f'Handshake failed on {port}: {reply!r}')

    def render(self, lines):
        normalized = [str(line or '').replace('|', '/').replace('\n', ' ')[:MAX_LINE_LENGTH] for line in lines[:4]]
        while len(normalized) < 4:
            normalized.append('')
        payload = 'SCREEN|' + '|'.join(normalized) + '\n'
        self.ser.write(payload.encode('utf-8'))
        self.ser.flush()

    def close(self):
        try:
            self.ser.close()
        except Exception:
            pass


def detect_arduino_backend():
    if list_ports is None:
        return None
    for port in list_ports.comports():
        description = ' '.join(filter(None, [port.device, port.description, port.manufacturer or ''])).lower()
        if any(keyword in description for keyword in SERIAL_KEYWORDS):
            try:
                return ArduinoBackend(port.device)
            except Exception:
                pass
    return None
