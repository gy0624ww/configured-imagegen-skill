---
name: configured-imagegen
description: Generate or edit raster images through the user's configured OpenAI-compatible provider. Use when a user requests image generation or editing and native image_gen is unavailable, or when the user explicitly asks to use the provider configured in ~/.codex/config.toml.
---

# Configured Image Generation

Use the native `image_gen` tool first when it is available. It has the best desktop integration and does not require credentials from configuration.

When native `image_gen` is unavailable, use the bundled wrapper. Resolve all commands relative to this `SKILL.md` file; never assume the skill is installed at a fixed path or folder name. Invoke shell scripts with `sh` so the workflow still works when an archive, copy, or package install does not preserve executable bits.

If the wrapper reports that its Python environment is missing, bootstrap it once. The setup script creates `.venv` inside the actual skill directory; do not install dependencies into the system Python environment.

```bash
sh "<skill-directory>/scripts/setup_imagegen_env.sh"
sh "<skill-directory>/scripts/run_imagegen.sh" generate \
  --prompt "<structured image prompt>" \
  --out "<workspace delivery path>.png"
```

The wrapper selects the provider named by top-level `model_provider` in `${CODEX_CONFIG_PATH:-${CODEX_HOME:-$HOME/.codex}/config.toml}`. `CODEX_IMAGEGEN_PROVIDER` overrides that selection. If neither is set, it selects the only configured provider, or uses `OpenAI` as a backward-compatible fallback when that table exists. Never assume the provider is named `OpenAI`.

Use credentials in this order: `OPENAI_API_KEY`; the selected provider's `experimental_bearer_token`; `${CODEX_AUTH_PATH:-${CODEX_HOME:-$HOME/.codex}/auth.json}` field `OPENAI_API_KEY`; then the environment variable named by the provider's `env_key`. Use `OPENAI_BASE_URL` before the selected provider's `base_url`. The wrapper exposes resolved values only to the image CLI child process. Do not print, copy, persist, or ask the user for a configured token. Do not use ChatGPT access tokens from `auth.json` as Images API keys.

The wrapper explicitly selects `gpt-image-2` unless a caller supplies `--model` or deliberately sets `CODEX_IMAGEGEN_MODEL` to a verified newer compatible GPT Image model. Pass `edit` and its normal GPT Image CLI arguments for image edits. Keep image prompts and output paths appropriate to the user request. Do not print, copy, persist, or ask the user for the configured token.

Before final delivery, inspect the resulting image and report the saved path. The wrapper returns a clear error if the compatible-provider configuration is missing.
