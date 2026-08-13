# SPDX-FileCopyrightText: 2026 Trackmind
# SPDX-License-Identifier: MIT

"""
tests/test_schema_resolution.py

Direct unit tests for introspection's JSON Schema flattening
(_resolve_schema / _build_input_schema) — the most intricate pure logic in
the pipeline, previously only exercised indirectly through live fixtures.

Covers the G1/G10 fixes ($ref/$defs, allOf, oneOf/anyOf, property-level refs)
plus pathological shapes: deep chains, cycles, and combos.
"""

from typing import Any

from introspection.introspect import (
    _build_input_schema,
    _map_tool_annotations,
    _resolve_schema,
)

# ---------------------------------------------------------------------------
# $ref resolution
# ---------------------------------------------------------------------------


class TestRefResolution:
    def test_top_level_ref(self):
        schema = {
            "$ref": "#/$defs/Params",
            "$defs": {
                "Params": {
                    "type": "object",
                    "properties": {"q": {"type": "string", "description": "Query."}},
                    "required": ["q"],
                }
            },
        }
        resolved = _resolve_schema(schema)
        assert "q" in resolved["properties"]
        assert resolved["required"] == ["q"]

    def test_definitions_key_also_supported(self):
        """Draft-07 uses 'definitions', newer drafts '$defs' — both occur in the wild."""
        schema = {
            "$ref": "#/definitions/Params",
            "definitions": {
                "Params": {"type": "object", "properties": {"x": {"type": "integer"}}},
            },
        }
        resolved = _resolve_schema(schema)
        assert "x" in resolved["properties"]

    def test_chained_refs_within_depth(self):
        """A → B → C chain, well within the depth guard."""
        schema = {
            "$ref": "#/$defs/A",
            "$defs": {
                "A": {"$ref": "#/$defs/B"},
                "B": {"$ref": "#/$defs/C"},
                "C": {"type": "object", "properties": {"leaf": {"type": "string"}}},
            },
        }
        resolved = _resolve_schema(schema)
        assert "leaf" in resolved["properties"]

    def test_cyclic_refs_terminate(self):
        """A → B → A must terminate via the depth guard, not hang or recurse forever."""
        schema = {
            "$ref": "#/$defs/A",
            "$defs": {
                "A": {"$ref": "#/$defs/B"},
                "B": {"$ref": "#/$defs/A"},
            },
        }
        resolved = _resolve_schema(schema)  # no RecursionError, no hang
        assert isinstance(resolved, dict)

    def test_very_deep_chain_terminates(self):
        """A 15-link chain exceeds the depth-10 guard: must degrade gracefully
        (returning an unresolved node), never crash."""
        defs: dict[str, Any] = {f"L{i}": {"$ref": f"#/$defs/L{i + 1}"} for i in range(15)}
        defs["L15"] = {"type": "object", "properties": {"deep": {"type": "string"}}}
        schema = {"$ref": "#/$defs/L0", "$defs": defs}
        resolved = _resolve_schema(schema)
        assert isinstance(resolved, dict)

    def test_unresolvable_external_ref(self):
        """A ref to another document can't be resolved without a fetch —
        must not crash; produces an (accurately) empty shape."""
        schema = {"$ref": "https://example.com/schema.json#/Foo"}
        resolved = _resolve_schema(schema)
        assert isinstance(resolved, dict)

    def test_dangling_local_ref(self):
        """$ref points at a $defs entry that doesn't exist."""
        schema = {"$ref": "#/$defs/Missing", "$defs": {}}
        resolved = _resolve_schema(schema)
        assert isinstance(resolved, dict)
        assert resolved.get("properties", {}) == {}


# ---------------------------------------------------------------------------
# allOf / oneOf / anyOf composition
# ---------------------------------------------------------------------------


class TestComposition:
    def test_allof_merges_properties_and_required(self):
        schema = {
            "allOf": [
                {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]},
                {
                    "type": "object",
                    "properties": {"status": {"type": "string"}},
                    "required": ["status"],
                },
            ]
        }
        resolved = _resolve_schema(schema)
        assert set(resolved["properties"]) == {"id", "status"}
        assert set(resolved["required"]) == {"id", "status"}

    def test_oneof_unions_properties_and_marks_union(self):
        schema = {
            "oneOf": [
                {
                    "type": "object",
                    "properties": {"text": {"type": "string"}},
                    "required": ["text"],
                },
                {
                    "type": "object",
                    "properties": {"expr": {"type": "object"}},
                    "required": ["expr"],
                },
            ]
        }
        resolved = _resolve_schema(schema)
        assert set(resolved["properties"]) == {"text", "expr"}
        assert resolved["x-mcp-rubriq-is-union"] is True
        # Branch-level required lists must NOT merge — the variants are alternatives.
        assert resolved["required"] == []

    def test_anyof_treated_like_oneof(self):
        schema = {
            "anyOf": [
                {"type": "object", "properties": {"a": {"type": "string"}}},
                {"type": "object", "properties": {"b": {"type": "string"}}},
            ]
        }
        resolved = _resolve_schema(schema)
        assert set(resolved["properties"]) == {"a", "b"}
        assert resolved["x-mcp-rubriq-is-union"] is True

    def test_allof_of_refs(self):
        """The realistic shape: allOf composing two $refs (schema_edge_cases fixture)."""
        schema = {
            "allOf": [{"$ref": "#/$defs/A"}, {"$ref": "#/$defs/B"}],
            "$defs": {
                "A": {
                    "type": "object",
                    "properties": {"id": {"type": "string"}},
                    "required": ["id"],
                },
                "B": {"type": "object", "properties": {"patch": {"type": "object"}}},
            },
        }
        resolved = _resolve_schema(schema)
        assert set(resolved["properties"]) == {"id", "patch"}
        assert resolved["required"] == ["id"]

    def test_oneof_of_refs_with_nested_allof(self):
        """Combo: oneOf → $ref → allOf. Exercises recursion across all three."""
        schema = {
            "oneOf": [
                {"$ref": "#/$defs/Composite"},
                {"type": "object", "properties": {"raw": {"type": "string"}}},
            ],
            "$defs": {
                "Composite": {
                    "allOf": [
                        {"type": "object", "properties": {"x": {"type": "integer"}}},
                        {"type": "object", "properties": {"y": {"type": "integer"}}},
                    ]
                }
            },
        }
        resolved = _resolve_schema(schema)
        assert {"x", "y", "raw"} <= set(resolved["properties"])
        assert resolved["x-mcp-rubriq-is-union"] is True


