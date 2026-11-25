#!/usr/bin/env python3

import subprocess
import os
import time
import threading
import queue
import csv
import serial
import cv2
import numpy as np

from ultralytics import YOLO


# =========================================================
# CONFIGURATION
# =========================================================

MODEL_PATH = "/home/major_project/yolo/Crop.pt"
ARDUINO_PORT = "/dev/ttyACM0"
BAUD_RATE = 9600

CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_FPS = 5

IMAGE_SIZE = 320
CONFIDENCE_THRESHOLD = 0.40

WINDOW_NAME = "Agricultural Rover - Crop Monitoring"

HEARTBEAT_INTERVAL = 0.4

CLASS_STATUS = {
    "Bacterial Spot": "Potentially affected",
    "Cercospora Leaf Spot": "Potentially affected",
    "Curl Virus": "Potentially affected",
    "Healthy Leaf": "Healthy",
    "Nutrition Deficiency": "Potentially affected",
    "White spot": "Potentially affected",
}

# AUTOMATIC DISEASE SPRAY + T2 SOFTWARE TIMING
DISEASE_CLASSES = {
    "Bacterial Spot",
    "Cercospora Leaf Spot",
    "Curl Virus",
    "Nutrition Deficiency",
    "White spot",
}
AUTO_SPRAY_ENABLED = True
SPRAY_PULSE_SECONDS = 1.0
DISEASE_CLEAR_SECONDS = 2.0
T2_LOG_PATH = "/home/major_project/yolo/t2_timing.csv"


# =========================================================
# SERIAL COMMUNICATION
# =========================================================

class ArduinoController:

    def __init__(self, port, baudrate):

        self.serial_port = serial.Serial(
            port,
            baudrate,
            timeout=0.05,
            write_timeout=0.5
        )

        # Arduino Uno normally resets when serial opens.
        time.sleep(2)

        self.serial_port.reset_input_buffer()

        self.lock = threading.Lock()
        self.connected = True

        self.mode = "MANUAL"
        self.motion = "STOP"
        self.spraying = False

        self.last_heartbeat = 0

        self.responses = queue.Queue()

        self.reader_thread = threading.Thread(
            target=self._read_responses,
            daemon=True
        )

        self.reader_thread.start()

        self.send("STOP")
        print("Arduino serial connection established.")

    def send(self, command):

        if not self.connected:
            return None

        try:
            with self.lock:
                self.serial_port.write(
                    (command + "\n").encode("ascii")
                )
                self.serial_port.flush()

            # Timestamp after command is written/flushed.
            return time.perf_counter()

        except (serial.SerialException, OSError) as exc:
            self.connected = False
            self.spraying = False
            print("Arduino communication error:", exc)
            return None

    def _read_responses(self):
        while self.connected:
            try:
                line = self.serial_port.readline()

                if line:
                    message = line.decode(
                        "utf-8",
                        errors="replace"
                    ).strip()

                    if message:
                        self.responses.put(message)

            except (
                serial.SerialException,
                OSError,
                TypeError,
                ValueError
            ):
                break

    def show_responses(self):

        while True:
            try:
                message = self.responses.get_nowait()
                print("Arduino:", message)
            except queue.Empty:
                break

    def heartbeat(self):

        now = time.monotonic()

        if now - self.last_heartbeat >= HEARTBEAT_INTERVAL:

            self.send("HEARTBEAT")
            self.last_heartbeat = now

    def set_mode(self, mode):

        if mode not in ("MANUAL", "AUTO"):
            return

        self.send("STOP")
        self.send("MODE " + mode)

        self.mode = mode
        self.motion = "STOP"
        self.spraying = False

        self.send("SPRAY OFF")

        print("Mode selected:", mode)

    def move(self, command):

        if self.mode != "MANUAL":
            print("Movement keys require MANUAL mode.")
            return

        if command not in (
            "FWD",
            "BACK",
            "LEFT",
            "RIGHT",
            "STOP"
        ):
            return

        # Send STOP when releasing or changing movement.
        # Avoid unnecessary duplicate commands.
        if command != self.motion:

            self.send(command)
            self.motion = command

            if command == "STOP":
                self.spraying = False
                self.send("SPRAY OFF")

    def spray_on(self):

        if not self.connected:
            print("Cannot spray: Arduino disconnected.")
            return None

        command_sent_at = self.send("SPRAY ON")

        if command_sent_at is not None:
            self.spraying = True
            print("Spray requested.")
            return command_sent_at

        self.spraying = False
        return None

    def spray_off(self):

        self.send("SPRAY OFF")
        self.spraying = False

        print("Sprayer OFF.")

    def emergency_stop(self):

        self.send("ESTOP")

        self.motion = "STOP"
        self.spraying = False

        print("EMERGENCY STOP ACTIVATED.")

    def reset_emergency_stop(self):

        self.send("RESET")

        self.motion = "STOP"
        self.spraying = False

        print("Emergency stop reset. Rover remains stopped.")

    def close(self):

        if self.connected:

            try:
                self.send("STOP")
                self.send("SPRAY OFF")
                self.send("HEARTBEAT")
                time.sleep(0.1)

                self.serial_port.close()

            except Exception as exc:
                print("Serial shutdown warning:", exc)

        self.connected = False


