# feishu-hook Installation

Use this file as a complete standalone instruction set for a coding agent.

If the user says:

> Install and configure `feishu-hook` by following the instructions here

then this file should be sufficient even if the agent does not yet know:

- the repository URL
- whether the repo is already cloned locally
- whether the task is a fresh install or a repair
- whether the target environment is plain Codex or `oh-my-codex` / OMX

## Repository

Canonical repository URL:

```text
https://github.com/panjd123/feishu-hook.git
```

If the repo is not already available locally, clone it first:

```bash
git clone https://github.com/panjd123/feishu-hook.git
cd feishu-hook
```

If the repo is already present locally, use that checkout instead. If the task is a repair or upgrade, pull the latest changes before installing, but only after handling webhook acquisition rules below.

## Goal

Install the Feishu notification integration in the correct mode for the current environment:

- `codex` mode for plain Codex
- `omx` mode for `oh-my-codex`

The agent must also be able to repair an existing install when the environment has drifted.

## Required First Decision

Before running any installer command, determine whether the task is:

- a fresh install
- a repair / reinstall / upgrade

This matters because webhook acquisition works differently for fresh installs and repairs.

## Webhook Acquisition Rule

### Fresh install

For a fresh install, the agent must first obtain the Feishu webhook from the user.

Accepted input forms:

- full Feishu webhook URL
- only the final hook token

Example token form:

```text
xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

For fresh installs, do not:

- invent or guess a webhook
- assume the repo contains one
- proceed with installation before the user provides it

### Repair / reinstall / upgrade

For a repair or reinstall, inspect local existing configuration first and reuse it if a valid webhook is already present.

Typical places to inspect:

- target `.codex/hooks/feishu_stop_notify_config.json`
- project-local `./.codex/hooks/feishu_stop_notify_config.json`
- user-level `~/.codex/hooks/feishu_stop_notify_config.json`

If a valid webhook is already present in the active target environment, you may reuse it.

If no valid webhook is found, ask the user for:

- the full Feishu webhook URL
- or the final hook token

## Practical Order Of Operations

1. Decide whether this is a fresh install or a repair
2. If repair, inspect local config first
3. If no reusable webhook is found, ask the user
4. Ensure the repo is available locally
5. If repairing/upgrading from an existing checkout, pull latest changes
6. Inspect the target environment
7. Choose the correct install mode
8. Run the installer
9. Verify that the installation actually works

## Environment Inspection

Inspect all of the following before deciding what to do:

1. `./.omx/setup-scope.json` if present
2. target `.codex/hooks.json`
3. target `.codex/hooks/feishu_stop_notify_config.json` if present
4. target `.codex/hooks/` runtime files if present

You must explicitly determine:

- which `codex-home` is currently authoritative
- whether OMX owns the target `Stop` hook
- whether `feishu-hook` is already installed
- whether the current installation mode matches the current environment

## Installation vs Repair Decision

### Treat it as fresh install when

- no Feishu runtime files are present in the target `hooks/` directory
- and no Feishu-related command is present in the target `hooks.json`

### Treat it as repair / refresh when any of these are true

- Feishu runtime files exist
- Feishu config exists
- `hooks.json` contains a Feishu command
- OMX owns the `Stop` hook but Feishu config says `install_mode = "codex"`
- Feishu wrapper is installed but `hooks.json` no longer points to it
- original OMX `Stop` command was lost or changed

In repair mode, the correct default action is usually to run `scripts/install.py` again with the correct mode, not to manually patch files.

## Mode Selection

Choose `omx` mode when all of these are true:

- the project contains `.omx/setup-scope.json`, or you know `omx setup` was run
- the target `.codex/hooks.json` has a `Stop` command containing `codex-native-hook.js`

Choose `codex` mode when any of these are true:

- there is no `.omx/setup-scope.json`
- the target `.codex/hooks.json` does not look OMX-managed
- the user wants plain Codex only

If uncertain, use `--mode auto`.

## Common Repair Scenarios

### Scenario A: Feishu was installed first, then `omx setup` was run later

Expected symptom:

- Feishu files still exist
- but target `.codex/hooks.json` was rewritten by OMX and now points directly to `codex-native-hook.js`

Correct action:

```bash
python3 scripts/install.py --mode omx --webhook-url '<FULL_URL_OR_TOKEN>'
```

If scope is ambiguous, prefer:

```bash
python3 scripts/install.py --mode auto --webhook-url '<FULL_URL_OR_TOKEN>'
```

Then verify that the target `Stop` command now points to `feishu_stop_notify_omx_wrapper.py`.

### Scenario B: OMX exists, but Feishu was later installed in plain `codex` mode

Expected symptom:

- target `Stop` hook points directly to `feishu_stop_notify.py`
- but OMX should still own lifecycle decisions

Correct action:

```bash
python3 scripts/install.py --mode omx --webhook-url '<FULL_URL_OR_TOKEN>'
```

Then verify that:

- `hooks.json` points to `feishu_stop_notify_omx_wrapper.py`
- config stores `omx_original_stop_command`

### Scenario C: OMX scope changed

Expected symptom:

- Feishu may still be installed under the old `codex-home`
- but current `.omx/setup-scope.json` points somewhere else

Correct action:

1. determine the current intended `codex-home`
2. reinstall into that target
3. optionally uninstall from the old target if requested

Do not assume `~/.codex` is still correct after OMX project-scope setup.

## Codex Home Resolution

If `--codex-home` is not provided, the installer uses this logic:

1. If `./.omx/setup-scope.json` says `project`, target `./.codex`
2. If `./.omx/setup-scope.json` says `user`, target `~/.codex`
3. Otherwise target `~/.codex`

Override this with `--codex-home` when necessary.

## Public-Safe Defaults

- Default `title_prefix` is `[Codex]`
- There is no bundled webhook in this public-safe repo
- The user must provide a webhook explicitly, unless a valid existing local config is being reused during repair

## Canonical Install Commands

### Auto mode

```bash
python3 scripts/install.py --webhook-url '<FULL_URL_OR_TOKEN>'
```

Use this by default when repairing an unknown environment.

### Plain Codex mode

```bash
python3 scripts/install.py --mode codex --webhook-url '<FULL_URL_OR_TOKEN>'
```

### oh-my-codex / OMX mode

If OMX is not installed yet, install/setup OMX first:

```bash
omx setup
```

Then install:

```bash
python3 scripts/install.py --mode omx --webhook-url '<FULL_URL_OR_TOKEN>'
```

### Full URL example

```bash
python3 scripts/install.py \
  --webhook-url 'https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx' \
  --title-prefix '[Codex]'
