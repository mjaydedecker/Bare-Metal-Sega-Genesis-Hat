# GPIO Pin Reassignment for Zero-Crossing Routing

**Date:** 2026-07-22
**Status:** Implemented (firmware repo + this HAT repo)

## Background

The original GPIO pin assignment (Port 1 = GPIO4/5/6/7/8/9/10, Port 2 =
GPIO11/12/13/16/17/22/23, from the firmware repo's
`docs/superpowers/specs/2026-06-25-gpio-sega-controllers-design.md`) was
fixed before this HAT's PCB was laid out. Routing J2/J3 to that assignment
left `kicad-cli pcb drc` reporting 14 `tracks_crossing` violations (same-
layer shorts between different nets) that a scripted greedy two-layer router
could not eliminate, on top of a smaller set of pad-clearance issues.

## Root cause

`tracks_crossing` is not a routing-algorithm limitation — it's a consequence
of *which* GPIOs were assigned to which port. The Raspberry Pi's 40-pin
header has a fixed physical column order (BCM numbering does not follow
header position). Mapping the original assignment onto physical header
columns shows each port's 7 signals scattered across non-adjacent columns,
interleaved with the other port's signals and with reserved pins (I2S,
UART, I2C, EEPROM):

```
Port 1: GPIO4, 5, 6, 7, 8, 9, 10   -> interleaved with Port 2's columns
Port 2: GPIO11, 12, 13, 16, 17, 22, 23 -> interleaved with Port 1's columns
```

Since J2 (Port 1) and J3 (Port 2) sit at opposite ends of the board, and
each port's breakout tracks must reach across the header to their assigned
columns, an interleaved assignment forces Port 1's and Port 2's tracks to
physically cross each other en route — regardless of routing cleverness.

This was confirmed with a graph-theoretic analysis: model each net's
breakout path as a line segment from its connector pad to its target header
column, and build a conflict graph where two nets conflict if their segments
must cross. The original assignment's conflict graph was **not**
2-colorable across the two PCB layers (F.Cu/B.Cu) without at least 12-14
residual same-layer crossings — consistent with what DRC observed.

## Reassignment

The new assignment groups each port's 7 signals (1 SELECT + 6 data) onto
physically adjacent header columns, on the side of the header nearest that
port's own DB9 connector (Port 1 -> lower-numbered columns/nearer J2, Port 2
-> higher-numbered columns/nearer J3):

| Signal               | DB9 pin | Port 1 (J2) | Port 2 (J3) |
|-----------------------|---------|-------------|-------------|
| SELECT (output)       | 7       | GPIO22      | GPIO12      |
| D0 -- Up              | 1       | GPIO10      | GPIO26      |
| D1 -- Down             | 2       | GPIO23      | GPIO13      |
| D2 -- Left            | 3       | GPIO27      | GPIO6       |
| D3 -- Right           | 4       | GPIO17      | GPIO5       |
| D4 -- TL (B / A)      | 6       | GPIO24      | GPIO16      |
| D5 -- TR (C / Start)  | 9       | GPIO4       | GPIO7       |

Reservations (I2S GPIO18-21, UART GPIO14/15, I2C GPIO2/3, HAT EEPROM
GPIO0/1) are unchanged — only which *available* pins are used, and by which
port, changed. The available-but-unused set shifted from GPIO24-27 to
GPIO8/9/11/25.

Rebuilding the same conflict-graph analysis against this assignment found
exactly **one** crossing pair, and the resulting graph is fully
2-colorable — i.e. a 2-layer assignment exists with **zero** same-layer
crossings.

## Result

| DRC category         | Before (old assignment) | After (new assignment) |
|-----------------------|:---:|:---:|
| `tracks_crossing`     | 14  | **0** |
| `hole_clearance`      | 4   | **0** |
| `shorting_items`      | 2   | 6   |
| `copper_edge_clearance` | 2 | 2   |
| `silk_edge_clearance` | 5   | 5   |
| `solder_mask_bridge`  | 6   | 6   |
| `unconnected_items`   | 2   | 2   |
| `lib_footprint_mismatch` | 1 | 1  |
| **Total errors/warnings** | 30 / 6 | **16 / 6** |

The reassignment achieved its goal: zero same-layer trace crossings and
zero hole-clearance violations. `shorting_items` rose from 2 to 6 — these
are cases where a diagonal breakout track, now free of other tracks, grazes
an unrelated J1 pad along its path. This is a smaller, more tractable
problem than the crossings it replaced: each is a single trace needing a
small manual jog in the KiCad GUI, not a fundamental routing conflict
requiring a different pin assignment or connector placement. All other
categories are unchanged, pre-existing conditions (see this repo's
`README.md` "Known limitation" sections for the itemized breakdown).

## Changes made

- Firmware repo (`Bare-Metal-Sega-Genesis`): `src/input/sega_board.h`
  (`kBoardPinMap`), `test/test_sega_board.cpp` (updated assertions),
  `docs/superpowers/specs/2026-06-25-gpio-sega-controllers-design.md` (pin
  table + reservations list).
- This repo: `genesis-controller-hat.kicad_sch` (J2/J3 rewired),
  `genesis-controller-hat.kicad_pcb` (J2/J3 re-placed and re-routed, ground
  plane re-filled), `docs/superpowers/specs/2026-07-21-controller-hat-v1-design.md`,
  `README.md`.
- `.github/workflows/verify-pinmap.yml` + `scripts/check_pinmap.py` (added
  separately) now catch any future drift between the two repos' pin maps
  automatically, on every push.
