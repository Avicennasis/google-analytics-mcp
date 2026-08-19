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

"""Tools for checking dimension and metric compatibility."""

import asyncio
from typing import Any, Dict, List

from analytics_mcp.tools.utils import (
    construct_property_rn,
    proto_to_dict,
)
from analytics_mcp.tools.client import create_data_api_client
from google.analytics import data_v1beta


async def check_compatibility(
    property_id: int | str,
    dimensions: List[str] = None,
    metrics: List[str] = None,
    dimension_filter: Dict[str, Any] = None,
    metric_filter: Dict[str, Any] = None,
    compatibility_filter: str = None,
) -> Dict[str, Any]:
    """Checks which dimensions and metrics can be added to a report.

    Use this before `run_report` when combining several dimensions and
    metrics, to avoid wasted report requests with incompatible field
    combinations. The check is fast and consumes minimal quota.

    The response lists dimensions and metrics with their compatibility:
    `COMPATIBLE` fields can be added to a report containing the
    requested fields; `INCOMPATIBLE` fields cannot.

    Args:
        property_id: The Google Analytics property ID. Accepted formats
          are:
          - A number
          - A string consisting of 'properties/' followed by a number
        dimensions: The dimensions already in the report, e.g.
          `["country", "city"]`. May be empty or omitted.
        metrics: The metrics already in the report, e.g.
          `["activeUsers"]`. May be empty or omitted.
        dimension_filter: A Data API FilterExpression
          (https://developers.google.com/analytics/devguides/reporting/data/v1/rest/v1beta/FilterExpression)
          applied to the dimensions in the planned report.
        metric_filter: A Data API FilterExpression applied to the
          metrics in the planned report.
        compatibility_filter: Optionally restrict the response to a
          single compatibility level. One of `"COMPATIBLE"` or
          `"INCOMPATIBLE"`. Filtering to `"COMPATIBLE"` is recommended
          since the full response can be large.
    """
    request = data_v1beta.CheckCompatibilityRequest(
        property=construct_property_rn(property_id),
        dimensions=[data_v1beta.Dimension(name=d) for d in (dimensions or [])],
        metrics=[data_v1beta.Metric(name=m) for m in (metrics or [])],
    )

    if dimension_filter:
        request.dimension_filter = data_v1beta.FilterExpression(
            dimension_filter
        )

    if metric_filter:
        request.metric_filter = data_v1beta.FilterExpression(metric_filter)

    if compatibility_filter:
        try:
            request.compatibility_filter = data_v1beta.Compatibility[
                compatibility_filter.upper()
            ]
        except KeyError:
            raise ValueError(
                "compatibility_filter must be 'COMPATIBLE' or "
                f"'INCOMPATIBLE'. Got '{compatibility_filter}'."
            )

    def _sync_call():
        return create_data_api_client().check_compatibility(request)

    response = await asyncio.to_thread(_sync_call)

    return proto_to_dict(response)
