# Sega Genesis Controller HAT

A passive Raspberry Pi HAT exposing two DB9 (DE-9) ports for original Sega
Genesis / Mega Drive controllers, wired directly to the Pi's 40-pin GPIO
header.

This board has no firmware of its own. The pin assignment and electrical
contract it implements are owned by the firmware repo,
[Bare-Metal-Sega-Genesis](../Bare-Metal-Sega-Genesis), specifically
`src/input/sega_board.h` and
`docs/superpowers/specs/2026-06-25-gpio-sega-controllers-design.md`. If
those ever disagree with this repo, the firmware repo wins — update this
board to match it, not the other way around.

See `docs/superpowers/specs/2026-07-21-controller-hat-v1-design.md` for the
full design rationale (why no ID EEPROM, no protection circuitry, no
stacking header) and `docs/superpowers/plans/2026-07-21-controller-hat-v1.md`
for how it was built.

**2026-07-22:** the GPIO pin assignment was reassigned (see
`docs/reviews/2026-07-22-pinmap-reassignment.md`) to eliminate PCB routing
crossings, and a GND ground plane pour was added on `B.Cu`. A GitHub Actions
workflow (`.github/workflows/verify-pinmap.yml`) now checks on every push
that this board's schematic wiring matches the firmware repo's
`sega_board.h` exactly. The template's camera flex slot cutout (next to J3)
was also removed — this board has no camera and the slot was only crowding
J3's mounting plate; the recommended (not required) display flex cutout on
the left edge was left in place. J2 and J3 were then moved 3mm right / 6mm
left respectively so all 4 of their mounting holes sit fully on the board
(previously J2's left hole and J3's right hole were partially/fully off the
board edge) — each hole now has about 1mm of clearance to the edge, with
about 2mm of clearance between the two connector shells.

**Also 2026-07-22:** J2/J3 were switched from KiCad's `DSUB-9_Socket_Vertical`
footprint to `DSUB-9_Socket_Horizontal_..._EdgePinOffset7.70mm_Housed_MountingHolesOffset9.12mm`
— the vertical footprint has its DB9 opening facing straight up (a cable
plugs in from directly above the HAT), not out over the board edge. The
edge-mount/right-angle footprint hangs the connector's shell 9.12mm past the
board's bottom edge so a controller cable plugs in horizontally, console-
style. See "Known limitation: edge-mount connectors overlap the corner
mounting holes" below for a real trade-off this introduced.

**2026-07-22 (later the same day):** upgraded the project files from KiCad
9 to KiCad 10 format (`kicad-cli sch upgrade` / `pcb upgrade`) after the
toolchain was updated. ERC/DRC results are unaffected — see "Verifying the
board" below for current counts.

**2026-07-22 (still later):** replaced the "Genesis Controller HAT" title
silkscreen text with the "Bare-Metal Genesis" wordmark logo from
`design_files/Bare-metal Sega Genesis-handoff.zip`
(`project/kicad/bmg-logo-wordmark.svg`), placed on `F.Silkscreen` centered
between J1 and the two DB9 connectors (48mm wide, ~14mm tall). The source
SVG is entirely axis-aligned `<rect>` elements (pixel-art style), so it was
converted directly to 153 filled `gr_rect` silkscreen shapes at 1:1 fidelity
rather than traced/vectorized. "Rev A" was moved down slightly to stay clear
of the logo, and "Controller HAT" was added back alongside it on the same
line. No DRC/ERC change from this (silkscreen doesn't need clearance from
the copper traces it sits over).

**2026-07-22 (yet later):** added this repo's URL and a build date to the
board's *back* silkscreen (`B.Silkscreen`) — the front was already full
with the logo, title, and port labels. Back-layer text needs its "mirrored"
flag set so it reads correctly once the board is physically flipped over;
easy to miss when adding text via `pcbnew` scripting (the GUI does this
automatically, scripting does not).

## Files

- `genesis-controller-hat.kicad_pro` / `.kicad_sch` / `.kicad_pcb` — the
  KiCad 10 project.
- `design_files/` — source design assets (currently the Bare-Metal Genesis
  logo handoff package); not needed to open or modify the board, kept for
  provenance.
- `scripts/` — the editing scripts used to build the schematic and PCB from
  KiCad's official `RaspberryPi-HAT` template. Not needed to open or modify
  the board in the KiCad GUI; kept for provenance/audit.

## Known limitation: PCB net table includes stale entries

The PCB's net table still lists nets for GPIO pins and the ID EEPROM/+5V
circuit that were deleted from the schematic (I2C, UART, I2S, the four
spare GPIOs, `ID_SDA`/`ID_SCL`, `+5V`). No footprint or track references
them, so they're inert, but a `kicad-cli pcb drc --schematic-parity` run
will flag the mismatch. There is no headless "update PCB from schematic"
command in this KiCad install — if you need full parity (e.g. before
opening this in the GUI to do further layout work), open the project in
the KiCad GUI once and run Tools → Update PCB from Schematic.

## Known limitation: only 2 of the 4 official corner mounting holes remain

J2/J3's edge-mount footprint has a 30.85mm-wide plastic mounting base (the
flat bracket that carries the connector's own two screws). The board's
official corner mounting holes are only 58mm apart, and the math didn't
work out: positioning each connector far enough from its nearest corner
hole to fully clear it pushed the two connectors' bases into each other in
the middle. Clearing J2/J3 from each other (the more important constraint,
since overlapping *each other* would mean the parts can't be populated at
all) was prioritized, which left each connector's base overlapping its
nearest corner hole — J2 over the bottom-left hole (`MH3`), J3 over the
bottom-right hole (`MH4`). Both bottom corners were affected, not just one.

