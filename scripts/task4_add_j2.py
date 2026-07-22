import sys
sys.path.insert(0, "scripts")
import kicad_sexpr as ks

PATH = "genesis-controller-hat.kicad_sch"
tree = ks.parse(open(PATH).read())
proj = ks.project_name(tree)
root = ks.root_uuid(tree)

# J2 anchor at (50.8, 254.0) rotation 0 -> pin N absolute = (50.8 - 7.62, 254.0 - local_y)
J2_PINS = {
    "1": (43.18, 243.84),  # Up      -> GPIO5
    "6": (43.18, 246.38),  # TL      -> GPIO9
    "2": (43.18, 248.92),  # Down    -> GPIO6
    "7": (43.18, 251.46),  # SELECT  -> GPIO4
    "3": (43.18, 254.00),  # Left    -> GPIO7
    "8": (43.18, 256.54),  # GND
    "4": (43.18, 259.08),  # Right   -> GPIO8
    "9": (43.18, 261.62),  # TR      -> GPIO10
    "5": (43.18, 264.16),  # +3.3V
    "0": (50.80, 269.24),  # shell/mounting pad -> NC
}

PIN_TO_LABEL = {
    "1": "GPIO5",
    "2": "GPIO6",
    "3": "GPIO7{slash}SPI0.CE1",
    "4": "GPIO8{slash}SPI0.CE0",
    "6": "GPIO9{slash}SPI0.MISO",
    "7": "GPIO4{slash}GPCLK0",
    "9": "GPIO10{slash}SPI0.MOSI",
}

ks.ensure_lib_symbol_cached(tree, "Connector:DE9_Socket_MountingHoles")
tree.append(ks.make_db9_symbol("J2", "DE9_Socket_MountingHoles", (50.8, 254.0), proj, root))

for pin, label_text in PIN_TO_LABEL.items():
    tree.append(ks.make_label(label_text, J2_PINS[pin]))

tree.append(ks.make_power_symbol("power:+3.3V", "#PWR901", "+3V3", J2_PINS["5"], proj, root))
tree.append(ks.make_power_symbol("power:GND", "#PWR902", "GND", J2_PINS["8"], proj, root))
tree.append(ks.make_no_connect(J2_PINS["0"]))

open(PATH, "w").write(ks.dumps(tree))
print("Task 4 edits applied.")
