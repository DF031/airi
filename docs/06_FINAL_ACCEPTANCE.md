# 最终验收记录

验收日期：2026-04-23

## 验收环境

| 项 | 状态 |
|---|---|
| 工作目录 | `C:\duan\home\BS\airi` |
| 后端 | FastAPI / Uvicorn / `http://127.0.0.1:8000` |
| 前端 | Vite / React / `http://127.0.0.1:5173` |
| RAG | PortableRAGV4 |
| LLM | zhipu / GLM-4-Flash-250414 |
| TTS | edge-tts / zh-CN-XiaoxiaoNeural |
| 知识库 | 74 文件 / 35.01 MB |

## 服务验收

| 检查项 | 结果 |
|---|---|
| 后端 `/api/system/status` | 200 OK |
| 前端首页 | 200 OK |
| RAG 加载 | 74 docs / 32635 evidence units |
| Live2D 模型列表 | 8 个模型 |
| TTS 音色列表 | 18 个中文音色 |
| 浏览器控制台 | Errors: 0 / Warnings: 0 |

## API 验收

系统状态返回确认：

- `chat_provider`: `zhipu`
- `chat_model`: `GLM-4-Flash-250414`
- `rag_strategy`: `portable_v4`
- `rag_engine`: `portable_rag_v4`
- `rag_loaded`: `true`
- `tts_engine`: `edge-tts`
- `tts_voice`: `zh-CN-XiaoxiaoNeural`

TTS 合成测试：

- 输入：`你好，我是 AIRI，正在进行最终验收。`
- 结果：成功返回音频。
- mouth cues：存在。

## 浏览器真实问答验收

测试问题：

```text
学分认定和转换过程中如果弄虚作假会有什么后果？
```

页面回答：

```text
学分认定和转换过程中如果弄虚作假，将受到纪律处分，取消相应课程的认定结果。
```

验收结果：

- `/api/chat/stream`: 200 OK
- `/api/tts`: 200 OK
- 页面正常显示知识来源。
- 返回 8 条来源。
- 前端未暴露 `<|ACT|>` 动作 token。
- 回答内容与知识库证据匹配。

## 数字人验收

| 检查项 | 结果 |
|---|---|
| Hiyori 默认加载 | 通过 |
| Hiyori -> Natori 切换 | 通过 |
| Natori -> Hiyori 切回 | 通过 |
| 模型 profile 展示 | 通过 |
| TTS 试听 | 通过 |
| 语音播放状态 | 出现“语音播放中” |
| Level Meter | 有实时变化 |
| 嘴型参数 | 有实时变化 |
| 调试面板 | 可展开、可交互 |

## 工程检查

前端：

```powershell
npm run lint
npm run build
```

结果：通过。构建时有 chunk size warning，不影响运行。

后端：

```powershell
.\venv\Scripts\python.exe -m compileall backend experiments\rag_reproduction\raglab
```

结果：通过。

## 已知注意点

- 智谱免费层级可能返回 429 限速，连续高频提问时需要等待。
- RAG 离线代理指标不能等同于真实答案准确率，论文中应使用严格标注指标作为主结论。
- TTS 依赖 edge-tts 服务可用性，网络波动时可能需要重试。
- 前端生产包存在体积 warning，后续可通过代码拆分优化，但不影响毕设演示。

## 结论

平台最终运行验收通过。当前系统已经形成完整闭环：

```text
用户提问 -> RAG 检索 -> GLM 生成 -> 知识来源展示 -> TTS 语音 -> Live2D 动作与口型
```

该状态可以作为毕业设计工程演示和论文系统实现章节的基础版本。

