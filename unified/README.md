# Unified display bridge

This folder contains a unified output path for the DDJ-400 display bridge.

## What it does

The Python bridge listens for local UDP updates on `127.0.0.1:5005` and automatically selects one output backend:

1. **Raspberry Pi local OLED** over I2C, if an OLED is detected on `0x3C` or `0x3D`
2. **Arduino OLED receiver** over serial, if an Arduino replies to the handshake

If Raspberry Pi OLED is present, it is preferred by default. Override with:

```bash
export PREFERRED_OUTPUT=arduino
```

## Files

- `display_bridge_unified.py` - unified Python receiver with auto-detection
- `requirements.txt` - Python dependencies
- `arduino_oled_receiver/arduino_oled_receiver.ino` - Arduino sketch for serial-driven OLED output

## Raspberry Pi setup

```bash
sudo apt update
sudo apt install -y python3-pip python3-venv i2c-tools
python3 -m venv .venv
source .venv/bin/activate
pip install -r unified/requirements.txt
```

Enable I2C and confirm the OLED address:

```bash
sudo raspi-config nonint do_i2c 0
i2cdetect -y 1
```

## Run on Raspberry Pi

```bash
source .venv/bin/activate
python unified/display_bridge_unified.py
```

## Arduino setup

1. Install the **U8g2** library in Arduino IDE
2. Open `arduino_oled_receiver/arduino_oled_receiver.ino`
3. Upload it to Arduino UNO or MEGA
4. Connect the OLED over I2C to the Arduino
5. Start the same Python bridge on the Raspberry Pi

The Python bridge will detect the Arduino over serial and use it when no local Raspberry Pi OLED is available.

## UDP message format

The bridge expects JSON packets like this:

```json
{"deck": 1, "bpm": 174.3, "playing": true, "elapsed": "01:25", "title": "Track name"}
```

## Notes

- Local Raspberry Pi OLED currently assumes SSD1306 on I2C
- Arduino sketch also assumes SSD1306 128x64 via U8g2
- Titles are trimmed to fit a 128x64 display
