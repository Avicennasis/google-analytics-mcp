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

"""Tools for creating and querying audience exports using the Data API."""

import asyncio
from typing import Any, Dict, List

from analytics_mcp.tools.utils import (
    construct_property_rn,
    proto_to_dict,
)
from analytics_mcp.tools.client import create_data_api_client
from google.analytics import data_v1beta


def _construct_audience_export_rn(
    property_id: int | str, audience_export: int | str
) -> str:
    """Returns an audience export resource name.

    Args:
        property_id: The property the export belongs to.
        audience_export: Either a numeric audience export ID or a full
            resource name of the form
            'properties/{property}/audienceExports/{id}'.
    """
    if isinstance(audience_export, str):
        audience_export = audience_export.strip()
        if audience_export.startswith("properties/"):
            return audience_export

    return (
        f"{construct_property_rn(property_id)}/"
        f"audienceExports/{audience_export}"
    )


async def create_audience_export(
    property_id: int | str,
    audience_id: int | str,
    dimensions: List[str],
) -> Dict[str, Any]:
    """Starts an asynchronous audience export job.

    An audience export is a snapshot of the users in an audience at the
    time of creation. Creating the export starts a long-running job;
    poll its state with `get_audience_export`, and retrieve the user
    rows with `query_audience_export` once the state is ACTIVE.

    Note: although this creates an export object, the operation only
    reads analytics data and is permitted by the analytics.readonly
    scope. Exports are retained for about 72 hours, and creation
    charges audience export quota tokens.

    Args:
        property_id: The Google Analytics property ID. Accepted formats
          are:
          - A number
          - A string consisting of 'properties/' followed by a number
        audience_id: The audience to export. Accepted formats are:
          - A number (the audience ID)
          - A full resource name, e.g. 'properties/1234/audiences/5678'
          Use the `list_audiences` tool to discover audience IDs.
        dimensions: The dimensions to include for each user, e.g.
          `["deviceId"]`. Valid names are listed at
          https://developers.google.com/analytics/devguides/reporting/data/v1/audience-list-basics#dimensions.
    """
    property_rn = construct_property_rn(property_id)

    if isinstance(audience_id, str) and audience_id.strip().startswith(
        "properties/"
    ):
        audience_rn = audience_id.strip()
    else:
        audience_rn = f"{property_rn}/audiences/{audience_id}"

    request = data_v1beta.CreateAudienceExportRequest(
        parent=property_rn,
        audience_export=data_v1beta.AudienceExport(
            audience=audience_rn,
            dimensions=[
                data_v1beta.AudienceDimension(dimension_name=d)
                for d in dimensions
            ],
        ),
    )

    def _sync_call():
        operation = create_data_api_client().create_audience_export(
            request=request
        )
        # The operation metadata is the AudienceExport being created,
        # including its name and state. Don't block on completion;
        # callers poll with get_audience_export.
        return operation.metadata

    metadata = await asyncio.to_thread(_sync_call)

    return proto_to_dict(metadata)


async def get_audience_export(
    property_id: int | str, audience_export: int | str
) -> Dict[str, Any]:
    """Returns the configuration and state of an audience export.

    Use this to poll an export created with `create_audience_export`.
    When `state` is ACTIVE, the export can be queried with
    `query_audience_export`.

    Args:
        property_id: The Google Analytics property ID. Accepted formats
          are:
          - A number
          - A string consisting of 'properties/' followed by a number
        audience_export: The audience export to look up. Accepted
          formats are:
          - A number (the audience export ID)
          - A full resource name, e.g.
            'properties/1234/audienceExports/5678'
    """
    request = data_v1beta.GetAudienceExportRequest(
        name=_construct_audience_export_rn(property_id, audience_export)
    )

    def _sync_call():
        return create_data_api_client().get_audience_export(request=request)

    response = await asyncio.to_thread(_sync_call)

    return proto_to_dict(response)


async def list_audience_exports(
    property_id: int | str,
) -> List[Dict[str, Any]]:
    """Returns all audience exports for a property.

    Exports are retained for about 72 hours after creation.

    Args:
        property_id: The Google Analytics property ID. Accepted formats
          are:
          - A number
          - A string consisting of 'properties/' followed by a number
    """
    request = data_v1beta.ListAudienceExportsRequest(
        parent=construct_property_rn(property_id)
    )

    def _sync_call():
        exports_pager = create_data_api_client().list_audience_exports(
            request=request
        )
        return [proto_to_dict(export) for export in exports_pager]

    return await asyncio.to_thread(_sync_call)


async def query_audience_export(
    property_id: int | str,
    audience_export: int | str,
    offset: int = None,
    limit: int = None,
) -> Dict[str, Any]:
    """Retrieves the user rows from a completed audience export.

    The export must be in the ACTIVE state; check with
    `get_audience_export` first. Each row contains the dimension values
    requested when the export was created.

    Args:
        property_id: The Google Analytics property ID. Accepted formats
          are:
          - A number
          - A string consisting of 'properties/' followed by a number
        audience_export: The audience export to query. Accepted formats
          are:
          - A number (the audience export ID)
          - A full resource name, e.g.
            'properties/1234/audienceExports/5678'
        offset: The row count of the start row (0-indexed).
        limit: The maximum number of rows to return.
    """
    request = data_v1beta.QueryAudienceExportRequest(
        name=_construct_audience_export_rn(property_id, audience_export)
    )

    if offset:
        request.offset = offset

    if limit:
        request.limit = limit

    def _sync_call():
        return create_data_api_client().query_audience_export(request=request)

    response = await asyncio.to_thread(_sync_call)

    return proto_to_dict(response)
