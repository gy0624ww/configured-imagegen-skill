# Configured Image Generation for Codex

Use GPT Image models from Codex when the native `image_gen` tool is not available in a desktop task. The skill invokes the bundled GPT Image CLI through an isolated Python environment and supplies credentials from either standard environment variables or a Codex OpenAI-compatible provider configuration.

## Why this exists

The native `image_gen` tool is normally the preferred image-generation path in Codex and does not require an API key from the shell. Some desktop tasks created after the ChatGPT and Codex product surfaces were unified do not receive that tool, even when the `image_generation` feature is enabled. The remaining bundled CLI fallback is useful, but it only reads `OPENAI_API_KEY`; it does not automatically read Codex's `experimental_bearer_token` from `~/.codex/config.toml`.

This skill bridges that gap. It keeps native generation as the first choice, and when native generation is unavailable it:

1. runs the bundled GPT Image CLI with a current, isolated OpenAI Python SDK;
2. uses `OPENAI_API_KEY` and `OPENAI_BASE_URL` when they are already set; or
3. falls back to `model_providers.OpenAI.experimental_bearer_token` and `base_url` in the local Codex configuration.

The skill never stores a key in the repository. Each user supplies their own OpenAI API key or compatible third-party provider token.

## Requirements

- Codex with the bundled image-generation skill installed.
- Python 3.9 or later.
- `uv` is recommended. The setup script falls back to `python -m venv` and `pip` when `uv` is unavailable.
- An OpenAI API key or a third-party OpenAI-compatible provider that supports the Images API and the selected GPT Image model.

## Install

Clone the repository into the global Codex skills directory:

```zsh
git clone https://github.com/gy0624ww/configured-imagegen.git \
  ~/.codex/skills/configured-imagegen
~/.codex/skills/configured-imagegen/scripts/setup_imagegen_env.sh
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
[model_providers.OpenAI]
base_url = "https://your-compatible-provider.example/v1"
experimental_bearer_token = "your-provider-token"
```

The wrapper reads these fields only at execution time. It does not copy them into the skill directory or terminal output. Environment variables take precedence over this configuration.

## Generate an Image

Ask Codex to use `$configured-imagegen`, or invoke the wrapper directly:

```zsh
~/.codex/skills/configured-imagegen/scripts/run_imagegen.sh generate \
  --prompt "A photorealistic product photograph of a ceramic mug on a stone table" \
  --size 1024x1024 \
  --out output/imagegen/mug.png
```

For an edit, use the same wrapper with the bundled CLI's `edit` command and its image arguments:

```zsh
~/.codex/skills/configured-imagegen/scripts/run_imagegen.sh edit \
  --image input.png \
  --prompt "Replace only the background with a warm sunset" \
  --out output/imagegen/sunset-edit.png
```

Use a new output filename rather than overwriting an existing asset unless replacement is intentional.

## Model Selection

The wrapper explicitly selects `gpt-image-2`, rather than relying on a CLI default. Use another model only after verifying that the provider advertises and supports it:

```zsh
CODEX_IMAGEGEN_MODEL="gpt-image-2" \
  ~/.codex/skills/configured-imagegen/scripts/run_imagegen.sh generate ...
```

An explicit CLI `--model` argument overrides the wrapper default. `gpt-image-2` does not support native transparent backgrounds; use the normal Codex chroma-key workflow or deliberately select a compatible model when native transparency is required.

## Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| `image_gen` is unavailable | Use this skill's wrapper. It is intended for this fallback path. |
| Python environment is missing | Run `scripts/setup_imagegen_env.sh`. |
| `OPENAI_API_KEY` is not set | Export the variable or add the provider token to the local Codex configuration shown above. |
| Authentication or model error | Verify the provider URL, token, billing, and support for `gpt-image-2`. |
| Unsupported `output_format` argument | Re-run the setup script. It installs an isolated current OpenAI SDK. |
| Generated file is missing | Check the command error, output directory permissions, and provider response before retrying. |

## Security

- Never commit `.venv`, `config.toml`, `.env`, API keys, or provider tokens.
- Treat third-party compatible providers as separate services with their own privacy, billing, and retention policies.
- Review a provider's Images API support before sending prompts or source images.

## License

Distributed under the [MIT License](LICENSE).
