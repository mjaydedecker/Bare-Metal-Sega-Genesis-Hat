#!/usr/bin/env python3
"""Verify this HAT's schematic wiring matches the firmware repo's pin map.

The firmware repo's src/input/sega_board.h is the single authoritative
source for which BCM GPIO drives each DB9 signal (see that file's own
header comment). This script extracts the *actual* wiring from the
committed KiCad schematic -- not from a markdown table or from the scripts
that built it, but from the real .kicad_sch file -- and fails if it
disagrees with sega_board.h.

Usage:
    check_pinmap.py <path/to/sega_board.h> [path/to/genesis-controller-hat.kicad_sch]

The schematic path defaults to genesis-controller-hat.kicad_sch next to
this script's repo root, so a local run only needs the header path.
"""
import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import kicad_sexpr as ks  # noqa: E402

# DE9_Socket_MountingHoles local pin offsets (from KiCad's Connector.kicad_sym),
# relative to the symbol's own placement anchor. x is fixed per pin column;
# y varies per pin. Placing a symbol at rotation 0 puts pin N's absolute
# position at (anchor_x + local_x, anchor_y - local_y) -- KiCad negates the
# local Y offset on placement (library coordinates increase upward, page
# coordinates increase downward).
LOCAL_PIN_XY = {
    "1": (-7.62, 10.16), "6": (-7.62, 7.62), "2": (-7.62, 5.08),
    "7": (-7.62, 2.54), "3": (-7.62, 0.0), "8": (-7.62, -2.54),
    "4": (-7.62, -5.08), "9": (-7.62, -7.62), "5": (-7.62, -10.16),
}

# DB9 pin -> sega_board.h role. Pin 7 is SELECT; pins 1,2,3,4,6,9 are
# D0..D5, per sega_board.h's own comment: "Data lines D0..D5 map to DB9
# pins 1,2,3,4,6,9."
DB9_PIN_TO_ROLE = {"7": "select", "1": "D0", "2": "D1", "3": "D2", "4": "D3", "6": "D4", "9": "D5"}

CONNECTOR_TO_PORT = {"J2": "Port 1 (Player 1)", "J3": "Port 2 (Player 2)"}


def find_symbol_anchor(tree, ref):
    for n in tree:
        if isinstance(n, list) and ks.get_tag(n) == "symbol" and ks.get_property(n, "Reference") == ref:
            at = next(c for c in n if isinstance(c, list) and ks.get_tag(c) == "at")
            return float(at[1]), float(at[2])
    raise ValueError(f"symbol {ref} not found in schematic")


def label_at(tree, x, y, tol=0.01):
    for n in tree:
        if isinstance(n, list) and ks.get_tag(n) == "label":
            at = next(c for c in n if isinstance(c, list) and ks.get_tag(c) == "at")
            lx, ly = float(at[1]), float(at[2])
            if abs(lx - x) < tol and abs(ly - y) < tol:
                return n[1]
    return None


def gpio_number(label_text):
    m = re.match(r"GPIO(\d+)", label_text)
    if not m:
        raise ValueError(f"label {label_text!r} doesn't start with GPIO<n> -- unexpected net name")
    return int(m.group(1))


def extract_connector_pinmap(tree, ref):
    ax, ay = find_symbol_anchor(tree, ref)
    result = {}
    for pin, (lx, ly) in LOCAL_PIN_XY.items():
        if pin not in DB9_PIN_TO_ROLE:
            continue
        abs_x, abs_y = ax + lx, ay - ly
        label = label_at(tree, abs_x, abs_y)
        if label is None:
            raise ValueError(
                f"{ref} pin {pin}: no label found at ({abs_x:.2f}, {abs_y:.2f}) -- "
                f"schematic wiring may have moved without updating this checker's "
                f"pin-offset table"
            )
        result[DB9_PIN_TO_ROLE[pin]] = gpio_number(label)
    return result


def parse_sega_board_h(path):
    text = Path(path).read_text()
    m = re.search(
        r"kBoardPinMap\s*=\s*\{\s*\{\s*"
        r"\{\s*(\d+)\s*,\s*\{\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\}\s*\}\s*,"
        r"(?:[ \t]*//[^\n]*)?\s*"
        r"\{\s*(\d+)\s*,\s*\{\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\}\s*\}",
        text,
    )
    if not m:
        raise ValueError(
            f"could not find the kBoardPinMap struct in {path} -- its layout "
            f"may have changed in a way this checker's regex doesn't expect"
        )
    nums = [int(g) for g in m.groups()]
    fields = ("select", "D0", "D1", "D2", "D3", "D4", "D5")
    return dict(zip(fields, nums[:7])), dict(zip(fields, nums[7:]))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("header_path", help="path to the firmware repo's src/input/sega_board.h")
    parser.add_argument(
        "schematic_path", nargs="?",
        default=str(REPO_ROOT / "genesis-controller-hat.kicad_sch"),
        help="path to genesis-controller-hat.kicad_sch (default: repo root)",
    )
    args = parser.parse_args()

    sch_tree = ks.parse(Path(args.schematic_path).read_text())
    hat_ports = {ref: extract_connector_pinmap(sch_tree, ref) for ref in CONNECTOR_TO_PORT}
    fw_port1, fw_port2 = parse_sega_board_h(args.header_path)
    fw_ports = {"J2": fw_port1, "J3": fw_port2}

    mismatches = []
    for ref, label in CONNECTOR_TO_PORT.items():
        hat, fw = hat_ports[ref], fw_ports[ref]
        if hat != fw:
            mismatches.append((ref, label, hat, fw))

    for ref in CONNECTOR_TO_PORT:
        print(f"{ref} ({CONNECTOR_TO_PORT[ref]}):")
        print(f"  HAT schematic:  {hat_ports[ref]}")
        print(f"  sega_board.h:   {fw_ports[ref]}")

    if mismatches:
        print()
        print("MISMATCH -- the HAT's wiring disagrees with sega_board.h:")
        for ref, label, hat, fw in mismatches:
            print(f"  {ref} ({label}): HAT has {hat}, firmware has {fw}")
        print()
        print("sega_board.h is the source of truth (see its own header comment).")
        print("Update the HAT schematic to match, not the other way around.")
        return 1

    print()
    print("OK -- HAT schematic wiring matches sega_board.h exactly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
