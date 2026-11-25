
/*
  AGRICULTURAL ROVER
  Controller: Arduino Uno
  Motor driver: L298N
  Sensors: 3 ultrasonic sensors
  Pump: 5V relay module on D4
  Communication: USB Serial at 9600 baud

  Raspberry Pi commands:
    MODE MANUAL
    MODE AUTO
    FWD
    BACK
    LEFT
    RIGHT
    STOP
    SPRAY ON
    SPRAY OFF
    ESTOP
    RESET
    HEARTBEAT
*/

// =====================================================
// 1. MOTOR DRIVER PINS - L298N
// =====================================================

#define ENA 9
#define IN1 8
#define IN2 7

#define ENB 10
#define IN3 6
#define IN4 5

// =====================================================
// 2. ULTRASONIC SENSOR PINS
// =====================================================

// Left sensor
#define LEFT_TRIG A0
#define LEFT_ECHO A3

// Front sensor
#define FRONT_TRIG A1
#define FRONT_ECHO A4

// Right sensor
#define RIGHT_TRIG A2
#define RIGHT_ECHO A5

// =====================================================
// 3. RELAY / PUMP
// =====================================================

#define RELAY_PIN 4

// Set true if LOW activates your relay.
// Set false if HIGH activates your relay.
#define RELAY_ACTIVE_LOW true

// =====================================================
// 4. CONFIGURATION
// =====================================================

const int MOTOR_SPEED = 160;
const int FRONT_THRESHOLD = 35;  // centimetres

const unsigned long TURN_DELAY = 600;
const unsigned long COMMUNICATION_TIMEOUT = 1500;
const unsigned long SENSOR_INTERVAL = 80;

// pulseIn timeout: approximately 4 metres maximum range
const unsigned long ULTRASONIC_TIMEOUT = 25000;

// =====================================================
// 5. ROVER STATE
// =====================================================

enum RoverMode {
  MANUAL_MODE,
  AUTO_MODE
};

enum Motion {
  STOPPED,
  FORWARD,
  BACKWARD,
  TURN_LEFT,
  TURN_RIGHT
};

enum AutoState {
  AUTO_DRIVE,
  AUTO_TURNING
};

RoverMode roverMode = MANUAL_MODE;
Motion currentMotion = STOPPED;
AutoState autoState = AUTO_DRIVE;

bool emergencyStop = false;
bool pumpRequested = false;
bool pumpIsOn = false;

unsigned long lastCommunication = 0;
unsigned long lastSensorRead = 0;
unsigned long turnStartTime = 0;

int leftDistance = 0;
int frontDistance = 0;
int rightDistance = 0;

// =====================================================
// 6. FUNCTION DECLARATIONS
// =====================================================

int readDistance(int trigPin, int echoPin);

void stopMotors();
void moveForward();
void moveBackward();
void turnLeft();
void turnRight();

void setPump(bool enabled);
void updatePump();
void readSensors();
void processCommand(String command);
void runAutoMode();
void stopEverything();

// =====================================================
// 7. SETUP
// =====================================================

void setup() {
  Serial.begin(9600);

  // Motor pins
  pinMode(ENA, OUTPUT);
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);

  pinMode(ENB, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);

  // Ultrasonic pins
  pinMode(LEFT_TRIG, OUTPUT);
  pinMode(LEFT_ECHO, INPUT);

  pinMode(FRONT_TRIG, OUTPUT);
  pinMode(FRONT_ECHO, INPUT);

  pinMode(RIGHT_TRIG, OUTPUT);
  pinMode(RIGHT_ECHO, INPUT);

  // Initialize relay to its OFF level
  digitalWrite(RELAY_PIN, RELAY_ACTIVE_LOW ? HIGH : LOW);
  pinMode(RELAY_PIN, OUTPUT);

  // Force motors and pump off at startup
  stopMotors();
  setPump(false);

  lastCommunication = millis();
  lastSensorRead = 0;

  Serial.println("ROVER_READY");
  Serial.println("Mode: MANUAL");
  Serial.println("Motors: STOPPED");
  Serial.println("Sprayer: OFF");
}

// =====================================================
// 8. MAIN LOOP
// =====================================================