# =========================================================
# CAMERA STREAM
# =========================================================

def start_camera():

    print("Starting Raspberry Pi camera...")

    camera = subprocess.Popen(
        [
            "rpicam-vid",
            "-t", "0",
            "--width", str(CAMERA_WIDTH),
            "--height", str(CAMERA_HEIGHT),
            "--framerate", str(CAMERA_FPS),
            "--codec", "mjpeg",
            "-o", "-"
        ],
        stdout=subprocess.PIPE,
        stderr=None,
        bufsize=0
    )

    if camera.stdout is None:
        camera.terminate()
        raise RuntimeError("Could not open camera stream.")

    return camera


def get_latest_frame(camera, buffer):

    chunk = camera.stdout.read(4096)

    if not chunk:
        return None

    buffer.extend(chunk)

    latest_frame = None

    while True:

        start = buffer.find(b"\xff\xd8")

        if start < 0:

            if len(buffer) > 1:

                if buffer[-1] == 0xFF:
                    buffer[:] = buffer[-1:]
                else:
                    buffer.clear()

            break

        if start > 0:
            del buffer[:start]

        end = buffer.find(b"\xff\xd9", 2)

        if end < 0:
            break

        latest_frame = bytes(buffer[:end + 2])
        del buffer[:end + 2]

    if latest_frame is None:
        return None

    return cv2.imdecode(
        np.frombuffer(latest_frame, dtype=np.uint8),
        cv2.IMREAD_COLOR
    )


# =========================================================
# USER INTERFACE
# =========================================================

