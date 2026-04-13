# feishu-hook

`feishu-hook` sends the final assistant message from Codex to a Feishu bot webhook when a turn is actually finished.

It supports two environments:

- plain Codex
- `oh-my-codex` / OMX

The important behavior difference is:

- in plain Codex, it installs a normal `Stop` hook
- in OMX, it wraps the OMX-managed `Stop` hook and only sends Feishu after OMX decides the turn will not continue

## Installation

### For Humans

If you want an AI coding agent to install or repair this project, give it this document and tell it to follow it exactly:

```text
Install and configure feishu-hook by following the instructions here:
https://raw.githubusercontent.com/panjd123/feishu-hook/refs/heads/main/docs/installation.md
```

That file is the source of truth for installation, repair, environment detection, webhook acquisition, verification, and rollback.

## How It Works

### Plain Codex mode

- installs a standalone `Stop` hook into the target `hooks.json`
- sends `last_assistant_message` to Feishu
- truncates only when the final Feishu request body would exceed `20 KB`

### OMX mode

- keeps OMX in control of lifecycle decisions
- wraps the OMX-managed `Stop` command instead of replacing OMX behavior
- delegates to OMX first
- sends Feishu only if OMX does not return a continuation decision

## Repository Layout

- `src/feishu_notify_core.py`: shared Feishu send and size-limit logic
- `src/feishu_stop_notify.py`: plain Codex `Stop` hook
- `src/feishu_stop_notify_omx_wrapper.py`: OMX-aware wrapper
- `scripts/install.py`: installer with mode detection
- `scripts/uninstall.py`: uninstall and rollback helper
- `docs/installation.md`: complete install and repair instructions for AI agents