# ---------------------------------------------------------------------------
# _build_input_schema — property-level resolution and model mapping
# ---------------------------------------------------------------------------


class TestBuildInputSchema:
    def test_property_level_ref_resolved(self):
        """Regression: a property whose value is itself a $ref must resolve
        (type/description found one level down), not read as type-missing."""
        resolved = _resolve_schema(
            {
                "type": "object",
                "properties": {
                    "filters": {"$ref": "#/$defs/Filters"},
                },
                "$defs": {
                    "Filters": {"type": "object", "properties": {"author": {"type": "string"}}},
                },
            }
        )
        built = _build_input_schema(resolved)
        assert built.properties["filters"].type == "object"

    def test_non_dict_property_value_tolerated(self):
        """A malformed schema can put a non-dict where a property schema belongs
        (e.g. true/false JSON Schema booleans). Must not crash."""
        built = _build_input_schema({"type": "object", "properties": {"anything": True}})
        assert built.properties["anything"].type is None

    def test_union_flag_carried_into_model(self):
        resolved = _resolve_schema(
            {
                "oneOf": [
                    {"type": "object", "properties": {"a": {"type": "string"}}},
                    {"type": "object", "properties": {"b": {"type": "string"}}},
                ]
            }
        )
        built = _build_input_schema(resolved)
        assert built.is_union is True

    def test_enum_preserved(self):
        built = _build_input_schema(
            {
                "type": "object",
                "properties": {"status": {"type": "string", "enum": ["open", "closed"]}},
            }
        )
        assert built.properties["status"].enum == ["open", "closed"]

    def test_empty_schema(self):
        built = _build_input_schema({})
        assert built.type == "object"
        assert built.properties == {}
        assert built.required == []

    def test_extra_preserves_min_max(self):
        """Regression: extra was declared but never populated,
        so the annotator's needs_bounds check ("minimum" in prop_obj.extra)
        always saw {} and ignored real bounds entirely. A port property WITH
        explicit minimum/maximum must have them survive into extra."""
        built = _build_input_schema(
            {
                "type": "object",
                "properties": {
                    "port": {
                        "type": "integer",
                        "description": "Port.",
                        "minimum": 1,
                        "maximum": 65535,
                    },
                },
            }
        )
        assert built.properties["port"].extra == {"minimum": 1, "maximum": 65535}

    def test_schema_extra_preserves_additional_properties(self):
        built = _build_input_schema(
            {
                "type": "object",
                "properties": {"a": {"type": "string"}},
                "additionalProperties": True,
            }
        )
        assert built.extra == {"additionalProperties": True}

    def test_modeled_keys_not_duplicated_into_extra(self):
        built = _build_input_schema(
            {
                "type": "object",
                "properties": {"a": {"type": "string", "description": "d", "enum": ["x"]}},
                "required": ["a"],
            }
        )
        assert built.properties["a"].extra == {}
        assert built.extra == {}


class TestMapToolAnnotations:
    """camelCase spec hints → snake_case model, None-preserving."""

    def test_none_input_returns_none(self):
        assert _map_tool_annotations(None) is None

    def test_dict_input_mapped(self):
        result = _map_tool_annotations(
            {
                "title": "Delete",
                "readOnlyHint": False,
                "destructiveHint": True,
                "idempotentHint": False,
                "openWorldHint": True,
            }
        )
        assert result is not None
        assert result.title == "Delete"
        assert result.read_only_hint is False
        assert result.destructive_hint is True
        assert result.idempotent_hint is False
        assert result.open_world_hint is True

    def test_partial_dict_leaves_others_none(self):
        """A partially-annotated tool: unset hints stay None (not coerced to a
        default), so 'never declared' is distinguishable from explicit false."""
        result = _map_tool_annotations({"readOnlyHint": True})
        assert result is not None
        assert result.read_only_hint is True
        assert result.destructive_hint is None
        assert result.idempotent_hint is None

    def test_pydantic_model_input(self):
        """The SDK path yields a model with .model_dump(), not a dict."""
        from mcp.types import ToolAnnotations as SDKToolAnnotations

        raw = SDKToolAnnotations(readOnlyHint=True, openWorldHint=False)
        result = _map_tool_annotations(raw)
        assert result is not None
        assert result.read_only_hint is True
        assert result.open_world_hint is False

    def test_non_dict_non_model_returns_none(self):
        """Defensive: a malformed annotations value must not crash the map."""
        assert _map_tool_annotations("garbage") is None
