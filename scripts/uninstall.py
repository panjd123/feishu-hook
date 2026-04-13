#!/usr/bin/env python3

"""Remove the Feishu notification hook from plain Codex or oh-my-codex."""

from __future__ import annotations

import argparse
import json
import pathlib
import shutil
from datetime import datetime


PLAIN_HOOK_FILENAME = "feishu_stop_notify.py"
OMX_WRAPPER_FILENAME = "feishu_stop_notify_omx_wrapper.py"
CORE_FILENAME = "feishu_notify_core.py"
CONFIG_FILENAME = "feishu_stop_notify_config.json"
PROJECT_SCOPE_FILE = pathlib.Path(".omx") / "setup-scope.json"


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


def remove_plain_stop_hook(hooks_path: pathlib.Path) -> tuple[bool, pathlib.Path | None]:
    payload = load_json(hooks_path, {"hooks": {}})
    hooks = payload.get("hooks")
    if not isinstance(hooks, dict):
        return False, None

    stop_hooks = hooks.get("Stop")
    if not isinstance(stop_hooks, list):
        return False, None

    changed = False
    new_stop_hooks = []
    for group in stop_hooks:
        if not isinstance(group, dict):
            new_stop_hooks.append(group)
            continue
        group_hooks = group.get("hooks")
        if not isinstance(group_hooks, list):
            new_stop_hooks.append(group)
            continue
        filtered_hooks = []
        for hook in group_hooks:
            if not isinstance(hook, dict):
                filtered_hooks.append(hook)
                continue
            command = str(hook.get("command") or "")
            if PLAIN_HOOK_FILENAME in command:
                changed = True
                continue
            filtered_hooks.append(hook)
        if filtered_hooks:
            new_group = dict(group)
            new_group["hooks"] = filtered_hooks
            new_stop_hooks.append(new_group)
        else:
            changed = True

    if not changed:
        return False, None

    hooks["Stop"] = new_stop_hooks
    backup_path = backup_file(hooks_path)
    write_json(hooks_path, payload)
    return True, backup_path


def restore_omx_stop_hook(
    hooks_path: pathlib.Path,
    original_command: str,
) -> tuple[bool, pathlib.Path | None]:
    payload = load_json(hooks_path, {"hooks": {}})
    hooks = payload.get("hooks")
    if not isinstance(hooks, dict):
        return False, None

    stop_hooks = hooks.get("Stop")
    if not isinstance(stop_hooks, list):
        return False, None

    changed = False
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
            if OMX_WRAPPER_FILENAME not in command:
                continue
            if command != original_command:
                hook["type"] = "command"
                hook["command"] = original_command
                changed = True

    if not changed:
        return False, None

    backup_path = backup_file(hooks_path)
    write_json(hooks_path, payload)
    return True, backup_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
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
    hooks_json_path = codex_home / "hooks.json"

    config = load_json(config_path, {})
    install_mode = str(config.get("install_mode") or "").strip() or "codex"
    hooks_changed = False
    hooks_backup: pathlib.Path | None = None

    if install_mode == "omx":
        original_command = str(config.get("omx_original_stop_command") or "").strip()
        if original_command:
            hooks_changed, hooks_backup = restore_omx_stop_hook(
                hooks_json_path,
                original_command,
            )
    else:
        hooks_changed, hooks_backup = remove_plain_stop_hook(hooks_json_path)

    removed_files = []
    for filename in (PLAIN_HOOK_FILENAME, OMX_WRAPPER_FILENAME, CORE_FILENAME, CONFIG_FILENAME):
        path = hooks_dir / filename
        if path.exists():
            path.unlink()
            removed_files.append(path)

    print(f"Project root:         {project_root}")
    print(f"Codex home:           {codex_home}")
    print(f"Codex home source:    {codex_home_reason}")
    print(f"Detected mode:        {install_mode}")
    print(f"hooks.json changed:   {'yes' if hooks_changed else 'no'}")
    if hooks_backup:
        print(f"hooks.json backup:    {hooks_backup}")
    if removed_files:
        for path in removed_files:
            print(f"Removed:              {path}")
    else:
        print("Removed:              none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
