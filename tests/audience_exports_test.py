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

"""Test cases for the audience export tools."""

import asyncio
import unittest
from unittest.mock import MagicMock, patch

from google.analytics import data_v1beta

from analytics_mcp.tools.reporting.audience_exports import (
    _construct_audience_export_rn,
    create_audience_export,
    get_audience_export,
    list_audience_exports,
    query_audience_export,
)

_CLIENT_PATH = (
    "analytics_mcp.tools.reporting.audience_exports.create_data_api_client"
)


class TestConstructAudienceExportRn(unittest.TestCase):
    """Test cases for _construct_audience_export_rn."""

    def test_numeric_id(self):
        self.assertEqual(
            _construct_audience_export_rn(12345, 678),
            "properties/12345/audienceExports/678",
        )

    def test_full_resource_name_passthrough(self):
        self.assertEqual(
            _construct_audience_export_rn(
                12345, "properties/999/audienceExports/1"
            ),
            "properties/999/audienceExports/1",
        )

    def test_invalid_property_raises(self):
        with self.assertRaises(ValueError):
            _construct_audience_export_rn("bogus", 678)


class TestCreateAudienceExport(unittest.TestCase):
    """Test cases for create_audience_export."""

    @patch(_CLIENT_PATH)
    def test_builds_request_and_returns_metadata(self, mock_create_client):
        """Tests request construction and metadata passthrough."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_operation = MagicMock()
        mock_operation.metadata = data_v1beta.AudienceExport(
            name="properties/12345/audienceExports/42",
            audience="properties/12345/audiences/777",
            state=data_v1beta.AudienceExport.State.CREATING,
        )
        mock_client.create_audience_export.return_value = mock_operation

        result = asyncio.run(
            create_audience_export(12345, 777, dimensions=["deviceId"])
        )

        request = mock_client.create_audience_export.call_args.kwargs["request"]
        self.assertEqual(request.parent, "properties/12345")
        self.assertEqual(
            request.audience_export.audience,
            "properties/12345/audiences/777",
        )
        self.assertEqual(
            [d.dimension_name for d in request.audience_export.dimensions],
            ["deviceId"],
        )
        self.assertEqual(result["name"], "properties/12345/audienceExports/42")
        self.assertEqual(result["state"], "CREATING")

    @patch(_CLIENT_PATH)
    def test_accepts_full_audience_rn(self, mock_create_client):
        """Tests that a full audience resource name is passed through."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_operation = MagicMock()
        mock_operation.metadata = data_v1beta.AudienceExport()
        mock_client.create_audience_export.return_value = mock_operation

        asyncio.run(
            create_audience_export(
                12345,
                "properties/12345/audiences/888",
                dimensions=["deviceId"],
            )
        )

        request = mock_client.create_audience_export.call_args.kwargs["request"]
        self.assertEqual(
            request.audience_export.audience,
            "properties/12345/audiences/888",
        )


class TestGetAudienceExport(unittest.TestCase):
    """Test cases for get_audience_export."""

    @patch(_CLIENT_PATH)
    def test_returns_export_state(self, mock_create_client):
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_client.get_audience_export.return_value = (
            data_v1beta.AudienceExport(
                name="properties/12345/audienceExports/42",
                state=data_v1beta.AudienceExport.State.ACTIVE,
                row_count=100,
            )
        )

        result = asyncio.run(get_audience_export(12345, 42))

        request = mock_client.get_audience_export.call_args.kwargs["request"]
        self.assertEqual(request.name, "properties/12345/audienceExports/42")
        self.assertEqual(result["state"], "ACTIVE")
        self.assertEqual(result["row_count"], 100)


class TestListAudienceExports(unittest.TestCase):
    """Test cases for list_audience_exports."""

    @patch(_CLIENT_PATH)
    def test_lists_exports(self, mock_create_client):
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_client.list_audience_exports.return_value = [
            data_v1beta.AudienceExport(
                name="properties/12345/audienceExports/1"
            )
        ]

        result = asyncio.run(list_audience_exports(12345))

        request = mock_client.list_audience_exports.call_args.kwargs["request"]
        self.assertEqual(request.parent, "properties/12345")
        self.assertEqual(len(result), 1)


class TestQueryAudienceExport(unittest.TestCase):
    """Test cases for query_audience_export."""

    @patch(_CLIENT_PATH)
    def test_queries_rows(self, mock_create_client):
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_client.query_audience_export.return_value = (
            data_v1beta.QueryAudienceExportResponse(
                audience_rows=[
                    data_v1beta.AudienceRow(
                        dimension_values=[
                            data_v1beta.AudienceDimensionValue(
                                value="device-abc"
                            )
                        ]
                    )
                ],
                row_count=1,
            )
        )

        result = asyncio.run(query_audience_export(12345, 42, limit=10))

        request = mock_client.query_audience_export.call_args.kwargs["request"]
        self.assertEqual(request.name, "properties/12345/audienceExports/42")
        self.assertEqual(request.limit, 10)
        self.assertEqual(
            result["audience_rows"][0]["dimension_values"][0]["value"],
            "device-abc",
        )


if __name__ == "__main__":
    unittest.main()
