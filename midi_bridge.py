#!/usr/bin/env python3
import sys
import time
import mido

PHYSICAL_PORT_NAME = "DDJ-400 MIDI 1"
VIRTUAL_PORT_NAME = "DDJ400 Bridge"


def find_port(port_names, needle):
    for name in port_names:
        if needle in name:
            return name
    return None


def transform_mixxx_to_ddj(msg):
    return msg


def transform_ddj_to_mixxx(msg):
    return msg


def main():
    mido.set_backend("mido.backends.rtmidi")

    print("Available MIDI input names:")
    input_names = mido.get_input_names()
    for name in input_names:
        print("  ", name)

    print("\nAvailable MIDI output names:")
    output_names = mido.get_output_names()
    for name in output_names:
        print("  ", name)

    ddj_in_name = find_port(input_names, PHYSICAL_PORT_NAME)
    ddj_out_name = find_port(output_names, PHYSICAL_PORT_NAME)

    if not ddj_in_name or not ddj_out_name:
        print(f"\nERROR: could not find physical port containing '{PHYSICAL_PORT_NAME}'")
        sys.exit(1)

    print(f"\nOpening physical MIDI input : {ddj_in_name}")
    print(f"Opening physical MIDI output: {ddj_out_name}")

    ddj_in = mido.open_input(ddj_in_name)
    ddj_out = mido.open_output(ddj_out_name)

    print(f"Opening virtual MIDI INPUT port : {VIRTUAL_PORT_NAME}")
    mixxx_to_bridge = mido.open_input(VIRTUAL_PORT_NAME, virtual=True)

    print(f"Opening virtual MIDI OUTPUT port: {VIRTUAL_PORT_NAME}")
    bridge_to_mixxx = mido.open_output(VIRTUAL_PORT_NAME, virtual=True)

    print("\nBridge is running")
    print(f"  Virtual controller name : {VIRTUAL_PORT_NAME}")
    print(f"  Physical controller     : {PHYSICAL_PORT_NAME}")
    print("\nPress Ctrl+C to stop\n")

    try:
        while True:
            # DDJ -> Bridge -> Mixxx
            for msg in ddj_in.iter_pending():
                out_msg = transform_ddj_to_mixxx(msg)
                if out_msg is not None:
                    bridge_to_mixxx.send(out_msg)

            # Mixxx -> Bridge -> DDJ
            for msg in mixxx_to_bridge.iter_pending():
                print("FROM MIXXX:", msg)
                out_msg = transform_mixxx_to_ddj(msg)
                if out_msg is not None:
                    ddj_out.send(out_msg)

            time.sleep(0.001)

    finally:
        ddj_in.close()
        ddj_out.close()
        mixxx_to_bridge.close()
        bridge_to_mixxx.close()


if __name__ == "__main__":
    main()
