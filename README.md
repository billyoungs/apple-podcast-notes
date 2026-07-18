# apple-podcast-notes

> Apple Podcasts 笔记生成器 · 一个 AI 智能体技能  
> 把你的 Apple Podcasts 单集链接变成结构化 Markdown 笔记，自动转录 + 自动分类 + 自动套模板。

给 AI 智能体（Claude Code / Codex / OpenClaw 等海外及 WorkBuddy / DuMate / LobsterAI / QwenPaw 等国产智能体工作台）用的技能。用户只需给出一个 Apple Podcasts 链接，智能体就会自动完成 **解析链接 → 获取 shownotes → 转录音频 → 判断内容类型 → 套用模板 → 输出笔记** 的完整工作流。

---

## 安装

### 让智能体自己装（推荐）

把这个仓库交给你的 AI 智能体（Claude Code / Codex / OpenClaw / WorkBuddy / DuMate / LobsterAI / QwenPaw 等），告诉它：

> 安装 apple-podcast-notes 技能，仓库在 `https://github.com/billyoungs/apple-podcast-notes`

智能体会自动把技能文件放到正确位置，后续即可使用。

### 或者手动克隆

```bash
git clone https://github.com/billyoungs/apple-podcast-notes.git
# 然后把仓库路径告诉 AI 助手即可
```

---

## 🎯 支持平台

| 平台 | 链接格式 | 数据来源 | 音频直链 |
|------|---------|---------|---------|
| **Apple Podcasts** | `podcasts.apple.com/.../id<podcast_id>?i=<episode_id>` | iTunes Lookup API + RSS feed | ✅ 通过 RSS 获取 |

> Apple Podcasts 链接**必须包含单集 ID**（URL 中的 `?i=...` 参数），仅播客首页链接无法确定具体单集。

解析流程：
1. 从 URL 提取播客 ID 和单集 ID
2. 调用 iTunes Lookup API 获取单集元数据和 RSS feed URL
3. 从 RSS feed 中匹配单集并提取音频直链

> 本方式依赖 iTunes 公开 API 和播客的 RSS feed，因此仅在 iTunes/Apple 播客目录中上架的播客可用。如果 RSS feed 受保护，则仅能获取元数据和 shownotes，用户需自备音频文件。

---

## 🎤 转录后端（你需要选一个）

转录需要**一个 API Key**。下面提供两个平台，选一个你觉得方便的就行。

### ▌ 方案 A：阿里云百炼（推荐，中文播客首选）

- 注册地址：https://bailian.console.aliyun.com/（需实名认证）
- 开通后免费额度：**paraformer 每月 10h（自动续期）**，qwen/funasr 各 10h（90天一次性）
- 适合：**中文播客为主**，对谈/单人/中英混都能处理

**配置方法（只需三步）：**

```bash
# ① 打开百炼控制台 -> API-KEY，创建一个 key
# ② 把 key 设为环境变量（当前终端生效）
export DASHSCOPE_API_KEY="sk-你的key"
# ③ 想永久生效：把上面这行加到 ~/.bashrc 或 ~/.zshrc，再 source ~/.zshrc
```

**支持的模型与价格：**

| `--backend` | 模型 | 单价（元/秒） | 说话人分离 | 免费额度 |
|-------------|------|:-----------:|:---------:|:--------:|
| `paraformer` | paraformer-v2 | **0.00008** | ✅ 支持 | 每月 10h，自动续 |
| `funasr` | fun-asr | 0.00022 | ✅ 支持 | 开通后 90天 10h |
| `qwen` | qwen3-asr-flash-filetrans | 0.00022 | ❌ 不支持 | 开通后 90天 10h |

> 三个模型共用同一个 API Key，免费额度是**独立三个池子**。90 分钟一期：paraformer 约 ¥0.43，qwen/funasr 约 ¥1.2。

**选型建议：**
- 日常对谈/单人 → **优先 `paraformer`**（最便宜 + 每月自动续费 + 也支持说话人分离）
- 中英混、专名多、音质差的少数期 → **`funasr`**（精度更高，把 90 天一次性额度用在刀刃上）
- 单人口播、不需要区分说话人 → **`qwen`** 或 `paraformer`

