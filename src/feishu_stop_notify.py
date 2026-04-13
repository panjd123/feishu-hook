#!/usr/bin/env python3

"""Plain Codex Stop hook: send the last assistant message to a Feishu bot."""

from __future__ import annotations

import json
import pathlib
import sys

from feishu_notify_core import load_json, log, send_notification_from_event


SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "feishu_stop_notify_config.json"
LOG_PATH = SCRIPT_DIR / "logs" / "feishu_stop_notify.log"


def emit_continue() -> int:
    sys.stdout.write(json.dumps({"continue": True}, ensure_ascii=False))
    sys.stdout.flush()
    return 0


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception as exc:
        log(LOG_PATH, f"plain stdin_parse_error={exc!r}")
        return emit_continue()

    try:
        config = load_json(CONFIG_PATH)
    except Exception as exc:
        log(LOG_PATH, f"plain config_load_error={exc!r}")
        return emit_continue()

    send_notification_from_event(
        event,
        config,
        LOG_PATH,
        log_prefix="plain",
    )
    return emit_continue()


if __name__ == "__main__":
    raise SystemExit(main())

