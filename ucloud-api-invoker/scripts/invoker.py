#!/usr/bin/env python3
"""UCloud OpenAPI invoker. Reads JSON from stdin, writes JSON to stdout.

Input  schema: {"action": str, "params": {str: str}, "profile": str?}
Output schema: {"ok": bool, "action": str, "http_status": int, "response": dict}
            or {"ok": false, "error_class": str, "message": str, ...}
"""

import hashlib
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_BASE_URL = "https://api.ucloud.cn"
CONFIG_PATH = os.path.expanduser("~/.ucloud/config.json")
CREDENTIAL_PATH = os.path.expanduser("~/.ucloud/credential.json")


class ConfigError(Exception):
    pass


class NetworkError(Exception):
    pass


class SigningError(Exception):
    pass


class APIError(Exception):
    def __init__(self, ret_code: int, message: str, response: dict):
        super().__init__(message)
        self.ret_code = ret_code
        self.message = message
        self.response = response


def sign(params, private_key):
    """Compute UCloud OpenAPI signature.

    Algorithm (from /tmp/ucloud-doc-api/summary/signature.md):
      1. Sort params by key ascending.
      2. Concatenate as 'key1val1key2val2...' (no separators, no URL escaping).
      3. Append private_key to the concatenated string.
      4. SHA1 hex digest of the result.

    All param values must be strings (caller's responsibility).
    """
    if not isinstance(private_key, str) or not private_key:
        raise SigningError("private_key must be a non-empty string")
    parts = []
    for key in sorted(params.keys()):
        value = params[key]
        if not isinstance(value, str):
            raise SigningError(f"param '{key}' value must be string, got {type(value).__name__}")
        parts.append(key)
        parts.append(value)
    parts.append(private_key)
    payload = "".join(parts)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def load_credential(profile):
    """Load credential from ~/.ucloud/{config,credential}.json.

    If profile is None, picks the entry with Active=True from config.json.
    Otherwise picks the entry with matching Profile name.
    Merges fields from config.json and credential.json into a single dict.

    Returns: dict with at least PublicKey, PrivateKey, BaseURL, optionally ProjectID, Region, Zone.
    Raises: ConfigError when files missing or profile not found.
    """
    if not os.path.exists(CONFIG_PATH):
        raise ConfigError(f"config file not found: {CONFIG_PATH}; run scripts/setup_credentials.py to create it")
    if not os.path.exists(CREDENTIAL_PATH):
        raise ConfigError(f"credential file not found: {CREDENTIAL_PATH}; run scripts/setup_credentials.py to create it")

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            configs = json.load(f)
        with open(CREDENTIAL_PATH, "r", encoding="utf-8") as f:
            credentials = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        raise ConfigError(f"failed to read ucloud config: {e}")

    if not isinstance(configs, list) or not isinstance(credentials, list):
        raise ConfigError("config.json and credential.json must be JSON arrays")

    if profile is None:
        matched_config = next((c for c in configs if c.get("Active")), None)
        if matched_config is None:
            raise ConfigError("no active profile in config.json; specify `profile` or set Active=true")
        active_count = sum(1 for c in configs if c.get("Active"))
        if active_count > 1:
            raise ConfigError(f"multiple active profiles found in config.json ({active_count}); only one allowed")
        profile = matched_config.get("Profile")
    else:
        matched_config = next((c for c in configs if c.get("Profile") == profile), None)
        if matched_config is None:
            raise ConfigError(f"profile '{profile}' not found in config.json")

    matched_cred = next((c for c in credentials if c.get("Profile") == profile), None)
    if matched_cred is None:
        raise ConfigError(f"profile '{profile}' not found in credential.json")

    merged = {**matched_config, **matched_cred}
    if not merged.get("PublicKey") or not merged.get("PrivateKey"):
        raise ConfigError(f"profile '{profile}' missing PublicKey or PrivateKey")
    merged.setdefault("BaseURL", DEFAULT_BASE_URL)
    return merged


