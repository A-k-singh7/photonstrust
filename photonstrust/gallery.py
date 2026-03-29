"""Scenario gallery -- pre-built configurations for common QKD use cases.

Example
-------
    from photonstrust.gallery import list_scenarios, run_scenario

    for s in list_scenarios(category="qkd", difficulty="beginner"):
        print(s.name, "-", s.title)

    result = run_scenario("bb84_metro")
    print(result.summary())
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# ScenarioMeta dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScenarioMeta:
    """Metadata and configuration for a pre-built scenario."""

    name: str
    title: str
    description: str
    category: str       # "qkd", "pic", "network", "satellite", "full_stack"
    difficulty: str     # "beginner", "intermediate", "advanced"
    personas: tuple[str, ...]
    tags: tuple[str, ...]
    config: dict        # ready-to-use kwargs for the appropriate easy.py function
    runner: str         # which easy.py function to call
    notes: str = ""


# ---------------------------------------------------------------------------
# Built-in scenario registry
# ---------------------------------------------------------------------------

_SCENARIOS: tuple[ScenarioMeta, ...] = (
    # 1. bb84_metro
    ScenarioMeta(
        name="bb84_metro",
        title="BB84 Metropolitan QKD Link",
        description=(
            "Simulate a BB84 decoy-state QKD link over a 20 km metropolitan "
            "fiber connecting two data-centers. Uses C-band (1550 nm) photons "
            "and SNSPD detectors for high key rates."
        ),
        category="qkd",
        difficulty="beginner",
        personas=("researcher", "engineer", "student"),
        tags=("bb84", "metro", "fiber", "c_band"),
        runner="simulate_qkd_link",
        config={
            "protocol": "bb84",
            "distance_km": 20,
            "band": "c_1550",
            "detector": "snspd",
            "include_uncertainty": False,
        },
    ),
    # 2. bb84_intercity
    ScenarioMeta(
        name="bb84_intercity",
        title="BB84 Intercity QKD Link",
        description=(
            "Simulate a BB84 decoy-state QKD link over a 100 km intercity "
            "fiber. Demonstrates the impact of fiber loss on key rate at "
            "longer distances."
        ),
        category="qkd",
        difficulty="beginner",
        personas=("researcher", "engineer"),
        tags=("bb84", "intercity", "fiber", "c_band", "long_distance"),
        runner="simulate_qkd_link",
        config={
            "protocol": "bb84",
            "distance_km": 100,
            "band": "c_1550",
            "detector": "snspd",
            "include_uncertainty": False,
        },
    ),
    # 3. bbm92_campus
    ScenarioMeta(
        name="bbm92_campus",
        title="BBM92 Campus Entanglement Link",
        description=(
            "Simulate a BBM92 entanglement-based QKD link over a short 5 km "
            "campus fiber. Demonstrates entanglement-based security without "
            "trusted source assumptions."
        ),
        category="qkd",
        difficulty="beginner",
        personas=("researcher", "student"),
        tags=("bbm92", "entanglement", "campus", "fiber"),
        runner="simulate_qkd_link",
        config={
            "protocol": "bbm92",
            "distance_km": 5,
            "band": "c_1550",
            "detector": "snspd",
            "include_uncertainty": False,
        },
    ),
    # 4. mdi_relay
    ScenarioMeta(
        name="mdi_relay",
        title="MDI-QKD Untrusted Relay",
        description=(
            "Simulate measurement-device-independent QKD with an untrusted "
            "relay node at 50 km. Eliminates all detector side-channel "
            "attacks."
        ),
        category="qkd",
        difficulty="intermediate",
        personas=("researcher", "engineer"),
        tags=("mdi", "relay", "side_channel", "fiber"),
        runner="simulate_qkd_link",
        config={
            "protocol": "mdi_qkd",
            "distance_km": 50,
            "band": "c_1550",
            "detector": "snspd",
            "include_uncertainty": False,
        },
    ),
    # 5. tf_long_haul
    ScenarioMeta(
        name="tf_long_haul",
        title="Twin-Field QKD Long-Haul",
        description=(
            "Simulate twin-field QKD over a sweep from 0 to 400 km in 20 km "
            "steps. TF-QKD surpasses the PLOB bound, enabling key generation "
            "at distances beyond 300 km without quantum repeaters."
        ),
        category="qkd",
        difficulty="intermediate",
        personas=("researcher",),
        tags=("tf_qkd", "long_haul", "plob_bound", "fiber"),
        runner="simulate_qkd_link",
        config={
            "protocol": "tf_qkd",
            "distance_km": {"start": 0, "stop": 400, "step": 20},
            "band": "c_1550",
            "detector": "snspd",
            "include_uncertainty": False,
        },
    ),
    # 6. cv_qkd_urban
    ScenarioMeta(
        name="cv_qkd_urban",
        title="CV-QKD Urban Link",
        description=(
            "Simulate continuous-variable QKD over short urban distances "
            "(0-30 km in 2 km steps). CV-QKD uses homodyne/heterodyne "
            "detection compatible with standard telecom hardware."
        ),
        category="qkd",
        difficulty="intermediate",
        personas=("engineer", "telecom_operator"),
        tags=("cv_qkd", "urban", "continuous_variable", "telecom"),
        runner="simulate_qkd_link",
        config={
            "protocol": "cv_qkd",
            "distance_km": {"start": 0, "stop": 30, "step": 2},
            "band": "c_1550",
            "detector": "snspd",
            "include_uncertainty": False,
        },
    ),
    # 7. satellite_leo
    ScenarioMeta(
        name="satellite_leo",
        title="LEO Satellite QKD Downlink",
        description=(
            "Plan a low-Earth-orbit (LEO) satellite QKD constellation at "
            "500 km altitude. Simulates pass scheduling and expected key "
            "volumes for satellite-to-ground BB84."
        ),
        category="satellite",
        difficulty="intermediate",
        personas=("researcher", "space_engineer"),
        tags=("satellite", "leo", "bb84", "downlink"),
        runner="plan_satellite",
        config={
            "orbit_altitude_km": 500,
            "protocol": "bb84",
        },
    ),
    # 8. satellite_geo
    ScenarioMeta(
        name="satellite_geo",
        title="GEO Satellite QKD (Challenging)",
        description=(
            "Plan a geostationary-orbit (GEO) satellite QKD link at "
            "36 000 km altitude. This extreme scenario illustrates the "
            "difficulty of QKD at GEO distances due to very high free-space "
            "loss."
        ),
        category="satellite",
        difficulty="advanced",
        personas=("researcher",),
        tags=("satellite", "geo", "bb84", "extreme_loss"),
        runner="plan_satellite",
        config={
            "orbit_altitude_km": 36000,
            "protocol": "bb84",
        },
    ),
    # 9. underwater_harbor
    ScenarioMeta(
        name="underwater_harbor",
        title="Underwater Harbor QKD",
        description=(
            "Simulate QKD over a very short (0.5 km) underwater channel "
            "between harbor-side facilities. Uses NIR 850 nm band and "
            "silicon APD detectors suited to shorter wavelengths."
        ),
        category="qkd",
        difficulty="intermediate",
        personas=("researcher", "defense"),
        tags=("underwater", "harbor", "nir", "short_range"),
        runner="simulate_qkd_link",
        config={
            "protocol": "bb84",
            "distance_km": 0.5,
            "band": "nir_850",
            "detector": "si_apd",
            "channel_model": "fiber",
            "include_uncertainty": False,
        },
    ),
    # 10. pic_mzi_switch
    ScenarioMeta(
        name="pic_mzi_switch",
        title="MZI Optical Switch (PIC)",
        description=(
            "Design a simple Mach-Zehnder interferometer (MZI) optical "
            "switch built from two MMI 2x2 couplers on a silicon-photonics "
            "platform."
        ),
        category="pic",
        difficulty="beginner",
        personas=("pic_designer", "student"),
        tags=("pic", "mzi", "switch", "mmi"),
        runner="design_pic",
        config={
            "components": ["mmi_2x2", "mmi_2x2"],
            "connections": [
                {"from": [0, "out1"], "to": [1, "in1"]},
            ],
        },
    ),
    # 11. pic_awg_demux
    ScenarioMeta(
        name="pic_awg_demux",
        title="AWG Wavelength Demultiplexer (PIC)",
        description=(
            "Design an arrayed waveguide grating (AWG) wavelength "
            "demultiplexer for WDM-compatible QKD systems. Operates at "
            "1550 nm."
        ),
        category="pic",
        difficulty="intermediate",
        personas=("pic_designer", "engineer"),
        tags=("pic", "awg", "demux", "wdm"),
        runner="design_pic",
        config={
            "components": ["awg"],
            "wavelength_nm": 1550.0,
        },
    ),
    # 12. network_3node
    ScenarioMeta(
        name="network_3node",
        title="3-Node Linear QKD Network",
        description=(
            "Plan a simple 3-node linear QKD network: Alice -- Relay -- Bob. "
            "The relay node enables key distribution over a combined 50 km "
            "distance with trusted-node key relaying."
        ),
        category="network",
        difficulty="beginner",
        personas=("network_planner", "student"),
        tags=("network", "linear", "relay", "trusted_node"),
        runner="plan_network",
        config={
            "nodes": ["Alice", "Relay", "Bob"],
            "links": [
                {"a": "Alice", "b": "Relay", "distance_km": 20},
                {"a": "Relay", "b": "Bob", "distance_km": 30},
            ],
        },
    ),
    # 13. network_backbone
    ScenarioMeta(
        name="network_backbone",
        title="5-Node Backbone Ring Network",
        description=(
            "Plan a 5-node backbone QKD network with ring topology plus a "
            "shortcut link for redundancy. Demonstrates path diversity and "
            "bottleneck analysis."
        ),
        category="network",
        difficulty="intermediate",
        personas=("network_planner", "telecom_operator"),
        tags=("network", "backbone", "ring", "redundancy"),
        runner="plan_network",
        config={
            "nodes": ["HQ", "DataCenter1", "DataCenter2", "DataCenter3", "DR_Site"],
            "links": [
                {"a": "HQ", "b": "DataCenter1", "distance_km": 15},
                {"a": "DataCenter1", "b": "DataCenter2", "distance_km": 25},
                {"a": "DataCenter2", "b": "DataCenter3", "distance_km": 20},
                {"a": "DataCenter3", "b": "DR_Site", "distance_km": 30},
                {"a": "DR_Site", "b": "HQ", "distance_km": 35},
                {"a": "HQ", "b": "DataCenter2", "distance_km": 40},
            ],
        },
    ),
    # 14. repeater_chain
    ScenarioMeta(
        name="repeater_chain",
        title="Multi-Segment Repeater Chain Analysis",
        description=(
            "Compare BB84, TF-QKD, and SNS-TF-QKD protocols over a sweep "
            "from 0 to 500 km in 25 km steps. Highlights which protocol "
            "families are best suited for repeater-chain deployments."
        ),
        category="qkd",
        difficulty="advanced",
        personas=("researcher",),
        tags=("repeater", "comparison", "tf_qkd", "sns_tf_qkd", "long_haul"),
        runner="compare_protocols",
        config={
            "protocols": ["bb84", "tf_qkd", "sns_tf_qkd"],
            "distances": {"start": 0, "stop": 500, "step": 25},
        },
    ),
    # 15. full_stack_demo
    ScenarioMeta(
        name="full_stack_demo",
        title="Full-Stack Protocol Comparison",
        description=(
            "Compare all available QKD protocols over 0-100 km in 5 km "
            "steps. Provides a comprehensive overview of every protocol "
            "supported by PhotonsTrust."
        ),
        category="full_stack",
        difficulty="advanced",
        personas=("researcher", "decision_maker"),
        tags=("full_stack", "comparison", "all_protocols"),
        runner="compare_protocols",
        config={
            "protocols": None,
            "distances": {"start": 0, "stop": 100, "step": 5},
        },
    ),
)


# Build index for O(1) lookup
_INDEX: dict[str, ScenarioMeta] = {s.name: s for s in _SCENARIOS}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def list_scenarios(
    category: str | None = None,
    difficulty: str | None = None,
) -> list[ScenarioMeta]:
    """Return scenarios, optionally filtered by *category* and/or *difficulty*.

    Parameters
    ----------
    category
        Filter by category (``"qkd"``, ``"pic"``, ``"network"``,
        ``"satellite"``, ``"full_stack"``).  ``None`` means no filter.
    difficulty
        Filter by difficulty (``"beginner"``, ``"intermediate"``,
        ``"advanced"``).  ``None`` means no filter.

    Returns
    -------
    list[ScenarioMeta]
    """
    result = list(_SCENARIOS)
    if category is not None:
        result = [s for s in result if s.category == category]
    if difficulty is not None:
        result = [s for s in result if s.difficulty == difficulty]
    return result


def load_scenario(name: str) -> dict:
    """Return a copy of the config dict for scenario *name*.

    The returned dict contains the kwargs that should be passed to the
    scenario's runner function (e.g. ``simulate_qkd_link``).

    Raises
    ------
    KeyError
        If *name* is not a registered scenario.
    """
    meta = _INDEX.get(name)
    if meta is None:
        raise KeyError(
            f"Unknown scenario {name!r}. "
            f"Available: {', '.join(scenario_names())}"
        )
    # Return a shallow copy so callers can mutate without affecting the registry
    return dict(meta.config)


def describe_scenario(name: str) -> str:
    """Return a human-readable multi-line description of scenario *name*.

    Raises
    ------
    KeyError
        If *name* is not a registered scenario.
    """
    meta = _INDEX.get(name)
    if meta is None:
        raise KeyError(
            f"Unknown scenario {name!r}. "
            f"Available: {', '.join(scenario_names())}"
        )
    lines = [
        f"Scenario: {meta.name}",
        f"Title:    {meta.title}",
        f"Category: {meta.category}  |  Difficulty: {meta.difficulty}",
        "",
        meta.description,
        "",
        f"Runner:   {meta.runner}",
        f"Personas: {', '.join(meta.personas)}",
        f"Tags:     {', '.join(meta.tags)}",
    ]
    if meta.notes:
        lines.append(f"Notes:    {meta.notes}")
    return "\n".join(lines)


def scenario_names() -> list[str]:
    """Return a sorted list of all registered scenario names."""
    return sorted(_INDEX.keys())


def run_scenario(name: str, **extra_kwargs: Any) -> Any:
    """Run scenario *name* and return its result object.

    The scenario's pre-built config is merged with any *extra_kwargs*
    supplied by the caller (caller overrides win).

    Parameters
    ----------
    name
        Registered scenario name (see :func:`scenario_names`).
    **extra_kwargs
        Override or extend the scenario config.

    Returns
    -------
    The result object produced by the runner function (e.g.
    :class:`~photonstrust.easy.QKDLinkResult`).

    Raises
    ------
    KeyError
        If *name* is not a registered scenario.
    """
    meta = _INDEX.get(name)
    if meta is None:
        raise KeyError(
            f"Unknown scenario {name!r}. "
            f"Available: {', '.join(scenario_names())}"
        )

    # Import the runner from easy.py
    easy = importlib.import_module("photonstrust.easy")
    runner_fn = getattr(easy, meta.runner)

    # Merge config with caller overrides
    kwargs = dict(meta.config)
    kwargs.update(extra_kwargs)

    return runner_fn(**kwargs)
