# Codex 配置化生图技能

[English](README.md) | [简体中文](README.zh-CN.md)

当 Codex 桌面任务中无法使用原生 `image_gen` 工具时，使用此技能调用 GPT Image 模型生成或编辑图片。技能通过隔离的 Python 环境调用 Codex 内置的 GPT Image CLI，并从标准环境变量或 Codex 的 OpenAI 兼容服务配置中取得凭据。

## 背景

在 Codex 中，原生 `image_gen` 通常是首选生图方式，不需要从 shell 读取 API key。但在 ChatGPT 和 Codex 产品界面合并之后，部分桌面任务不会收到该工具，即使 `image_generation` 功能开关已启用。

此时可以使用内置 CLI 作为兜底，但它只读取 `OPENAI_API_KEY`，不会自动读取 `~/.codex/config.toml` 里的 `experimental_bearer_token`。如果你使用第三方 OpenAI 兼容服务，便会出现已配置 Codex、但 CLI 仍无法生图的问题。

此技能用于桥接这一差异：优先使用原生 `image_gen`；当原生工具缺失时，技能会：

1. 使用独立且较新的 OpenAI Python SDK 运行内置 GPT Image CLI；
2. 优先读取已设置的 `OPENAI_API_KEY` 与 `OPENAI_BASE_URL`；
3. 根据顶层 `model_provider` 选择 provider，并读取对应配置中的 `experimental_bearer_token`（或 `env_key`）和 `base_url`；
4. 当所选 provider 没有 bearer token 时，回退读取 `~/.codex/auth.json` 顶层的 `OPENAI_API_KEY`。

仓库不包含任何 key。每位使用者必须配置自己的 OpenAI API key 或第三方兼容服务令牌。

## 前置条件

- 已安装带有内置图片生成技能的 Codex。
- Python 3.9 或更高版本。
- 推荐安装 `uv`。若没有，安装脚本会使用 `python -m venv` 与 `pip`。
- 可用的 OpenAI API key，或支持 Images API 与所选 GPT Image 模型的第三方 OpenAI 兼容服务。

## 安装

将仓库克隆到全局 Codex 技能目录：

```zsh
codex_home="${CODEX_HOME:-$HOME/.codex}"
mkdir -p "$codex_home/skills"
git clone https://github.com/gy0624ww/configured-imagegen-skill.git \
  "$codex_home/skills/configured-imagegen"
sh "$codex_home/skills/configured-imagegen/scripts/setup_imagegen_env.sh"
```

安装后请新建一个 Codex 任务，让 Codex 自动发现该技能。虚拟环境会在本机创建，且被 Git 忽略。

## 配置凭据

### 方式一：标准环境变量

适用于官方 OpenAI API 或任意兼容服务。若使用官方 API，则不必设置 `OPENAI_BASE_URL`。

```zsh
export OPENAI_API_KEY="your-api-key"
export OPENAI_BASE_URL="https://your-compatible-provider.example/v1"
```

不要将 API key 写入仓库、提交记录或公开的 issue。

### 方式二：Codex 第三方服务配置

如果你已经通过 OpenAI 兼容服务使用 Codex，可以在自己的 `~/.codex/config.toml` 中配置：

```toml
model_provider = "my-provider"

[model_providers.my-provider]
base_url = "https://your-compatible-provider.example/v1"
experimental_bearer_token = "your-provider-token"
```

provider 表名不是固定值。包装脚本默认跟随顶层 `model_provider`；也可通过 `CODEX_IMAGEGEN_PROVIDER` 单独覆盖生图所用 provider。两者都未设置时，若只配置了一个 provider，会自动选择它。已有的 `[model_providers.OpenAI]` 配置仍然兼容。

也可以不把 token 写入 TOML，而是让 provider 指定环境变量名：

```toml
model_provider = "my-provider"

[model_providers.my-provider]
base_url = "https://your-compatible-provider.example/v1"
env_key = "MY_PROVIDER_API_KEY"
```

