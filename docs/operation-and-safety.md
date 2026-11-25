# Operation and safety

## Before testing
- Stabilize the rover; raise wheels or disconnect motor power for initial tests.
- Keep pump OFF while checking motor direction.
- Use water for initial pump tests and aim at a safe target.
- Keep hands, clothing, and cables away from moving wheels.
- Confirm the emergency stop and physical power disconnect.

## Suggested test order
1. Arduino startup and serial communication.
2. STOP and emergency stop.
3. Motor directions with wheels raised.
4. Ultrasonic readings and obstacle avoidance at low speed.
5. Relay switching with pump disconnected.
6. Pump with water.
7. Disease-triggered spray with a controlled sample.
8. Integrated operation in a clear test area.

Software emergency stop alone cannot guarantee electrical isolation.
