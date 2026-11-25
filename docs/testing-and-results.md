# Testing and results

Keep raw data separate from processed summaries. For each test record date, test ID, hardware revision, OS/Python versions, model checksum, image size, confidence threshold, trial count, raw measurements, units, and notes.

## Keep timing definitions separate
- **Inference time:** model forward pass.
- **Detection pipeline time:** image acquisition/preprocessing through final detection.
- **Software detection-to-serial latency:** decision to serial write/flush.
- **Physical actuator response:** command to physical relay/pump response, measured independently.

Do not describe serial-write latency as physical pump response. Report trial count and explain any excluded samples.
