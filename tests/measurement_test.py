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

"""Test cases for the Measurement Protocol tools."""

import asyncio
import unittest
from unittest.mock import MagicMock, patch

from analytics_mcp.tools import measurement
from analytics_mcp.tools.measurement import send_event, validate_event

_SECRET_ENV = {"ANALYTICS_MCP_MP_API_SECRET": "test-secret"}

_EVENTS = [{"name": "tutorial_complete", "params": {"step": 5}}]


def _mock_response(validation_messages=None):
    """Returns a mock httpx response."""
    response = MagicMock()
    response.json.return_value = (
        {"validationMessages": validation_messages}
        if validation_messages is not None
        else {}
    )
    response.raise_for_status.return_value = None
    return response


class TestValidateEvent(unittest.TestCase):
    """Test cases for validate_event."""

    @patch.dict("os.environ", _SECRET_ENV)
    @patch("analytics_mcp.tools.measurement.httpx.post")
    def test_posts_to_debug_endpoint(self, mock_post):
        """Tests that validation hits only the debug endpoint."""
        mock_post.return_value = _mock_response(validation_messages=[])

        result = asyncio.run(validate_event("G-TEST123", "client-1", _EVENTS))

        self.assertTrue(result["valid"])
        self.assertEqual(result["validation_messages"], [])
        self.assertEqual(mock_post.call_count, 1)
        url = mock_post.call_args.args[0]
        self.assertEqual(url, measurement._DEBUG_COLLECT_URL)
        params = mock_post.call_args.kwargs["params"]
        self.assertEqual(params["measurement_id"], "G-TEST123")
        self.assertEqual(params["api_secret"], "test-secret")
        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["client_id"], "client-1")
        self.assertEqual(payload["events"], _EVENTS)

    @patch.dict("os.environ", _SECRET_ENV)
    @patch("analytics_mcp.tools.measurement.httpx.post")
    def test_reports_validation_messages(self, mock_post):
        """Tests that validation messages are surfaced."""
        messages = [{"description": "bad event name"}]
        mock_post.return_value = _mock_response(validation_messages=messages)

        result = asyncio.run(validate_event("G-TEST123", "client-1", _EVENTS))

        self.assertFalse(result["valid"])
        self.assertEqual(result["validation_messages"], messages)

    @patch.dict("os.environ", {"ANALYTICS_MCP_MP_API_SECRET": ""})
    def test_missing_secret_raises(self):
        """Tests that a missing API secret raises a clear error."""
        with self.assertRaises(ValueError) as ctx:
            asyncio.run(validate_event("G-TEST123", "client-1", _EVENTS))
        self.assertIn("ANALYTICS_MCP_MP_API_SECRET", str(ctx.exception))

    @patch.dict("os.environ", _SECRET_ENV)
    def test_too_many_events_raises(self):
        """Tests that more than 25 events raises a ValueError."""
        with self.assertRaises(ValueError):
            asyncio.run(
                validate_event("G-TEST123", "client-1", [{"name": "e"}] * 26)
            )

    @patch.dict("os.environ", _SECRET_ENV)
    def test_event_without_name_raises(self):
        """Tests that an event without a name raises a ValueError."""
        with self.assertRaises(ValueError):
            asyncio.run(
                validate_event("G-TEST123", "client-1", [{"params": {}}])
            )


class TestSendEvent(unittest.TestCase):
    """Test cases for send_event."""

    @patch.dict("os.environ", _SECRET_ENV)
    @patch("analytics_mcp.tools.measurement.httpx.post")
    def test_dry_run_by_default(self, mock_post):
        """Tests that without confirm=True nothing is recorded."""
        mock_post.return_value = _mock_response(validation_messages=[])

        result = asyncio.run(send_event("G-TEST123", "client-1", _EVENTS))

        self.assertFalse(result["sent"])
        self.assertTrue(result["dry_run"])
        self.assertTrue(result["validation"]["valid"])
        # Only the debug endpoint may be called on a dry run.
        urls = [call.args[0] for call in mock_post.call_args_list]
        self.assertEqual(urls, [measurement._DEBUG_COLLECT_URL])

    @patch.dict("os.environ", _SECRET_ENV)
    @patch("analytics_mcp.tools.measurement.httpx.post")
    def test_confirm_sends_after_validation(self, mock_post):
        """Tests that confirm=True validates then sends."""
        mock_post.return_value = _mock_response(validation_messages=[])

        result = asyncio.run(
            send_event("G-TEST123", "client-1", _EVENTS, confirm=True)
        )

        self.assertTrue(result["sent"])
        self.assertFalse(result["dry_run"])
        self.assertEqual(result["events_sent"], 1)
        urls = [call.args[0] for call in mock_post.call_args_list]
        self.assertEqual(
            urls,
            [measurement._DEBUG_COLLECT_URL, measurement._COLLECT_URL],
        )

    @patch.dict("os.environ", _SECRET_ENV)
    @patch("analytics_mcp.tools.measurement.httpx.post")
    def test_confirm_blocked_by_validation_failure(self, mock_post):
        """Tests that invalid payloads are never sent, even confirmed."""
        mock_post.return_value = _mock_response(
            validation_messages=[{"description": "bad"}]
        )

        result = asyncio.run(
            send_event("G-TEST123", "client-1", _EVENTS, confirm=True)
        )

        self.assertFalse(result["sent"])
        urls = [call.args[0] for call in mock_post.call_args_list]
        self.assertEqual(urls, [measurement._DEBUG_COLLECT_URL])

    @patch.dict("os.environ", _SECRET_ENV)
    @patch("analytics_mcp.tools.measurement.httpx.post")
    def test_optional_fields_in_payload(self, mock_post):
        """Tests that optional payload fields are passed through."""
        mock_post.return_value = _mock_response(validation_messages=[])

        asyncio.run(
            send_event(
                "G-TEST123",
                "client-1",
                _EVENTS,
                user_id="user-9",
                timestamp_micros=1700000000000000,
                user_properties={"plan": {"value": "premium"}},
                non_personalized_ads=True,
            )
        )

        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["user_id"], "user-9")
        self.assertEqual(payload["timestamp_micros"], 1700000000000000)
        self.assertEqual(
            payload["user_properties"], {"plan": {"value": "premium"}}
        )
        self.assertTrue(payload["non_personalized_ads"])


if __name__ == "__main__":
    unittest.main()
