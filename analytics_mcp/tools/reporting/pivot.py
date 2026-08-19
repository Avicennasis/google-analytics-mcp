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

"""Tools for running pivot reports using the Data API."""

import asyncio
from typing import Any, Dict, List

from analytics_mcp.tools.reporting.metadata import (
    get_date_ranges_hints,
    get_dimension_filter_hints,
    get_metric_filter_hints,
)
from analytics_mcp.tools.utils import (
    construct_property_rn,
    proto_to_dict,
    proto_to_json,
)
from analytics_mcp.tools.client import create_data_api_client
from google.analytics import data_v1beta


def _get_pivots_hints() -> str:
    """Returns hints and examples for pivots arguments."""
    pivot_country = data_v1beta.Pivot(
        field_names=["country"],
        limit=10,
    )
    pivot_device = data_v1beta.Pivot(
        field_names=["deviceCategory"],
        limit=5,
        order_bys=[
            data_v1beta.OrderBy(
                metric=data_v1beta.OrderBy.MetricOrderBy(
                    metric_name="activeUsers"
                ),
                desc=True,
            )
        ],
    )
    pivot_aggregated = data_v1beta.Pivot(
        field_names=["eventName"],
        limit=20,
        metric_aggregations=["TOTAL"],
    )

    return f"""Example pivots arguments:

    1.  A single pivot on 'country':
        [ {proto_to_json(pivot_country)} ]

    2.  Cross-tabulate 'country' by 'deviceCategory', ordering the
        device columns by descending active users:
        [
          {proto_to_json(pivot_country)},
          {proto_to_json(pivot_device)}
        ]

    3.  A pivot with metric aggregations (totals):
        [ {proto_to_json(pivot_aggregated)} ]

    Each pivot's `field_names` must be a subset of the report request's
    `dimensions`. A `limit` is required in practice: the product of all
    pivots' limits must not exceed 250,000, and each pivot's limit
    defaults to a large value if omitted.
    """


def _run_pivot_report_description() -> str:
    """Returns the description for the `run_pivot_report` tool."""
    return f"""
          {run_pivot_report.__doc__}

          ## Hints for arguments

          ### Hints for `dimensions`

          The `dimensions` list must consist solely of either of the
          following:

          1.  Standard dimensions defined in the HTML table at
              https://developers.google.com/analytics/devguides/reporting/data/v1/api-schema#dimensions.
              These dimensions are available to *every* property.
          2.  Custom dimensions for the `property_id`. Use the
              `get_custom_dimensions_and_metrics` tool to retrieve the
              list of custom dimensions for a property.

          ### Hints for `metrics`

          The `metrics` list must consist solely of either of the
          following:

          1.  Standard metrics defined in the HTML table at
              https://developers.google.com/analytics/devguides/reporting/data/v1/api-schema#metrics.
              These metrics are available to *every* property.
          2.  Custom metrics for the `property_id`. Use the
              `get_custom_dimensions_and_metrics` tool to retrieve the
              list of custom metrics for a property.

          ### Hints for `pivots`:
          {_get_pivots_hints()}

          ### Hints for `date_ranges`:
          {get_date_ranges_hints()}

          ### Hints for `dimension_filter`:
          {get_dimension_filter_hints()}

          ### Hints for `metric_filter`:
          {get_metric_filter_hints()}

          """


