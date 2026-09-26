#!/usr/bin/env python3
"""Switch Gateway routing for Claude Desktop and standalone Claude Code.

Uses only macOS and Python standard libraries. Never stores credentials.
"""

import argparse
import fcntl
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from datetime import datetime


HOME = Path.home()
GATEWAY_URL = ""
GATEWAY_PROFILE_ID = str(__import__("uuid").uuid5(__import__("uuid").NAMESPACE_DNS,"ai-control-studio.desktop.gateway"))
HELPER = HOME / ".claude" / "ai-control-credential.sh"
CODE_SETTINGS = HOME / ".claude" / "settings.json"
DESKTOP_ROOT = HOME / "Library" / "Application Support" / ("Claude-3p" if (HOME / "Library/Application Support/Claude-3p").exists() else "Claude")
DESKTOP_SETTINGS = DESKTOP_ROOT / "claude_desktop_config.json"
PROFILE_META = DESKTOP_ROOT / "configLibrary" / "_meta.json"
if PROFILE_META.exists():
    try:
        candidate=json.loads(PROFILE_META.read_text()).get("appliedId")
        if candidate: GATEWAY_PROFILE_ID=str(__import__("uuid").UUID(candidate))
    except (ValueError,TypeError):pass
GATEWAY_PROFILE = DESKTOP_ROOT / "configLibrary" / f"{GATEWAY_PROFILE_ID}.json"
ZSHRC = HOME / ".zshrc"
STATE_ROOT = HOME / "Library" / "Application Support" / "AI Control Studio"
import gateway_profiles as gp
ACTIVE_GATEWAY = gp.selected() or {"id":"unconfigured","name":"No gateway configured","claudeUrl":"","codexUrl":"","auth":"helper","helper":str(HELPER)}
GATEWAY_URL = ACTIVE_GATEWAY["claudeUrl"]
HELPER = Path(gp.helper(ACTIVE_GATEWAY))
OLD_EXPORT = f'export ANTHROPIC_BASE_URL="{GATEWAY_URL}"'


def read_json(path):
    if not path.exists():return {}
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected an object in {path}")
    return data


def write_atomic(path, contents):
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o600
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(contents)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_name, mode)
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def dump_json(data):
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def inspect():
    code = read_json(CODE_SETTINGS)
    desktop = read_json(DESKTOP_SETTINGS)
    meta = read_json(PROFILE_META)
    profile = read_json(GATEWAY_PROFILE)

    env = code.get("env", {})
    if not isinstance(env, dict):
        raise ValueError("Claude Code settings.env is not an object")
    desktop_gateway = bool(GATEWAY_URL) and desktop.get("deploymentMode") != "1p" and meta.get("appliedId") == GATEWAY_PROFILE_ID and profile.get("inferenceGatewayBaseUrl")==GATEWAY_URL
    code_gateway = bool(GATEWAY_URL) and env.get("ANTHROPIC_BASE_URL") == GATEWAY_URL and code.get("apiKeyHelper") == str(HELPER)
    return {
        "desktop_gateway": desktop_gateway,
        "code_gateway": code_gateway,
        "desktop_mode": desktop.get("deploymentMode"),
        "desktop_profile": meta.get("appliedId"),
        "desktop_label": profile.get("deploymentDisplayName"),
        "gateway_name": ACTIVE_GATEWAY["name"],
        "old_shell_export": ZSHRC.exists() and OLD_EXPORT in ZSHRC.read_text(),
    }


def back_up(paths):
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    directory = STATE_ROOT / "backups" / stamp
    directory.mkdir(parents=True, mode=0o700)
    os.chmod(directory, 0o700)
    for path in paths:
        if path.exists():
            destination = directory / path.name
            shutil.copy2(path, destination)
            os.chmod(destination, 0o600)
    return directory


