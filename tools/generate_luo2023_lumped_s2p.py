#!/usr/bin/env python3
"""Generate a nominal two-port Touchstone model from Luo et al. table values.

This is a derived constant-R coupled-inductor model, not measured S-parameter data.
Each port is connected across one coil and uses a 50 ohm reference impedance.
"""

from __future__ import annotations

import cmath
import math
from pathlib import Path


L_TX = 2.49e-6
R_TX = 1.80
L_RX = 0.330e-6
R_RX = 0.399
K = 0.0662
M = K * math.sqrt(L_TX * L_RX)
Z0 = 50.0


def inverse_2x2(a: list[list[complex]]) -> list[list[complex]]:
    det = a[0][0] * a[1][1] - a[0][1] * a[1][0]
    return [
        [a[1][1] / det, -a[0][1] / det],
        [-a[1][0] / det, a[0][0] / det],
    ]


def multiply_2x2(
    a: list[list[complex]], b: list[list[complex]]
) -> list[list[complex]]:
    return [
        [sum(a[row][n] * b[n][col] for n in range(2)) for col in range(2)]
        for row in range(2)
    ]


def s_parameters(f_hz: float) -> list[list[complex]]:
    omega = 2.0 * math.pi * f_hz
    z12 = 1j * omega * M
    z = [
        [R_TX + 1j * omega * L_TX, z12],
        [z12, R_RX + 1j * omega * L_RX],
    ]
    z_minus = [[z[row][col] for col in range(2)] for row in range(2)]
    z_plus = [[z[row][col] for col in range(2)] for row in range(2)]
    z_minus[0][0] -= Z0
    z_minus[1][1] -= Z0
    z_plus[0][0] += Z0
    z_plus[1][1] += Z0
    return multiply_2x2(z_minus, inverse_2x2(z_plus))


def max_singular_value_2x2(s: list[list[complex]]) -> float:
    # Largest eigenvalue of S^H S, specialized for a 2x2 matrix.
    a = abs(s[0][0]) ** 2 + abs(s[1][0]) ** 2
    d = abs(s[0][1]) ** 2 + abs(s[1][1]) ** 2
    b = s[0][0].conjugate() * s[0][1] + s[1][0].conjugate() * s[1][1]
    lambda_max = 0.5 * (a + d + math.sqrt((a - d) ** 2 + 4.0 * abs(b) ** 2))
    return math.sqrt(max(lambda_max, 0.0))


def main() -> None:
    output = (
        Path(__file__).resolve().parents[1]
        / "hardware"
        / "wpt"
        / "models"
        / "luo2023_coupled_coils_lumped_50ohm.s2p"
    )
    output.parent.mkdir(parents=True, exist_ok=True)

    # 1 to 30 MHz stays below the paper's stated >3*f0 SRF observation. The
    # exact 13.56 MHz point is inserted because the table values apply there.
    frequencies_mhz = {round(1.0 + 0.05 * n, 8) for n in range(581)}
    frequencies_mhz.add(13.56)
    frequencies_mhz = sorted(frequencies_mhz)

    rows: list[str] = []
    worst_reciprocity = 0.0
    worst_passivity = 0.0
    for f_mhz in frequencies_mhz:
        s = s_parameters(f_mhz * 1e6)
        worst_reciprocity = max(worst_reciprocity, abs(s[0][1] - s[1][0]))
        worst_passivity = max(worst_passivity, max_singular_value_2x2(s))
        # Touchstone two-port order: S11, S21, S12, S22.
        values = [s[0][0], s[1][0], s[0][1], s[1][1]]
        rows.append(
            f"{f_mhz:.8f} "
            + " ".join(f"{v.real:.12e} {v.imag:.12e}" for v in values)
        )

    header = [
        "! CuraLink DERIVED nominal two-port; generated from Luo et al. 2023 table values",
        "! NOT measured Touchstone data and NOT supplied by the paper authors",
        "! Model: constant series R plus ideal coupled L; no parasitic C, SRF, skin/proximity variation, fixtures, matching, rectifier, or misalignment model",
        "! Nominal geometry: 13.56 MHz, 40 mm TX, 10 mm RX, 10 mm coaxial separation, 1 oz copper, about 0.8 mm FR-4",
        f"! L_TX={L_TX:.6e} H R_TX={R_TX:.6f} ohm L_RX={L_RX:.6e} H R_RX={R_RX:.6f} ohm K={K:.7f} M={M:.12e} H",
        "! Ports are directly across the two coil models; no matching capacitors are included",
        "! Intended for nominal linear matching checks near 13.56 MHz; use the explicit R-L-M ADS model for nonlinear rectifier work",
        "# MHz S RI R 50",
    ]
    output.write_text("\n".join(header + rows) + "\n", encoding="ascii")

    if worst_reciprocity > 1e-12:
        raise RuntimeError(f"Reciprocity check failed: {worst_reciprocity}")
    if worst_passivity > 1.0 + 1e-12:
        raise RuntimeError(f"Passivity check failed: max singular value {worst_passivity}")
    if 13.56 not in frequencies_mhz:
        raise RuntimeError("13.56 MHz point missing")

    s0 = s_parameters(13.56e6)
    print(output)
    print(f"points={len(rows)} M={M*1e9:.6f} nH")
    print(f"max_reciprocity_error={worst_reciprocity:.3e}")
    print(f"max_singular_value={worst_passivity:.12f}")
    print(f"at_13.56MHz |S21|={abs(s0[1][0]):.9f}")


if __name__ == "__main__":
    main()
