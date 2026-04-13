#!/usr/bin/env python3

"""OMX Stop wrapper: delegate to OMX first, then notify only on final stop."""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys

from feishu_notify_core import load_json, log, send_notification_from_event


SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "feishu_stop_notify_config.json"
LOG_PATH = SCRIPT_DIR / "logs" / "feishu_stop_notify.log"


def main() -> int:
    raw_input = sys.stdin.buffer.read()
    try:
        event = json.loads(raw_input.decode("utf-8")) if raw_input.strip() else {}
    except Exception as exc:
        log(LOG_PATH, f"omx stdin_parse_error={exc!r}")
        return 0

    try:
        config = load_json(CONFIG_PATH)
    except Exception as exc:
        log(LOG_PATH, f"omx config_load_error={exc!r}")
        return 0

    original_command = str(config.get("omx_original_stop_command") or "").strip()
    if not original_command:
        log(LOG_PATH, "omx missing_original_stop_command")
        return 0

    completed = subprocess.run(
        original_command,
        shell=True,
        input=raw_input,
        capture_output=True,
    )

    if completed.stderr:
        sys.stderr.buffer.write(completed.stderr)
        sys.stderr.flush()

    if completed.returncode != 0:
        if completed.stdout:
            sys.stdout.buffer.write(completed.stdout)
            sys.stdout.flush()
        log(LOG_PATH, f"omx delegate_failed returncode={completed.returncode}")
        return completed.returncode

    hook_event_name = str(
        event.get("hook_event_name")
        or event.get("hookEventName")
        or event.get("event")
        or event.get("name")
        or ""
    ).strip()

    if hook_event_name != "Stop":
        if completed.stdout:
            sys.stdout.buffer.write(completed.stdout)
            sys.stdout.flush()
        return 0

    if completed.stdout.strip():
        sys.stdout.buffer.write(completed.stdout)
        sys.stdout.flush()
        log(LOG_PATH, "omx stop_continued_by_omx skip_notify=true")
        return 0

    send_notification_from_event(
        event,
        config,
        LOG_PATH,
        log_prefix="omx",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
