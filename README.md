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

## Known limitation: edge-mount connectors overlap the corner mounting holes

J2/J3's edge-mount footprint has a 30.85mm-wide plastic mounting base (the
flat bracket that carries the connector's own two screws). The board's
official corner mounting holes are only 58mm apart. The math doesn't work
out: positioning each connector far enough from its nearest corner hole to
fully clear it pushes the two connectors' bases into each other in the
middle — there is no position that clears both constraints on this board
width. Clearing J2/J3 from each other (the more important constraint, since
overlapping *each other* would mean the parts can't be populated at all) was
prioritized, which leaves each connector's base overlapping its nearest
corner hole's clearance (`courtyards_overlap`, 2 errors — J2 vs `MH3`, J3 vs
`MH4`, both bottom corners).

This is a genuine mechanical conflict, not a cosmetic DRC nag: the DSUB
bracket's plastic physically occupies where that corner's mounting screw
would go. **Before fabricating, decide how to resolve it** — options include
omitting that corner's mounting screw (the HAT would be held by the other
three), sourcing a DSUB with a narrower bracket, or accepting a 3-point-
mounted HAT. This wasn't a factor with the previous vertical-mount
footprint, which had a much smaller footprint envelope.

## Routing is now fully clean of crossings and shorts

`kicad-cli pcb drc --severity-all` on `genesis-controller-hat.kicad_pcb`
reports 4 errors / 5 warnings, not zero — down from 30 errors / 6 warnings
before the 2026-07-22 pin reassignment. `tracks_crossing`, `shorting_items`,
`solder_mask_bridge`, `hole_clearance`, and `copper_edge_clearance` are all
now **zero**. Getting there took three passes:

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

Remaining violations, all pre-existing or cosmetic:

- `courtyards_overlap` (2) — the edge-mount connector/corner-hole conflict
  documented above. Not a routing issue.
- `unconnected_items` (2), `lib_footprint_mismatch` (1) — pre-existing in
  KiCad's own template since before this HAT project touched it (J1's +5V
  pins 2/4 are simply unused, and J1's two +3.3V pins, 1 and 17, aren't
  tied together on this board because they're already tied together
  upstream on the Pi itself). Unrelated to J2/J3. The schematic side has the
  same kind of cache-drift warning: ERC reports 2 `lib_symbol_mismatch`
  warnings (0 errors) for J2/J3's `DE9_Socket_MountingHoles` symbol, whose
  cached copy no longer matches KiCad 10's revised system library copy —
  cosmetic only, same as `lib_footprint_mismatch`.
- `silk_edge_clearance` (4) — cosmetic; a silkscreen clip at the board edge,
  not a copper/electrical issue.

**Before fabricating this board, clean up the silkscreen clips noted
above** and resolve the corner-hole trade-off documented earlier; DRC is
otherwise clean.

## Verifying the board

```bash
kicad-cli sch erc --severity-all genesis-controller-hat.kicad_sch
kicad-cli pcb drc --severity-all genesis-controller-hat.kicad_pcb
python3 scripts/check_pinmap.py ../Bare-Metal-Sega-Genesis/src/input/sega_board.h
```

ERC should report 0 errors / 2 warnings (the `lib_symbol_mismatch` cache-drift
warnings noted above). DRC will report 4 errors/5 warnings — see "Routing
is now fully clean of crossings and shorts" above for
the exact breakdown and why this isn't a bug to fix here; the schematic
(electrical topology) is fully verified, the PCB's routing needs one more
manual pass in the KiCad GUI before this board goes to fab. `check_pinmap.py`
(also run in CI on every push) confirms the
schematic's actual wiring matches the firmware repo's `sega_board.h`.
