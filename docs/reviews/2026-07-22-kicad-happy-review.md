# KiCad Design Review — Sega Genesis Controller HAT

**Date:** 2026-07-22
**Tool:** kicad-happy v2.1.0 (`kicad`, `emc` skills)
**Analysis run:** `analysis/2026-07-22_0915/`
**Files reviewed:** `genesis-controller-hat.kicad_sch`, `genesis-controller-hat.kicad_pcb`

## Verdict

**No blockers.** This is a 3-component passive board (one generic 2×20 GPIO
header, two DB9 sockets) with no ICs, no regulators, and no analog
subcircuits — most of this tool's IC-datasheet and SPICE-verification
machinery doesn't apply here. Of the findings that *do* apply, two are
real, pre-existing, already-documented items (the stale PCB net table, the
missing ground plane) and several others are false positives caused by this
design repurposing Pi GPIO pins whose net names still carry the Raspberry
Pi's generic alternate-function labels (`GPCLK0`, `SPI0.SCLK`, etc.) even
though this board drives them as plain digital I/O, not as a hardware clock
or SPI bus.

## Analyses Run

| Analysis | Run? | Result |
|---|---|---|
| Datasheet sync | No | 0/2 unique parts have MPNs (generic DB9/header footprints, no distributor part chosen yet) — see Verification Basis below |
| `analyze_schematic.py` | Yes | 0 electrical findings beyond sourcing/lifecycle disclosure |
| `analyze_pcb.py --full` | Yes | 20 findings (placement, routing, EMC-adjacent) |
| `cross_analysis.py` | Yes | 8 findings (all EMC-plane-related, overlaps with EMC run) |
| `analyze_emc.py` | Yes | included in the 20/8 above |
| SPICE | **Not run** | no `ngspice`/`ltspice`/`xyce` on this machine, and this board has no simulatable subcircuit (no filters, dividers, or op-amps — just direct pass-through wiring) |
| `analyze_thermal.py` | Yes | 0 findings, thermal score `SKIPPED` — no power-dissipating components on this board |
| `analyze_gerbers.py` | **Not run** | no gerbers generated yet; fabrication output was explicitly out of scope for this v1 (see the project's own design spec) |
| Lifecycle audit | **Not run** | no MPNs assigned yet, nothing to look up |
| Prior review delta | N/A | this is the first review of this project |

## Verification Basis

`DS-001` fired (no datasheets, 0/2 parts have MPNs). Per this skill's own
disclosure rule: **every claim below is a consistency check, not a
datasheet-verified one.** That said, this project's own build process
already did the equivalent of datasheet verification for the parts that
matter here — not against a manufacturer PDF, but against the two sources
that actually govern this design:

- **Pin mapping** — every net was verified against the firmware repo's
  `src/input/sega_board.h` (the authoritative pin-map contract this whole
  board is built to implement), independently confirmed three times during
  this project's own build/review process (once per DB9 connector, plus the
  final whole-branch review), each time by re-deriving the schematic
  label → PCB pad net → target GPIO pad chain and comparing it against that
  table pin-by-pin.
- **Footprint correctness** — the 2×20 header and both DE9 socket footprints
  are KiCad's own official library parts (`Connector_PinSocket_2.54mm`,
  `Connector_Dsub`), not hand-drawn, so there's no custom pin-to-pad mapping
  to get wrong the way a community-authored symbol could.

So while `DS-001`'s literal trigger condition is true, this isn't a case of
"nobody checked the pinout" — it's a case of "the pinout was checked against
a domain-specific spec instead of a component datasheet," which is the
correct source of truth for a board whose entire purpose is implementing
someone else's protocol on someone else's GPIO header.

## Findings

### High/Error

**GP-002 — No ground plane zones detected.** Real, not a false positive.
Confirmed directly: the PCB has exactly one `zone` object, and it's an
unfilled keepout zone left over from the official `RaspberryPi-HAT` template
(named `"PoE"`, net-less, on `B.Cu` — irrelevant to a DB9-only board, same
class of template leftover already cleaned up elsewhere in this project's
final review pass, just missed for this one zone object specifically). There
is genuinely no ground or +3.3V copper pour anywhere on this board — every
net was routed as individual point-to-point traces in Task 6's greedy
router. For this board's actual signal profile (a handful of GPIO lines
polled at frame rate, no RF, no high-speed buses), a ground plane isn't
electrically required for function, but it's cheap insurance for noise
immunity and it's what a "real" 2-layer board would normally have. **Recommend
adding a ground pour on B.Cu in the same manual GUI cleanup pass the project
already has scheduled for the routing crossings** (see the project's
`README.md` "Known limitation" section) — and deleting the leftover `"PoE"`
keepout zone while in there.

**RT-001 — Unrouted net +5V (2 pads).** Already known and already documented.
This is the same stale-net-table situation the project's own `README.md`
calls out explicitly ("PCB net table includes stale entries") — the +5V net
is a leftover from the vanilla template (this design never uses 5V, only
3.3V, per the approved design spec), and J1's two physical +5V pins were
deliberately never wired to anything. Not a new finding, not an action item
beyond what's already documented.

**PM-002 — "J1 is 0.43mm from board edge."** Likely a tool false positive
for this specific footprint, not a real manufacturability defect. Compare
against the tool's own treatment of J2/J3/MH2/MH4, all of which it correctly
recognized as "edge-mount footprint — by-design at board edge" and
downgraded to `info`. J1 didn't get that same recognition, but it's under
the identical constraint: a HAT's 40-pin GPIO header position is fixed by
the official Raspberry Pi HAT mechanical spec (it must align with the Pi's
own header), not a placement choice this project made — and J1's position
was never touched in this project, inherited verbatim from KiCad's own
official `RaspberryPi-HAT` template. **No action recommended**; flagging
this as a tool limitation (its "is this footprint supposed to be at the
edge" heuristic doesn't recognize a generic 2×20 socket the way it
recognizes the DB9 footprints) rather than a design defect.

