# CuraLink

Eight-channel benchtop neural acquisition prototype with a custom analog front end, analog spike detection, MCU event counting, BLE telemetry, and battery-buffered wireless charging. The current design direction removes waveform ADC acquisition.

Start with the [Engineering Handbook](docs/engineering-handbook.md) for current requirements, design decisions, rationale, verification needs, and open work.

Project assistants maintain that record under [AGENTS.md](AGENTS.md).

Current study: [two-board stimulus and analog-event AFE design](docs/design/2026-09-22-two-board-analog-afe.md). The selected working controller is STM32WBA52 with its waveform ADC unused; AFE component values remain provisional.