def apply(desktop_on, code_on):
    before = inspect()
    if (desktop_on or code_on) and ACTIVE_GATEWAY["id"]=="unconfigured":raise ValueError("Add and select a gateway in Gateway profiles first.")
    STATE_ROOT.mkdir(parents=True,exist_ok=True)
    if code_on and not HELPER.is_file():
        raise FileNotFoundError(f"Claude Code credential helper is missing: {HELPER}")

    desktop = read_json(DESKTOP_SETTINGS)
    meta = read_json(PROFILE_META)
    profile = read_json(GATEWAY_PROFILE)
    code = read_json(CODE_SETTINGS)
    env = code.setdefault("env", {})
    if not isinstance(env, dict):
        raise ValueError("Claude Code settings.env is not an object")

    if desktop_on:
        desktop["deploymentMode"] = "3p"
        meta["appliedId"] = GATEWAY_PROFILE_ID
        entries=meta.setdefault("entries",[])
        if not any(x.get("id")==GATEWAY_PROFILE_ID for x in entries):entries.append({"id":GATEWAY_PROFILE_ID,"name":ACTIVE_GATEWAY["name"]})
        original_path=STATE_ROOT/"original-desktop-inference.json"
        if ACTIVE_GATEWAY["id"] != "existing":
            if not original_path.exists():write_atomic(original_path,dump_json({k:v for k,v in profile.items() if k.startswith("inference")}))
            for k in list(profile):
                if k.startswith("inference") and k not in ("inferenceGatewayBaseUrl","inferenceProvider"):profile.pop(k)
            profile["inferenceCredentialKind"]="static"
            profile["inferenceCredentialHelper"]=str(HELPER)
            profile["inferenceCredentialHelperTtlSec"]=300
            profile["inferenceGatewayAuthScheme"]="bearer"
        elif original_path.exists():
            for k in list(profile):
                if k.startswith("inference"):profile.pop(k)
            profile.update(read_json(original_path))
        profile["deploymentDisplayName"] = ACTIVE_GATEWAY["name"]
        profile["inferenceGatewayBaseUrl"] = GATEWAY_URL
    else:
        desktop["deploymentMode"] = "1p"

    model_state=STATE_ROOT/'original-code-model.json'
    model_original=read_json(model_state) if model_state.exists() else None
    if code_on and ACTIVE_GATEWAY.get('kind')=='Ollama':
        if model_original is None:
            write_atomic(model_state,dump_json({'present':'ANTHROPIC_MODEL' in env,'value':env.get('ANTHROPIC_MODEL')}))
        env['ANTHROPIC_MODEL']=ACTIVE_GATEWAY['claudeModel']
    elif model_original is not None:
        if model_original['present']:env['ANTHROPIC_MODEL']=model_original['value']
        else:env.pop('ANTHROPIC_MODEL',None)
        model_state.unlink()
    if code_on:
        if env.get("ANTHROPIC_API_KEY") not in (None, "") or env.get("ANTHROPIC_AUTH_TOKEN") not in (None, ""):
            raise ValueError("Claude Code settings contain another gateway credential; remove that conflict first")
        env.pop("ANTHROPIC_API_KEY", None)
        env.pop("ANTHROPIC_AUTH_TOKEN", None)
        env["ANTHROPIC_BASE_URL"] = GATEWAY_URL
        env["CLAUDE_CODE_API_KEY_HELPER_TTL_MS"] = "300000"
        code["apiKeyHelper"] = str(HELPER)
    else:
        if env.get("ANTHROPIC_BASE_URL") in [p["claudeUrl"] for p in gp.load()["profiles"]]:
            env.pop("ANTHROPIC_BASE_URL")
        if env.get("CLAUDE_CODE_API_KEY_HELPER_TTL_MS") in ("300000", "3600000"):
            env.pop("CLAUDE_CODE_API_KEY_HELPER_TTL_MS")
        if code.get("apiKeyHelper") in [gp.helper(p) for p in gp.load()["profiles"]]:
            code.pop("apiKeyHelper")
        if not env:
            code.pop("env", None)

    shell_text = ZSHRC.read_text() if ZSHRC.exists() else None
    new_shell = None
    if shell_text is not None:
        new_shell = "".join(line for line in shell_text.splitlines(keepends=True) if line.strip() != OLD_EXPORT)

    changes = []
    for path, new_text in (
        (DESKTOP_SETTINGS, dump_json(desktop)),
        (PROFILE_META, dump_json(meta)),
        (GATEWAY_PROFILE, dump_json(profile)),
        (CODE_SETTINGS, dump_json(code)),
        (ZSHRC, new_shell),
    ):
        if new_text is not None and (not path.exists() or path.read_text() != new_text):
            changes.append((path, new_text))
    backup = None
    if changes:
        backup = back_up([path for path, _ in changes])
        for path, new_text in changes:
            path.parent.mkdir(parents=True,exist_ok=True)
            write_atomic(path, new_text)

    after = inspect()
    return {
        **after,
        "desktop_restart_needed": before["desktop_gateway"] != after["desktop_gateway"] or before["desktop_label"] != after["desktop_label"] or any(str(p)==str(GATEWAY_PROFILE) for p,_ in changes),
        "code_new_terminal_needed": before["code_gateway"] != after["code_gateway"] or before["old_shell_export"] or any(p==CODE_SETTINGS for p,_ in changes),
        "changed": [str(path) for path, _ in changes],
        "backup": str(backup) if backup else None,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("status", "apply"))
    parser.add_argument("--desktop", choices=("on", "off"))
    parser.add_argument("--code", choices=("on", "off"))
    args = parser.parse_args()
    try:
        STATE_ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(STATE_ROOT, 0o700)
        with (STATE_ROOT / "switch.lock").open("w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if args.command == "status":
                result = inspect()
            else:
                if args.desktop is None or args.code is None:
                    parser.error("apply requires --desktop and --code")
                result = apply(args.desktop == "on", args.code == "on")
        print(json.dumps({"ok": True, **result}))
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
