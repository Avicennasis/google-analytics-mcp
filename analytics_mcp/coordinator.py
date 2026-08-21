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
)
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

# Instantiate the ADK tools
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

tools = [
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

tool_map = {t.name: t for t in tools}

app = Server(
    name="Google Analytics MCP Server",
)

mcp_tools = [adk_to_mcp_tool_type(tool) for tool in tools]


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


# Update the inputSchema for tools that do not have parameters.
# TODO: This is a bug in the ADK and can be removed once it is fixed.
# https://github.com/google/adk-python/issues/948
for tool in mcp_tools:
    # Check if inputSchema is empty
    if tool.inputSchema == {}:
        tool.inputSchema = {"type": "object", "properties": {}}
    # Fix union type hints generating spurious "type": "null"
    for prop in tool.inputSchema.get("properties", {}).values():
        if "anyOf" in prop and prop.get("type") == "null":
            del prop["type"]

    # Ensure additionalProperties is compatible with all MCP clients
    sanitize_mcp_schema_properties(tool.inputSchema)

    # Explicitly mark required fields for reporting tools to guide the LLM
    if tool.name == "run_report":
        tool.inputSchema["required"] = [
            "property_id",
            "date_ranges",
            "dimensions",
            "metrics",
        ]
    elif tool.name == "batch_run_reports":
        tool.inputSchema["required"] = [
            "property_id",
            "requests",
        ]
    elif tool.name == "check_compatibility":
        tool.inputSchema["required"] = ["property_id"]
    elif tool.name == "run_pivot_report":
        tool.inputSchema["required"] = [
            "property_id",
            "date_ranges",
            "dimensions",
            "metrics",
            "pivots",
        ]
    elif tool.name == "batch_run_pivot_reports":
        tool.inputSchema["required"] = [
            "property_id",
            "requests",
        ]
    elif tool.name == "run_realtime_report":
        tool.inputSchema["required"] = ["property_id", "dimensions", "metrics"]
    elif tool.name == "run_access_report":
        tool.inputSchema["required"] = [
            "entity",
            "date_ranges",
            "dimensions",
            "metrics",
        ]
    elif tool.name == "run_conversions_report":
        tool.inputSchema["required"] = [
            "property_id",
            "date_ranges",
            "dimensions",
            "metrics",
            "conversion_spec",
        ]
    elif tool.name == "create_audience_export":
        tool.inputSchema["required"] = [
            "property_id",
            "audience_id",
            "dimensions",
        ]
    elif tool.name in ("validate_event", "send_event"):
        tool.inputSchema["required"] = [
            "measurement_id",
            "client_id",
            "events",
        ]


@app.list_tools()
async def list_tools() -> list[mcp_types.Tool]:
    return mcp_tools


@app.call_tool()
async def call_mcp_tool(
    name: str, arguments: dict
) -> list[mcp_types.Content] | mcp_types.CallToolResult:
    if name in tool_map:
        tool = tool_map[name]
        try:
            adk_tool_response = await tool.run_async(
                args=arguments,
                tool_context=None,
            )
            # Serialize the ADK tool response to JSON for MCP response
            response_text = json.dumps(adk_tool_response, indent=2)
            # MCP expects a list of mcp_types.Content parts
            return [mcp_types.TextContent(type="text", text=response_text)]

        except Exception as e:
            print(
                f"MCP Server: Error executing ADK tool '{name}': {e}",
                file=sys.stderr,
            )
            # Return an error message in MCP format. isError=True so MCP
            # clients can detect the failure programmatically instead of
            # treating the error text as a successful response.
            error_text = json.dumps(
                {"error": f"Failed to execute tool '{name}': {str(e)}"}
            )
            return mcp_types.CallToolResult(
                content=[mcp_types.TextContent(type="text", text=error_text)],
                isError=True,
            )

    error_text = json.dumps(
        {"error": f"Tool '{name}' not implemented by this server."}
    )
    return mcp_types.CallToolResult(
        content=[mcp_types.TextContent(type="text", text=error_text)],
        isError=True,
    )
