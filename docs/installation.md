# feishu-hook Installation

Use this document when the task is:

> Install and configure `feishu-hook` by following the instructions here.

Your job is to inspect the environment, decide whether this is a fresh install or a repair, choose the correct mode, run the installer, and verify that the installation actually works.

## Goal

Install the Feishu notification integration in the correct mode for the current environment:

- `codex` mode for plain Codex
- `omx` mode for `oh-my-codex`

The agent must also be able to repair an existing install when the environment has drifted.

## Repository Root

Run all commands from the repository root.

## Required First Step

Before cloning this repository, before pulling updates, and before running any installer command, the agent must determine whether the task is:

- a fresh install
- a repair / reinstall

The webhook acquisition rule depends on that distinction.

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

For fresh installs, the agent must not:

- assume the webhook already exists in the repo
- invent or guess a webhook
- proceed with installation before the user provides it

### Repair / reinstall

For a repair or reinstall, the agent may first inspect local existing configuration and reuse it if a valid webhook is already present.

Typical places to inspect:

- target `.codex/hooks/feishu_stop_notify_config.json`
- project-local `./.codex/hooks/feishu_stop_notify_config.json`
- user-level `~/.codex/hooks/feishu_stop_notify_config.json`

If a valid existing webhook is found in the active target environment, the agent may proceed without asking the user again.

If no valid webhook is found, the agent must ask the user for:

- the full Feishu webhook URL
- or the final hook token

## Practical Order Of Operations

1. Decide whether this is fresh install vs repair
2. If repair, inspect local config first
3. If no reusable webhook is found, ask the user
4. Only then continue with clone / pull / install / repair steps

## High-Level Rule

Choose the installation mode based on who owns `hooks.json`.

- If `oh-my-codex` / OMX already manages the target `.codex/hooks.json`, use `omx` mode.
- Otherwise use `codex` mode.

If uncertain, run the installer with `--mode auto` and verify the detected mode from stdout.

Do not assume the current environment is healthy just because Feishu hook files or OMX files already exist.
The current task may be a repair, not a fresh install.

## Repair-First Mindset

Before changing anything, inspect the target environment and classify the task as one of:

- fresh install
- reinstall / refresh
- repair after another tool rewrote `hooks.json`
- repair after scope changed

Typical drift cases:

- Feishu hook was installed first, then `omx setup` was run later
- OMX was installed first, then Feishu hook was installed in plain `codex` mode by mistake
- OMX changed from user scope to project scope, or the reverse
- `hooks.json` still exists, but points to the wrong command for the current environment
- Feishu runtime files exist, but `hooks.json` no longer references them

The agent should treat these as repair scenarios and not as evidence that installation can be skipped.

## Required Inspection Before Install Or Repair

Inspect all of the following before deciding what to do:

1. `./.omx/setup-scope.json` if present
2. target `.codex/hooks.json`
3. target `.codex/hooks/feishu_stop_notify_config.json` if present
4. target `.codex/hooks/` runtime files if present

The agent should explicitly determine:

- which `codex-home` is currently authoritative
- whether OMX owns the target `Stop` hook
- whether Feishu is already installed
- whether the current Feishu installation mode matches the current environment

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

## Mode Selection Procedure

### Choose `omx` mode when all of these are true

- The project contains `.omx/setup-scope.json`, or you know `omx setup` was run.
- The target `.codex/hooks.json` already has a `Stop` command containing `codex-native-hook.js`.

### Choose `codex` mode when any of these are true

- There is no `.omx/setup-scope.json`.
- The target `.codex/hooks.json` does not look OMX-managed.
- The user wants plain Codex only.

## Common Repair Scenarios

### Scenario A: Feishu was installed first, then `omx setup` was run

Expected symptom:

- Feishu files still exist
- but target `.codex/hooks.json` was rewritten by OMX and now points directly to `codex-native-hook.js`

Correct action:

```bash
python3 scripts/install.py --mode omx
```

If scope is ambiguous, prefer:

```bash
python3 scripts/install.py --mode auto
```