def invoke(action, params, cred):
    """Build signed request, POST to UCloud OpenAPI, return parsed result dict.

    Args:
        action: PascalCase Action name (e.g. "CreateUHostInstance")
        params: dict[str, str] of business params (no Action/PublicKey/Signature)
        cred:   credential dict from load_credential()

    Returns: dict with shape:
      success: {"ok": True, "action": action, "http_status": 200, "response": {...}}
    Raises: NetworkError | SigningError | APIError
    """
    full_params = dict(params)
    full_params["Action"] = action
    full_params["PublicKey"] = cred["PublicKey"]
    if "ProjectId" not in full_params and cred.get("ProjectID"):
        full_params["ProjectId"] = cred["ProjectID"]

    for k, v in full_params.items():
        if not isinstance(v, str):
            raise SigningError(f"param '{k}' must be string, got {type(v).__name__}: {v!r}")

    full_params["Signature"] = sign(full_params, cred["PrivateKey"])

    body = urllib.parse.urlencode(full_params).encode("utf-8")
    url = cred.get("BaseURL", DEFAULT_BASE_URL)
    print(f"POST {url} action={action}", file=sys.stderr)

    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    timeout = cred.get("Timeout", 30)
    if not isinstance(timeout, (int, float)):
        timeout = 30

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            http_status = resp.status
            raw = resp.read().decode("utf-8")
    except urllib.error.URLError as e:
        raise NetworkError(f"network error calling {url}: {e}")

    try:
        response = json.loads(raw)
    except json.JSONDecodeError:
        raise NetworkError(f"non-JSON response (HTTP {http_status}): {raw[:200]}")

    ret_code = response.get("RetCode")
    if ret_code is None:
        raise NetworkError("malformed API response: missing RetCode field")
    if not isinstance(ret_code, int):
        raise NetworkError(f"malformed API response: RetCode must be int, got {type(ret_code).__name__}")
    if ret_code != 0:
        raise APIError(
            ret_code=ret_code,
            message=response.get("Message", "unknown UCloud API error"),
            response=response,
        )

    return {
        "ok": True,
        "action": action,
        "http_status": http_status,
        "response": response,
    }


def main():
    """Read JSON from stdin, invoke API, write JSON result to stdout.

    Exit codes:
      0 - success (ok=true)
      1 - any failure (ok=false)
    """
    raw_input = sys.stdin.read()
    try:
        payload = json.loads(raw_input)
    except json.JSONDecodeError as e:
        _emit_error("config_error", f"stdin is not valid JSON: {e}")
        sys.exit(1)

    if not isinstance(payload, dict):
        _emit_error("config_error", "stdin JSON must be an object")
        sys.exit(1)

    action = payload.get("action")
    params = payload.get("params")
    profile = payload.get("profile")

    if not isinstance(action, str) or not action:
        _emit_error("config_error", "'action' field required and must be non-empty string")
        sys.exit(1)
    if not isinstance(params, dict):
        _emit_error("config_error", "'params' field required and must be object")
        sys.exit(1)

    try:
        cred = load_credential(profile)
        result = invoke(action, params, cred)
        json.dump(result, sys.stdout, ensure_ascii=False)
        sys.stdout.write("\n")
        sys.exit(0)
    except ConfigError as e:
        _emit_error("config_error", str(e))
        sys.exit(1)
    except SigningError as e:
        _emit_error("signing_error", str(e))
        sys.exit(1)
    except NetworkError as e:
        _emit_error("network_error", str(e))
        sys.exit(1)
    except APIError as e:
        _emit_error("api_error", e.message, ret_code=e.ret_code, response=e.response)
        sys.exit(1)


def _emit_error(error_class, message, ret_code=None, response=None):
    """Write a {ok:false,...} object to stdout."""
    obj = {"ok": False, "error_class": error_class, "message": message}
    if ret_code is not None:
        obj["ret_code"] = ret_code
    if response is not None:
        obj["response"] = response
    json.dump(obj, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
