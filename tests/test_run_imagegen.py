from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
LAUNCHER_PATH = REPO_ROOT / "scripts/run_imagegen.py"
WRAPPER_PATH = REPO_ROOT / "scripts/run_imagegen.sh"

spec = importlib.util.spec_from_file_location("run_imagegen", LAUNCHER_PATH)
assert spec and spec.loader
run_imagegen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_imagegen)


class ProviderSelectionTests(unittest.TestCase):
    def test_selects_top_level_model_provider(self) -> None:
        config = {
            "model_provider": "acme",
            "model_providers": {"OpenAI": {}, "acme": {"base_url": "https://acme.test/v1"}},
        }
        with patch.dict(os.environ, {}, clear=True):
            name, provider = run_imagegen.select_provider(config)
        self.assertEqual(name, "acme")
        self.assertEqual(provider["base_url"], "https://acme.test/v1")

    def test_explicit_override_and_case_insensitive_match(self) -> None:
        config = {
            "model_provider": "first",
            "model_providers": {"first": {}, "MyProvider": {"base_url": "https://my.test/v1"}},
        }
        with patch.dict(os.environ, {"CODEX_IMAGEGEN_PROVIDER": "myprovider"}, clear=True):
            name, _ = run_imagegen.select_provider(config)
        self.assertEqual(name, "MyProvider")

    def test_selects_only_provider_without_top_level_setting(self) -> None:
        config = {"model_providers": {"anything": {"base_url": "https://only.test/v1"}}}
        with patch.dict(os.environ, {}, clear=True):
            name, _ = run_imagegen.select_provider(config)
        self.assertEqual(name, "anything")

    def test_reads_provider_env_key(self) -> None:
        provider = {"env_key": "ACME_IMAGE_KEY", "base_url": "https://acme.test/v1"}
        with tempfile.TemporaryDirectory() as temporary_directory, patch.dict(
            os.environ, {"ACME_IMAGE_KEY": "provider-secret"}, clear=True
        ):
            api_key, base_url = run_imagegen.configured_credentials(
                provider, Path(temporary_directory) / "missing-auth.json"
            )
        self.assertEqual(api_key, "provider-secret")
        self.assertEqual(base_url, "https://acme.test/v1")

    def test_reads_auth_json_after_missing_provider_token(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            auth_path = Path(temporary_directory) / "auth.json"
            auth_path.write_text('{"OPENAI_API_KEY": "auth-secret"}', encoding="utf-8")
            with patch.dict(os.environ, {}, clear=True):
                api_key, _ = run_imagegen.configured_credentials({}, auth_path)
        self.assertEqual(api_key, "auth-secret")

    def test_provider_token_takes_precedence_over_auth_json(self) -> None:
        provider = {"experimental_bearer_token": "provider-secret"}
        with tempfile.TemporaryDirectory() as temporary_directory:
            auth_path = Path(temporary_directory) / "auth.json"
            auth_path.write_text('{"OPENAI_API_KEY": "auth-secret"}', encoding="utf-8")
            with patch.dict(os.environ, {}, clear=True):
                api_key, _ = run_imagegen.configured_credentials(provider, auth_path)
        self.assertEqual(api_key, "provider-secret")

    def test_standard_environment_variables_take_precedence(self) -> None:
        provider = {"experimental_bearer_token": "config-secret", "base_url": "https://config.test/v1"}
        environment = {"OPENAI_API_KEY": "env-secret", "OPENAI_BASE_URL": "https://env.test/v1"}
        with tempfile.TemporaryDirectory() as temporary_directory, patch.dict(
            os.environ, environment, clear=True
        ):
            api_key, base_url = run_imagegen.configured_credentials(
                provider, Path(temporary_directory) / "missing-auth.json"
            )
        self.assertEqual(api_key, "env-secret")
        self.assertEqual(base_url, "https://env.test/v1")


class WrapperIntegrationTests(unittest.TestCase):
    def test_wrapper_uses_dynamic_provider_and_injects_default_model(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temp = Path(temporary_directory)
            config_path = temp / "config.toml"
            capture_path = temp / "capture.json"
            fake_cli = temp / "image_gen.py"
            config_path.write_text(
                textwrap.dedent(
                    """\
                    model_provider = "custom-name"

                    [model_providers.custom-name]
                    base_url = "https://images.example/v1"
                    env_key = "CUSTOM_IMAGE_KEY"
                    """
                ),
                encoding="utf-8",
            )
            fake_cli.write_text(
                "import json, os, sys\n"
                "json.dump({'argv': sys.argv[1:], 'key': os.environ.get('OPENAI_API_KEY'), "
                "'url': os.environ.get('OPENAI_BASE_URL')}, open(os.environ['CAPTURE_PATH'], 'w'))\n",
                encoding="utf-8",
            )
            environment = os.environ.copy()
            environment.update(
                {
                    "CAPTURE_PATH": str(capture_path),
                    "CODEX_AUTH_PATH": str(temp / "missing-auth.json"),
                    "CODEX_CONFIG_PATH": str(config_path),
                    "CODEX_IMAGEGEN_CLI": str(fake_cli),
                    "CODEX_IMAGEGEN_PYTHON": sys.executable,
                    "CUSTOM_IMAGE_KEY": "test-secret",
                }
            )
            environment.pop("OPENAI_API_KEY", None)
            environment.pop("OPENAI_BASE_URL", None)

            subprocess.run(
                ["sh", str(WRAPPER_PATH), "generate", "--prompt", "test prompt"],
                check=True,
                env=environment,
                capture_output=True,
                text=True,
            )

            captured = json.loads(capture_path.read_text(encoding="utf-8"))
            self.assertEqual(captured["key"], "test-secret")
            self.assertEqual(captured["url"], "https://images.example/v1")
            self.assertEqual(captured["argv"][-2:], ["--model", "gpt-image-2"])

    def test_wrapper_falls_back_to_auth_json(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temp = Path(temporary_directory)
            config_path = temp / "config.toml"
            auth_path = temp / "auth.json"
            capture_path = temp / "capture.json"
            fake_cli = temp / "image_gen.py"
            config_path.write_text(
                '[model_providers.OpenAI]\nbase_url = "https://images.example/v1"\n',
                encoding="utf-8",
            )
            auth_path.write_text('{"OPENAI_API_KEY": "auth-secret"}', encoding="utf-8")
            fake_cli.write_text(
                "import json, os\n"
                "json.dump({'key': os.environ.get('OPENAI_API_KEY')}, "
                "open(os.environ['CAPTURE_PATH'], 'w'))\n",
                encoding="utf-8",
            )
            environment = os.environ.copy()
            environment.update(
                {
                    "CAPTURE_PATH": str(capture_path),
                    "CODEX_CONFIG_PATH": str(config_path),
                    "CODEX_AUTH_PATH": str(auth_path),
                    "CODEX_IMAGEGEN_CLI": str(fake_cli),
                    "CODEX_IMAGEGEN_PYTHON": sys.executable,
                }
            )
            environment.pop("OPENAI_API_KEY", None)
            environment.pop("OPENAI_BASE_URL", None)

            subprocess.run(
                ["sh", str(WRAPPER_PATH), "generate", "--prompt", "test prompt"],
                check=True,
                env=environment,
                capture_output=True,
                text=True,
            )

            captured = json.loads(capture_path.read_text(encoding="utf-8"))
            self.assertEqual(captured["key"], "auth-secret")


if __name__ == "__main__":
    unittest.main()