Then verify that the target `Stop` command now points to `feishu_stop_notify_omx_wrapper.py`.

### Scenario B: OMX exists, but Feishu was later installed in plain `codex` mode

Expected symptom:

- target `Stop` hook points directly to `feishu_stop_notify.py`
- but OMX should still own lifecycle decisions

Correct action:

```bash
python3 scripts/install.py --mode omx
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

The agent must not assume `~/.codex` is still correct after OMX project-scope setup.

## Target Codex Home Resolution

If `--codex-home` is not provided, the installer uses this logic:

1. If `./.omx/setup-scope.json` says `project`, target `./.codex`
2. If `./.omx/setup-scope.json` says `user`, target `~/.codex`
3. Otherwise target `~/.codex`

Override this with `--codex-home` when necessary.

## Bundled Defaults

- Default `title_prefix` is `[Codex]`

There is no bundled webhook in the public-safe version of this repo.
The installer requires the user to provide a webhook explicitly.

## Canonical Commands

### Auto

```bash
python3 scripts/install.py --webhook-url '<FULL_URL_OR_TOKEN>'
```

Use this by default when repairing an unknown environment.

### Plain Codex

```bash
python3 scripts/install.py --mode codex --webhook-url '<FULL_URL_OR_TOKEN>'
```

### oh-my-codex / OMX

First ensure OMX is already installed and set up for the intended scope:

```bash
omx setup
```

Then install:

```bash
python3 scripts/install.py --mode omx --webhook-url '<FULL_URL_OR_TOKEN>'
```

### Override defaults

```bash
python3 scripts/install.py \
  --webhook-url 'https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx' \
  --title-prefix '[Codex]'
```

The same `--webhook-url` flag also accepts only the final hook token:

```bash
python3 scripts/install.py \
  --webhook-url 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'
```

The installer automatically expands the token into the full Feishu webhook URL.

## What `codex` Mode Does

1. Copies runtime files into `<codex-home>/hooks/`
2. Writes `<codex-home>/hooks/feishu_stop_notify_config.json`
3. Ensures `<codex-home>/config.toml` enables `codex_hooks = true`
4. Adds a standalone `Stop` hook running:

```bash
python3 /ABSOLUTE/PATH/TO/<codex-home>/hooks/feishu_stop_notify.py
```

## What `omx` Mode Does

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

1. Confirm installer stdout shows:
   - target `Codex home`
   - detected `Install mode`
2. Inspect the config:

```bash
cat <codex-home>/hooks/feishu_stop_notify_config.json
```

3. Inspect the hook registration:

```bash
cat <codex-home>/hooks.json
```

4. Trigger a completed turn and inspect:

```bash
tail -n 50 <codex-home>/hooks/logs/feishu_stop_notify.log
```

5. Confirm a Feishu bot message appears.

## Repair Validation Checklist

After any repair or reinstall, the agent should verify all of the following:

1. The chosen `codex-home` matches the active environment.
2. `hooks.json` points to the correct command for that environment:
   - plain Codex: `feishu_stop_notify.py`
   - OMX: `feishu_stop_notify_omx_wrapper.py`
3. In OMX mode, `feishu_stop_notify_config.json` contains `omx_original_stop_command`.
4. Triggering a final stop sends Feishu.
5. In OMX mode, a continuation-style `Stop` still returns OMX continuation JSON and does not send Feishu.

If any of these checks fail, treat the environment as still broken and continue repairing.

## Idempotency

- Re-running `scripts/install.py` is supported.
- In `omx` mode, re-running after `omx setup` is expected because `omx setup` rewrites `.codex/hooks.json`.

Because of this, if the user says installation already happened but behavior is wrong, the agent should usually inspect and then re-run the installer rather than assuming the install is intact.

## Rollback

Run:

```bash
python3 scripts/uninstall.py
```

Rollback behavior:

- `codex` mode: removes the standalone Feishu `Stop` hook
- `omx` mode: restores the original OMX `Stop` command and removes the Feishu runtime files
