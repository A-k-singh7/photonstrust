"""TOML-based declarative PIC netlist format."""
from __future__ import annotations

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    try:
        import tomli as tomllib  # fallback
    except ModuleNotFoundError:
        tomllib = None  # type: ignore


def _toml_loads(text: str) -> dict:
    """Parse TOML text, trying tomllib then tomli."""
    if tomllib is not None:
        return tomllib.loads(text)
    # Minimal fallback for simple TOML (only handles our subset)
    raise ImportError("No TOML parser available. Install tomli: pip install tomli")


def load_graph_toml(path: str) -> dict:
    """Load a TOML PIC netlist file and return internal graph dict.

    Expected format:
    [circuit]
    id = "mzi_2x2"
    wavelength_nm = 1550.0

    [[nodes]]
    id = "gc_in"
    kind = "pic.grating_coupler"
    [nodes.params]
    insertion_loss_db = 2.5

    [[edges]]
    from = "gc_in"
    to = "wg1"
    from_port = "out"
    to_port = "in"
    """
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    return load_graph_toml_str(text)


def load_graph_toml_str(text: str) -> dict:
    """Parse TOML string into graph dict."""
    data = _toml_loads(text)

    circuit = data.get("circuit", {})
    graph: dict = {
        "id": circuit.get("id", "unnamed"),
        "wavelength_nm": circuit.get("wavelength_nm", 1550.0),
    }

    # Nodes
    nodes = []
    for n in data.get("nodes", []):
        node = {
            "id": n["id"],
            "kind": n.get("kind", "pic.waveguide"),
        }
        if "params" in n:
            node["params"] = dict(n["params"])
        else:
            node["params"] = {}
        nodes.append(node)
    graph["nodes"] = nodes

    # Edges
    edges = []
    for e in data.get("edges", []):
        edge = {
            "from": e["from"],
            "to": e["to"],
            "from_port": e.get("from_port", "out"),
            "to_port": e.get("to_port", "in"),
        }
        edges.append(edge)
    graph["edges"] = edges

    return graph


def save_graph_toml(graph: dict, path: str) -> None:
    """Export graph dict to TOML file."""
    text = save_graph_toml_str(graph)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def save_graph_toml_str(graph: dict) -> str:
    """Export graph dict to TOML string."""
    lines = ["[circuit]"]
    lines.append(f'id = "{graph.get("id", "unnamed")}"')
    if "wavelength_nm" in graph:
        lines.append(f"wavelength_nm = {graph['wavelength_nm']}")
    lines.append("")

    for node in graph.get("nodes", []):
        lines.append("[[nodes]]")
        lines.append(f'id = "{node["id"]}"')
        if "kind" in node:
            lines.append(f'kind = "{node["kind"]}"')
        params = node.get("params", {})
        if params:
            lines.append("[nodes.params]")
            for k, v in params.items():
                if isinstance(v, str):
                    lines.append(f'{k} = "{v}"')
                elif isinstance(v, bool):
                    lines.append(f"{k} = {'true' if v else 'false'}")
                elif isinstance(v, (int, float)):
                    lines.append(f"{k} = {v}")
            lines.append("")
        else:
            lines.append("")

    for edge in graph.get("edges", []):
        lines.append("[[edges]]")
        # Use 'from' and 'to' keys directly -- valid in TOML
        lines.append(f'from = "{edge["from"]}"')
        lines.append(f'to = "{edge["to"]}"')
        if "from_port" in edge:
            lines.append(f'from_port = "{edge["from_port"]}"')
        if "to_port" in edge:
            lines.append(f'to_port = "{edge["to_port"]}"')
        lines.append("")

    return "\n".join(lines) + "\n"