```

### Token-only example

```bash
python3 scripts/install.py \
  --webhook-url 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'
```

The installer automatically expands a token into the full Feishu webhook URL.

## What Each Mode Does

### `codex` mode

1. Copies runtime files into `<codex-home>/hooks/`
2. Writes `<codex-home>/hooks/feishu_stop_notify_config.json`
3. Ensures `<codex-home>/config.toml` enables `codex_hooks = true`
4. Adds a standalone `Stop` hook running:

```bash
python3 /ABSOLUTE/PATH/TO/<codex-home>/hooks/feishu_stop_notify.py
```

### `omx` mode

1. Copies runtime files into `<codex-home>/hooks/`
2. Writes `<codex-home>/hooks/feishu_stop_notify_config.json`
3. Leaves OMX ownership of lifecycle logic intact
4. Replaces only the OMX-managed `Stop` command with:

```bash
python3 /ABSOLUTE/PATH/TO/<codex-home>/hooks/feishu_stop_notify_omx_wrapper.py
```

5. Stores the original OMX `Stop` command in config under `omx_original_stop_command`

## OMX Behavioral Contract

In `omx` mode the wrapper:

1. delegates the same stdin payload to the original OMX `Stop` command
2. waits for OMX to decide whether the turn should continue
3. if OMX returns hook output, it forwards that output and does **not** send Feishu
4. if OMX returns no hook output, it sends Feishu

This is the key difference from plain Codex mode.

## Validation Steps

After installation, verify all of the following:

1. installer stdout shows the expected `Codex home`
2. installer stdout shows the correct `Install mode`
3. target `hooks.json` points to the correct command
4. target `hooks/feishu_stop_notify_config.json` exists
5. in OMX mode, config contains `omx_original_stop_command`

Command checks:

```bash
cat <codex-home>/hooks.json
cat <codex-home>/hooks/feishu_stop_notify_config.json
tail -n 50 <codex-home>/hooks/logs/feishu_stop_notify.log
```

Expected `Stop` command:

- plain Codex: `feishu_stop_notify.py`
- OMX: `feishu_stop_notify_omx_wrapper.py`

## Repair Validation Checklist

After any repair or reinstall, verify all of the following:

1. the chosen `codex-home` matches the active environment
2. `hooks.json` points to the correct command for that environment
3. in OMX mode, `feishu_stop_notify_config.json` contains `omx_original_stop_command`
4. triggering a final stop sends Feishu
5. in OMX mode, a continuation-style `Stop` still returns OMX continuation JSON and does not send Feishu

If any of these checks fail, treat the environment as still broken and continue repairing.

## Idempotency

- Re-running `scripts/install.py` is supported
- In `omx` mode, re-running after `omx setup` is expected because `omx setup` rewrites `.codex/hooks.json`

If the user says installation already happened but behavior is wrong, inspect and then re-run the installer rather than assuming the existing install is intact.

## Rollback

Run:

```bash
python3 scripts/uninstall.py
```

Rollback behavior:

- `codex` mode: removes the standalone Feishu `Stop` hook
- `omx` mode: restores the original OMX `Stop` command and removes the Feishu runtime files
