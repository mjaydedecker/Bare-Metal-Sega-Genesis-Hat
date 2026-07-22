# Sega Genesis Controller HAT v1 — Design

**Date:** 2026-07-21
**Status:** Design (approved, pending implementation plan)

## Goal

A passive Raspberry Pi add-on board ("HAT") that exposes two female DB9 (DE-9)
ports for original Sega Genesis / Mega Drive controllers, wired directly to the
Pi's 40-pin GPIO header per the electrical contract and pin assignment already
defined in the firmware repo (`Bare-Metal-Sega-Genesis`, `src/input/sega_board.h`
and `docs/superpowers/specs/2026-06-25-gpio-sega-controllers-design.md`).

This project owns the physical board only. It has no firmware of its own — the
kernel repo is agnostic to this board via its `BoardPinMap` abstraction, so this
design's only job is to match that contract exactly.

## Scope decisions

- **Not officially HAT-spec certified.** No ID EEPROM (GPIO0/1 stay unpopulated
  and unconnected). This is a bare-metal kernel with no Linux/device-tree, so
  EEPROM auto-config has no consumer. GPIO0/1 are kept clear per the firmware
  doc's reservation, simply left unused rather than wired to an EEPROM.
- **Board outline:** Standard full-size HAT footprint, 65×56.5mm. Originally
  4 mounting holes matching the Pi 2/3/4B hole pattern (the firmware doc's
  `BoardPinMap` comment targets "Pi 2, 40-pin header, BCM numbering");
  **updated 2026-07-22:** the bottom two (`MH3`/`MH4`) were removed after
  the edge-mount DB9 connectors' brackets made them physically unusable —
  see "Components" below and the HAT repo's `README.md`. This board mounts
  on the remaining 2 top corner holes plus the GPIO header's friction fit,
  and no longer meets the official HAT spec's 4-hole requirement (already
  not pursuing certification, per above).
- **No electrical protection.** Data/SELECT lines wire straight from the DB9
  sockets to GPIO with no series resistors, no TVS/ESD diodes, no polyfuse on
  the 3.3V rail. This mirrors the firmware spec's documented contract exactly
  (it explicitly rules out level shifters, dividers, and shift registers, and
  relies on the Pi's internal `GPIOModeInputPullUp` pull-ups). Trade-off
  accepted: a shorted or miswired third-party DB9 cable could damage a GPIO pin
  — the same risk already accepted for the firmware team's bring-up jumper
  harness.
- **No stacking.** Plain 2×20 female GPIO header (J1), not a pass-through
  stacking header — nothing else is expected to stack on top of this HAT.
- **No extras.** No status LEDs, no use of the spare GPIO24-27 pins the
  firmware doc reserves for "future use." Bare minimum: 2 ports + header only.
- **EDA tool:** KiCad.

## Components

- **J1** — 2×20 female header, standard 0.1" pitch, plain (non-stacking),
  positioned to mate with the Pi's 40-pin GPIO header.
- **J2** — DB9 (DE-9) female socket, right-angle/edge-mount, Player 1.
- **J3** — DB9 (DE-9) female socket, right-angle/edge-mount, Player 2.
- J2 and J3 sit side-by-side along the board's bottom edge, opposite the GPIO
  header side, with their shells overhanging the board edge (9.12mm) so
  controller cables plug in horizontally at the board's edge, console-style.
  **Updated 2026-07-22:** switched from a vertical-mount footprint (opening
  faces straight up, cable plugs in from above) to this edge-mount one. The
  edge-mount connector's wider mounting bracket didn't fully clear the
  board's corner mounting holes at this board width, so the two affected
  holes (`MH3`/`MH4`) were removed — see the HAT repo's `README.md` "Known
  limitation: only 2 of the 4 official corner mounting holes remain".
- No other active or passive components (no resistors, diodes, LEDs, EEPROM,
  or fuses).

## Pin map (authoritative source: firmware repo's `sega_board.h`)

**Updated 2026-07-22:** reassigned from the original table below (Port 1 =
GPIO4/5/6/7/8/9/10, Port 2 = GPIO11/12/13/16/17/22/23) to eliminate PCB
routing crossings — the original assignment interleaved each port's 7
signals across non-adjacent GPIO header columns. The new assignment groups
each port's signals onto physically adjacent header columns, nearest that
port's DB9 connector, which lets this board route both ports with zero
same-layer trace crossings. See `docs/reviews/2026-07-22-pinmap-reassignment.md`
for the full analysis.

BCM numbering, Pi 40-pin header:

| DB9 pin | Signal              | Port 1 (J2) | Port 2 (J3) |
|---------|---------------------|-------------|-------------|
| 1       | Up                  | GPIO10      | GPIO26      |
| 2       | Down                | GPIO23      | GPIO13      |
| 3       | Left                | GPIO27      | GPIO6       |
| 4       | Right               | GPIO17      | GPIO5       |
| 5       | +3.3V (NOT 5V)      | Pi 3.3V rail| Pi 3.3V rail|
| 6       | TL (B / A)          | GPIO24      | GPIO16      |
| 7       | SELECT (output)     | GPIO22      | GPIO12      |
| 8       | GND                 | GND         | GND         |
| 9       | TR (C / Start)      | GPIO4       | GPIO7       |

**Do not connect / leave unpopulated:**
- GPIO0/1 — reserved for HAT ID EEPROM by the firmware doc; unused here since
  there is no EEPROM on this board.
- GPIO2/3 — reserved for a deferred I2C-config DAC on the firmware side.
- GPIO14/15 — UART (Circle serial init).
- GPIO18-21 — I2S DAC (PCM_CLK/FS/DIN/DOUT), live `audio_output=i2s` option.
- GPIO8/9/11/25 — left spare by the firmware doc for possible future use
  (status LED, multitap); not populated in this v1 board.

If this table and `src/input/sega_board.h` in the firmware repo ever disagree,
the firmware repo's `BoardPinMap` is authoritative — this board must be updated
to match, not the other way around, since the kernel already ships against it.

## Deliverables

- KiCad project (schematic + PCB layout) checked into this repo.
- Silkscreen: "Player 1" / "Player 2" labels at J2/J3, pin-1 orientation marked
  on both DB9 footprints, board name/rev.
- A top-level README in this repo pointing at the firmware repo's pin-map
  source of truth, so the two can't silently drift.
- Not in this pass: fab-ready Gerbers/BOM/ordering. That's a follow-on step
  once the layout is reviewed.

## Testing / verification

No firmware logic exists in this project to unit test. Verification is:

1. **ERC/DRC clean in KiCad** — no unrouted nets, no footprint courtyard
   violations, silkscreen clear of the mounting holes and header.
2. **Continuity check** DB9 pin → GPIO pin against the table above once a
   board is fabricated, before first use with a real Pi.
3. **Functional bring-up** against the firmware repo's existing
   `docs/hardware-checklist-gpio-controllers.md` (checklist W) — that
   checklist already assumes "DB9 jacks wired to GPIO per `sega_board.h`
   (jumper harness or HAT)" and needs no changes for this board.

## Out of scope

- Official Raspberry Pi HAT certification / ID EEPROM.
- Any electrical protection circuitry (resistors, TVS, fuses).
- Stacking/pass-through header support for additional HATs.
- Status LEDs or use of the spare GPIO24-27 pins.
- Multitap or more than two controller ports (matches the firmware repo's
  explicit out-of-scope call for the same).
- Fabrication ordering (BOM sourcing, Gerber export, panelization).
