"""Tests for the PICComponentBase and QKDProtocolBase ABC infrastructure."""

from __future__ import annotations

import numpy as np
import pytest


class TestPICComponentDiscovery:
    """Verify all PIC components are auto-discovered and have valid schemas."""

    def test_all_17_components_discovered(self):
        from photonstrust.components.pic.library import all_component_classes
        classes = all_component_classes()
        assert len(classes) >= 17

    def test_each_component_has_valid_meta(self):
        from photonstrust.components.pic.library import all_component_classes
        for kind, cls in all_component_classes().items():
            meta = cls.meta()
            assert meta.kind == kind
            assert meta.title
            assert meta.category == "pic"
            assert len(meta.in_ports) >= 0
            assert len(meta.out_ports) >= 0

    def test_each_component_has_params_schema(self):
        from photonstrust.components.pic.library import all_component_classes
        for kind, cls in all_component_classes().items():
            schema_cls = cls.params_schema()
            schema = schema_cls.model_json_schema()
            assert "properties" in schema, f"{kind} schema missing properties"
            assert "title" in schema

    def test_params_schema_has_defaults(self):
        from photonstrust.components.pic.library import all_component_classes
        for kind, cls in all_component_classes().items():
            if kind.startswith("pic.touchstone"):
                continue  # touchstone file_path has no default
            schema_cls = cls.params_schema()
            instance = schema_cls()  # should work with all defaults
            assert instance is not None, f"{kind} params not instantiable with defaults"

    def test_forward_matrix_with_defaults(self):
        from photonstrust.components.pic.library import all_component_classes
        skip = {"pic.touchstone_2port", "pic.touchstone_nport"}
        for kind, cls in all_component_classes().items():
            if kind in skip:
                continue
            params = cls.params_schema()()
            mat = cls.forward_matrix(params)
            mat_np = np.asarray(mat)
            assert mat_np.ndim == 2, f"{kind} forward_matrix should return 2-D array"

    def test_forward_matrix_accepts_dict(self):
        from photonstrust.components.pic.library import all_component_classes
        cls = all_component_classes()["pic.mmi"]
        params_dict = {"n_ports_in": 1, "n_ports_out": 2, "insertion_loss_db": 0.3}
        mat = cls.forward_matrix(params_dict)
        assert mat.shape == (2, 1)

    def test_component_class_lookup(self):
        from photonstrust.components.pic.library import component_class
        cls = component_class("pic.mmi")
        assert cls is not None
        assert cls.meta().kind == "pic.mmi"

    def test_component_class_returns_none_for_unknown(self):
        from photonstrust.components.pic.library import component_class
        assert component_class("pic.nonexistent") is None


class TestQKDProtocolDiscovery:
    """Verify all QKD protocols are auto-discovered and have valid schemas."""

    def test_all_9_protocols_discovered(self):
        from photonstrust.qkd_protocols.registry import all_protocol_classes
        classes = all_protocol_classes()
        assert len(classes) >= 9

    def test_each_protocol_has_valid_meta(self):
        from photonstrust.qkd_protocols.registry import all_protocol_classes
        for pid, cls in all_protocol_classes().items():
            meta = cls.meta()
            assert meta.protocol_id == pid
            assert meta.title
            assert len(meta.channel_models) >= 1

    def test_each_protocol_has_params_schema(self):
        from photonstrust.qkd_protocols.registry import all_protocol_classes
        for pid, cls in all_protocol_classes().items():
            schema_cls = cls.params_schema()
            schema = schema_cls.model_json_schema()
            assert "properties" in schema, f"{pid} schema missing properties"

    def test_params_schema_instantiable_with_defaults(self):
        from photonstrust.qkd_protocols.registry import all_protocol_classes
        for pid, cls in all_protocol_classes().items():
            instance = cls.params_schema()()
            assert instance is not None, f"{pid} params not instantiable with defaults"

    def test_fiber_only_protocols_reject_free_space(self):
        from photonstrust.qkd_protocols.registry import all_protocol_classes
        fiber_only = {"mdi_qkd", "amdi_qkd", "pm_qkd", "tf_qkd", "sns_tf_qkd"}
        free_space_scenario = {"channel": {"model": "free_space"}}
        for pid, cls in all_protocol_classes().items():
            result = cls.applicability(free_space_scenario)
            if pid in fiber_only:
                assert result.status == "fail", f"{pid} should fail for free_space"
            else:
                assert result.status == "pass", f"{pid} should pass for free_space"

    def test_protocol_class_lookup(self):
        from photonstrust.qkd_protocols.registry import protocol_class
        cls = protocol_class("bb84_decoy")
        assert cls is not None
        assert cls.meta().protocol_id == "bb84_decoy"

    def test_protocol_class_returns_none_for_unknown(self):
        from photonstrust.qkd_protocols.registry import protocol_class
        assert protocol_class("nonexistent_protocol") is None

    def test_backward_compatible_with_existing_registry(self):
        """The old _PROTOCOLS dict still works alongside the new class registry."""
        from photonstrust.qkd_protocols.registry import (
            available_protocols,
            resolve_protocol_module,
        )
        protos = available_protocols()
        assert "bb84_decoy" in protos
        module = resolve_protocol_module("bb84")
        assert module.protocol_id == "bb84_decoy"
