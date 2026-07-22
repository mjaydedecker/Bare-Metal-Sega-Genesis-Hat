"""Round-trip-safe S-expression parser/serializer for KiCad 9 files, plus
helpers for the specific find/remove/create operations this project's
schematic-editing scripts need. Not a general KiCad API replacement — no
pcbnew module is installed in this environment, so file-format editing is
the only scripting path available."""

import uuid as _uuid

# Global symbol libraries this project ever pulls a not-yet-cached lib_id
# from. Schematic files cache a copy of every symbol definition they use in
# their own top-level lib_symbols section; KiCad 9 fails to load a file that
# references a lib_id with no matching cache entry, even when the global
# library table resolves the nickname fine. See ensure_lib_symbol_cached().
_SYMBOL_LIBRARY_PATHS = {
    "power": "/usr/share/kicad/symbols/power.kicad_sym",
    "Connector": "/usr/share/kicad/symbols/Connector.kicad_sym",
}


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
                    esc = text[p + 1]
                    # KiCad escape sequences that are NOT "drop the backslash,
                    # keep the char verbatim": \n is a two-byte escape meaning
                    # an actual line break, not the literal letter 'n'.
                    if esc == 'n':
                        buf.append('\n')
                    elif esc == '\\':
                        buf.append('\\')
                    elif esc == '"':
                        buf.append('"')
                    else:
                        # Safe default for any other/unknown escape: drop the
                        # backslash, keep the next character verbatim.
                        buf.append(esc)
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
        return '"' + (node.replace('\\', '\\\\')
                          .replace('"', '\\"')
                          .replace('\n', '\\n')) + '"'
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


def ensure_lib_symbol_cached(tree, lib_id):
    """Make sure tree's top-level lib_symbols section has a cached copy of
    lib_id's definition. KiCad 9 fails to load a schematic that references a
    lib_id with no matching cache entry, even when the global sym-lib-table
    resolves the library nickname correctly -- discovered while wiring up
    the first PWR_FLAG symbol this project ever added (the template's own
    lib_symbols only caches the symbols it itself uses). No-op if lib_id is
    already cached.
    """
    nickname, symbol_name = lib_id.split(":", 1)
    lib_symbols = next(n for n in tree if get_tag(n) == "lib_symbols")
    if any(isinstance(s, list) and s[1] == lib_id for s in lib_symbols[1:]):
        return
    lib_path = _SYMBOL_LIBRARY_PATHS[nickname]
    lib_tree = parse(open(lib_path).read())
    definition = next(n for n in lib_tree
                       if isinstance(n, list) and get_tag(n) == "symbol" and n[1] == symbol_name)
    # Cached entries are keyed by the full "nickname:SymbolName" lib_id, not
    # the library's own bare symbol name -- e.g. the template's cache holds
    # "power:+3.3V", not "+3.3V". Referencing a lib_id with no cache entry
    # under this exact name crashes kicad-cli's loader (confirmed: it is NOT
    # graceful, unlike a lib_id with no entry at all, which fails to load
    # cleanly instead).
    definition[1] = lib_id
    lib_symbols.append(definition)


def _effects(size="1.27"):
    return [Sym("effects"), [Sym("font"), [Sym("size"), Sym(size), Sym(size)]]]


def make_power_symbol(lib_id, ref, value, at_xy, project, root_uuid_str):
    x, y = at_xy
    new_uuid = str(_uuid.uuid4())
    return [
        Sym("symbol"),
        [Sym("lib_id"), lib_id],
        [Sym("at"), Sym(str(x)), Sym(str(y)), Sym("0")],
        [Sym("unit"), Sym("1")],
        [Sym("exclude_from_sim"), Sym("no")],
        [Sym("in_bom"), Sym("yes")],
        [Sym("on_board"), Sym("yes")],
        [Sym("dnp"), Sym("no")],
        [Sym("uuid"), new_uuid],
        [Sym("property"), "Reference", ref, [Sym("at"), Sym(str(x)), Sym(str(y + 3.81)), Sym("0")],
         [Sym("effects"), [Sym("font"), [Sym("size"), Sym("1.27"), Sym("1.27")]], [Sym("hide"), Sym("yes")]]],
        [Sym("property"), "Value", value, [Sym("at"), Sym(str(x)), Sym(str(y - 4.32)), Sym("0")], _effects()],
        [Sym("property"), "Footprint", "", [Sym("at"), Sym(str(x)), Sym(str(y)), Sym("0")], _effects()],
        [Sym("property"), "Datasheet", "", [Sym("at"), Sym(str(x)), Sym(str(y)), Sym("0")], _effects()],
        [Sym("pin"), "1", [Sym("uuid"), str(_uuid.uuid4())]],
        [Sym("instances"), [Sym("project"), project,
                             [Sym("path"), "/" + root_uuid_str,
                              [Sym("reference"), ref], [Sym("unit"), Sym("1")]]]],
    ]


def make_db9_symbol(ref, value, at_xy, project, root_uuid_str):
    x, y = at_xy
    new_uuid = str(_uuid.uuid4())
    return [
        Sym("symbol"),
        [Sym("lib_id"), "Connector:DE9_Socket_MountingHoles"],
        [Sym("at"), Sym(str(x)), Sym(str(y)), Sym("0")],
        [Sym("unit"), Sym("1")],
        [Sym("exclude_from_sim"), Sym("no")],
        [Sym("in_bom"), Sym("yes")],
        [Sym("on_board"), Sym("yes")],
        [Sym("dnp"), Sym("no")],
        [Sym("uuid"), new_uuid],
        [Sym("property"), "Reference", ref, [Sym("at"), Sym(str(x)), Sym(str(y - 17.78)), Sym("0")], _effects()],
        [Sym("property"), "Value", value, [Sym("at"), Sym(str(x)), Sym(str(y - 15.875)), Sym("0")], _effects()],
        [Sym("property"), "Footprint",
         "Connector_Dsub:DSUB-9_Socket_Vertical_P2.77x2.84mm_MountingHoles",
         [Sym("at"), Sym(str(x)), Sym(str(y)), Sym("0")],
         [Sym("effects"), [Sym("font"), [Sym("size"), Sym("1.27"), Sym("1.27")]], [Sym("hide"), Sym("yes")]]],
        [Sym("property"), "Datasheet", "~", [Sym("at"), Sym(str(x)), Sym(str(y)), Sym("0")],
         [Sym("effects"), [Sym("font"), [Sym("size"), Sym("1.27"), Sym("1.27")]], [Sym("hide"), Sym("yes")]]],
        [Sym("instances"), [Sym("project"), project,
                             [Sym("path"), "/" + root_uuid_str,
                              [Sym("reference"), ref], [Sym("unit"), Sym("1")]]]],
    ]


def make_label(text, at_xy, angle=180):
    x, y = at_xy
    return [Sym("label"), text, [Sym("at"), Sym(str(x)), Sym(str(y)), Sym(str(angle))],
            [Sym("effects"), [Sym("font"), [Sym("size"), Sym("1.27"), Sym("1.27")]],
             [Sym("justify"), Sym("left"), Sym("bottom")]],
            [Sym("uuid"), str(_uuid.uuid4())]]


def make_no_connect(at_xy):
    x, y = at_xy
    return [Sym("no_connect"), [Sym("at"), Sym(str(x)), Sym(str(y))], [Sym("uuid"), str(_uuid.uuid4())]]
