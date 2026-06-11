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

"""Tools for the Google Analytics Measurement Protocol.

Unlike the other tools in this server, the Measurement Protocol is a
plain HTTP API (not a gRPC client library) and it WRITES data: events
sent to the collect endpoint are recorded in the property. To keep the
server safe by default:

- The API secret is only ever read from the
  ``ANALYTICS_MCP_MP_API_SECRET`` environment variable, never from tool
  arguments, so a model cannot supply or exfiltrate secrets.
- ``send_event`` defaults to a dry run that only validates the payload.
  Recording an event requires the explicit ``confirm=True`` argument,
  and the payload must pass validation first.
"""

import asyncio
import os
from typing import Any, Dict, List

import httpx

_MP_API_SECRET_ENV_VAR = "ANALYTICS_MCP_MP_API_SECRET"

_COLLECT_URL = "https://www.google-analytics.com/mp/collect"
_DEBUG_COLLECT_URL = "https://www.google-analytics.com/debug/mp/collect"

_REQUEST_TIMEOUT_SECONDS = 10.0

_MAX_EVENTS_PER_REQUEST = 25


def _get_api_secret() -> str:
    """Returns the Measurement Protocol API secret from the environment."""
    api_secret = os.environ.get(_MP_API_SECRET_ENV_VAR, "").strip()
    if not api_secret:
        raise ValueError(
            "No Measurement Protocol API secret is configured. Set the "
            f"{_MP_API_SECRET_ENV_VAR} environment variable to an API "
            "secret created under the data stream's 'Measurement "
            "Protocol API secrets' settings in Google Analytics."
        )
    return api_secret


def _build_payload(
    client_id: str,
    events: List[Dict[str, Any]],
    user_id: str = None,
    timestamp_micros: int = None,
    user_properties: Dict[str, Any] = None,
    non_personalized_ads: bool = False,
) -> Dict[str, Any]:
    """Builds and validates a Measurement Protocol request payload."""
    if not client_id or not str(client_id).strip():
        raise ValueError("client_id must be a non-empty string.")
    if not isinstance(events, list) or not events:
        raise ValueError("events must contain at least one event.")
    if len(events) > _MAX_EVENTS_PER_REQUEST:
        raise ValueError(
            "events must contain at most "
            f"{_MAX_EVENTS_PER_REQUEST} events. Got {len(events)}."
        )
    for i, event in enumerate(events):
        if not isinstance(event, dict):
            raise ValueError(f"Event {i + 1} must be a dictionary.")
        if not event.get("name"):
            raise ValueError(f"Event {i + 1} is missing required key 'name'.")

    payload = {
        "client_id": str(client_id),
        "events": events,
    }

    if user_id:
        payload["user_id"] = user_id

    if timestamp_micros:
        payload["timestamp_micros"] = timestamp_micros

    if user_properties:
        payload["user_properties"] = user_properties

    if non_personalized_ads:
        payload["non_personalized_ads"] = True

    return payload


