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

"""Tools for gathering Google Analytics account and property information."""

import asyncio
import datetime
from typing import Any, Dict, List, Tuple

from analytics_mcp.tools.utils import (
    construct_account_rn,
    construct_property_rn,
    proto_to_dict,
)
from analytics_mcp.tools.client import (
    create_admin_api_client,
    create_admin_alpha_api_client,
)
from google.analytics import admin_v1beta, admin_v1alpha
from google.type import date_pb2

# Note: ReportingDataAnnotation.Color.ORANGE (7) is reserved by Google Analytics
# exclusively for system-generated annotations and cannot be used when creating
# annotations via the API.
_AnnotationColor = admin_v1alpha.ReportingDataAnnotation.Color
_VALID_ANNOTATION_COLORS = tuple(
    c.name
    for c in _AnnotationColor
    if c not in (_AnnotationColor.COLOR_UNSPECIFIED, _AnnotationColor.ORANGE)
)
_MAX_ANNOTATION_TITLE_LENGTH = 60
_MAX_ANNOTATION_DESCRIPTION_LENGTH = 150


def _parse_annotation_date(
    date_str: str,
) -> Tuple[datetime.date, date_pb2.Date]:
    """Parses a YYYY-MM-DD string into a datetime.date and date_pb2.Date."""
    if not isinstance(date_str, str) or not date_str.strip():
        raise ValueError(
            f"Invalid date: {date_str!r}. Expected a string in YYYY-MM-DD format."
        )
    try:
        parsed = datetime.date.fromisoformat(date_str.strip())
    except ValueError as exc:
        raise ValueError(
            f"Invalid date '{date_str}'. Expected YYYY-MM-DD format."
        ) from exc
    return parsed, date_pb2.Date(
        year=parsed.year, month=parsed.month, day=parsed.day
    )


async def get_account_summaries() -> List[Dict[str, Any]]:
    """Retrieves information about the user's Google Analytics accounts and properties."""

    def _sync_call():
        summary_pager = create_admin_api_client().list_account_summaries()
        return [proto_to_dict(summary_page) for summary_page in summary_pager]

    return await asyncio.to_thread(_sync_call)


async def list_google_ads_links(property_id: int | str) -> List[Dict[str, Any]]:
    """Returns a list of links to Google Ads accounts for a property.

    Args:
        property_id: The Google Analytics property ID. Accepted formats are:
          - A number
          - A string consisting of 'properties/' followed by a number
    """
    request = admin_v1beta.ListGoogleAdsLinksRequest(
        parent=construct_property_rn(property_id)
    )

    def _sync_call():
        links_pager = create_admin_api_client().list_google_ads_links(
            request=request
        )
        return [proto_to_dict(link_page) for link_page in links_pager]

    return await asyncio.to_thread(_sync_call)


async def get_property_details(property_id: int | str) -> Dict[str, Any]:
    """Returns details about a property.
    Args:
        property_id: The Google Analytics property ID. Accepted formats are:
          - A number
          - A string consisting of 'properties/' followed by a number
    """
    request = admin_v1beta.GetPropertyRequest(
        name=construct_property_rn(property_id)
    )

    def _sync_call():
        client = create_admin_api_client()
        return client.get_property(request=request)

    response = await asyncio.to_thread(_sync_call)
    return proto_to_dict(response)


async def list_properties(
    account_id: int | str, show_deleted: bool = False
) -> List[Dict[str, Any]]:
    """Returns the properties under a Google Analytics account.

    Returns full property objects, including display name, industry
    category, time zone, currency code, service level, and create time.
    Use this for deeper property discovery than `get_account_summaries`,
    which only returns summary information.

    Args:
        account_id: The Google Analytics account ID. Accepted formats are:
          - A number
          - A string consisting of 'accounts/' followed by a number
        show_deleted: Whether to include soft-deleted (i.e. "trashed")
          properties in the results. Defaults to False.
    """
    request = admin_v1beta.ListPropertiesRequest(
        filter=f"parent:{construct_account_rn(account_id)}",
        show_deleted=show_deleted,
    )

    def _sync_call():
        properties_pager = create_admin_api_client().list_properties(
            request=request
        )
        return [proto_to_dict(prop) for prop in properties_pager]

    return await asyncio.to_thread(_sync_call)


