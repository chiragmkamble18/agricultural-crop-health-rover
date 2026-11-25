# Installation

Fill in and verify these instructions against the exact Pi OS/Ubuntu image before release.

1. Install and update the supported Raspberry Pi OS/Ubuntu image.
2. Enable and test the camera with the camera tools for that OS.
3. Connect the Arduino by USB and identify its serial device (often `/dev/ttyACM0`, but it can vary).
4. Set up serial-port permissions for the Pi user if needed.
5. Copy the tested controller and helper scripts into `raspberry_pi/`.
6. Create a clean Python virtual environment and install the reviewed dependency versions.
7. Place `Crop.pt` in `models/` only if redistribution is permitted; otherwise follow `models/README.md`.
8. Open the Arduino sketch from `arduino/` in Arduino IDE on your laptop, select Arduino Uno and the correct port, then upload.

The previously tested Pi setup ran `rover_control.py` from `~/yolo` in a `yolo-cpu` environment. That source is not in this starter, so add it and confirm the final run command before publishing.
