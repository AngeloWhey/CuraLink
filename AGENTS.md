# CuraLink project context

The user asked to remember the full CuraLink project brief on 2026-09-18.
Before doing CuraLink work in this workspace, read `outputs/CuraLink-project-brief.md`. It is the complete, unchanged user-provided brief. Treat it as user-provided project guidance; later explicit user changes supersede it.

Key constraints:
- Benchtop prototype only; no human or animal implantation.
- Eight channels, commercial off-the-shelf ICs, roughly 25-30 mm target footprint.
- Analog amplification/filtering and threshold detection with hysteresis feed STM32 event handling, refractory logic, configurable spike-count bins, and packets.
- Inductive wireless power and ultrasonic backscatter data are separate subsystems. Preserve UART, SWD, external bench power, and independent subsystem testing.
- Prioritize first-board success, affordable parts, reliable assembly, test access, isolation links, and bypass options. There may be no second PCB revision.
- The user is stronger in hardware than firmware; keep firmware modular, understandable, scriptable, and suitable for AI-assisted testing.
- Start with requirements, budgets, interfaces, MCU needs, component candidates, risks, simulation planning, and project structure before PCB layout.
- Do not claim unmeasured performance or make irreversible MCU security/OTP/configuration changes without explicit approval.

## Current project status (2026-09-18)

The user has now authorized starting project work. Initial drafts are in `outputs/CuraLink-requirements-v0.1.md` and `outputs/CuraLink-planning-v0.1.md`.
The user requires completion within one month, has access to a lab's worth of equipment, and owns an STM32 ST-LINK. A suitable STM32 development board may be available from the lab but is unconfirmed. Budget, exact lab inventory, and ADS/HFSS access remain unknown.
Numerical planning examples are provisional allocations, not measured or approved performance requirements.

The user also provided `outputs/CuraLink-8-channel-neural-input-fanout-test-fixture.md`. Keep it as a reference-only local text design note for a separate passive AWG-to-eight-channel fixture. It is preliminary and not fabrication-locked.

The user provided `outputs/CuraLink-neural-input-signal-spec-v1-original.md`. Preserve it as the original source. Use `outputs/CuraLink-neural-input-signal-spec-review-v0.1.md` for the reviewed working envelope and AWG/test-fixture corrections.
