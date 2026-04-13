#!/usr/bin/env python3

"""Install the Feishu notification hook for plain Codex or oh-my-codex."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import sys
from datetime import datetime


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCE_CORE_PATH = REPO_ROOT / "src" / "feishu_notify_core.py"
SOURCE_PLAIN_HOOK_PATH = REPO_ROOT / "src" / "feishu_stop_notify.py"
SOURCE_OMX_WRAPPER_PATH = REPO_ROOT / "src" / "feishu_stop_notify_omx_wrapper.py"

CORE_FILENAME = "feishu_notify_core.py"
PLAIN_HOOK_FILENAME = "feishu_stop_notify.py"
OMX_WRAPPER_FILENAME = "feishu_stop_notify_omx_wrapper.py"
CONFIG_FILENAME = "feishu_stop_notify_config.json"

DEFAULT_TITLE_PREFIX = "[Codex]"
DEFAULT_MODE = "auto"
PLAIN_STOP_TIMEOUT_SEC = 10
PROJECT_SCOPE_FILE = pathlib.Path(".omx") / "setup-scope.json"
FEISHU_WEBHOOK_PREFIX = "https://open.feishu.cn/open-apis/bot/v2/hook/"


def backup_file(path: pathlib.Path) -> pathlib.Path | None:
    if not path.exists():
        return None
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = path.with_name(f"{path.name}.bak.{timestamp}")
    shutil.copy2(path, backup_path)
    return backup_path


def load_json(path: pathlib.Path, default: dict) -> dict:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: pathlib.Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def read_project_scope(project_root: pathlib.Path) -> str | None:
    scope_file = project_root / PROJECT_SCOPE_FILE
    data = load_json(scope_file, {})
    scope = str(data.get("scope") or "").strip()
    return scope or None


def resolve_codex_home(
    codex_home_arg: str | None,
    project_root: pathlib.Path,
) -> tuple[pathlib.Path, str]:
    if codex_home_arg:
        return pathlib.Path(codex_home_arg).expanduser().resolve(), "cli"

    scope = read_project_scope(project_root)
    if scope == "project":
        return (project_root / ".codex").resolve(), "omx_project_scope"
    if scope == "user":
        return pathlib.Path("~/.codex").expanduser().resolve(), "omx_user_scope"
    return pathlib.Path("~/.codex").expanduser().resolve(), "default_user_scope"


def ensure_codex_hooks_enabled(config_path: pathlib.Path) -> tuple[bool, pathlib.Path | None]:
    existing = ""
    if config_path.exists():
        existing = config_path.read_text(encoding="utf-8")

    lines = existing.splitlines()
    changed = False
    features_start = None
    features_end = len(lines)

    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            if stripped == "[features]":
                features_start = index
                continue
            if features_start is not None:
                features_end = index
                break

    if features_start is None:
        if lines and lines[-1] != "":
            lines.append("")
        lines.extend(["[features]", "codex_hooks = true"])
        changed = True
    else:
        found = False
        for index in range(features_start + 1, features_end):
            if re.match(r"\s*codex_hooks\s*=", lines[index]):
                found = True
                indent = lines[index][: len(lines[index]) - len(lines[index].lstrip())]
                desired = f"{indent}codex_hooks = true"
                if lines[index] != desired:
                    lines[index] = desired
                    changed = True
                break
        if not found:
            lines.insert(features_end, "codex_hooks = true")
            changed = True

    if not changed:
        return False, None

    backup_path = backup_file(config_path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return True, backup_path


def normalize_plain_stop_entry(command: str) -> dict:
    return {
        "hooks": [
            {
                "type": "command",
                "command": command,
                "timeout": PLAIN_STOP_TIMEOUT_SEC,
            }
        ]
    }


def list_stop_commands(payload: dict) -> list[str]:
    commands: list[str] = []
    hooks = payload.get("hooks")
    if not isinstance(hooks, dict):
        return commands
    stop_hooks = hooks.get("Stop")
    if not isinstance(stop_hooks, list):
        return commands
    for group in stop_hooks:
        if not isinstance(group, dict):
            continue
        group_hooks = group.get("hooks")
        if not isinstance(group_hooks, list):
            continue
        for hook in group_hooks:
            if not isinstance(hook, dict):
                continue
            command = str(hook.get("command") or "").strip()
            if command:
                commands.append(command)
    return commands


def detect_install_mode(hooks_path: pathlib.Path, requested_mode: str) -> tuple[str, str]:
    if requested_mode != DEFAULT_MODE:
        return requested_mode, "explicit"

    payload = load_json(hooks_path, {"hooks": {}})
    commands = list_stop_commands(payload)
    if any("codex-native-hook.js" in command for command in commands):
        return "omx", "detected_omx_stop_command"
    if any(OMX_WRAPPER_FILENAME in command for command in commands):
        return "omx", "existing_omx_wrapper"
    return "codex", "fallback_plain_codex"


def ensure_plain_stop_hook(hooks_path: pathlib.Path, command: str) -> tuple[bool, pathlib.Path | None]:
    payload = load_json(hooks_path, {"hooks": {}})
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {hooks_path}")

    hooks = payload.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError(f"Expected 'hooks' to be an object in {hooks_path}")

    stop_hooks = hooks.setdefault("Stop", [])
    if not isinstance(stop_hooks, list):
        raise ValueError(f"Expected 'hooks.Stop' to be a list in {hooks_path}")

    changed = False
    found = False
    for group in stop_hooks:
        if not isinstance(group, dict):
            continue
        group_hooks = group.get("hooks")
        if not isinstance(group_hooks, list):
            continue
        for hook in group_hooks:
            if not isinstance(hook, dict):
                continue
            existing_command = str(hook.get("command") or "")
            if PLAIN_HOOK_FILENAME not in existing_command:
                continue
            found = True
            desired = {
                "type": "command",
                "command": command,
                "timeout": PLAIN_STOP_TIMEOUT_SEC,
            }
            if hook != desired:
                hook.clear()
                hook.update(desired)
                changed = True

    if not found:
        stop_hooks.append(normalize_plain_stop_entry(command))
        changed = True

    if not changed:
        return False, None

    backup_path = backup_file(hooks_path)
    write_json(hooks_path, payload)
    return True, backup_path


def ensure_omx_stop_wrapper(
    hooks_path: pathlib.Path,
    wrapper_command: str,
    existing_original_command: str,
) -> tuple[bool, pathlib.Path | None, str, list[str]]:
    payload = load_json(hooks_path, {"hooks": {}})
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {hooks_path}")

    hooks = payload.get("hooks")
    if not isinstance(hooks, dict):
        raise ValueError(f"Expected 'hooks' to be an object in {hooks_path}")

    stop_hooks = hooks.get("Stop")
    if not isinstance(stop_hooks, list):
        raise RuntimeError(
            f"No Stop hooks found in {hooks_path}. Run `omx setup` first or use --mode codex."
        )

    changed = False
    target_hook: dict | None = None
    original_command = existing_original_command.strip()
    extra_stop_commands: list[str] = []

    for group in stop_hooks:
        if not isinstance(group, dict):
            continue
        group_hooks = group.get("hooks")
        if not isinstance(group_hooks, list):
            continue
        for hook in group_hooks:
            if not isinstance(hook, dict):
                continue
            command = str(hook.get("command") or "").strip()
            if not command:
                continue
            if OMX_WRAPPER_FILENAME in command:
                target_hook = hook
                continue
            if "codex-native-hook.js" in command and target_hook is None:
                target_hook = hook
                if not original_command:
                    original_command = command
                continue
            extra_stop_commands.append(command)

    if target_hook is None:
        raise RuntimeError(
            "Could not find the OMX-managed Stop command in hooks.json. "
            "Expected a command containing codex-native-hook.js."
        )

    if not original_command:
        raise RuntimeError(
            "Missing original OMX Stop command; cannot install a safe wrapper."
        )

    desired_command = wrapper_command
    if str(target_hook.get("command") or "").strip() != desired_command:
        target_hook["type"] = "command"
        target_hook["command"] = desired_command
        changed = True

    if "timeout" not in target_hook:
        target_hook["timeout"] = 30
        changed = True

    if not changed:
        return False, None, original_command, extra_stop_commands

    backup_path = backup_file(hooks_path)
    write_json(hooks_path, payload)
    return True, backup_path, original_command, extra_stop_commands


def install_runtime_files(hooks_dir: pathlib.Path) -> dict[str, pathlib.Path]:
    hooks_dir.mkdir(parents=True, exist_ok=True)
    installed = {
        CORE_FILENAME: hooks_dir / CORE_FILENAME,
        PLAIN_HOOK_FILENAME: hooks_dir / PLAIN_HOOK_FILENAME,
        OMX_WRAPPER_FILENAME: hooks_dir / OMX_WRAPPER_FILENAME,
    }
    shutil.copy2(SOURCE_CORE_PATH, installed[CORE_FILENAME])
    shutil.copy2(SOURCE_PLAIN_HOOK_PATH, installed[PLAIN_HOOK_FILENAME])
    shutil.copy2(SOURCE_OMX_WRAPPER_PATH, installed[OMX_WRAPPER_FILENAME])
    return installed


def normalize_webhook_url(value: str) -> str:
    candidate = value.strip()
    if not candidate:
        raise ValueError("missing webhook URL or hook token")

    if candidate.startswith("https://") or candidate.startswith("http://"):
        return candidate

    return FEISHU_WEBHOOK_PREFIX + candidate


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=["auto", "codex", "omx"],
        default=DEFAULT_MODE,
        help="Install mode. auto detects an OMX-managed Stop hook and wraps it; otherwise uses plain Codex mode.",
    )
    parser.add_argument(
        "--webhook-url",
        help="Required. Accepts either a full Feishu webhook URL or just the final hook token.",
    )
    parser.add_argument(
        "--title-prefix",
        default=DEFAULT_TITLE_PREFIX,
        help="Prefix shown before the repo name. Default: [Codex].",
    )
    parser.add_argument(
        "--codex-home",
        help="Codex home directory. If omitted, auto-detect from .omx/setup-scope.json or fall back to ~/.codex.",
    )
    parser.add_argument(
        "--project-root",
        default=".",
        help="Project root used for OMX scope detection. Default: current directory.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    project_root = pathlib.Path(args.project_root).expanduser().resolve()
    codex_home, codex_home_reason = resolve_codex_home(args.codex_home, project_root)
    hooks_dir = codex_home / "hooks"
    config_path = hooks_dir / CONFIG_FILENAME
    config_toml_path = codex_home / "config.toml"
    hooks_json_path = codex_home / "hooks.json"

    mode, mode_reason = detect_install_mode(hooks_json_path, args.mode)
    installed_files = install_runtime_files(hooks_dir)
    plain_hook_path = installed_files[PLAIN_HOOK_FILENAME]
    omx_wrapper_path = installed_files[OMX_WRAPPER_FILENAME]

    if not args.webhook_url:
        print(
            "error: --webhook-url is required. Pass either the full Feishu webhook URL "
            "or just the final hook token.",
            file=sys.stderr,
        )
        return 1

    try:
        webhook_url = normalize_webhook_url(str(args.webhook_url))
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    config_changed, config_backup = ensure_codex_hooks_enabled(config_toml_path)
    hooks_changed = False
    hooks_backup: pathlib.Path | None = None
    original_omx_command = ""
    extra_stop_commands: list[str] = []

    if mode == "codex":
        plain_command = f"python3 {plain_hook_path}"
        hooks_changed, hooks_backup = ensure_plain_stop_hook(hooks_json_path, plain_command)
    else:
        wrapper_command = f"python3 {omx_wrapper_path}"
        existing_config = load_json(config_path, {})
        existing_original_command = str(existing_config.get("omx_original_stop_command") or "").strip()
        hooks_changed, hooks_backup, original_omx_command, extra_stop_commands = ensure_omx_stop_wrapper(
            hooks_json_path,
            wrapper_command,
            existing_original_command,
        )

    write_json(
        config_path,
        {
            "webhook_url": webhook_url,
            "title_prefix": str(args.title_prefix or DEFAULT_TITLE_PREFIX).strip() or DEFAULT_TITLE_PREFIX,
            "install_mode": mode,
            **({"omx_original_stop_command": original_omx_command} if mode == "omx" else {}),
        },
    )

    print(f"Project root:            {project_root}")
    print(f"Codex home:              {codex_home}")
    print(f"Codex home source:       {codex_home_reason}")
    print(f"Install mode:            {mode}")
    print(f"Mode source:             {mode_reason}")
    print(f"Installed runtime core:  {installed_files[CORE_FILENAME]}")
    print(f"Installed plain hook:    {plain_hook_path}")
    print(f"Installed OMX wrapper:   {omx_wrapper_path}")
    print(f"Installed hook config:   {config_path}")
    print(f"config.toml changed:     {'yes' if config_changed else 'no'}")
    if config_backup:
        print(f"config.toml backup:      {config_backup}")
    print(f"hooks.json changed:      {'yes' if hooks_changed else 'no'}")
    if hooks_backup:
        print(f"hooks.json backup:       {hooks_backup}")
    if mode == "omx":
        print(f"Original OMX Stop cmd:   {original_omx_command}")
        if extra_stop_commands:
            print("Extra Stop commands:     detected")
            for command in extra_stop_commands:
                print(f"  - {command}")
            print(
                "Warning: extra Stop hooks remain alongside the OMX wrapper; "
                "only the OMX-managed Stop command is wrapped."
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