async def run_pivot_report(
    property_id: int | str,
    date_ranges: List[Dict[str, Any]],
    dimensions: List[str],
    metrics: List[str],
    pivots: List[Dict[str, Any]],
    dimension_filter: Dict[str, Any] = None,
    metric_filter: Dict[str, Any] = None,
    currency_code: str = None,
    keep_empty_rows: bool = False,
    return_property_quota: bool = False,
) -> Dict[str, Any]:
    """Runs a Google Analytics Data API pivot report.

    Pivot reports cross-tabulate dimensions, e.g. country x device
    category, without client-side post-processing. Use `run_report`
    instead for flat, non-pivoted tables.

    Note that the reference docs at
    https://developers.google.com/analytics/devguides/reporting/data/v1/rest/v1beta
    all use camelCase field names, but field names passed to this method
    should be in snake_case since the tool is using the protocol buffers
    (protobuf) format. The protocol buffers for the Data API are
    available at
    https://github.com/googleapis/googleapis/tree/master/google/analytics/data/v1beta.

    Args:
        property_id: The Google Analytics property ID. Accepted formats
          are:
          - A number
          - A string consisting of 'properties/' followed by a number
        date_ranges: A list of date ranges
          (https://developers.google.com/analytics/devguides/reporting/data/v1/rest/v1beta/DateRange)
          to include in the report.
        dimensions: A list of dimensions to include in the report. Every
          dimension referenced by a pivot must be listed here.
        metrics: A list of metrics to include in the report.
        pivots: A list of Data API Pivot
          (https://developers.google.com/analytics/devguides/reporting/data/v1/rest/v1beta/properties/runPivotReport#Pivot)
          objects describing the visual layout of the report's
          dimension columns and rows. Each pivot must contain
          `field_names` (a subset of `dimensions`) and should contain a
          `limit`. The product of all pivots' limits must not exceed
          250,000.
        dimension_filter: A Data API FilterExpression
          (https://developers.google.com/analytics/devguides/reporting/data/v1/rest/v1beta/FilterExpression)
          to apply to the dimensions. Must not contain metrics.
        metric_filter: A Data API FilterExpression to apply to the
          metrics. Must not contain dimensions.
        currency_code: An ISO4217 currency code (e.g. "USD").
        keep_empty_rows: Whether to include rows whose metrics are all
          zero.
        return_property_quota: Whether to return property quota
          information in the response.
    """
    request = _build_pivot_report_request(
        construct_property_rn(property_id),
        {
            "date_ranges": date_ranges,
            "dimensions": dimensions,
            "metrics": metrics,
            "pivots": pivots,
            "dimension_filter": dimension_filter,
            "metric_filter": metric_filter,
            "currency_code": currency_code,
            "keep_empty_rows": keep_empty_rows,
            "return_property_quota": return_property_quota,
        },
    )

    def _sync_call():
        return create_data_api_client().run_pivot_report(request)

    response = await asyncio.to_thread(_sync_call)

    return proto_to_dict(response)


def _validate_pivot_report_spec(spec: Dict[str, Any], label: str) -> None:
    """Validates a pivot report specification dict.

    Args:
        spec: The report specification to validate.
        label: A label identifying the spec in error messages.
    """
    for key in ("dimensions", "metrics", "date_ranges", "pivots"):
        if not spec.get(key):
            raise ValueError(f"{label} is missing required key '{key}'.")
        if not isinstance(spec[key], list):
            raise ValueError(f"{label} '{key}' must be a list.")

    for i, pivot in enumerate(spec["pivots"]):
        if not isinstance(pivot, dict):
            raise ValueError(f"{label} pivot {i + 1} must be a dictionary.")
        if not pivot.get("field_names"):
            raise ValueError(
                f"{label} pivot {i + 1} is missing required key "
                "'field_names'."
            )


