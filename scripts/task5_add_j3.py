import sys
sys.path.insert(0, "scripts")
import kicad_sexpr as ks

PATH = "genesis-controller-hat.kicad_sch"
tree = ks.parse(open(PATH).read())
proj = ks.project_name(tree)
root = ks.root_uuid(tree)

# J3 anchor at (101.6, 254.0) rotation 0 -> pin N absolute = (101.6 - 7.62, 254.0 - local_y)
J3_PINS = {
    "1": (93.98, 243.84),  # Up      -> GPIO12
    "6": (93.98, 246.38),  # TL      -> GPIO22
    "2": (93.98, 248.92),  # Down    -> GPIO13
    "7": (93.98, 251.46),  # SELECT  -> GPIO11
    "3": (93.98, 254.00),  # Left    -> GPIO16
    "8": (93.98, 256.54),  # GND
    "4": (93.98, 259.08),  # Right   -> GPIO17
    "9": (93.98, 261.62),  # TR      -> GPIO23
    "5": (93.98, 264.16),  # +3.3V
    "0": (101.60, 269.24),  # shell/mounting pad -> NC
}

PIN_TO_LABEL = {
    "1": "GPIO12{slash}PWM0",
    "2": "GPIO13{slash}PWM1",
    "3": "GPIO16",
    "4": "GPIO17",
    "6": "GPIO22",
    "7": "GPIO11{slash}SPI0.SCLK",
    "9": "GPIO23",
}

ks.ensure_lib_symbol_cached(tree, "Connector:DE9_Socket_MountingHoles")
tree.append(ks.make_db9_symbol("J3", "DE9_Socket_MountingHoles", (101.6, 254.0), proj, root))

for pin, label_text in PIN_TO_LABEL.items():
    tree.append(ks.make_label(label_text, J3_PINS[pin]))

tree.append(ks.make_power_symbol("power:+3.3V", "#PWR903", "+3V3", J3_PINS["5"], proj, root))
tree.append(ks.make_power_symbol("power:GND", "#PWR904", "GND", J3_PINS["8"], proj, root))
tree.append(ks.make_no_connect(J3_PINS["0"]))

open(PATH, "w").write(ks.dumps(tree))
print("Task 5 edits applied.")
