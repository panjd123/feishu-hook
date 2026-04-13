# feishu-hook

Feishu notification integration for two environments:

- plain Codex
- `oh-my-codex` / OMX

The same repo supports both, but the installation strategy is different.

## Modes

### Plain Codex mode

Use this when you are using Codex directly and want a normal `Stop` hook.

- Installs a standalone `Stop` hook into the target `hooks.json`
- Sends `last_assistant_message` to Feishu
- Truncates only if the final Feishu request body would exceed `20 KB`

### OMX mode

Use this when `oh-my-codex` already owns `.codex/hooks.json`.

- Does not replace OMX lifecycle ownership
- Wraps the OMX-managed `Stop` command only
- Delegates to OMX first
- Sends Feishu only when OMX does **not** return a continuation decision

This is the important difference: in OMX mode the notification is sent only after OMX has decided the turn is truly finished.

## Repository Layout

- `src/feishu_notify_core.py`: shared Feishu send/size-limit logic
- `src/feishu_stop_notify.py`: plain Codex `Stop` hook
- `src/feishu_stop_notify_omx_wrapper.py`: OMX `Stop` wrapper
- `scripts/install.py`: auto-detecting installer
- `scripts/uninstall.py`: removes the installed integration
- `docs/installation.md`: installation and repair guide for coding agents

## Manual Commands

If you are installing through another coding agent, do not use this section as the primary instruction source. Point the agent to the raw installation guide in the `Installation` section below.

### Recommended

Run:

```bash
python3 scripts/install.py --webhook-url '<FULL_URL_OR_TOKEN>'
```

The installer defaults to `--mode auto`:

- if the target `Stop` command looks OMX-managed, it installs OMX mode
- otherwise it installs plain Codex mode

### Force plain Codex mode

```bash
python3 scripts/install.py --mode codex --webhook-url '<FULL_URL_OR_TOKEN>'
```

### Force OMX mode

Run `omx setup` first, then:

```bash
python3 scripts/install.py --mode omx --webhook-url '<FULL_URL_OR_TOKEN>'
```

If OMX was configured with project scope, the installer can infer that from `.omx/setup-scope.json` and target `./.codex`. Otherwise it falls back to `~/.codex`.

### Examples

```bash
python3 scripts/install.py \
  --webhook-url 'https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx' \
  --title-prefix '[Codex]'
```

`--webhook-url` is required for public-safe installs. It accepts either:

- the full Feishu webhook URL
- only the final hook token, such as `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`

If you pass only the token, the installer automatically expands it into the full Feishu webhook URL.

## Verify

1. Confirm installer output shows the chosen mode.
2. Trigger a finished Codex turn.
3. Check Feishu for the bot message.
4. Inspect the local log if needed:

```bash
tail -n 50 ~/.codex/hooks/logs/feishu_stop_notify.log
```

For OMX project-scope installs, the log lives under `./.codex/hooks/logs/feishu_stop_notify.log`.

## Uninstall

```bash
python3 scripts/uninstall.py
```

In OMX mode this restores the original OMX `Stop` command. In plain Codex mode this removes the standalone Feishu `Stop` hook entry.

## Installation

### For Humans

Copy and paste this prompt to your LLM agent (Claude Code, AmpCode, Cursor, etc.):

```markdown
Install or repair `feishu-hook` by following this document exactly:

https://raw.githubusercontent.com/panjd123/feishu-hook/refs/heads/main/docs/installation.md
```
