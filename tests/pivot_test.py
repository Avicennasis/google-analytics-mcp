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

"""Test cases for the run_pivot_report tool."""

import asyncio
import unittest
from unittest.mock import MagicMock, patch

from google.analytics import data_v1beta

from analytics_mcp.tools.reporting.pivot import (
    _run_pivot_report_description,
    run_pivot_report,
)

_BASE_ARGS = {
    "date_ranges": [{"start_date": "7daysAgo", "end_date": "today"}],
    "dimensions": ["country", "deviceCategory"],
    "metrics": ["activeUsers"],
    "pivots": [
        {"field_names": ["country"], "limit": 10},
        {"field_names": ["deviceCategory"], "limit": 5},
    ],
}


class TestRunPivotReport(unittest.TestCase):
    """Test cases for run_pivot_report."""

    @patch("analytics_mcp.tools.reporting.pivot.create_data_api_client")
    def test_builds_request(self, mock_create_client):
        """Tests that the request proto is built correctly."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_client.run_pivot_report.return_value = (
            data_v1beta.RunPivotReportResponse()
        )

        asyncio.run(run_pivot_report(12345, **_BASE_ARGS))

        request = mock_client.run_pivot_report.call_args.args[0]
        self.assertIsInstance(request, data_v1beta.RunPivotReportRequest)
        self.assertEqual(request.property, "properties/12345")
        self.assertEqual(
            [d.name for d in request.dimensions],
            ["country", "deviceCategory"],
        )
        self.assertEqual([m.name for m in request.metrics], ["activeUsers"])
        self.assertEqual(len(request.pivots), 2)
        self.assertEqual(list(request.pivots[0].field_names), ["country"])
        self.assertEqual(request.pivots[0].limit, 10)
        self.assertEqual(
            list(request.pivots[1].field_names), ["deviceCategory"]
        )
        self.assertFalse(request.keep_empty_rows)

    @patch("analytics_mcp.tools.reporting.pivot.create_data_api_client")
    def test_optional_fields(self, mock_create_client):
        """Tests that optional fields are set when provided."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_client.run_pivot_report.return_value = (
            data_v1beta.RunPivotReportResponse()
        )

        asyncio.run(
            run_pivot_report(
                12345,
                **_BASE_ARGS,
                dimension_filter={
                    "filter": {
                        "field_name": "country",
                        "string_filter": {"value": "Japan"},
                    }
                },
                currency_code="USD",
                keep_empty_rows=True,
                return_property_quota=True,
            )
        )

        request = mock_client.run_pivot_report.call_args.args[0]
        self.assertEqual(request.dimension_filter.filter.field_name, "country")
        self.assertEqual(request.currency_code, "USD")
        self.assertTrue(request.keep_empty_rows)
        self.assertTrue(request.return_property_quota)

    def test_empty_pivots_raises(self):
        """Tests that an empty pivots list raises a ValueError."""
        args = dict(_BASE_ARGS, pivots=[])
        with self.assertRaises(ValueError):
            asyncio.run(run_pivot_report(12345, **args))

    def test_pivot_missing_field_names_raises(self):
        """Tests that a pivot without field_names raises a ValueError."""
        args = dict(_BASE_ARGS, pivots=[{"limit": 5}])
        with self.assertRaises(ValueError):
            asyncio.run(run_pivot_report(12345, **args))

    @patch("analytics_mcp.tools.reporting.pivot.create_data_api_client")
    def test_converts_response(self, mock_create_client):
        """Tests that the proto response is converted to a dict."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_client.run_pivot_report.return_value = (
            data_v1beta.RunPivotReportResponse(
                aggregates=[],
                rows=[
                    data_v1beta.Row(
                        dimension_values=[
                            data_v1beta.DimensionValue(value="Japan")
                        ],
                        metric_values=[data_v1beta.MetricValue(value="42")],
                    )
                ],
            )
        )

        result = asyncio.run(run_pivot_report(12345, **_BASE_ARGS))

        self.assertEqual(
            result["rows"][0]["dimension_values"][0]["value"], "Japan"
        )
        self.assertEqual(result["rows"][0]["metric_values"][0]["value"], "42")

    def test_invalid_property_id_raises(self):
        """Tests that an invalid property ID raises a ValueError."""
        with self.assertRaises(ValueError):
            asyncio.run(run_pivot_report("bogus", **_BASE_ARGS))


class TestDescription(unittest.TestCase):
    """Test cases for the tool description."""

    def test_description_includes_hints(self):
        """Tests that the description contains pivot hints."""
        description = _run_pivot_report_description()
        self.assertIn("pivots", description)
        self.assertIn("field_names", description)
        self.assertIn("date_range", description)


if __name__ == "__main__":
    unittest.main()


class TestBatchRunPivotReports(unittest.TestCase):
    """Test cases for batch_run_pivot_reports."""

    @patch("analytics_mcp.tools.reporting.pivot.create_data_api_client")
    def test_builds_batch_request(self, mock_create_client):
        """Tests that the batch request proto is built correctly."""
        from analytics_mcp.tools.reporting.pivot import (
            batch_run_pivot_reports,
        )

        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_client.batch_run_pivot_reports.return_value = (
            data_v1beta.BatchRunPivotReportsResponse()
        )

        asyncio.run(
            batch_run_pivot_reports(12345, requests=[_BASE_ARGS, _BASE_ARGS])
        )

        request = mock_client.batch_run_pivot_reports.call_args.args[0]
        self.assertIsInstance(request, data_v1beta.BatchRunPivotReportsRequest)
        self.assertEqual(request.property, "properties/12345")
        self.assertEqual(len(request.requests), 2)
        self.assertEqual(request.requests[0].property, "properties/12345")
        self.assertEqual(len(request.requests[0].pivots), 2)

    def test_empty_requests_raises(self):
        """Tests that an empty requests list raises a ValueError."""
        from analytics_mcp.tools.reporting.pivot import (
            batch_run_pivot_reports,
        )

        with self.assertRaises(ValueError):
            asyncio.run(batch_run_pivot_reports(12345, requests=[]))

    def test_too_many_requests_raises(self):
        """Tests that more than 5 requests raises a ValueError."""
        from analytics_mcp.tools.reporting.pivot import (
            batch_run_pivot_reports,
        )

        with self.assertRaises(ValueError):
            asyncio.run(
                batch_run_pivot_reports(12345, requests=[_BASE_ARGS] * 6)
            )

    def test_request_missing_pivots_raises(self):
        """Tests that a request without pivots raises a ValueError."""
        from analytics_mcp.tools.reporting.pivot import (
            batch_run_pivot_reports,
        )

        bad = {k: v for k, v in _BASE_ARGS.items() if k != "pivots"}
        with self.assertRaises(ValueError):
            asyncio.run(batch_run_pivot_reports(12345, requests=[bad]))
