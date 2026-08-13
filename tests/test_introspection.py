# SPDX-FileCopyrightText: 2026 Trackmind
# SPDX-License-Identifier: MIT

"""
tests/test_introspection.py

Unit tests for the introspection mapping layer and the ServerModel.

These tests do NOT connect to a live MCP server. They use the fixture
data from conftest.py and directly exercise the mapping functions and
model construction logic.
"""

from models.server_model import (
    PromptArgument,
    PromptModel,
    ResourceModel,
    ServerCapabilities,
    ServerInfo,
    ServerModel,
    ToolInputProperty,
    ToolInputSchema,
    ToolModel,
)

# ---------------------------------------------------------------------------
# Helpers that mirror the mapping logic in introspect.py
# (without importing the async introspect module, which has side effects)
# ---------------------------------------------------------------------------


def _make_tool(raw: dict) -> ToolModel:
    schema = raw.get("inputSchema", {})
    properties = {}
    for name, prop in schema.get("properties", {}).items():
        properties[name] = ToolInputProperty(
            type=prop.get("type"),
            description=prop.get("description"),
            enum=prop.get("enum"),
        )
    return ToolModel(
        name=raw["name"],
        description=raw.get("description"),
        input_schema=ToolInputSchema(
            type=schema.get("type", "object"),
            properties=properties,
            required=schema.get("required", []),
        ),
    )


def _make_resource(raw: dict) -> ResourceModel:
    return ResourceModel(
        uri=raw["uri"],
        name=raw.get("name"),
        description=raw.get("description"),
        mime_type=raw.get("mimeType"),
    )


def _make_prompt(raw: dict) -> PromptModel:
    arguments = [
        PromptArgument(
            name=arg["name"],
            description=arg.get("description"),
            required=arg.get("required", False),
        )
        for arg in raw.get("arguments", [])
    ]
    return PromptModel(
        name=raw["name"],
        description=raw.get("description"),
        arguments=arguments,
    )


# ---------------------------------------------------------------------------
# ServerModel tests
# ---------------------------------------------------------------------------


class TestServerModel:
    def test_empty_model_is_valid(self):
        model = ServerModel()
        assert model.tools == []
        assert model.resources == []
        assert model.prompts == []
        assert model.server_info.name is None

    def test_summary_with_data(self):
        model = ServerModel(
            server_info=ServerInfo(name="my-server", version="1.0.0"),
            tools=[ToolModel(name="t1", description="d")],
            resources=[ResourceModel(uri="file:///x", name="x")],
            prompts=[],
        )
        summary = model.summary()
        assert "my-server" in summary
        assert "1 tool" in summary
        assert "1 resource" in summary
        assert "0 prompt" in summary

    def test_model_serializes_to_json(self):
        model = ServerModel(
            server_info=ServerInfo(name="s", version="0.1", protocol_version="2024-11-05"),
        )
        data = model.model_dump()
        assert data["server_info"]["name"] == "s"
        assert data["tools"] == []


# ---------------------------------------------------------------------------
# Tool mapping tests
# ---------------------------------------------------------------------------


class TestToolMapping:
    def test_maps_full_tool(self, sample_tools_list):
        raw = sample_tools_list["tools"][0]
        tool = _make_tool(raw)
        assert tool.name == "read_file"
        assert tool.description is not None and "Reads" in tool.description
        assert "path" in tool.input_schema.properties
        assert tool.input_schema.properties["path"].type == "string"
        assert "path" in tool.input_schema.required

    def test_maps_tool_with_empty_description(self, sample_tools_list):
        raw = sample_tools_list["tools"][1]
        tool = _make_tool(raw)
        assert tool.name == "delete_file"
        assert tool.description == ""  # empty, not None — important distinction for linting

    def test_tool_property_without_description(self, sample_tools_list):
        raw = sample_tools_list["tools"][1]
        tool = _make_tool(raw)
        path_prop = tool.input_schema.properties.get("path")
        assert path_prop is not None
        assert path_prop.description is None  # missing description

    def test_tool_required_fields(self, sample_tools_list):
        raw = sample_tools_list["tools"][0]
        tool = _make_tool(raw)
        assert "path" in tool.input_schema.required

    def test_tool_no_input_schema_defaults(self):
        raw = {"name": "bare_tool", "description": "A tool with no schema."}
        tool = _make_tool(raw)
        assert tool.input_schema.type == "object"
        assert tool.input_schema.properties == {}
        assert tool.input_schema.required == []


# ---------------------------------------------------------------------------
# Resource mapping tests
# ---------------------------------------------------------------------------


class TestResourceMapping:
    def test_maps_resource(self, sample_resources_list):
        raw = sample_resources_list["resources"][0]
        resource = _make_resource(raw)
        assert resource.uri == "file:///workspace"
        assert resource.name == "workspace"
        assert resource.description == "The root workspace directory."
        assert resource.mime_type is None

    def test_resource_minimal(self):
        raw = {"uri": "file:///data"}
        resource = _make_resource(raw)
        assert resource.uri == "file:///data"
        assert resource.name is None
        assert resource.description is None


# ---------------------------------------------------------------------------
# Prompt mapping tests
# ---------------------------------------------------------------------------


class TestPromptMapping:
    def test_maps_prompt(self, sample_prompts_list):
        raw = sample_prompts_list["prompts"][0]
        prompt = _make_prompt(raw)
        assert prompt.name == "summarize"
        assert prompt.description is not None and "Summarize" in prompt.description
        assert len(prompt.arguments) == 1
        assert prompt.arguments[0].name == "text"
        assert prompt.arguments[0].required is True

    def test_prompt_no_arguments(self):
        raw = {"name": "hello", "description": "Say hello."}
        prompt = _make_prompt(raw)
        assert prompt.arguments == []


# ---------------------------------------------------------------------------
# ServerCapabilities tests
# ---------------------------------------------------------------------------


class TestServerCapabilities:
    def test_defaults_all_false(self):
        caps = ServerCapabilities()
        assert caps.tools is False
        assert caps.resources is False
        assert caps.prompts is False

    def test_can_set_individual_caps(self):
        caps = ServerCapabilities(tools=True, resources=False, prompts=True)
        assert caps.tools is True
        assert caps.resources is False
        assert caps.prompts is True