def _build_pivot_report_request(
    property_rn: str, spec: Dict[str, Any]
) -> data_v1beta.RunPivotReportRequest:
    """Builds a RunPivotReportRequest proto from a specification dict.

    Args:
        property_rn: The property resource name (e.g. "properties/12345").
        spec: A dict with keys matching the `run_pivot_report` tool's
            parameters: `date_ranges`, `dimensions`, `metrics`,
            `pivots`, and optionally `dimension_filter`,
            `metric_filter`, `currency_code`, `keep_empty_rows`,
            `return_property_quota`.

    Returns:
        A RunPivotReportRequest proto.
    """
    _validate_pivot_report_spec(spec, "Request")

    request = data_v1beta.RunPivotReportRequest(
        property=property_rn,
        dimensions=[data_v1beta.Dimension(name=d) for d in spec["dimensions"]],
        metrics=[data_v1beta.Metric(name=m) for m in spec["metrics"]],
        date_ranges=[data_v1beta.DateRange(dr) for dr in spec["date_ranges"]],
        pivots=[data_v1beta.Pivot(p) for p in spec["pivots"]],
        keep_empty_rows=spec.get("keep_empty_rows", False),
        return_property_quota=spec.get("return_property_quota", False),
    )

    dimension_filter = spec.get("dimension_filter")
    if dimension_filter:
        request.dimension_filter = data_v1beta.FilterExpression(
            dimension_filter
        )

    metric_filter = spec.get("metric_filter")
    if metric_filter:
        request.metric_filter = data_v1beta.FilterExpression(metric_filter)

    currency_code = spec.get("currency_code")
    if currency_code:
        request.currency_code = currency_code

    return request


def _batch_run_pivot_reports_description() -> str:
    """Returns the description for the `batch_run_pivot_reports` tool."""
    return f"""
          {batch_run_pivot_reports.__doc__}

          ## Hints for arguments

          Each object in the `requests` list uses the same argument
          formats as the `run_pivot_report` tool. See that tool's
          description for hints on `dimensions`, `metrics`, `pivots`,
          `date_ranges`, and filters.

          ### Hints for `pivots` (per request):
          {_get_pivots_hints()}
          """


async def batch_run_pivot_reports(
    property_id: int | str,
    requests: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Runs multiple Google Analytics pivot reports in a single request.

    Use this tool instead of calling `run_pivot_report` multiple times
    when you need several pivot reports for the same property. This
    reduces latency by combining up to 5 pivot reports into one API
    call.

    Each object in the `requests` list accepts the same arguments as
    the `run_pivot_report` tool.

    Args:
        property_id: The Google Analytics property ID. Accepted formats
          are:
          - A number
          - A string consisting of 'properties/' followed by a number
        requests: A list of 1 to 5 pivot report request objects. Each
          object must contain the following required keys:
          - `date_ranges`: A list of date ranges to include.
          - `dimensions`: A list of dimensions to include.
          - `metrics`: A list of metrics to include.
          - `pivots`: A list of Pivot objects, each with `field_names`
            (a subset of the request's `dimensions`) and a `limit`.

          Each object may also contain the following optional keys:
          - `dimension_filter`: A Data API FilterExpression to apply to
            the dimensions.
          - `metric_filter`: A Data API FilterExpression to apply to
            the metrics.
          - `currency_code`: An ISO4217 currency code (e.g. "USD").
          - `keep_empty_rows`: Whether to include rows whose metrics
            are all zero.
          - `return_property_quota`: Whether to return property quota
            information in the response.
    """
    if not isinstance(requests, list):
        raise ValueError("requests must be a list.")
    if not requests:
        raise ValueError(
            "requests must contain at least one pivot report request."
        )
    if len(requests) > 5:
        raise ValueError(
            "requests must contain at most 5 pivot report requests. "
            f"Got {len(requests)}."
        )

    for i, spec in enumerate(requests):
        if not isinstance(spec, dict):
            raise ValueError(f"Request {i + 1} must be a dictionary.")
        _validate_pivot_report_spec(spec, f"Request {i + 1}")

    property_rn = construct_property_rn(property_id)

    batch_request = data_v1beta.BatchRunPivotReportsRequest(
        property=property_rn,
        requests=[
            _build_pivot_report_request(property_rn, spec) for spec in requests
        ],
    )

    def _sync_call():
        return create_data_api_client().batch_run_pivot_reports(batch_request)

    response = await asyncio.to_thread(_sync_call)

    return proto_to_dict(response)
