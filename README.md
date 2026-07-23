# Configured Image Generation Skill for Codex

[English](README.md) | [简体中文](README.zh-CN.md)

Use GPT Image models from Codex when the native `image_gen` tool is not available in a desktop task. The skill invokes the bundled GPT Image CLI through an isolated Python environment and supplies credentials from either standard environment variables or a Codex OpenAI-compatible provider configuration.

## Why this exists

The native `image_gen` tool is normally the preferred image-generation path in Codex and does not require an API key from the shell. Some desktop tasks created after the ChatGPT and Codex product surfaces were unified do not receive that tool, even when the `image_generation` feature is enabled. The remaining bundled CLI fallback is useful, but it only reads `OPENAI_API_KEY`; it does not automatically read Codex's `experimental_bearer_token` from `~/.codex/config.toml`.

This skill bridges that gap. It keeps native generation as the first choice, and when native generation is unavailable it:

1. runs the bundled GPT Image CLI with a current, isolated OpenAI Python SDK;
2. uses `OPENAI_API_KEY` and `OPENAI_BASE_URL` when they are already set; or
3. selects the provider named by top-level `model_provider` and reads its `experimental_bearer_token` (or `env_key`) and `base_url` from the local Codex configuration; or
4. falls back to the top-level `OPENAI_API_KEY` in `~/.codex/auth.json` when the selected provider has no bearer token.

The skill never stores a key in the repository. Each user supplies their own OpenAI API key or compatible third-party provider token.

## Requirements

- Codex with the bundled image-generation skill installed.
- Python 3.9 or later.
- `uv` is recommended. The setup script falls back to `python -m venv` and `pip` when `uv` is unavailable.
- An OpenAI API key or a third-party OpenAI-compatible provider that supports the Images API and the selected GPT Image model.

## Install

Clone the repository into the global Codex skills directory:

```zsh
codex_home="${CODEX_HOME:-$HOME/.codex}"
mkdir -p "$codex_home/skills"
git clone https://github.com/gy0624ww/configured-imagegen-skill.git \
  "$codex_home/skills/configured-imagegen"
sh "$codex_home/skills/configured-imagegen/scripts/setup_imagegen_env.sh"
```

Open a new Codex task after installation so Codex discovers the skill. The virtual environment is created locally and is intentionally ignored by Git.

## Configure Credentials

### Option A: Standard environment variables

Use this option for the official OpenAI API or any compatible provider. For the official API, omit `OPENAI_BASE_URL`.

```zsh
export OPENAI_API_KEY="your-api-key"
export OPENAI_BASE_URL="https://your-compatible-provider.example/v1"
```

Do not put an API key in the repository, commit history, or issue tracker.

### Option B: Codex third-party provider configuration

For users already routing Codex through an OpenAI-compatible provider, configure their own local `~/.codex/config.toml`:

```toml
model_provider = "my-provider"

[model_providers.my-provider]
base_url = "https://your-compatible-provider.example/v1"
experimental_bearer_token = "your-provider-token"
```

The provider table name is not fixed. By default, the wrapper follows top-level `model_provider`; `CODEX_IMAGEGEN_PROVIDER` can override it for image generation. If neither is set, a single configured provider is selected automatically. Existing `[model_providers.OpenAI]` configurations remain supported.

Instead of storing a token in TOML, a provider may name an environment variable:

```toml
model_provider = "my-provider"

[model_providers.my-provider]
base_url = "https://your-compatible-provider.example/v1"
env_key = "MY_PROVIDER_API_KEY"
```

The wrapper reads these fields only at execution time. It does not copy them into the skill directory or terminal output. `OPENAI_API_KEY` and `OPENAI_BASE_URL` take precedence over provider configuration.

### Option C: Codex auth file fallback

When the selected provider does not contain `experimental_bearer_token`, the wrapper reads the top-level `OPENAI_API_KEY` from `${CODEX_AUTH_PATH:-${CODEX_HOME:-$HOME/.codex}/auth.json}`. It does not read or repurpose ChatGPT access tokens. Provider `env_key` is used only when this fallback also has no key.

### Configuration Scope

For this skill's fallback wrapper, the relevant provider fields are `base_url` plus either `experimental_bearer_token` or `env_key`. From `auth.json`, only the top-level `OPENAI_API_KEY` field is used.

The wrapper uses top-level `model_provider` only to select the matching table under `model_providers`. Fields such as top-level `model`, or provider-level `name` and `wire_api`, continue to control Codex itself and are not used for image generation.

## Generate an Image

Ask Codex to use `$configured-imagegen`, or invoke the wrapper directly:

```zsh
sh ~/.codex/skills/configured-imagegen/scripts/run_imagegen.sh generate \
  --prompt "A photorealistic product photograph of a ceramic mug on a stone table" \
  --size 1024x1024 \
  --out output/imagegen/mug.png
```

For an edit, use the same wrapper with the bundled CLI's `edit` command and its image arguments:

```zsh
sh ~/.codex/skills/configured-imagegen/scripts/run_imagegen.sh edit \
  --image input.png \
  --prompt "Replace only the background with a warm sunset" \
  --out output/imagegen/sunset-edit.png
```

Use a new output filename rather than overwriting an existing asset unless replacement is intentional.

## Model Selection

The wrapper explicitly selects `gpt-image-2`, rather than relying on a CLI default. Use another model only after verifying that the provider advertises and supports it:

```zsh
CODEX_IMAGEGEN_MODEL="gpt-image-2" \
  sh ~/.codex/skills/configured-imagegen/scripts/run_imagegen.sh generate ...
```

An explicit CLI `--model` argument overrides the wrapper default. `gpt-image-2` does not support native transparent backgrounds; use the normal Codex chroma-key workflow or deliberately select a compatible model when native transparency is required.

## Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| `image_gen` is unavailable | Use this skill's wrapper. It is intended for this fallback path. |
| Python environment is missing | Run `sh scripts/setup_imagegen_env.sh` from the skill directory. The path is discovered dynamically. |
| `OPENAI_API_KEY` is not set | Export it, configure the selected provider's token, add it to Codex `auth.json`, or set the environment variable named by `env_key`. |
| Wrong provider is selected | Check top-level `model_provider`, or set `CODEX_IMAGEGEN_PROVIDER` to the desired provider table name. |
| Authentication or model error | Verify the provider URL, token, billing, and support for `gpt-image-2`. |
| Unsupported `output_format` argument | Re-run the setup script. It installs an isolated current OpenAI SDK. |
| Generated file is missing | Check the command error, output directory permissions, and provider response before retrying. |

## Security

- Never commit `.venv`, `config.toml`, `.env`, API keys, or provider tokens.
- Treat third-party compatible providers as separate services with their own privacy, billing, and retention policies.
- Review a provider's Images API support before sending prompts or source images.

## License

Distributed under the [MIT License](LICENSE).