**阿里云百炼的详细配置步骤**（注册 → 获取 Key → 验证），见[附录](#阿里云百炼详细配置步骤)。

---

### ▌ 方案 B：SenseAudio（备选，OpenAI 兼容）

- 官网：https://senseaudio.cn/
- 注册即用，无需实名认证，API 兼容 OpenAI 格式
- 适合：**不想用阿里云**、或需要**英文/多语言**识别时

**配置方法（只需三步）：**

```bash
# ① 打开 https://senseaudio.cn/ → 注册 → 获取 API Token
# ② 把 Token 设为环境变量
export ASR_API_KEY="你的senseaudio-token"
export ASR_API_BASE="https://api.senseaudio.cn/v1"
export ASR_MODEL="senseaudio-asr-lite-1.5-260319"
# ③ 想永久生效：把上面三行加到 ~/.bashrc 或 ~/.zshrc
```

**支持的模型与价格：**

| 模型 ID | 价格（元/小时） | 说话人分离 | 适合场景 |
|---------|:------------:|:---------:|---------|
| `senseaudio-asr-lite-1.5-260319` | **0.9** | ✅ 支持 | 轻量低成本，日常够用 |
| `senseaudio-asr-1.5-260319` | 1.8 | ✅ 支持 | 通用识别，精度更好 |
| `senseaudio-asr-pro-1.5-260319` | 3.6 | ✅ 支持 | 专业级高精度 |
| `senseaudio-asr-deepthink-1.5-260319` | 3.6 | ✅ 支持 | 深度推理增强 |

> 价格对比：SenseAudio Lite（0.9 元/小时）≈ **paraformer 的一半**，一期 90 分钟约 ¥1.35。无需预存大额费用，按量计费。

---

### ▌ 快速决策：我该选哪个？

| 你的情况 | 推荐方案 |
|---------|---------|
| 主要听中文播客 | **阿里云百炼 paraformer**（每月白送 10h，够用） |
| 中英混、需要高质量 | **阿里云百炼 funasr**（精度高，有说话人分离） |
| 不想实名认证 | **SenseAudio**（注册即用，0.9元/小时起） |
| 主要听英文播客 | **SenseAudio**（OpenAI 兼容，多语言支持好） |
| 已有 OpenAI Key | 直接用 `--backend api` 配 OpenAI Whisper |

---

## 🚀 快速上手

### 一句话让智能体干活

安装好技能并配好转录 API Key 后，把 Apple Podcasts 链接交给 AI 助手：

> 把这期 Apple Podcasts 整理成笔记：[播客链接]

它会自动：**解析链接 → 拿转录 → 判类型 → 套模板 → 输出笔记文件**。

你也可以指定模板类型：

> 把这期 Apple Podcasts 整理成笔记：[链接] （财经类）

### 手动分步流程

如果你已自备音频或只想跑其中某一步：

```bash
# 1️⃣ 解析 Apple Podcasts 链接，获取元数据和音频
python scripts/fetch_episode.py "<Apple Podcasts 链接>" --out ./_work

# 2️⃣ 转录音频（选一个你配置好的后端）
# 阿里云百炼 paraformer（推荐，省钱）：
python scripts/transcribe.py --from-meta ./_work --out ./_work --backend paraformer --diarize --speaker-count 2 --language zh

# 3️⃣ 用任意 LLM（DeepSeek / 通义 / Kimi / GPT 等）离线生成笔记
python scripts/make_notes.py --work ./_work --type auto --out ./笔记.md
```

### 自动降级（阿里云百炼专用）

如果怕某个模型额度用完，可以给一串后端顺序，自动降级：

```bash
python scripts/transcribe.py --from-meta ./_work --out ./_work \
  --fallback paraformer,funasr,qwen --diarize --speaker-count 2 --language zh
```

> ⚠️ **费用提示**：当 `paraformer` 额度用尽、自动降级到 `funasr` 时，脚本会**暂停并提示费用风险**，要求你加 `--confirm-funasr` 参数确认后才能继续。这是因为 fun-asr 无法启用「免费额度用完即停」机制，使用即按量计费（0.00022 元/秒）。确认的方式：
>
> ```bash
> python scripts/transcribe.py --from-meta ./_work --out ./_work \
>   --fallback paraformer,funasr,qwen --confirm-funasr \
>   --diarize --speaker-count 2 --language zh
> ```
>
> 若你直接选 `--backend funasr` 则无需确认（已为主动选择）。

> qwen 不支持说话人分离，若降级到它则该期不带 `【说话人N】` 标注。

---

## 📖 用任意 LLM 写笔记（不绑定 Claude）

`make_notes.py` 走 OpenAI 兼容接口，DeepSeek / 通义千问 / Kimi / GPT / 智谱 GLM 等都行：

```bash
# 1) 配置任意 OpenAI 兼容 LLM
export LLM_API_BASE="https://api.deepseek.com/v1"
export LLM_API_KEY="sk-xxx"
export LLM_MODEL="deepseek-chat"

# 2) 生成笔记（--type 可指定类型，或 auto 让模型自己判断）
python scripts/make_notes.py --work ./_work --type auto --out ./笔记.md
```

常见 base_url：DeepSeek `https://api.deepseek.com/v1`；通义千问百炼 `https://dashscope.aliyuncs.com/compatible-mode/v1`；Kimi `https://api.moonshot.cn/v1`；智谱 `https://open.bigmodel.cn/api/paas/v4`。

**没有 API Key？** 用 `--dump-prompt` 把提示词导出，整段粘贴到任意网页版 AI：

```bash
python scripts/make_notes.py --work ./_work --type knowledge --dump-prompt
# 生成 ./_work/note_prompt.md，整段贴进任意聊天框
```

---

## 📁 目录结构

```
apple-podcast-notes/
├── SKILL.md                   流程说明（技能主文件，AI 智能体读取它来工作）
├── scripts/
│   ├── fetch_episode.py       解析 Apple Podcasts 链接、下载音频、取 shownotes
│   ├── transcribe.py          转录（阿里云百炼 qwen/funasr/paraformer + SenseAudio + 通用 api）
│   └── make_notes.py          用任意 OpenAI 兼容 LLM 写笔记
├── templates/                 五套模板（财经、科技商业、访谈、知识科普、通用）
├── saved-notes/               生成的笔记默认保存到这里（若智能体指定了项目工作文件夹则优先存入项目文件夹）
└── README.md                  本文件
```

---

## 附录：阿里云百炼详细配置步骤

### 第 1 步：注册并开通阿里云百炼
1. 打开 https://bailian.console.aliyun.com/ ，用阿里云账号登录（没有就先注册，需实名认证）。
2. 首次进入会提示「开通百炼大模型服务」，点开通（开通免费；新用户有免费额度）。

### 第 2 步：获取 API Key
1. 在百炼控制台右上角头像 → 「API-KEY」，或直接访问 https://bailian.console.aliyun.com/?tab=api#/api-key
2. 点「创建我的 API-KEY」，复制出来的 `sk-xxxxxxxx`（只显示一次，妥善保存）。
3. 地域说明：默认「北京」地域。若用「新加坡（国际）」地域，API Key 不同，且运行时要加 `--region intl`。

### 第 3 步：把 Key 设为环境变量
```bash
# macOS / Linux（当前终端临时生效）
export DASHSCOPE_API_KEY="sk-你复制的key"

# 永久生效：把上面这行加进 ~/.bashrc 或 ~/.zshrc，再 source ~/.zshrc
```

### 验证是否配置成功
```bash
echo $DASHSCOPE_API_KEY
# 应该输出 sk-xxxx... 而不是空行
```

### 常见报错
- `缺配置 DASHSCOPE_API_KEY`：环境变量没设或没在同一个终端，检查 `echo $DASHSCOPE_API_KEY` 是否有输出。
- 提交后一直 FAILED：多为音频 URL 不可公网访问、或地域与 Key 不匹配（北京 Key 配了 intl，或反之）。
- **报"未解析出文本"但任务其实成功了**：脚本会存 `./_work/dashscope_raw_result.json`。用恢复模式重新解析、**不重复计费**：
  ```bash
  python scripts/transcribe.py --from-raw ./_work/dashscope_raw_result.json --out ./_work
  ```
  （结果下载链接有时效，一般约 24 小时内有效，过期需重新转录。）