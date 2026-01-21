#!/usr/bin/env python3
import hashlib
import hmac
import json
import os
import sys
import requests
from datetime import datetime, timezone

SUBMISSION_URL = "https://b12.io/apply/submission"


def _build_repository_link() -> str | None:
    server_url = os.getenv("GITHUB_SERVER_URL")
    repo = os.getenv("GITHUB_REPOSITORY")
    if server_url and repo:
        return f"{server_url}/{repo}"
    return None


def _build_action_run_link() -> str | None:
    server_url = os.getenv("GITHUB_SERVER_URL")
    repo = os.getenv("GITHUB_REPOSITORY")
    run_id = os.getenv("GITHUB_RUN_ID")
    if server_url and repo and run_id:
        return f"{server_url}/{repo}/actions/runs/{run_id}"
    return None


def main() -> int:
    email = os.getenv("EMAIL")
    resume_link = os.getenv("RESUME_LINK")
    secret = os.getenv("SIGNING_SECRET")
    repository_link = os.getenv("REPOSITORY_LINK") or _build_repository_link()
    action_run_link = os.getenv("ACTION_RUN_LINK") or _build_action_run_link()

    missing = []
    if not email:
        missing.append("EMAIL")
    if not resume_link:
        missing.append("RESUME_LINK")
    if not secret:
        missing.append("SIGNING_SECRET")
    if not repository_link:
        missing.append("REPOSITORY_LINK (or GITHUB_SERVER_URL + GITHUB_REPOSITORY)")
    if not action_run_link:
        missing.append(
            "ACTION_RUN_LINK (or GITHUB_SERVER_URL + GITHUB_REPOSITORY + GITHUB_RUN_ID)"
        )

    if missing:
        print("Missing required environment variables:", file=sys.stderr)
        for name in missing:
            print(f"- {name}", file=sys.stderr)
        return 2

    payload = {
        "timestamp": datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z"),
        "name": "Vadim Panov",
        "email": email,
        "resume_link": resume_link,
        "repository_link": repository_link,
        "action_run_link": action_run_link,
    }

    body = json.dumps(
        payload,
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=False,
    ).encode("utf-8")
    print(body.decode("utf-8"))

    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    signature = f"sha256={digest}"

    try:
        response = requests.post(
            SUBMISSION_URL,
            data=body,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "X-Signature-256": signature,
            },
            timeout=20,
        )
        response.raise_for_status()
        print(response.text)
    except requests.HTTPError as exc:
        error_body = exc.response.text if exc.response else ""
        status_code = exc.response.status_code if exc.response else "error"
        print(f"HTTP {status_code}: {error_body}", file=sys.stderr)
        return 1
    except requests.RequestException as exc:
        print(f"Network error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
