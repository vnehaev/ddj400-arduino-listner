from pathlib import Path

try:
    from smbus2 import SMBus
except Exception:
    SMBus = None

OLED_I2C_PORT = 1
OLED_I2C_ADDRESSES = (0x3C, 0x3D)
MAX_LINE_LENGTH = 21


class RaspberryBackend:
    name = 'raspberry'

    def __init__(self, address, port=OLED_I2C_PORT):
        from luma.core.interface.serial import i2c
        from luma.oled.device import ssd1306
        from PIL import Image, ImageDraw, ImageFont
        self.Image = Image
        self.ImageDraw = ImageDraw
        self.font = ImageFont.load_default()
        self.device = ssd1306(i2c(port=port, address=address))

    def render(self, lines):
        image = self.Image.new('1', (self.device.width, self.device.height))
        draw = self.ImageDraw.Draw(image)
        draw.rectangle((0, 0, self.device.width, self.device.height), outline=0, fill=0)
        visible = lines[:2] if self.device.height <= 32 else lines[:4]
        for index, line in enumerate(visible):
            draw.text((0, index * 16), str(line)[:MAX_LINE_LENGTH], font=self.font, fill=255)
        self.device.display(image)

    def close(self):
        try:
            self.device.clear()
        except Exception:
            pass


def detect_raspberry_backend(port=OLED_I2C_PORT):
    if SMBus is None:
        return None
    if not Path(f'/dev/i2c-{port}').exists():
        return None
    try:
        with SMBus(port) as bus:
            for address in OLED_I2C_ADDRESSES:
                try:
                    bus.read_byte(address)
                    return RaspberryBackend(address, port=port)
                except OSError:
                    pass
    except Exception:
        return None
    return None