def draw_panel(
    image,
    class_name,
    confidence,
    status,
    fps,
    controller
):

    panel = image.copy()

    cv2.rectangle(
        panel,
        (10, 10),
        (460, 275),
        (0, 0, 0),
        -1
    )

    image = cv2.addWeighted(
        panel, 0.70,
        image, 0.30,
        0
    )

    lines = [
        ("AGRICULTURAL ROVER", (255, 255, 255)),
        (f"Mode: {controller.mode}", (0, 255, 255)),
        (f"Prediction: {class_name}", (255, 255, 255)),
        (f"Confidence: {confidence:.1f}%", (255, 255, 255)),
        (f"Crop status: {status}", (0, 255, 0)
         if status == "Healthy" else (0, 0, 255)),
        (f"FPS: {fps:.1f}", (255, 255, 0)),
        (f"Motion: {controller.motion}", (255, 255, 255)),
        (f"Sprayer request: {'ON' if controller.spraying else 'OFF'}",
         (0, 200, 255)),
    ]

    y = 35

    for text, color in lines:

        cv2.putText(
            image,
            text,
            (20, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.52,
            color,
            1,
            cv2.LINE_AA
        )

        y += 30

    return image


# =========================================================
# KEYBOARD HELP
# =========================================================

def show_controls():

    print("\n" + "=" * 55)
    print("AGRICULTURAL ROVER CONTROL")
    print("=" * 55)

    print("M : Manual mode")
    print("A : Autonomous obstacle-avoidance mode")
    print("W : Forward")
    print("S : Backward")
    print("J : Turn left")
    print("L : Turn right")
    print("X : Stop")
    print("P : Request sprayer ON")
    print("O : Sprayer OFF")
    print("E : Emergency stop")
    print("R : Reset software emergency stop")
    print("Q : Quit program")
    print()
    print("Automatic disease-triggered spraying: ENABLED.")
    print(f"Automatic spray pulse: {SPRAY_PULSE_SECONDS:.1f} s")
    print("Sprayer requests are subject to Arduino safety checks.")
    print("=" * 55 + "\n")


# =========================================================
# T2 LOGGING
# =========================================================

def log_t2_trial(detected_class, confidence_pct, detection_time, command_time):
    """Log detection-to-serial-command latency (not physical relay timing)."""
    delay_ms = (command_time - detection_time) * 1000.0
    file_exists = os.path.exists(T2_LOG_PATH)

    with open(T2_LOG_PATH, "a", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)

        if not file_exists:
            writer.writerow([
                "unix_timestamp",
                "detected_class",
                "confidence_percent",
                "detection_to_serial_command_ms"
            ])

        writer.writerow([
            f"{time.time():.3f}",
            detected_class,
            f"{confidence_pct:.2f}",
            f"{delay_ms:.3f}"
        ])

    return delay_ms


# =========================================================
# MAIN PROGRAM
# =========================================================

def main():

    controller = None
    camera = None

    try:

        # Load YOLO model
        print("Loading Crop.pt model...")

        model = YOLO(MODEL_PATH)

        print("Model loaded:", model.names)

        # Connect Arduino
        print("Connecting to Arduino...")

        controller = ArduinoController(
            ARDUINO_PORT,
            BAUD_RATE
        )

        # Start camera
        camera = start_camera()

        show_controls()
        print("T2 software timing log:", T2_LOG_PATH)

        buffer = bytearray()

        last_class = "No detection"
        last_confidence = 0.0
        last_status = "Waiting for leaf"

        auto_spray_active = False
        auto_spray_started = 0.0
        disease_latched = False
        last_disease_time = 0.0

        fps = 0.0
        previous_time = time.perf_counter()

        while True:

            # Keep Arduino watchdog alive.
            controller.heartbeat()
            controller.show_responses()

            frame = get_latest_frame(camera, buffer)

            if frame is None:
                if camera.poll() is not None:
                    print("Camera process stopped.")
                    break

                continue

            # Run YOLO on CPU.
            results = model.predict(
                source=frame,
                device="cpu",
                imgsz=IMAGE_SIZE,
                conf=CONFIDENCE_THRESHOLD,
                verbose=False
            )

            result = results[0]
            annotated = result.plot()
            detection_time = time.perf_counter()

            if result.boxes is not None and len(result.boxes) > 0:

                best_index = int(
                    result.boxes.conf.argmax().item()
                )

                class_id = int(
                    result.boxes.cls[best_index].item()
                )

                last_confidence = (
                    float(result.boxes.conf[best_index].item())
                    * 100
                )

                last_class = model.names[class_id]

                last_status = CLASS_STATUS.get(
                    last_class,
                    "Unclassified"
                )

            else:

                last_class = "No detection"
                last_confidence = 0.0
                last_status = "No confident detection"

            # AUTOMATIC DISEASE DETECTION AND SPRAY CONTROL
            spray_time = time.monotonic()

            diseased_detected = (
                last_class in DISEASE_CLASSES
                and last_confidence >= CONFIDENCE_THRESHOLD * 100
            )

            if diseased_detected:
                last_disease_time = spray_time

                # One spray pulse per detection episode.
                if AUTO_SPRAY_ENABLED and not disease_latched:
                    print(
                        f"AUTO SPRAY: {last_class} "
                        f"({last_confidence:.1f}%)"
                    )

                    command_time = controller.spray_on()

                    if command_time is not None:
                        auto_spray_active = True
                        auto_spray_started = spray_time
                        disease_latched = True

                        t2_ms = log_t2_trial(
                            last_class,
                            last_confidence,
                            detection_time,
                            command_time
                        )

                        print(
                            "T2 software detection-to-serial-command: "
                            f"{t2_ms:.2f} ms"
                        )

            elif disease_latched:
                if (
                    spray_time - last_disease_time
                    >= DISEASE_CLEAR_SECONDS
                ):
                    disease_latched = False
                    print("Disease detection cleared. Spray rearmed.")

            # Stop automatic pump pulse after configured duration.
            if auto_spray_active:
                if (
                    spray_time - auto_spray_started
                    >= SPRAY_PULSE_SECONDS
                ):
                    controller.spray_off()
                    auto_spray_active = False
                    print("AUTO SPRAY: Pump switched OFF.")

            now = time.perf_counter()
            elapsed = now - previous_time
            previous_time = now

            if elapsed > 0:

                instant_fps = 1.0 / elapsed

                if fps == 0:
                    fps = instant_fps
                else:
                    fps = 0.8 * fps + 0.2 * instant_fps

            display = draw_panel(
                annotated,
                last_class,
                last_confidence,
                last_status,
                fps,
                controller
            )

            cv2.imshow(WINDOW_NAME, display)

            key = cv2.waitKey(1) & 0xFF

            # -------------------------------------------------
            # KEY COMMANDS
            # -------------------------------------------------

            if key == ord("m"):

                controller.set_mode("MANUAL")

            elif key == ord("a"):

                controller.set_mode("AUTO")

            elif key == ord("w"):

                controller.move("FWD")

            elif key == ord("s"):

                controller.move("BACK")

            elif key == ord("j"):

                controller.move("LEFT")

            elif key == ord("l"):

                controller.move("RIGHT")

            elif key == ord("x"):

                controller.move("STOP")

            elif key == ord("p"):

                controller.spray_on()

            elif key == ord("o"):

                controller.spray_off()

            elif key == ord("e"):

                controller.emergency_stop()

            elif key == ord("r"):

                controller.reset_emergency_stop()

            elif key == ord("q"):

                break

    except KeyboardInterrupt:

        print("\nShutdown requested.")

    finally:

        # Stop motion and spraying before closing.
        if controller is not None:

            try:
                controller.emergency_stop()
                time.sleep(0.1)
                controller.close()

            except Exception as exc:
                print("Controller shutdown warning:", exc)

        if camera is not None:

            if camera.poll() is None:
                camera.terminate()

            try:
                camera.wait(timeout=3)
            except subprocess.TimeoutExpired:
                camera.kill()
                camera.wait()

            if camera.stdout is not None:
                camera.stdout.close()

        cv2.destroyAllWindows()

        print("Rover controller stopped.")


if __name__ == "__main__":
    main()