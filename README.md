# Google Analytics MCP Server (Experimental)

[![PyPI version](https://img.shields.io/pypi/v/analytics-mcp.svg)](https://pypi.org/project/analytics-mcp/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![GitHub branch check runs](https://img.shields.io/github/check-runs/googleanalytics/google-analytics-mcp/main)](https://github.com/googleanalytics/google-analytics-mcp/actions?query=branch%3Amain++)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/analytics-mcp)](https://pypi.org/project/analytics-mcp/)
[![GitHub stars](https://img.shields.io/github/stars/googleanalytics/google-analytics-mcp?style=social)](https://github.com/googleanalytics/google-analytics-mcp/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/googleanalytics/google-analytics-mcp?style=social)](https://github.com/googleanalytics/google-analytics-mcp/network/members)
[![YouTube Video Views](https://img.shields.io/youtube/views/PT4wGPxWiRQ)](https://www.youtube.com/watch?v=PT4wGPxWiRQ)

This repo contains the source code for running a local
[MCP](https://modelcontextprotocol.io) server that interacts with APIs for
[Google Analytics](https://support.google.com/analytics).

Join the discussion and ask questions in the
[🤖-analytics-mcp channel](https://discord.com/channels/971845904002871346/1398002598665257060)
on Discord.

## Tools 🛠️

The server uses the
[Google Analytics Admin API](https://developers.google.com/analytics/devguides/config/admin/v1)
and
[Google Analytics Data API](https://developers.google.com/analytics/devguides/reporting/data/v1)
to provide several
[Tools](https://modelcontextprotocol.io/docs/concepts/tools) for use with LLMs.

### Account and property information 🟠

- `get_account_summaries` — Google Analytics accounts and their properties.
- `get_property_details` — details about a property.
- `list_properties` — properties the user can access.
- `list_google_ads_links` — Google Ads links for a property.
- `get_data_retention_settings` — data-retention settings for a property.
- `list_property_annotations` — annotations on a property.
- `get_property_quotas` — quota usage for a property.
- `list_data_streams` — data streams for a property.

### Configuration and metadata 🗂️

- `get_custom_dimensions_and_metrics` — custom dimensions and metrics.
- `list_custom_dimensions` — custom dimensions for a property.
- `list_custom_metrics` — custom metrics for a property.
- `list_key_events` — key events (conversions).
- `list_audiences` — audiences defined on a property.
- `get_metadata` — available dimensions and metrics.
- `check_compatibility` — dimension/metric compatibility.

### Reports 📙

- `run_report` — run a Data API report.
- `run_realtime_report` — run a realtime report.
- `run_funnel_report` — run a funnel report.
- `run_conversions_report` — run a conversions report.
- `run_access_report` — run an access/entitlement report.
- `run_pivot_report` — run a pivot report.
- `batch_run_reports` — run several reports in one call.
- `batch_run_pivot_reports` — run several pivot reports in one call.

### Audience exports 📤

- `create_audience_export` — create an audience export.
- `get_audience_export` — get an audience export's status.
- `list_audience_exports` — list a property's audience exports.
- `query_audience_export` — query a completed audience export.

### Measurement Protocol (write) ✍️

- `validate_event` — validate a Measurement Protocol event.
- `send_event` — send a Measurement Protocol event.

## Setup instructions 🔧

✨ Watch the [Google Analytics MCP Setup
Tutorial](https://youtu.be/nS8HLdwmVlY) on YouTube for a step-by-step
walkthrough of these instructions.

[![Watch the video](https://img.youtube.com/vi/nS8HLdwmVlY/mqdefault.jpg)](https://www.youtube.com/watch?v=nS8HLdwmVlY)

Setup involves the following steps:

1.  Configure Python.
1.  Configure credentials for Google Analytics.
1.  Configure Gemini.

### Configure Python 🐍

[Install pipx](https://pipx.pypa.io/stable/#install-pipx).

### Enable APIs in your project ✅

[Follow the instructions](https://support.google.com/googleapi/answer/6158841)
to enable the following APIs in your Google Cloud project:

- [Google Analytics Admin API](https://console.cloud.google.com/apis/library/analyticsadmin.googleapis.com)
- [Google Analytics Data API](https://console.cloud.google.com/apis/library/analyticsdata.googleapis.com)

### Configure credentials 🔑

Configure your [Application Default Credentials
(ADC)](https://cloud.google.com/docs/authentication/provide-credentials-adc).
Make sure the credentials are for a user with access to your Google Analytics
accounts or properties.

Credentials must include the Google Analytics read-only scope:

```
https://www.googleapis.com/auth/analytics.readonly
```

Check out
[Manage OAuth Clients](https://support.google.com/cloud/answer/15549257)
for how to create an OAuth client.

Here are some sample `gcloud` commands you might find useful:

- Set up ADC using user credentials and an OAuth desktop or web client after
  downloading the client JSON to `YOUR_CLIENT_JSON_FILE`.

  ```shell
  gcloud auth application-default login \
    --scopes https://www.googleapis.com/auth/analytics.readonly,https://www.googleapis.com/auth/cloud-platform \
    --client-id-file=YOUR_CLIENT_JSON_FILE
  ```

- Set up ADC using service account impersonation.

  ```shell
  gcloud auth application-default login \
    --impersonate-service-account=SERVICE_ACCOUNT_EMAIL \
    --scopes=https://www.googleapis.com/auth/analytics.readonly,https://www.googleapis.com/auth/cloud-platform
  ```

When the `gcloud auth application-default` command completes, copy the
`PATH_TO_CREDENTIALS_JSON` file location printed to the console in the
following message. You'll need this for the next step!

```
Credentials saved to file: [PATH_TO_CREDENTIALS_JSON]
```

### Configure Gemini

1.  Install [Gemini
    CLI](https://github.com/google-gemini/gemini-cli/blob/main/docs/get-started/installation.md)
    or [Gemini Code
    Assist](https://marketplace.visualstudio.com/items?itemName=Google.geminicodeassist).

1.  Create or edit the file at `~/.gemini/settings.json`, adding your server
    to the `mcpServers` list.

    Replace `PATH_TO_CREDENTIALS_JSON` with the path you copied in the previous
    step.

    We also recommend that you add a `GOOGLE_CLOUD_PROJECT` attribute to the
    `env` object. Replace `YOUR_PROJECT_ID` in the following example with the
    [project ID](https://support.google.com/googleapi/answer/7014113) of your
    Google Cloud project.

    ```json
    {
      "mcpServers": {
        "analytics-mcp": {
          "command": "pipx",
          "args": ["run", "analytics-mcp"],
          "env": {
            "GOOGLE_APPLICATION_CREDENTIALS": "PATH_TO_CREDENTIALS_JSON",
            "GOOGLE_CLOUD_PROJECT": "YOUR_PROJECT_ID"
          }
        }
      }
    }
    ```

### Configure Claude Code

1.  Add the MCP server with the following command:

    Replace `PATH_TO_CREDENTIALS_JSON` with the path you copied in the previous
    step, and replace `YOUR_PROJECT_ID` with the
    [project ID](https://support.google.com/googleapi/answer/7014113) of your
    Google Cloud project.

    ```shell
    claude mcp add analytics-mcp \
      --scope user \
      -e "GOOGLE_APPLICATION_CREDENTIALS=PATH_TO_CREDENTIALS_JSON" \
      -e "GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID" \
      -- pipx run analytics-mcp
    ```

### Configure other MCP clients

Any MCP client that supports stdio servers works — Cursor, Windsurf, VS Code
Copilot, Claude Desktop, and others. Use the same JSON shape as the Gemini
example, adapting it to your client's config file:

```json
{
  "mcpServers": {
    "analytics-mcp": {
      "command": "pipx",
      "args": ["run", "analytics-mcp"],
      "env": {
        "GOOGLE_APPLICATION_CREDENTIALS": "PATH_TO_CREDENTIALS_JSON",
        "GOOGLE_CLOUD_PROJECT": "YOUR_PROJECT_ID"
      }
    }
  }
}
```

## Try it out 🥼

Launch Gemini Code Assist or Gemini CLI and type `/mcp`. You should see
`analytics-mcp` listed in the results.

Here are some sample prompts to get you started:

- Ask what the server can do:

  ```
  what can the analytics-mcp server do?
  ```

- Ask about a Google Analytics property

  ```
  Give me details about my Google Analytics property with 'xyz' in the name
  ```

- Prompt for analysis:

  ```
  what are the most popular events in my Google Analytics property in the last 180 days?
  ```

- Ask about signed-in users:

  ```
  were most of my users in the last 6 months logged in?
  ```

- Ask about property configuration:

  ```
  what are the custom dimensions and custom metrics in my property?
  ```

## Contributing ✨

Contributions welcome! See the [Contributing Guide](CONTRIBUTING.md).
