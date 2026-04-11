import logging

from display_output_pi import detect_raspberry_backend
from display_output_arduino import detect_arduino_backend
from bridge_config import PREFERRED_OUTPUT

log = logging.getLogger('display-output')


def detect_display_backend():
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
