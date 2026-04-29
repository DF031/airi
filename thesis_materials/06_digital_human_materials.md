# 数字人实现素材

本文件用于写第 5 章“数字人模块实现”和答辩 PPT。

## 实现目标

数字人模块需要解决三个层次的问题：

1. 能显示：Live2D 模型能加载、适配大小、切换模型。
2. 能说话：TTS 语音能播放，播放队列不会严重滞后。
3. 像在说话：语音播放时有口型、Level、身体轻动、表情和动作。

## AIRI 源码级迁移

上游项目：

```text
https://github.com/moeru-ai/airi
```

本地快照：

```text
frontend/src/airi/upstream/moeru-ai-airi
```

迁移重点：

| AIRI 原模块 | 本地实现 | 作用 |
|---|---|---|
| `pipelines-audio` | `frontend/src/airi/audio` | 音频队列、播放替换、中断、TTS 分段 |
| `model-driver-lipsync` | `frontend/src/airi/lipsync` | wLipSync 口型驱动 |
| `stage-ui-live2d` | `frontend/src/airi/live2d` | motion manager、自动眨眼、眼球注视、beat sync |

## Live2D 舞台管理

主要文件：

```text
frontend/src/avatar/live2dStageManager.js
```

实现点：

- `Live2DModel.from` 加载模型。
- 自动扫描模型参数、表情和 motion group。
- 根据容器大小自适应缩放。
- 模型切换时销毁旧模型并加载新模型。
- idle motion 和 interaction motion 分离。
- 说话时停止或弱化 idle motion，减少“身体动但不开口”的割裂感。
- 自动眨眼、眼球注视和随机扫视提升待机自然感。

## 每模型 profile

主要文件：

```text
frontend/src/avatar/modelProfilePresets.js
```

为什么需要 profile：

- 不同模型的口型参数不同，例如 `ParamMouthOpenY`、`PARAM_MOUTH_OPEN_Y`、`ParamA/I/U/E/O`。
- 不同模型 motion group 命名不同。
- 模型大小、中心点、默认位置不同。
- 同样的开口强度在不同模型上视觉效果不同。

profile 管理内容：

- 显示缩放。
- 横向和纵向偏移。
- 嘴型参数映射。
- 口型强度和平滑。
- idle motion 策略。
- 说话身体节奏。
- 情绪动作候选。

## TTS 与播放队列

后端文件：

```text
backend/avatar/tts.py
```

前端文件：

```text
frontend/src/utils/audioHandler.js
frontend/src/airi/audio/speechPipeline.js
frontend/src/airi/audio/playbackManager.js
```

实现点：

- 后端使用 edge-tts 生成语音。
- 前端支持多中文音色和语速。
- 支持 `queue`、`replace`、`interrupt` 语义。
- 新回答可以替换旧语音，避免语音排队导致回答已经显示但数字人迟迟才说话。
- TTS 分段用于降低一次性长文本语音生成等待。

## 口型同步

主要文件：

```text
frontend/src/airi/lipsync/live2dLipSync.js
frontend/src/utils/audioHandler.js
frontend/src/avatar/avatarRuntime.js
```

口型驱动来源：

| 来源 | 作用 |
|---|---|
| TTS mouth cues | 根据文本和音频时长生成近似 viseme 时间片 |
| wLipSync | 从真实音频中提取元音/频谱特征 |
| 每模型 mouth profile | 将通用口型信号映射到模型参数 |

优势：

- 比单纯按文本猜口型更稳定。
- 比单纯音量开合更接近说话状态。
- 可以兼容不同模型的参数族。

局限：

- 不是中文音素级强制对齐。
- edge-tts 不提供商业级 viseme 轨道。
- Live2D 模型本身口型绑定质量会限制最终效果。

## 支持模型

| 模型 | 口型参数数 | 说明 |
|---|---:|---|
| Hiyori | 2 | 默认模型，较稳定 |
| Natori | 3 | 表情和口型更丰富 |
| Mao Pro | 8 | 参数较多，适合调试口型 |
| Epsilon | 1 | 基础开合 |
| Izumi | 1 | 基础开合 |
| Shizuku | 1 | 基础开合 |
| Hijiki | 1 | 基础开合 |
| Tororo | 1 | 基础开合 |

## 调试面板

主要文件：

```text
frontend/src/components/AvatarDebugPanel.jsx
frontend/src/components/LevelMeter.jsx
```

支持：

- 当前模型 profile 查看。
- 情绪动作触发。
- 原生 motion 播放。
- 视线追踪、说话身体、呼吸幅度、情绪脸颊调节。
- Level、嘴型、音量、唇形实时显示。

## 可直接写入论文的段落

> 为提升数字人交互自然性，本文参考 AIRI 开源项目对音频播放、口型同步和 Live2D 舞台行为进行了源码级迁移与 React 工程化适配。系统通过 edge-tts 生成语音，在前端使用播放队列管理语音片段，并结合 TTS mouth cues 与 wLipSync 对真实音频进行口型驱动。由于不同 Live2D 模型的参数命名、motion group 和视觉比例存在差异，本文设计了逐模型 profile 机制，对缩放、位置、口型参数、动作策略和说话节奏进行统一配置。最终平台支持多个 Live2D 模型切换、多中文音色选择、语音播放中断替换、动作调试和实时音频电平显示。

