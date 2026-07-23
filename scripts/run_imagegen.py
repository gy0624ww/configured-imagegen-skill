#!/usr/bin/env python3
"""Launch Codex's bundled image CLI with the active provider configuration."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, NoReturn

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.9 and 3.10
    import tomli as tomllib  # type: ignore[no-redef]


def fail(message: str) -> NoReturn:
    print(f"Error: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("rb") as config_file:
            return tomllib.load(config_file)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        fail(f"cannot read Codex configuration at {path}: {exc}")


def load_auth_api_key(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        with path.open(encoding="utf-8") as auth_file:
            auth = json.load(auth_file)
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"cannot read Codex authentication at {path}: {exc}")

    if not isinstance(auth, dict):
        fail(f"Codex authentication at {path} must be a JSON object")
    api_key = auth.get("OPENAI_API_KEY", "")
    if not isinstance(api_key, str):
        fail(f"OPENAI_API_KEY in {path} must be a string")
    return api_key


def select_provider(config: dict[str, Any]) -> tuple[str | None, dict[str, Any]]:
    providers = config.get("model_providers", {})
    if not isinstance(providers, dict):
        fail("model_providers in config.toml must be a TOML table")

    requested = os.environ.get("CODEX_IMAGEGEN_PROVIDER") or config.get("model_provider")
    if requested is not None and not isinstance(requested, str):
        fail("model_provider in config.toml must be a string")

    if not requested:
        if len(providers) == 1:
            requested = next(iter(providers))
        elif "OpenAI" in providers:
            requested = "OpenAI"
        else:
            return None, {}

    provider = providers.get(requested)
    if provider is None:
        case_matches = [name for name in providers if name.lower() == requested.lower()]
        if len(case_matches) == 1:
            requested = case_matches[0]
            provider = providers[requested]
    if not isinstance(provider, dict):
        available = ", ".join(providers) or "none"
        fail(f"model provider {requested!r} is not configured (available: {available})")
    return requested, provider


def configured_credentials(provider: dict[str, Any], auth_path: Path) -> tuple[str, str]:
    api_key = os.environ.get("OPENAI_API_KEY", "")
    base_url = os.environ.get("OPENAI_BASE_URL", "")

    if not api_key:
        token = provider.get("experimental_bearer_token", "")
        if isinstance(token, str):
            api_key = token
    if not api_key:
        api_key = load_auth_api_key(auth_path)
    if not api_key:
        env_key = provider.get("env_key", "")
        if isinstance(env_key, str) and env_key:
            api_key = os.environ.get(env_key, "")
    if not base_url:
        configured_url = provider.get("base_url", "")
        if isinstance(configured_url, str):
            base_url = configured_url
    return api_key, base_url


def has_model_argument(arguments: list[str]) -> bool:
    return any(arg == "--model" or arg.startswith("--model=") for arg in arguments)


def main() -> None:
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()
    config_path = Path(
        os.environ.get("CODEX_CONFIG_PATH", codex_home / "config.toml")
    ).expanduser()
    auth_path = Path(
        os.environ.get("CODEX_AUTH_PATH", codex_home / "auth.json")
    ).expanduser()
    image_cli = Path(
        os.environ.get(
            "CODEX_IMAGEGEN_CLI",
            codex_home / "skills/.system/imagegen/scripts/image_gen.py",
        )
    ).expanduser()

    if not image_cli.is_file():
        fail(f"bundled image generator is not available: {image_cli}")

    config = load_config(config_path)
    provider_name, provider = select_provider(config)
    api_key, base_url = configured_credentials(provider, auth_path)
    if not api_key:
        provider_hint = (
            f"model_providers.{provider_name}" if provider_name else "the active model provider"
        )
        fail(
            "set OPENAI_API_KEY, set the provider's env_key variable, or configure "
            f"{provider_hint}.experimental_bearer_token or {auth_path}"
        )

    arguments = sys.argv[1:]
    if not has_model_argument(arguments):
        arguments.extend(["--model", os.environ.get("CODEX_IMAGEGEN_MODEL", "gpt-image-2")])

    child_env = os.environ.copy()
    child_env["OPENAI_API_KEY"] = api_key
    if base_url:
        child_env["OPENAI_BASE_URL"] = base_url
    os.execve(sys.executable, [sys.executable, str(image_cli), *arguments], child_env)


if __name__ == "__main__":
    main()
