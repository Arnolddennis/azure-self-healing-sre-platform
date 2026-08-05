#!/usr/bin/env python3
"""Create a local or optional AI-assisted incident summary from Azure alert JSON."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def load_payload(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"Alert payload not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path}: {exc}") from exc


def extract_essentials(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data") or {}
    essentials = data.get("essentials") or {}
    context = data.get("alertContext") or {}
    return {
        "alert_rule": essentials.get("alertRule", "Unknown"),
        "severity": essentials.get("severity", "Unknown"),
        "signal_type": essentials.get("signalType", "Unknown"),
        "monitor_condition": essentials.get("monitorCondition", "Unknown"),
        "fired_time": essentials.get("firedDateTime", "Unknown"),
        "resource_ids": essentials.get("alertTargetIDs", []),
        "description": essentials.get("description", ""),
        "context": context,
    }


def deterministic_summary(incident: dict[str, Any]) -> str:
    resources = incident["resource_ids"] or ["Unknown resource"]
    resource_text = ", ".join(str(item) for item in resources)
    return "\n".join(
        [
            "INCIDENT SUMMARY",
            f"Alert: {incident['alert_rule']}",
            f"Severity: {incident['severity']}",
            f"Condition: {incident['monitor_condition']}",
            f"Signal: {incident['signal_type']}",
            f"Fired: {incident['fired_time']}",
            f"Affected resource(s): {resource_text}",
            f"Description: {incident['description'] or 'No description supplied.'}",
            "",
            "RECOMMENDED TRIAGE",
            "1. Confirm the alert is not caused by a planned deployment or maintenance event.",
            "2. Review application, platform and dependency telemetry for the alert window.",
            "3. Check recent changes, error-rate trends, saturation and health-probe results.",
            "4. Validate that automated remediation ran once and did not enter a restart loop.",
            "5. Escalate, roll back or disable remediation if customer impact continues.",
            "6. Capture root cause, contributing factors and preventive actions in the post-incident review.",
        ]
    )


def ai_summary(incident: dict[str, Any]) -> str:
    api_url = os.getenv("AI_API_URL", "").rstrip("/")
    api_key = os.getenv("AI_API_KEY", "")
    model = os.getenv("AI_MODEL", "")
    if not api_url or not api_key or not model:
        raise RuntimeError("AI_API_URL, AI_API_KEY and AI_MODEL must be set for --use-ai.")

    prompt = (
        "You are an SRE incident assistant. Produce a concise incident summary, likely causes, "
        "five safe investigation steps, and two follow-up actions. Do not claim a root cause that "
        "is not present in the alert. Alert data:\n" + json.dumps(incident, indent=2, default=str)
    )
    request_body = json.dumps(
        {
            "model": model,
            "messages": [
                {"role": "system", "content": "Be cautious, operationally safe and evidence-based."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
    ).encode("utf-8")

    request = Request(
        f"{api_url}/chat/completions",
        data=request_body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"AI request failed: {exc}") from exc

    try:
        return str(result["choices"][0]["message"]["content"]).strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("AI response did not contain the expected chat-completions structure.") from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("payload", type=Path, help="Path to an Azure Monitor alert JSON payload")
    parser.add_argument("--use-ai", action="store_true", help="Use an OpenAI-compatible API")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = load_payload(args.payload)
    incident = extract_essentials(payload)

    if args.use_ai:
        try:
            print(ai_summary(incident))
            return 0
        except RuntimeError as exc:
            print(f"AI summary unavailable: {exc}", file=sys.stderr)
            print("Falling back to deterministic summary.\n", file=sys.stderr)

    print(deterministic_summary(incident))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