async def list_key_events(property_id: int | str) -> List[Dict[str, Any]]:
    """Returns the key events configured for a property.

    Key events (formerly known as conversion events) are the events that a
    property has marked as most important, such as purchases or sign-ups.
    Reports use key events to calculate conversion-related metrics.

    Args:
        property_id: The Google Analytics property ID. Accepted formats are:
          - A number
          - A string consisting of 'properties/' followed by a number
    """
    request = admin_v1beta.ListKeyEventsRequest(
        parent=construct_property_rn(property_id)
    )

    def _sync_call():
        key_events_pager = create_admin_api_client().list_key_events(
            request=request
        )
        return [proto_to_dict(key_event) for key_event in key_events_pager]

    return await asyncio.to_thread(_sync_call)


async def list_data_streams(property_id: int | str) -> List[Dict[str, Any]]:
    """Returns the data streams configured for a property.

    Data streams are the sources that send data to a property, such as a
    web site, an Android app, or an iOS app. Each stream includes its
    platform-specific details, e.g. the measurement ID for a web stream.

    Args:
        property_id: The Google Analytics property ID. Accepted formats are:
          - A number
          - A string consisting of 'properties/' followed by a number
    """
    request = admin_v1beta.ListDataStreamsRequest(
        parent=construct_property_rn(property_id)
    )

    def _sync_call():
        data_streams_pager = create_admin_api_client().list_data_streams(
            request=request
        )
        return [
            proto_to_dict(data_stream) for data_stream in data_streams_pager
        ]

    return await asyncio.to_thread(_sync_call)


async def list_audiences(property_id: int | str) -> List[Dict[str, Any]]:
    """Returns the audiences defined on a property.

    Audiences are segments of users, e.g. "Purchasers" or "Users who
    visited the pricing page". Knowing what audiences exist helps when
    interpreting audience-scoped dimensions in reports or suggesting
    targeting strategies.

    Note: this uses the alpha channel of the Admin API, which may
    change without notice.

    Args:
        property_id: The Google Analytics property ID. Accepted formats are:
          - A number
          - A string consisting of 'properties/' followed by a number
    """
    request = admin_v1alpha.ListAudiencesRequest(
        parent=construct_property_rn(property_id)
    )

    def _sync_call():
        audiences_pager = create_admin_alpha_api_client().list_audiences(
            request=request
        )
        return [proto_to_dict(audience) for audience in audiences_pager]

    return await asyncio.to_thread(_sync_call)


async def get_data_retention_settings(
    property_id: int | str,
) -> Dict[str, Any]:
    """Returns the data retention settings for a property.

    Shows how long event-level and user-level data is kept before being
    automatically deleted. Useful for compliance questions and for
    knowing how far back reports can reliably look: if retention is set
    to TWO_MONTHS, event-scoped data older than that is unavailable in
    explorations and some reports.

    Args:
        property_id: The Google Analytics property ID. Accepted formats are:
          - A number
          - A string consisting of 'properties/' followed by a number
    """
    request = admin_v1beta.GetDataRetentionSettingsRequest(
        name=f"{construct_property_rn(property_id)}/dataRetentionSettings"
    )

    def _sync_call():
        client = create_admin_api_client()
        return client.get_data_retention_settings(request=request)

    response = await asyncio.to_thread(_sync_call)
    return proto_to_dict(response)


async def list_custom_dimensions(
    property_id: int | str,
) -> List[Dict[str, Any]]:
    """Returns the custom dimensions defined on a property (Admin API).

    Includes details that the Data API metadata endpoint doesn't return:
    the dimension's scope (EVENT or USER), parameter name, description,
    and whether it's excluded from ads personalization. Use the
    `get_custom_dimensions_and_metrics` tool instead if you only need
    the API names for building reports.

    Args:
        property_id: The Google Analytics property ID. Accepted formats are:
          - A number
          - A string consisting of 'properties/' followed by a number
    """
    request = admin_v1beta.ListCustomDimensionsRequest(
        parent=construct_property_rn(property_id)
    )

    def _sync_call():
        dimensions_pager = create_admin_api_client().list_custom_dimensions(
            request=request
        )
        return [proto_to_dict(dimension) for dimension in dimensions_pager]

    return await asyncio.to_thread(_sync_call)


async def list_custom_metrics(property_id: int | str) -> List[Dict[str, Any]]:
    """Returns the custom metrics defined on a property (Admin API).

    Includes details that the Data API metadata endpoint doesn't return:
    the metric's scope, parameter name, description, measurement unit,
    and restricted metric type. Use the
    `get_custom_dimensions_and_metrics` tool instead if you only need
    the API names for building reports.

    Args:
        property_id: The Google Analytics property ID. Accepted formats are:
          - A number
          - A string consisting of 'properties/' followed by a number
    """
    request = admin_v1beta.ListCustomMetricsRequest(
        parent=construct_property_rn(property_id)
    )

    def _sync_call():
        metrics_pager = create_admin_api_client().list_custom_metrics(
            request=request
        )
        return [proto_to_dict(metric) for metric in metrics_pager]

    return await asyncio.to_thread(_sync_call)


