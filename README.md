# Agricultural Crop Health Rover

A prototype agricultural rover combining YOLO crop-health detection, manual/autonomous rover control, obstacle avoidance, and disease-triggered spraying.

> **Repository status:** Starter documentation only. The tested Raspberry Pi controller, Arduino sketch, and model weights have not yet been added. Do not assume this repository is ready to flash/run until those files are copied from the actual devices and tested.

## Features
- Crop-health classification with the trained `Crop.pt` model
- Raspberry Pi camera-based detection
- Manual and autonomous rover modes
- Three-ultrasonic-sensor obstacle avoidance
- Arduino Uno R3 motor and pump control
- Disease-triggered spray pulse
- Serial communication and emergency-stop handling

## Hardware
- Raspberry Pi 4
- OV5647 camera (tested setup)
- Arduino Uno R3
- L298N motor driver and four DC motors
- Three ultrasonic sensors
- Pump, suitable relay/driver, and separate suitable power supply

## Repository layout
See folders: `arduino/`, `raspberry_pi/`, `models/`, `docs/`, and `results/`.

## Setup
1. Read `docs/hardware.md` and `docs/operation-and-safety.md`.
2. Add the tested Arduino `.ino` to `arduino/`.
3. Add the tested Pi scripts to `raspberry_pi/`.
4. Add or document access to the model in `models/`.
5. Follow `docs/installation.md`.

## Safety
Never connect a motor or pump directly to an Arduino GPIO. Use properly rated drivers, wiring, fuses, and power supplies. Verify relay polarity and sensor voltage compatibility. Test with wheels raised and water only before field operation. A software emergency stop is not a substitute for a physical power disconnect.

## Performance
Report model inference, full detection pipeline, software detection-to-serial latency, and physical pump response as separate measurements. See `docs/testing-and-results.md`.

## Contributions
When reporting issues, include OS/Python versions, board/sketch version, exact command, and full error output.

## License
See `LICENSE`. Check third-party model and dataset terms separately.