void loop() {
  // Process all available serial commands first
  while (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    command.toUpperCase();

    if (command.length() > 0) {
      processCommand(command);
    }
  }

  // Communication watchdog
  if (millis() - lastCommunication > COMMUNICATION_TIMEOUT) {
    stopEverything();
    return;
  }

  // Emergency stop overrides all other actions
  if (emergencyStop) {
    stopEverything();
    return;
  }

  // Read sensors periodically
  if (millis() - lastSensorRead >= SENSOR_INTERVAL) {
    readSensors();
    lastSensorRead = millis();
  }

  // Execute automatic obstacle avoidance
  if (roverMode == AUTO_MODE) {
    runAutoMode();
  }

  // Pump safety is checked continuously
  updatePump();
}

// =====================================================
// 9. SERIAL COMMAND HANDLER
// =====================================================


void processCommand(String command) {
  command.trim();
  command.toUpperCase();

  // Accept the keyboard commands sent by rover_control.py
  if (command == "W") command = "FWD";
  else if (command == "S") command = "BACK";
  else if (command == "J") command = "LEFT";
  else if (command == "L") command = "RIGHT";
  else if (command == "X") command = "STOP";
  else if (command == "P") command = "SPRAY ON";
  else if (command == "O") command = "SPRAY OFF";
  else if (command == "M") command = "MODE MANUAL";
  else if (command == "A") command = "MODE AUTO";
  else if (command == "E") command = "ESTOP";
  else if (command == "R") command = "RESET";

  // Refresh communication watchdog
  lastCommunication = millis();

  if (command == "HEARTBEAT") {
    return;
  }

  if (command == "ESTOP") {
    emergencyStop = true;
    pumpRequested = false;
    stopEverything();
    Serial.println("ESTOP_ACTIVE");
    return;
  }

  if (command == "RESET") {
    emergencyStop = false;
    pumpRequested = false;
    stopEverything();
    lastCommunication = millis();
    Serial.println("ESTOP_RESET");
    return;
  }

  if (emergencyStop) {
    stopEverything();
    return;
  }

  if (command == "MODE MANUAL") {
    roverMode = MANUAL_MODE;
    pumpRequested = false;
    autoState = AUTO_DRIVE;
    stopEverything();
    Serial.println("MODE_MANUAL");
    return;
  }

  if (command == "MODE AUTO") {
    roverMode = AUTO_MODE;
    pumpRequested = false;
    autoState = AUTO_DRIVE;
    stopEverything();
    Serial.println("MODE_AUTO");
    return;
  }

  if (command == "STOP") {
    pumpRequested = false;
    stopEverything();
    Serial.println("STOPPED");
    return;
  }

  if (command == "SPRAY ON") {
    pumpRequested = true;
    setPump(true);
    Serial.println("PUMP_ON");
    return;
  }

  if (command == "SPRAY OFF") {
    pumpRequested = false;
    setPump(false);
    Serial.println("PUMP_OFF");
    return;
  }

  if (roverMode != MANUAL_MODE) {
    Serial.println("IGNORED_AUTO_MODE");
    return;
  }

  if (command == "FWD") {
    if (frontDistance == 0 ||
        frontDistance < FRONT_THRESHOLD) {
      stopMotors();
      pumpRequested = false;
      setPump(false);
      Serial.println("FRONT_BLOCKED");
    } else {
      moveForward();
      Serial.println("MOVING_FORWARD");
    }
    return;
  }

  if (command == "BACK") {
    setPump(false);
    moveBackward();
    Serial.println("MOVING_BACKWARD");
    return;
  }

  if (command == "LEFT") {
    setPump(false);
    turnLeft();
    Serial.println("TURNING_LEFT");
    return;
  }

  if (command == "RIGHT") {
    setPump(false);
    turnRight();
    Serial.println("TURNING_RIGHT");
    return;
  }

  Serial.print("UNKNOWN_COMMAND: ");
  Serial.println(command);
}


// =====================================================
// 10. MOTOR CONTROL
// =====================================================

void stopMotors() {
  analogWrite(ENA, 0);
  analogWrite(ENB, 0);

  digitalWrite(IN1, LOW);
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, LOW);

  currentMotion = STOPPED;
}

void moveForward() {
  digitalWrite(IN1, HIGH);
  digitalWrite(IN2, LOW);

  digitalWrite(IN3, HIGH);
  digitalWrite(IN4, LOW);

  analogWrite(ENA, MOTOR_SPEED);
  analogWrite(ENB, MOTOR_SPEED);

  currentMotion = FORWARD;
}