async def list_property_annotations(
    property_id: int | str,
) -> List[Dict[str, Any]]:
    """Returns annotations for a property.

    Annotations are a feature that allows you to leave notes on Google Analytics for specific dates or periods.
    They are typically used to record service releases, marketing campaign launches or changes,
    and rapid traffic increases or decreases due to external factors.

    Args:
        property_id: The Google Analytics property ID. Accepted formats are:
          - A number
          - A string consisting of 'properties/' followed by a number
    """
    request = admin_v1alpha.ListReportingDataAnnotationsRequest(
        parent=construct_property_rn(property_id)
    )

    def _sync_call():
        annotations_pager = (
            create_admin_alpha_api_client().list_reporting_data_annotations(
                request=request
            )
        )
        return [
            proto_to_dict(annotation_page)
            for annotation_page in annotations_pager
        ]

    return await asyncio.to_thread(_sync_call)


async def create_property_annotation(
    property_id: int | str,
    title: str,
    start_date: str,
    color: str = "BLUE",
    description: str = None,
    end_date: str = None,
) -> Dict[str, Any]:
    """Creates a reporting data annotation for a property.

    Annotations allow you to leave notes on Google Analytics for specific dates
    or date ranges to record service releases, GTM container publishes,
    marketing campaign launches, or traffic anomalies.

    Args:
        property_id: The Google Analytics property ID. Accepted formats are:
          - A number
          - A string consisting of 'properties/' followed by a number
        title: Human-readable title for the annotation (maximum 60 characters).
        start_date: The date (or start date of a range) in YYYY-MM-DD format
          (inclusive, e.g. '2026-10-21').
        color: Color used for displaying the annotation. Valid values are:
          'PURPLE', 'BROWN', 'BLUE', 'GREEN', 'RED', 'CYAN' ('ORANGE' is
          reserved by Google Analytics for system-generated annotations).
          Defaults to 'BLUE'.
        description: Optional description or notes for the annotation (maximum
          150 characters).
        end_date: Optional end date in YYYY-MM-DD format (inclusive) when
          creating a date-range annotation. Must be greater than or equal to
          start_date. If omitted, a single-date annotation is created on
          start_date.
    """
    if not title or not title.strip():
        raise ValueError("title must be a non-empty string.")
    stripped_title = title.strip()
    if len(stripped_title) > _MAX_ANNOTATION_TITLE_LENGTH:
        raise ValueError(
            f"title must be at most {_MAX_ANNOTATION_TITLE_LENGTH} characters "
            f"(got {len(stripped_title)})."
        )

    if (
        description is not None
        and len(description) > _MAX_ANNOTATION_DESCRIPTION_LENGTH
    ):
        raise ValueError(
            f"description must be at most {_MAX_ANNOTATION_DESCRIPTION_LENGTH} "
            f"characters (got {len(description)})."
        )

    normalized_color = (color or "").strip().upper()
    if normalized_color not in _VALID_ANNOTATION_COLORS:
        valid_str = ", ".join(_VALID_ANNOTATION_COLORS)
        raise ValueError(
            f"Invalid color '{color}'. Valid colors are: {valid_str}."
        )

    parsed_start, proto_start = _parse_annotation_date(start_date)

    annotation = admin_v1alpha.ReportingDataAnnotation(
        title=stripped_title,
        color=getattr(
            admin_v1alpha.ReportingDataAnnotation.Color, normalized_color
        ),
    )

    if description is not None:
        annotation.description = description

    if end_date is not None and end_date.strip():
        parsed_end, proto_end = _parse_annotation_date(end_date)
        if parsed_end < parsed_start:
            raise ValueError(
                f"end_date ({end_date}) must be greater than or equal to "
                f"start_date ({start_date})."
            )
        annotation.annotation_date_range = (
            admin_v1alpha.ReportingDataAnnotation.DateRange(
                start_date=proto_start,
                end_date=proto_end,
            )
        )
    else:
        annotation.annotation_date = proto_start

    request = admin_v1alpha.CreateReportingDataAnnotationRequest(
        parent=construct_property_rn(property_id),
        reporting_data_annotation=annotation,
    )

    def _sync_call():
        return create_admin_alpha_api_client().create_reporting_data_annotation(
            request=request
        )

    response = await asyncio.to_thread(_sync_call)
    return proto_to_dict(response)
