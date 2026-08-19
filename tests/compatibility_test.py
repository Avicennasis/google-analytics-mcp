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

"""Test cases for the check_compatibility tool."""

import asyncio
import unittest
from unittest.mock import MagicMock, patch

from google.analytics import data_v1beta

from analytics_mcp.tools.reporting.compatibility import check_compatibility


class TestCheckCompatibility(unittest.TestCase):
    """Test cases for check_compatibility."""

    @patch("analytics_mcp.tools.reporting.compatibility.create_data_api_client")
    def test_builds_request(self, mock_create_client):
        """Tests that the request proto is built correctly."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_client.check_compatibility.return_value = (
            data_v1beta.CheckCompatibilityResponse()
        )

        asyncio.run(
            check_compatibility(
                12345,
                dimensions=["country", "city"],
                metrics=["activeUsers"],
            )
        )

        request = mock_client.check_compatibility.call_args.args[0]
        self.assertEqual(request.property, "properties/12345")
        self.assertEqual(
            [d.name for d in request.dimensions], ["country", "city"]
        )
        self.assertEqual([m.name for m in request.metrics], ["activeUsers"])

    @patch("analytics_mcp.tools.reporting.compatibility.create_data_api_client")
    def test_compatibility_filter(self, mock_create_client):
        """Tests that the compatibility filter enum is resolved."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_client.check_compatibility.return_value = (
            data_v1beta.CheckCompatibilityResponse()
        )

        asyncio.run(
            check_compatibility(
                12345,
                dimensions=["country"],
                compatibility_filter="compatible",
            )
        )

        request = mock_client.check_compatibility.call_args.args[0]
        self.assertEqual(
            request.compatibility_filter,
            data_v1beta.Compatibility.COMPATIBLE,
        )

    def test_invalid_compatibility_filter_raises(self):
        """Tests that an invalid compatibility filter raises."""
        with self.assertRaises(ValueError):
            asyncio.run(
                check_compatibility(12345, compatibility_filter="bogus")
            )

    @patch("analytics_mcp.tools.reporting.compatibility.create_data_api_client")
    def test_converts_response(self, mock_create_client):
        """Tests that the proto response is converted to a dict."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_client.check_compatibility.return_value = (
            data_v1beta.CheckCompatibilityResponse(
                dimension_compatibilities=[
                    data_v1beta.DimensionCompatibility(
                        dimension_metadata=data_v1beta.DimensionMetadata(
                            api_name="country"
                        ),
                        compatibility=(data_v1beta.Compatibility.COMPATIBLE),
                    )
                ]
            )
        )

        result = asyncio.run(check_compatibility(12345))

        self.assertEqual(
            result["dimension_compatibilities"][0]["compatibility"],
            "COMPATIBLE",
        )

    def test_invalid_property_id_raises(self):
        """Tests that an invalid property ID raises a ValueError."""
        with self.assertRaises(ValueError):
            asyncio.run(check_compatibility("bogus"))


if __name__ == "__main__":
    unittest.main()
