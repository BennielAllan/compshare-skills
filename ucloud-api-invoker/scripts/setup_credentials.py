#!/usr/bin/env python3
"""Write a UCloud / CompShare credential into ~/.ucloud/{config,credential}.json.

Output schema (stdout, one JSON line):
  ok:   {"ok": true, "profile": str, "platform": str, "updated": bool,
         "config_path": str, "credential_path": str}
  err:  {"ok": false, "error": str}
Exit code: 0 on success, 1 on failure.

Two modes:
  1) CLI flags (for AI / scripted use). Required: --profile, --platform,
     --public-key, --private-key. Optional: --project-id, --active.
  2) Interactive (for humans). Triggered when no CLI flags are given.
"""

import argparse
import json
import os
import sys

CONFIG_PATH = os.path.expanduser("~/.ucloud/config.json")
CREDENTIAL_PATH = os.path.expanduser("~/.ucloud/credential.json")

BASE_URL_UCLOUD = "https://api.ucloud.cn"
BASE_URL_COMPSHARE = "https://api.compshare.cn/"


def emit_ok(**kwargs):
    json.dump({"ok": True, **kwargs}, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    sys.exit(0)


def emit_err(message):
    json.dump({"ok": False, "error": message}, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    sys.exit(1)


def load_array(path):
    """Read a JSON array from path. Returns [] if file missing.

    Raises ValueError on parse error or non-array content.
    """
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"{path} is not valid JSON: {e}")
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON array")
    return data


def write_array(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def upsert(items, profile, fields):
    """Replace matching entry's fields, or append a new entry. Returns updated=bool."""
    for entry in items:
        if entry.get("Profile") == profile:
            entry.clear()
            entry.update(fields)
            return True
    items.append(fields)
    return False


def setup(profile, platform, public_key, private_key, project_id, active):
    if not profile:
        emit_err("--profile is required and must be non-empty")
    if platform not in ("ucloud", "compshare"):
        emit_err("--platform must be 'ucloud' or 'compshare'")
    if not public_key or not private_key:
        emit_err("--public-key and --private-key are required and must be non-empty")
    if platform == "compshare" and project_id:
        emit_err("CompShare does not use ProjectID; drop --project-id")

    base_url = BASE_URL_COMPSHARE if platform == "compshare" else BASE_URL_UCLOUD

    try:
        configs = load_array(CONFIG_PATH)
        credentials = load_array(CREDENTIAL_PATH)
    except ValueError as e:
        emit_err(str(e))

    config_entry = {
        "Profile": profile,
        "Active": bool(active),
        "BaseURL": base_url,
    }
    if project_id:
        config_entry["ProjectID"] = project_id

    if active:
        for entry in configs:
            if entry.get("Profile") != profile:
                entry["Active"] = False

    updated_cfg = upsert(configs, profile, config_entry)
    updated_cred = upsert(credentials, profile, {
        "Profile": profile,
        "PublicKey": public_key,
        "PrivateKey": private_key,
    })

    try:
        write_array(CONFIG_PATH, configs)
        write_array(CREDENTIAL_PATH, credentials)
    except OSError as e:
        emit_err(f"failed to write credential files: {e}")

    emit_ok(
        profile=profile,
        platform=platform,
        updated=(updated_cfg or updated_cred),
        config_path=CONFIG_PATH,
        credential_path=CREDENTIAL_PATH,
    )


def prompt(label, hidden=False, allow_empty=False):
    if hidden:
        import getpass
        value = getpass.getpass(f"{label}: ")
    else:
        sys.stderr.write(f"{label}: ")
        sys.stderr.flush()
        value = sys.stdin.readline().rstrip("\n")
    if not value and not allow_empty:
        emit_err(f"{label} cannot be empty")
    return value


def interactive():
    sys.stderr.write("Setup UCloud / CompShare credentials (Ctrl-C to abort).\n\n")
    profile = prompt("Profile name (e.g. my-ucloud / my-compshare)")
    platform = prompt("Platform [ucloud / compshare]").lower()
    if platform not in ("ucloud", "compshare"):
        emit_err("platform must be 'ucloud' or 'compshare'")
    public_key = prompt("PublicKey", hidden=True)
    private_key = prompt("PrivateKey", hidden=True)
    project_id = None
    if platform == "ucloud":
        project_id = prompt("ProjectID (leave empty for main account)", allow_empty=True) or None
    active_in = prompt("Set as Active profile? [y/N]", allow_empty=True).lower()
    active = active_in in ("y", "yes")
    setup(profile, platform, public_key, private_key, project_id, active)


def main():
    parser = argparse.ArgumentParser(
        description="Write a UCloud / CompShare credential into ~/.ucloud/{config,credential}.json"
    )
    parser.add_argument("--profile", help="Profile name")
    parser.add_argument("--platform", choices=["ucloud", "compshare"], help="ucloud or compshare")
    parser.add_argument("--public-key", help="API PublicKey from console")
    parser.add_argument("--private-key", help="API PrivateKey from console")
    parser.add_argument("--project-id", help="UCloud ProjectID (required for sub-account; forbidden for compshare)")
    parser.add_argument("--active", action="store_true", help="Mark this profile as Active (and unset others)")
    args = parser.parse_args()

    has_any_flag = any([args.profile, args.platform, args.public_key, args.private_key,
                        args.project_id, args.active])
    if not has_any_flag:
        interactive()
    else:
        setup(args.profile, args.platform, args.public_key, args.private_key,
              args.project_id, args.active)


if __name__ == "__main__":
    main()
