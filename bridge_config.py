import os

UDP_HOST = os.getenv('UDP_HOST', '127.0.0.1')
UDP_PORT = int(os.getenv('UDP_PORT', '5005'))
REFRESH_INTERVAL = float(os.getenv('REFRESH_INTERVAL', '0.20'))
REDISCOVERY_INTERVAL = float(os.getenv('REDISCOVERY_INTERVAL', '3.0'))
PREFERRED_OUTPUT = os.getenv('PREFERRED_OUTPUT', 'auto').strip().lower()
MAX_LINE_LENGTH = int(os.getenv('MAX_LINE_LENGTH', '21'))
OLED_I2C_PORT = int(os.getenv('OLED_I2C_PORT', '1'))
SERIAL_BAUDRATE = int(os.getenv('SERIAL_BAUDRATE', '115200'))