def _post_payload(
    url: str, measurement_id: str, payload: Dict[str, Any]
) -> httpx.Response:
    """Posts a payload to a Measurement Protocol endpoint."""
    if not measurement_id or not str(measurement_id).strip():
        raise ValueError(
            "measurement_id must be a non-empty string, e.g. 'G-XXXXXXX'. "
            "Use the list_data_streams tool to find a web stream's "
            "measurement ID."
        )

    response = httpx.post(
        url,
        params={
            "measurement_id": measurement_id,
            "api_secret": _get_api_secret(),
        },
        json=payload,
        timeout=_REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response


def _validation_messages(response: httpx.Response) -> List[Dict[str, Any]]:
    """Extracts validation messages from a debug endpoint response."""
    try:
        body = response.json()
    except ValueError:
        return []
    return body.get("validationMessages", [])


async def validate_event(
    measurement_id: str,
    client_id: str,
    events: List[Dict[str, Any]],
    user_id: str = None,
    timestamp_micros: int = None,
    user_properties: Dict[str, Any] = None,
    non_personalized_ads: bool = False,
) -> Dict[str, Any]:
    """Validates Measurement Protocol events without recording them.

    Sends the events to the Measurement Protocol debug endpoint, which
    checks the payload and returns validation messages. Nothing is
    recorded in the property, so this is always safe to call.

    Requires the ANALYTICS_MCP_MP_API_SECRET environment variable to be
    set to a Measurement Protocol API secret for the data stream.

    Args:
        measurement_id: The web data stream's measurement ID, e.g.
          'G-XXXXXXX'. Use the `list_data_streams` tool to find it.
        client_id: A unique identifier for the client/user instance,
          e.g. the GA client ID from the _ga cookie, or any stable
          UUID-like string for server-generated events.
        events: A list of 1 to 25 event objects. Each object must
          contain a `name` key (e.g. 'tutorial_complete') and may
          contain a `params` dict, per
          https://developers.google.com/analytics/devguides/collection/protocol/ga4/reference/events.
        user_id: An optional persistent user identifier.
        timestamp_micros: Optional Unix epoch microseconds for the
          events. Must be within the last 72 hours.
        user_properties: Optional user properties dict, e.g.
          `{"plan": {"value": "premium"}}`.
        non_personalized_ads: Whether the events should be excluded
          from ads personalization.
    """
    payload = _build_payload(
        client_id,
        events,
        user_id=user_id,
        timestamp_micros=timestamp_micros,
        user_properties=user_properties,
        non_personalized_ads=non_personalized_ads,
    )

    def _sync_call():
        return _post_payload(_DEBUG_COLLECT_URL, measurement_id, payload)

    response = await asyncio.to_thread(_sync_call)
    messages = _validation_messages(response)

    return {
        "valid": not messages,
        "validation_messages": messages,
    }


async def send_event(
    measurement_id: str,
    client_id: str,
    events: List[Dict[str, Any]],
    user_id: str = None,
    timestamp_micros: int = None,
    user_properties: Dict[str, Any] = None,
    non_personalized_ads: bool = False,
    confirm: bool = False,
) -> Dict[str, Any]:
    """Sends Measurement Protocol events to a Google Analytics property.

    WARNING: with `confirm=True` this WRITES events into the property's
    data, which cannot be undone. By default (`confirm=False`) this
    tool performs a dry run: the payload is validated against the
    debug endpoint and nothing is recorded. Only pass `confirm=True`
    after the user has explicitly approved sending the events.

    Even with `confirm=True`, the payload is validated first and the
    send is aborted if validation fails.

    Requires the ANALYTICS_MCP_MP_API_SECRET environment variable to be
    set to a Measurement Protocol API secret for the data stream.

    Args:
        measurement_id: The web data stream's measurement ID, e.g.
          'G-XXXXXXX'. Use the `list_data_streams` tool to find it.
        client_id: A unique identifier for the client/user instance,
          e.g. the GA client ID from the _ga cookie, or any stable
          UUID-like string for server-generated events.
        events: A list of 1 to 25 event objects. Each object must
          contain a `name` key (e.g. 'tutorial_complete') and may
          contain a `params` dict, per
          https://developers.google.com/analytics/devguides/collection/protocol/ga4/reference/events.
        user_id: An optional persistent user identifier.
        timestamp_micros: Optional Unix epoch microseconds for the
          events. Must be within the last 72 hours.
        user_properties: Optional user properties dict, e.g.
          `{"plan": {"value": "premium"}}`.
        non_personalized_ads: Whether the events should be excluded
          from ads personalization.
        confirm: Must be True to actually record the events. When
          False (the default), only validation is performed and a
          dry-run result is returned.
    """
    validation = await validate_event(
        measurement_id,
        client_id,
        events,
        user_id=user_id,
        timestamp_micros=timestamp_micros,
        user_properties=user_properties,
        non_personalized_ads=non_personalized_ads,
    )

    if not confirm:
        return {
            "sent": False,
            "dry_run": True,
            "validation": validation,
            "message": (
                "Dry run only — no events were recorded. To send these "
                "events for real, call send_event again with "
                "confirm=True after the user has approved it."
            ),
        }

    if not validation["valid"]:
        return {
            "sent": False,
            "dry_run": False,
            "validation": validation,
            "message": (
                "Events were NOT sent because validation failed. Fix "
                "the issues in validation_messages and try again."
            ),
        }

    payload = _build_payload(
        client_id,
        events,
        user_id=user_id,
        timestamp_micros=timestamp_micros,
        user_properties=user_properties,
        non_personalized_ads=non_personalized_ads,
    )

    def _sync_call():
        return _post_payload(_COLLECT_URL, measurement_id, payload)

    await asyncio.to_thread(_sync_call)

    return {
        "sent": True,
        "dry_run": False,
        "events_sent": len(events),
        "validation": validation,
    }
