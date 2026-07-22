"""Round-trip-safe S-expression parser/serializer for KiCad 9 files, plus
helpers for the specific find/remove/create operations this project's
schematic-editing scripts need. Not a general KiCad API replacement — no
pcbnew module is installed in this environment, so file-format editing is
the only scripting path available."""

import uuid as _uuid


class Sym(str):
    """A bare (unquoted) token, as opposed to a quoted string."""
    pass


def parse(text):
    pos = 0
    n = len(text)

    def skip_ws(p):
        while p < n and text[p] in " \t\r\n":
            p += 1
        return p

    def parse_atom(p):
        if text[p] == '"':
            p += 1
            buf = []
            while text[p] != '"':
                if text[p] == '\\':
                    buf.append(text[p + 1])
                    p += 2
                else:
                    buf.append(text[p])
                    p += 1
            return "".join(buf), p + 1
        start = p
        while p < n and text[p] not in " \t\r\n()":
            p += 1
        return Sym(text[start:p]), p

    def parse_expr(p):
        p = skip_ws(p)
        assert text[p] == '(', f"expected '(' at {p}"
        p += 1
        items = []
        while True:
            p = skip_ws(p)
            if text[p] == ')':
                return items, p + 1
            if text[p] == '(':
                sub, p = parse_expr(p)
                items.append(sub)
            else:
                atom, p = parse_atom(p)
                items.append(atom)

    tree, _ = parse_expr(skip_ws(0))
    return tree


def serialize(node):
    if isinstance(node, Sym):
        return str(node)
    if isinstance(node, str):
        return '"' + node.replace('\\', '\\\\').replace('"', '\\"') + '"'
    return "(" + " ".join(serialize(c) for c in node) + ")"


def dumps(tree):
    return serialize(tree)


def get_tag(node):
    return node[0] if isinstance(node, list) and node else None


def get_property(symbol_node, name):
    for child in symbol_node:
        if isinstance(child, list) and get_tag(child) == "property" and child[1] == name:
            return child[2]
    return None


def find_symbols_by_ref(tree, refs):
    return [n for n in tree if isinstance(n, list) and get_tag(n) == "symbol"
            and get_property(n, "Reference") in refs]


def remove_symbols_by_ref(tree, refs):
    before = len(tree)
    tree[:] = [n for n in tree if not (isinstance(n, list) and get_tag(n) == "symbol"
                                        and get_property(n, "Reference") in refs)]
    return before - len(tree)


def remove_labels_by_text(tree, texts):
    before = len(tree)
    tree[:] = [n for n in tree if not (isinstance(n, list) and get_tag(n) == "label"
                                        and n[1] in texts)]
    return before - len(tree)


def root_uuid(tree):
    for node in tree:
        if isinstance(node, list) and get_tag(node) == "uuid":
            return node[1]
    raise ValueError("no top-level uuid found")


def project_name(tree):
    for node in tree:
        if isinstance(node, list) and get_tag(node) == "symbol":
            for child in node:
                if isinstance(child, list) and get_tag(child) == "instances":
                    for proj in child[1:]:
                        return proj[1]
    raise ValueError("no instances/project block found to infer project name")


def _effects(size=1.27):
    return [Sym("effects"), [Sym("font"), [Sym("size"), str(size), str(size)]]]


def make_power_symbol(lib_id, ref, value, at_xy, project, root_uuid_str):
    x, y = at_xy
    new_uuid = str(_uuid.uuid4())
    return [
        Sym("symbol"),
        [Sym("lib_id"), lib_id],
        [Sym("at"), str(x), str(y), "0"],
        [Sym("unit"), "1"],
        [Sym("exclude_from_sim"), Sym("no")],
        [Sym("in_bom"), Sym("yes")],
        [Sym("on_board"), Sym("yes")],
        [Sym("dnp"), Sym("no")],
        [Sym("uuid"), new_uuid],
        [Sym("property"), "Reference", ref, [Sym("at"), str(x), str(y + 3.81), "0"],
         [Sym("effects"), [Sym("font"), [Sym("size"), "1.27", "1.27"]], [Sym("hide"), Sym("yes")]]],
        [Sym("property"), "Value", value, [Sym("at"), str(x), str(y - 4.32), "0"], _effects()],
        [Sym("property"), "Footprint", "", [Sym("at"), str(x), str(y), "0"], _effects()],
        [Sym("property"), "Datasheet", "", [Sym("at"), str(x), str(y), "0"], _effects()],
        [Sym("pin"), "1", [Sym("uuid"), str(_uuid.uuid4())]],
        [Sym("instances"), [Sym("project"), project,
                             [Sym("path"), "/" + root_uuid_str,
                              [Sym("reference"), ref], [Sym("unit"), "1"]]]],
    ]


def make_db9_symbol(ref, value, at_xy, project, root_uuid_str):
    x, y = at_xy
    new_uuid = str(_uuid.uuid4())
    return [
        Sym("symbol"),
        [Sym("lib_id"), "Connector:DE9_Socket_MountingHoles"],
        [Sym("at"), str(x), str(y), "0"],
        [Sym("unit"), "1"],
        [Sym("exclude_from_sim"), Sym("no")],
        [Sym("in_bom"), Sym("yes")],
        [Sym("on_board"), Sym("yes")],
        [Sym("dnp"), Sym("no")],
        [Sym("uuid"), new_uuid],
        [Sym("property"), "Reference", ref, [Sym("at"), str(x), str(y - 17.78), "0"], _effects()],
        [Sym("property"), "Value", value, [Sym("at"), str(x), str(y - 15.875), "0"], _effects()],
        [Sym("property"), "Footprint",
         "Connector_Dsub:DSUB-9_Socket_Vertical_P2.77x2.84mm_MountingHoles",
         [Sym("at"), str(x), str(y), "0"], [Sym("effects"), [Sym("font"), [Sym("size"), "1.27", "1.27"]], [Sym("hide"), Sym("yes")]]],
        [Sym("property"), "Datasheet", "~", [Sym("at"), str(x), str(y), "0"],
         [Sym("effects"), [Sym("font"), [Sym("size"), "1.27", "1.27"]], [Sym("hide"), Sym("yes")]]],
        [Sym("instances"), [Sym("project"), project,
                             [Sym("path"), "/" + root_uuid_str,
                              [Sym("reference"), ref], [Sym("unit"), "1"]]]],
    ]


def make_label(text, at_xy, angle=180):
    x, y = at_xy
    return [Sym("label"), text, [Sym("at"), str(x), str(y), str(angle)],
            [Sym("effects"), [Sym("font"), [Sym("size"), "1.27", "1.27"]],
             [Sym("justify"), Sym("left"), Sym("bottom")]],
            [Sym("uuid"), str(_uuid.uuid4())]]


def make_no_connect(at_xy):
    x, y = at_xy
    return [Sym("no_connect"), [Sym("at"), str(x), str(y)], [Sym("uuid"), str(_uuid.uuid4())]]