**SS-001 — Sourcing blocker: BOM has <50% MPN coverage (0/2 unique parts).**
Real, expected, not yet in scope. This project's own design spec explicitly
deferred "fab-ready Gerbers/BOM/ordering" to a follow-on step past this v1.
Genuine pre-order todo (pick specific DB9 socket and header part numbers,
verify footprint match), not a v1 defect.

**RP-002 (2 of 6 flagged `error`) — "clock net /GPIO4/GPCLK0 crosses +3V3
plane gap"; "clock net /GPIO11/SPI0.SCLK crosses GND plane gap."** False
positive from net-name pattern matching, not a real EMC clock-routing issue.
`GPIO4`/`GPIO11` are this design's two DB9 **SELECT** lines (per
`sega_board.h`) — plain, software-toggled digital outputs, not hardware
clock generators. Their net names still carry the Raspberry Pi's *generic*
alternate-function label (`GPCLK0`/`SPI0.SCLK` — every Pi GPIO pin has one,
inherited straight from the official KiCad template's own per-pin labels)
even though this application never uses that alternate function. The EMC
analyzer's clock-detection heuristic pattern-matches on the `GPCLK`/`SCLK`
substring in the net name without knowing this. **No action needed** — but
worth being aware of if this finding resurfaces in a future automated run,
since the underlying net names won't change (they're inherited from the
Pi's own GPIO naming convention, not something this project controls).

### Warning

**RP-002 (4 of 6, `warning`) — "spi net /GPIO{7,8,9,10}/SPI0.* crosses +3V3
plane gap."** Same root cause and same verdict as the two `error`-level
instances above — these four GPIO pins are this design's TL/TR (button)
lines on both DB9 ports, not a real SPI bus. False positive, no action.

**IO-001 (high, listed as 2 findings) — "No EMC filtering near J1/J3."**
Expected and already a documented, approved design decision, not a gap this
review is surfacing for the first time: the project's design spec explicitly
calls for **no protection components** (no series resistors, no TVS/ESD
diodes) — direct wiring only, matching the firmware repo's own electrical
contract, which was deliberately chosen over filtering during this project's
brainstorming phase. Consistent with the design intent, not a defect.

**CK-003 (2) — "Clock ... routed near connector."** Same false-positive
root cause as the RP-002 clock findings above (net-name pattern match on
`GPCLK0`/`SCLK`, not an actual clock signal). No action.

**TE-001 — Test point coverage: 0/28 nets (0%).** Expected for a low-volume
hobbyist board with no ICT/production-test requirement. Not a defect for
this project's scope.

**VS-001 — "Via stitching may be insufficient."** Consequence of GP-002 (no
ground plane exists yet to stitch). Resolves itself once a ground pour is
added; not a separate action item.

### Info (no action needed — confirmed correct-by-design)

- **PM-002** (J2/J3/MH2/MH4 edge distances) — all four correctly recognized
  by the tool itself as intentional edge-mount/HAT-mounting-hole geometry.
- **EP-AUD** (ESD audit: none coverage on J1/J2/J3) — matches the approved
  "no protection components" design decision.
- **IO-002** / **CG-AUD** (J2/J3: only 1 ground pin out of 9, 8:1
  signal-to-ground ratio) — inherent to the DB9 Sega Genesis controller
  connector standard itself (pin 8 is the only ground on the real
  connector); not something a HAT redesign could change without breaking
  compatibility with real controllers.
- **PS-002** (+3V3/GND "plane split" into 2/8 islands) — another view of the
  same stale-net-table / no-ground-plane situation as GP-002/RT-001 above,
  not a new issue.
- **EE-001** (board cavity resonance estimate), **GP-001** (return path data
  unavailable — no plane to analyze), **SU-001** (F.Cu/B.Cu both carry
  signals) — informational only, no action implied.

## Known Analyzer Limitations for This Board

- SPICE and thermal analysis exist in the toolchain but have nothing to
  simulate/model here — this board has zero analog subcircuits and zero
  power-dissipating components. Their "0 findings" results are a correct
  reflection of the design, not a gap.
- Gerbers and a lifecycle audit weren't run because neither fabrication
  outputs nor MPNs exist yet — both are legitimate next steps before
  ordering, not part of this v1's stated scope.
- Net-name-driven heuristics (clock/SPI detection) don't have visibility
  into *actual* pin usage for a design that deliberately repurposes a
  general-purpose header's alternate-function-named pins as plain GPIO —
  worth remembering if this board is re-analyzed later and the same
  `GPCLK0`/`SPI0.*` findings reappear.

## Recommended Follow-ups (fold into the existing pre-fab GUI cleanup pass)

The project's `README.md` already documents a manual KiCad-GUI cleanup pass
for the routing crossings/shorts and the clipped "Player 2" label. Add two
items to that same list:

1. Pour a ground plane (B.Cu is the natural choice, since most signal
   routing is on F.Cu) and stitch it to J1's GND pins.
2. Delete the leftover unfilled `"PoE"` keepout zone (a separate object from
   the `"PoE"` text label already removed in this project's final review).

Neither blocks the board's electrical function as designed; both are cheap
to do in the same GUI session already planned for the routing cleanup.
