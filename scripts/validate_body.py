#!/usr/bin/env python3
"""Validate a saveAs body before it is POSTed to calculator.aws.

The save endpoint accepts almost anything: a malformed body stores fine and only
breaks later, in the recipient's browser, where nobody can fix it. This module
moves that failure forward to the one moment it is still cheap.

Two layers of checking:
  1. Structural — `body_schema.json` (JSON Schema draft 2020-12).
  2. Semantic — the key-naming conventions the SPA relies on but cannot express
     in a schema: every `services` key is `<serviceCode>-<uuid>`, and every
     `groups` key is `<name>-<uuid>`.

Usage: python validate_body.py <path/to/body.json>
Exit 0 when the body is clean, 1 when it is not (errors go to stderr).
"""
import argparse
import json
import re
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

SCHEMA_PATH = Path(__file__).resolve().parent / "body_schema.json"

# The SPA suffixes every services/groups key with a v4 UUID.
_UUID_SUFFIX = re.compile(
    r"-[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
_PLAIN_SEGMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# jsonschema echoes the failing instance; a line item is far too big to print.
MAX_MESSAGE = 200


def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text())


def _format_path(parts) -> str:
    out = "$"
    for part in parts:
        if isinstance(part, int):
            out += f"[{part}]"
        elif _PLAIN_SEGMENT.match(part):
            out += f".{part}"
        else:
            out += f"[{part!r}]"
    return out


def _key_prefix(key: str) -> str:
    """The name segment of a `<prefix>-<uuid>` key, minus the UUID."""
    stripped = _UUID_SUFFIX.sub("", key)
    if stripped != key:
        return stripped
    return key.rsplit("-", 1)[0] if "-" in key else key


def _message(err) -> str:
    """Readable one-liner for a schema error: our own wording for the oneOf we
    author, and a middle-elided cap for everything jsonschema generates."""
    if err.validator == "oneOf" and err.schema.get("$comment") == "cc-or-subservices":
        return (
            "a line item must carry exactly one of 'calculationComponents' "
            "(flat service) or 'subServices' (group service)"
        )
    message = err.message
    if len(message) > MAX_MESSAGE:
        # The diagnosis lives at the tail ("is not of type 'array'"), the echoed
        # instance in the middle — so elide the middle, not the end.
        message = f"{message[:MAX_MESSAGE - 60]} ... {message[-60:]}"
    return message


def _schema_errors(body: dict) -> list[str]:
    validator = Draft202012Validator(load_schema())
    errors = []
    for err in validator.iter_errors(body):
        errors.append((list(err.absolute_path), f"{_format_path(err.absolute_path)}: {_message(err)}"))
    # Stable ordering so the output is diffable and tests are deterministic.
    errors.sort(key=lambda pair: [str(p) for p in pair[0]])
    return [message for _, message in errors]


def _semantic_errors(body: dict) -> list[str]:
    """Key-naming rules the SPA depends on to route a line item back to its module."""
    errors: list[str] = []

    def walk(container, path: list):
        services = container.get("services")
        if isinstance(services, dict):
            for key, item in services.items():
                if not isinstance(item, dict):
                    continue
                code = item.get("serviceCode")
                if isinstance(code, str) and code and not key.startswith(f"{code}-"):
                    errors.append(
                        f"{_format_path(path + ['services', key])}: key must start with "
                        f"its serviceCode ('{code}-'), got '{key}'"
                    )
        groups = container.get("groups")
        if isinstance(groups, dict):
            for key, group in groups.items():
                if not isinstance(group, dict):
                    continue
                name = group.get("name")
                if isinstance(name, str) and _key_prefix(key) != name:
                    errors.append(
                        f"{_format_path(path + ['groups', key])}: key's name segment "
                        f"'{_key_prefix(key)}' does not match the group name '{name}'"
                    )
                walk(group, path + ["groups", key])

    walk(body, [])
    return errors


def validate(body) -> list[str]:
    """Return human-readable errors (path + message). Empty list means valid."""
    if not isinstance(body, dict):
        return [f"$: body must be a JSON object, got {type(body).__name__}"]
    return _schema_errors(body) + _semantic_errors(body)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="validate_body.py",
        description="Validate a calculator.aws saveAs body. Exit 1 if it is malformed.",
    )
    parser.add_argument("path", help="path to the saveAs body JSON")
    args = parser.parse_args(argv[1:])

    body = json.loads(Path(args.path).read_text())
    errors = validate(body)
    if errors:
        print(f"{len(errors)} validation error(s) in {args.path}:", file=sys.stderr)
        for err in errors:
            print(f"  {err}", file=sys.stderr)
        return 1
    print(f"{args.path}: valid")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
