# Hardware and wiring

Verify this pin plan against the actual rover wiring before powering it.

| Device | Arduino Uno pin |
|---|---|
| L298N ENA | D9 |
| L298N IN1 | D8 |
| L298N IN2 | D7 |
| L298N ENB | D10 |
| L298N IN3 | D6 |
| L298N IN4 | D5 |
| Left ultrasonic TRIG/ECHO | A0/A3 |
| Front ultrasonic TRIG/ECHO | A1/A4 |
| Right ultrasonic TRIG/ECHO | A2/A5 |
| Pump relay control (reported setup) | D4 |

These are the project’s previously used assignments, not a substitute for checking your wiring.

## Electrical safety
- Never power motors or pump from Arduino GPIO/5V.
- Use properly rated motor driver and pump relay/MOSFET driver.
- Verify relay active-high/active-low behavior and contact wiring.
- Check ultrasonic echo voltage compatibility.
- Use suitable fuses, wire gauge, common signal ground where required, and a physical power disconnect.
- Add a reviewed circuit diagram before public release.
