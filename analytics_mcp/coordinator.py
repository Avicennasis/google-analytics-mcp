# Copyright 2025 Google LLC All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Module declaring the singleton MCP server.

The singleton allows other modules to register their tools with the same MCP
server.
"""

# MCP Server Imports
import json
import sys
from mcp import types as mcp_types  # Use alias to avoid conflict
from mcp.server.lowlevel import Server

# ADK Tool Imports
from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.mcp_tool.conversion_utils import adk_to_mcp_tool_type
from google.api_core import exceptions as google_exceptions

from analytics_mcp.tools.admin.access import run_access_report
from analytics_mcp.tools.admin.info import (
    get_account_summaries,
    get_data_retention_settings,
    list_google_ads_links,
    get_property_details,
    list_audiences,
    list_custom_dimensions,
    list_custom_metrics,
    list_data_streams,
    list_key_events,
    list_properties,
    list_property_annotations,
    create_property_annotation,
)
from analytics_mcp.tools.client import set_allow_write
from analytics_mcp.tools.reporting.core import (
    run_report,
    _run_report_description,
)
from analytics_mcp.tools.reporting.realtime import (
    run_realtime_report,
    _run_realtime_report_description,
)
from analytics_mcp.tools.reporting.metadata import (
    get_custom_dimensions_and_metrics,
    get_metadata,
)
from analytics_mcp.tools.reporting.quotas import get_property_quotas
from analytics_mcp.tools.reporting.funnel import (
    run_funnel_report,
    _run_funnel_report_description,
)
from analytics_mcp.tools.reporting.conversions import (
    run_conversions_report,
    _run_conversions_report_description,
)
from analytics_mcp.tools.reporting.audience_exports import (
    create_audience_export,
    get_audience_export,
    list_audience_exports,
    query_audience_export,
)
from analytics_mcp.tools.measurement import (
    validate_event,
    send_event,
)
from analytics_mcp.tools.reporting.batch import (
    batch_run_reports,
    _batch_run_reports_description,
)
from analytics_mcp.tools.reporting.compatibility import check_compatibility
from analytics_mcp.tools.reporting.pivot import (
    run_pivot_report,
    _run_pivot_report_description,
    batch_run_pivot_reports,
    _batch_run_pivot_reports_description,
)

run_report_with_description = FunctionTool(run_report)
run_report_with_description.description = _run_report_description()
run_realtime_report_with_description = FunctionTool(run_realtime_report)
run_realtime_report_with_description.description = (
    _run_realtime_report_description()
)
run_funnel_report_with_description = FunctionTool(run_funnel_report)
run_funnel_report_with_description.description = (
    _run_funnel_report_description()
)
run_conversions_report_with_description = FunctionTool(run_conversions_report)
run_conversions_report_with_description.description = (
    _run_conversions_report_description()
)

# Instantiate the read-only ADK tools
run_pivot_report_with_description = FunctionTool(run_pivot_report)
run_pivot_report_with_description.description = _run_pivot_report_description()
batch_run_pivot_reports_with_description = FunctionTool(batch_run_pivot_reports)
batch_run_pivot_reports_with_description.description = (
    _batch_run_pivot_reports_description()
)

batch_run_reports_with_description = FunctionTool(batch_run_reports)
batch_run_reports_with_description.description = (
    _batch_run_reports_description()
)

read_only_tools = [
    batch_run_reports_with_description,
    FunctionTool(check_compatibility),
    run_pivot_report_with_description,
    batch_run_pivot_reports_with_description,
    FunctionTool(get_account_summaries),
    FunctionTool(list_google_ads_links),
    FunctionTool(get_property_details),
    FunctionTool(get_data_retention_settings),
    FunctionTool(list_audiences),
    FunctionTool(list_custom_dimensions),
    FunctionTool(list_custom_metrics),
    FunctionTool(list_data_streams),
    FunctionTool(list_key_events),
    FunctionTool(list_properties),
    FunctionTool(list_property_annotations),
    FunctionTool(run_access_report),
    FunctionTool(get_custom_dimensions_and_metrics),
    FunctionTool(get_metadata),
    FunctionTool(get_property_quotas),
    run_report_with_description,
    run_realtime_report_with_description,
    run_funnel_report_with_description,
    run_conversions_report_with_description,
    FunctionTool(create_audience_export),
    FunctionTool(get_audience_export),
    FunctionTool(list_audience_exports),
    FunctionTool(query_audience_export),
    FunctionTool(validate_event),
    FunctionTool(send_event),
]

# Instantiate the write ADK tools (only enabled when --allow-write is set)
write_tools = [
    FunctionTool(create_property_annotation),
]

_READ_ONLY_TOOL_NAMES = {t.name for t in read_only_tools}
_WRITE_TOOL_NAMES = {t.name for t in write_tools}
_WRITE_PERMISSION_DENIED_HINT = (
    " Hint: Write tools require the"
    " 'https://www.googleapis.com/auth/analytics.edit' OAuth scope and at least"
    " the Marketer or Editor role on the Google Analytics property. If using"
    " Application Default Credentials (ADC), re-authenticate with: gcloud auth"
    " application-default login --scopes="
    "https://www.googleapis.com/auth/analytics.readonly,"
    "https://www.googleapis.com/auth/analytics.edit,"
    "https://www.googleapis.com/auth/cloud-platform"
    " --client-id-file=YOUR_CLIENT_JSON_FILE"
)


def sanitize_mcp_schema_properties(node: dict) -> None:
    """Ensure additionalProperties is a boolean value to satisfy certain MCP clients.

    This addresses issues with clients like Claude Desktop that fail when
    additionalProperties is a schema object instead of a boolean.
    """
    if not isinstance(node, dict):
        return

    # Check and update the current node
    if "additionalProperties" in node:
        val = node["additionalProperties"]
        if not isinstance(val, bool):
            node["additionalProperties"] = True

    # Traverse children
    for key, child in node.items():
        if isinstance(child, dict):
            sanitize_mcp_schema_properties(child)
        elif isinstance(child, list):
            for element in child:
                if isinstance(element, dict):
                    sanitize_mcp_schema_properties(element)


def _prepare_mcp_tools(
    adk_tools: list[FunctionTool],
) -> list[mcp_types.Tool]:
    """Converts ADK tools to MCP tools and sanitizes their schemas."""
    converted_tools = [adk_to_mcp_tool_type(t) for t in adk_tools]

    # Update the input_schema for tools that do not have parameters.
    # TODO: This is a bug in the ADK and can be removed once it is fixed.
    # https://github.com/google/adk-python/issues/948
    for mcp_tool in converted_tools:
        # Check if input_schema is empty
        if mcp_tool.input_schema == {}:
            mcp_tool.input_schema = {"type": "object", "properties": {}}
        # Fix union type hints generating spurious "type": "null"
        for prop in mcp_tool.input_schema.get("properties", {}).values():
            if "anyOf" in prop and prop.get("type") == "null":
                del prop["type"]

        # Ensure additionalProperties is compatible with all MCP clients
        sanitize_mcp_schema_properties(mcp_tool.input_schema)

        # Explicitly mark required fields for reporting tools to guide the LLM
        if mcp_tool.name == "run_report":
            mcp_tool.input_schema["required"] = [
                "property_id",
                "date_ranges",
                "dimensions",
                "metrics",
            ]
        elif mcp_tool.name == "batch_run_reports":
            mcp_tool.input_schema["required"] = [
                "property_id",
                "requests",
            ]
        elif mcp_tool.name == "check_compatibility":
            mcp_tool.input_schema["required"] = ["property_id"]
        elif mcp_tool.name == "run_pivot_report":
            mcp_tool.input_schema["required"] = [
                "property_id",
                "date_ranges",
                "dimensions",
                "metrics",
                "pivots",
            ]
        elif mcp_tool.name == "batch_run_pivot_reports":
            mcp_tool.input_schema["required"] = [
                "property_id",
                "requests",
            ]
        elif mcp_tool.name == "run_realtime_report":
            mcp_tool.input_schema["required"] = [
                "property_id",
                "dimensions",
                "metrics",
            ]
        elif mcp_tool.name == "run_access_report":
            mcp_tool.input_schema["required"] = [
                "entity",
                "date_ranges",
                "dimensions",
                "metrics",
            ]
        elif mcp_tool.name == "run_conversions_report":
            mcp_tool.input_schema["required"] = [
                "property_id",
                "date_ranges",
                "dimensions",
                "metrics",
                "conversion_spec",
            ]
        elif mcp_tool.name == "create_audience_export":
            mcp_tool.input_schema["required"] = [
                "property_id",
                "audience_id",
                "dimensions",
            ]
        elif mcp_tool.name in ("validate_event", "send_event"):
            mcp_tool.input_schema["required"] = [
                "measurement_id",
                "client_id",
                "events",
            ]
        elif mcp_tool.name == "create_property_annotation":
            mcp_tool.input_schema["required"] = [
                "property_id",
                "title",
                "start_date",
            ]

        # Attach MCP ToolAnnotations so hosts know which tools are read-only
        if mcp_tool.name in _READ_ONLY_TOOL_NAMES:
            mcp_tool.annotations = mcp_types.ToolAnnotations(
                read_only_hint=True,
                destructive_hint=False,
                open_world_hint=True,
            )
        else:
            mcp_tool.annotations = mcp_types.ToolAnnotations(
                read_only_hint=False,
                destructive_hint=False,
                idempotent_hint=False,
                open_world_hint=True,
            )

    return converted_tools


_READ_ONLY_MCP_TOOLS = _prepare_mcp_tools(read_only_tools)
_WRITE_MCP_TOOLS = _prepare_mcp_tools(write_tools)


def create_server(allow_write: bool = False) -> Server:
    """Creates and configures an MCP Server instance."""
    set_allow_write(allow_write)
    active_tools = list(read_only_tools)
    active_mcp_tools = list(_READ_ONLY_MCP_TOOLS)
    if allow_write:
        active_tools.extend(write_tools)
        active_mcp_tools.extend(_WRITE_MCP_TOOLS)
    active_tool_map = {t.name: t for t in active_tools}

    async def list_tools(
        ctx=None,
        params: mcp_types.PaginatedRequestParams | None = None,
    ) -> mcp_types.ListToolsResult:
        return mcp_types.ListToolsResult(tools=active_mcp_tools)

    async def call_mcp_tool(
        ctx,
        params: mcp_types.CallToolRequestParams,
    ) -> mcp_types.CallToolResult:
        name = params.name
        arguments = params.arguments or {}
        if name in active_tool_map:
            adk_tool = active_tool_map[name]
            try:
                adk_tool_response = await adk_tool.run_async(
                    args=arguments,
                    tool_context=None,
                )
                # Serialize the ADK tool response to JSON for MCP response
                response_text = json.dumps(adk_tool_response, indent=2)
                # MCP expects a CallToolResult with mcp_types.Content parts
                return mcp_types.CallToolResult(
                    content=[
                        mcp_types.TextContent(type="text", text=response_text)
                    ]
                )

            except Exception as e:
                print(
                    f"MCP Server: Error executing ADK tool '{name}': {e}",
                    file=sys.stderr,
                )
                error_msg = f"Failed to execute tool '{name}': {str(e)}"
                if name in _WRITE_TOOL_NAMES and isinstance(
                    e, google_exceptions.Forbidden
                ):
                    error_msg += _WRITE_PERMISSION_DENIED_HINT
                # Return an error message in MCP format
                error_text = json.dumps({"error": error_msg})
                return mcp_types.CallToolResult(
                    content=[
                        mcp_types.TextContent(type="text", text=error_text)
                    ],
                    is_error=True,
                )

        if name in _WRITE_TOOL_NAMES:
            error_text = json.dumps(
                {
                    "error": (
                        f"Tool '{name}' is a write tool and is disabled by"
                        " default. Start the server with the --allow-write flag"
                        " to enable write tools."
                    )
                }
            )
        else:
            error_text = json.dumps(
                {"error": f"Tool '{name}' not implemented by this server."}
            )
        return mcp_types.CallToolResult(
            content=[mcp_types.TextContent(type="text", text=error_text)],
            is_error=True,
        )

    return Server(
        name="Google Analytics MCP Server",
        on_list_tools=list_tools,
        on_call_tool=call_mcp_tool,
    )