void moveBackward() {
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, HIGH);

  digitalWrite(IN3, LOW);
  digitalWrite(IN4, HIGH);

  analogWrite(ENA, MOTOR_SPEED);
  analogWrite(ENB, MOTOR_SPEED);

  currentMotion = BACKWARD;
}

void turnLeft() {
  // Left wheel backward, right wheel forward
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, HIGH);

  digitalWrite(IN3, HIGH);
  digitalWrite(IN4, LOW);

  analogWrite(ENA, MOTOR_SPEED);
  analogWrite(ENB, MOTOR_SPEED);

  currentMotion = TURN_LEFT;
}

void turnRight() {
  // Left wheel forward, right wheel backward
  digitalWrite(IN1, HIGH);
  digitalWrite(IN2, LOW);

  digitalWrite(IN3, LOW);
  digitalWrite(IN4, HIGH);

  analogWrite(ENA, MOTOR_SPEED);
  analogWrite(ENB, MOTOR_SPEED);

  currentMotion = TURN_RIGHT;
}

// =====================================================
// 11. ULTRASONIC DISTANCE
// =====================================================

int readDistance(int trigPin, int echoPin) {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(3);

  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  unsigned long duration =
      pulseIn(echoPin, HIGH, ULTRASONIC_TIMEOUT);

  // Zero means no valid echo was received
  if (duration == 0) {
    return 0;
  }

  int distance = duration / 58;

  if (distance < 2 || distance > 400) {
    return 0;
  }

  return distance;
}

void readSensors() {
  leftDistance = readDistance(LEFT_TRIG, LEFT_ECHO);
  frontDistance = readDistance(FRONT_TRIG, FRONT_ECHO);
  rightDistance = readDistance(RIGHT_TRIG, RIGHT_ECHO);
}

// =====================================================
// 12. AUTONOMOUS OBSTACLE AVOIDANCE
// =====================================================

void runAutoMode() {
  // During a turn, keep turning for the configured interval
  if (autoState == AUTO_TURNING) {
    setPump(false);

    if (millis() - turnStartTime >= TURN_DELAY) {
      autoState = AUTO_DRIVE;
      stopMotors();
    }

    return;
  }

  // Stop if front sensor is invalid or detects an obstacle
  if (frontDistance == 0 ||
      frontDistance < FRONT_THRESHOLD) {
    stopMotors();
    setPump(false);

    // Choose the side with more clearance.
    // An invalid side reading is treated as unknown,
    // not as proof that the path is clear.
    bool leftClear =
        leftDistance >= FRONT_THRESHOLD;

    bool rightClear =
        rightDistance >= FRONT_THRESHOLD;

    if (leftClear && rightClear) {
      if (leftDistance >= rightDistance) {
        turnLeft();
      } else {
        turnRight();
      }
    } else if (leftClear) {
      turnLeft();
    } else if (rightClear) {
      turnRight();
    } else {
      // Neither side has a confirmed safe clearance.
      stopMotors();
      return;
    }

    autoState = AUTO_TURNING;
    turnStartTime = millis();
    return;
  }

  // Path ahead is clear
  moveForward();
}

// =====================================================
// 13. RELAY CONTROL
// =====================================================

void setPump(bool enabled) {
  if (enabled == pumpIsOn) {
    return;
  }

  if (RELAY_ACTIVE_LOW) {
    digitalWrite(RELAY_PIN, enabled ? LOW : HIGH);
  } else {
    digitalWrite(RELAY_PIN, enabled ? HIGH : LOW);
  }

  pumpIsOn = enabled;

  if (enabled) {
    Serial.println("PUMP_ON");
  } else {
    Serial.println("PUMP_OFF");
  }
}

// =====================================================
// 14. PUMP SAFETY
// =====================================================


void updatePump() {
  bool communicationOK =
      (millis() - lastCommunication <= COMMUNICATION_TIMEOUT);

  // Pump must remain OFF during emergency stop
  // or if Raspberry Pi communication is lost.
  if (emergencyStop || !communicationOK) {
    pumpRequested = false;
    setPump(false);
    return;
  }

  // Manual and autonomous modes:
  // Pump depends only on the spray request,
  // emergency stop status, and communication health.
  if (pumpRequested) {
    setPump(true);
  } else {
    setPump(false);
  }
}


// =====================================================
// 15. STOP EVERYTHING
// =====================================================

void stopEverything() {
  stopMotors();
  setPump(false);
}