Since those two mounting screws could never actually be installed (the DSUB
bracket's plastic physically occupies the space), **`MH3` and `MH4` were
removed** rather than left in as dead weight — `courtyards_overlap` is now
zero. This board mounts on only the 2 remaining corner holes (`MH1`/`MH2`,
both at the top, next to the GPIO header) plus the GPIO header's own
friction fit; it no longer meets the official HAT spec's 4-corner-hole
requirement (this board was already not pursuing full HAT certification —
see the design spec's "Scope decisions"). If 4-point mounting matters for
your use case, the alternatives are the same as before: a DSUB with a
narrower bracket, or reverting to the smaller vertical-mount footprint
(mating face up, not edge-accessible).

## Routing is now fully clean of crossings and shorts

`kicad-cli pcb drc --severity-all` on `genesis-controller-hat.kicad_pcb`
reports 2 errors / 1 warning, not zero — down from 30 errors / 6 warnings
before the 2026-07-22 pin reassignment. `tracks_crossing`, `shorting_items`,
`solder_mask_bridge`, `hole_clearance`, `copper_edge_clearance`,
`courtyards_overlap`, and `silk_edge_clearance` are all now **zero**.
Getting the routing-related ones clean took three passes:

1. The pin reassignment itself (see `docs/reviews/2026-07-22-pinmap-reassignment.md`)
   eliminated same-layer crossings between J2/J3's own routing, but left
   `shorting_items`/`solder_mask_bridge` where the resulting breakout tracks
   skimmed past unrelated J1 pads.
2. Each affected track (`/GPIO24`, `/GPIO23`, `/GPIO7/SPI0.CE1`, `GND`,
   `/GPIO16`, `/GPIO12/PWM0`) was rerouted to jog around J1's row-A pins
   instead of skimming past them — J1's two pin rows are only 2.54mm apart,
   so a track targeting a row-B pin has to actively route around the row-A
   pin directly in front of it, not just aim at the target. This introduced
   2 new `tracks_crossing` errors in the resulting crowded cluster
   (`/GPIO12/PWM0` vs `GND`, and `/GPIO24` vs `/GPIO10/SPI0.MOSI`/`+3V3`),
   since 3+ nets ended up needing mutual separation with only 2 copper
   layers available.
3. Both were resolved by rerouting the *conflicting* nets out of the way
   rather than the flagged ones: `/GPIO6` moved further left (clearing room
   for `/GPIO12/PWM0` to approach its target from the other side, parallel
   to `/GPIO6` instead of crossing `GND`), and `/GPIO10/SPI0.MOSI` moved to
   `F.Cu` with its own jog around J1's row-A pins (clearing both `+3V3` and
   `/GPIO24`, which stayed put).

Remaining violations, all pre-existing:

- `unconnected_items` (2), `lib_footprint_mismatch` (1) — pre-existing in
  KiCad's own template since before this HAT project touched it (J1's +5V
  pins 2/4 are simply unused, and J1's two +3.3V pins, 1 and 17, aren't
  tied together on this board because they're already tied together
  upstream on the Pi itself). Unrelated to J2/J3.

The schematic's equivalent cache-drift warning (`lib_symbol_mismatch` on
J2/J3's `DE9_Socket_MountingHoles` symbol, introduced by the KiCad 9→10
upgrade revising that library symbol) has been fixed directly: ERC is now
**0 errors / 0 warnings**. `scripts/kicad_sexpr.py` gained a
`refresh_lib_symbol_cache(tree, lib_id)` helper that replaces a schematic's
stale cached symbol definition with the current one from the system
library — the schematic-side counterpart to `lib_footprint_mismatch`, which
is a PCB footprint (not a cached symbol) and would need re-placing the
footprint to fix the same way, not worth doing for one cosmetic warning.

`silk_edge_clearance` (was 4) is also now fixed: J2/J3's outline-box
silkscreen (drawn slightly larger than the copper, matching the connector's
real body) had two sides running right along the board edge — J2's left
side sat 0.025mm *past* the edge, and both connectors' outer sides dipped
down into the rounded bottom corners, where the board narrows and the line
ends up outside the board entirely. Nudged each offending line ~0.3mm
inward and trimmed its length to stop before the corner begins (at y=96,
just above where the rounding starts at y=97) — a purely cosmetic change
to the silkscreen artwork on these two footprint instances, no change to
pads, copper, or the connector's real footprint envelope.

**Before fabricating this board, resolve the corner-hole trade-off
documented earlier**; DRC is otherwise clean.

## Verifying the board

```bash
kicad-cli sch erc --severity-all genesis-controller-hat.kicad_sch
kicad-cli pcb drc --severity-all genesis-controller-hat.kicad_pcb
python3 scripts/check_pinmap.py ../Bare-Metal-Sega-Genesis/src/input/sega_board.h
```

ERC should report 0 errors / 0 warnings. DRC will report 2 errors/1 warning — see "Routing
is now fully clean of crossings and shorts" above for
the exact breakdown and why this isn't a bug to fix here; the schematic
(electrical topology) is fully verified, the PCB's routing needs one more
manual pass in the KiCad GUI before this board goes to fab. `check_pinmap.py`
(also run in CI on every push) confirms the
schematic's actual wiring matches the firmware repo's `sega_board.h`.