包装脚本只在执行时读取这些字段，不会将它们复制到技能目录或打印到终端。`OPENAI_API_KEY` 和 `OPENAI_BASE_URL` 的优先级高于 provider 配置。

### 方式三：Codex auth 文件回退

当所选 provider 未包含 `experimental_bearer_token` 时，包装器会读取 `${CODEX_AUTH_PATH:-${CODEX_HOME:-$HOME/.codex}/auth.json}` 顶层的 `OPENAI_API_KEY`。它不会读取或挪用 ChatGPT access token。只有这个回退也没有 key 时，才会使用 provider 的 `env_key`。

### 配置范围

对本技能的 CLI 兜底包装器而言，相关 provider 字段是 `base_url`，以及 `experimental_bearer_token` 或 `env_key` 二者之一。对于 `auth.json`，只会使用顶层 `OPENAI_API_KEY` 字段。

包装脚本只使用顶层 `model_provider` 来选择 `model_providers` 下的同名配置表。顶层 `model` 以及 provider 中的 `name`、`wire_api` 等字段仍用于控制 Codex 本身，不参与生图。

## 生成图片

在 Codex 中要求使用 `$configured-imagegen`，或直接调用包装脚本：

```zsh
sh ~/.codex/skills/configured-imagegen/scripts/run_imagegen.sh generate \
  --prompt "一张陶瓷马克杯放在石质桌面上的写实产品照片" \
  --size 1024x1024 \
  --out output/imagegen/mug.png
```

编辑图片时，使用同一包装脚本与内置 CLI 的 `edit` 命令：

```zsh
sh ~/.codex/skills/configured-imagegen/scripts/run_imagegen.sh edit \
  --image input.png \
  --prompt "仅将背景替换为温暖的日落场景" \
  --out output/imagegen/sunset-edit.png
```

除非确实需要替换已有资源，否则请使用新的输出文件名。

## 模型选择

包装脚本会显式选择 `gpt-image-2`，而不是依赖 CLI 默认值。只有在确认服务端同时提供并支持更新模型后，才应更改模型：

```zsh
CODEX_IMAGEGEN_MODEL="gpt-image-2" \
  sh ~/.codex/skills/configured-imagegen/scripts/run_imagegen.sh generate ...
```

显式传入的 CLI `--model` 参数会覆盖包装脚本默认值。`gpt-image-2` 不支持原生透明背景；需要透明背景时，请使用 Codex 的色键抠图流程，或有意识地选择支持该能力的兼容模型。

## 常见问题

| 现象 | 原因与解决方式 |
| --- | --- |
| `image_gen` 不可用 | 使用本技能的包装脚本，它就是为该兜底路径设计的。 |
| 缺少 Python 环境 | 在技能目录中运行 `sh scripts/setup_imagegen_env.sh`，脚本会动态识别实际安装路径。 |
| `OPENAI_API_KEY` 未设置 | 设置该变量、配置所选 provider 的 token、写入 Codex `auth.json`，或设置其 `env_key` 指向的环境变量。 |
| 选错 provider | 检查顶层 `model_provider`，或用 `CODEX_IMAGEGEN_PROVIDER` 指定目标 provider 表名。 |
| 认证或模型报错 | 检查服务地址、令牌、余额与服务端对 `gpt-image-2` 的支持。 |
| 不支持 `output_format` 参数 | 重新运行安装脚本，以安装隔离的新版 OpenAI SDK。 |
| 没有生成输出文件 | 检查命令错误、输出目录权限与服务端响应后再重试。 |

## 安全注意事项

- 不要提交 `.venv`、`config.toml`、`.env`、API key 或服务令牌。
- 第三方兼容服务有自己的隐私、计费与数据保留政策，使用前请自行确认。
- 向第三方服务发送提示词或源图片前，请先确认其 Images API 支持情况。

## 许可证

本项目采用 [MIT 许可证](LICENSE)。
