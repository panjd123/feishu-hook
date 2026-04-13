#!/usr/bin/env python3

"""Shared Feishu notification helpers for Codex/OMX hook integrations."""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import urllib.request


FEISHU_REQUEST_LIMIT_BYTES = 20 * 1024
REQUEST_TIMEOUT_SEC = 8
TRUNCATION_SUFFIX = "\n\n[Truncated]"
DEFAULT_TITLE_PREFIX = "[Codex]"


def log(log_path: pathlib.Path, message: str) -> None:
    timestamp = dt.datetime.now().isoformat(timespec="seconds")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"{timestamp} {message}\n")


def load_json(path: pathlib.Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def preview_text(text: str, limit: int = 120) -> str:
    preview = text.replace("\n", "\\n")
    if len(preview) <= limit:
        return preview
    return preview[:limit] + "..."


def build_message(event: dict, prefix: str) -> str | None:
    last_message = str(event.get("last_assistant_message") or "").strip()
    if not last_message:
        return None

    cwd = str(event.get("cwd") or "").strip()
    repo_name = pathlib.Path(cwd).name if cwd else "unknown"
    return f"{prefix} {repo_name}\n\n{last_message}"


def build_feishu_body(text: str) -> bytes:
    return json.dumps(
        {"msg_type": "text", "content": {"text": text}},
        ensure_ascii=False,
    ).encode("utf-8")


def fit_message_to_request_limit(text: str) -> tuple[str, bool]:
    if len(build_feishu_body(text)) <= FEISHU_REQUEST_LIMIT_BYTES:
        return text, False

    low = 0
    high = len(text)
    best = TRUNCATION_SUFFIX
    while low <= high:
        mid = (low + high) // 2
        candidate = text[:mid] + TRUNCATION_SUFFIX
        if len(build_feishu_body(candidate)) <= FEISHU_REQUEST_LIMIT_BYTES:
            best = candidate
            low = mid + 1
        else:
            high = mid - 1

    return best, True


def post_to_feishu(webhook_url: str, text: str) -> tuple[int, str]:
    body = build_feishu_body(text)
    request = urllib.request.Request(
        webhook_url,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SEC) as response:
        response_body = response.read().decode("utf-8", errors="replace")
        return response.status, response_body


def send_notification_from_event(
    event: dict,
    config: dict,
    log_path: pathlib.Path,
    *,
    log_prefix: str,
) -> bool:
    webhook_url = str(config.get("webhook_url") or "").strip()
    prefix = str(config.get("title_prefix") or DEFAULT_TITLE_PREFIX).strip() or DEFAULT_TITLE_PREFIX
    session_id = str(event.get("session_id") or "")
    turn_id = str(event.get("turn_id") or "")

    if not webhook_url:
        log(log_path, f"{log_prefix} missing_webhook_url")
        return False

    message = build_message(event, prefix)
    if not message:
        log(log_path, f"{log_prefix} skip_empty_last_assistant_message")
        return False

    request_bytes_before = len(build_feishu_body(message))
    message, truncated = fit_message_to_request_limit(message)
    request_bytes_after = len(build_feishu_body(message))

    if truncated:
        log(
            log_path,
            f"{log_prefix} request_truncated "
            f"session_id={session_id} "
            f"turn_id={turn_id} "
            f"before_bytes={request_bytes_before} "
            f"after_bytes={request_bytes_after} "
            f"preview={preview_text(message)}",
        )

    try:
        status_code, response_body = post_to_feishu(webhook_url, message)
        log(
            log_path,
            f"{log_prefix} feishu "
            f"session_id={session_id} "
            f"turn_id={turn_id} "
            f"request_bytes={request_bytes_after} "
            f"status={status_code} "
            f"preview={preview_text(message)} "
            f"body={response_body}",
        )
        return True
    except Exception as exc:
        log(
            log_path,
            f"{log_prefix} send_error "
            f"session_id={session_id} "
            f"turn_id={turn_id} "
            f"request_bytes={request_bytes_after} "
            f"preview={preview_text(message)} "
            f"error={exc!r}",
        )
        return False

