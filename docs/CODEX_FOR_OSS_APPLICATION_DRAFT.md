# Codex for OSS 申请草稿

这份草稿按当前仓库真实状态撰写：它是公开的学生开源研究项目，而不是已有大量社区用户的成熟开源项目。申请时建议保持诚实，把重点放在项目完整度、可复现实验和后续维护计划上。

## 仓库信息

- GitHub 用户名：`DF031`
- 仓库地址：`https://github.com/DF031/airi`
- 角色：主要维护者
- 项目类型：学生开源项目 / 研究型原型 / 数字人 RAG 问答平台

## 仓库为什么符合要求（中文，500 字以内）

本仓库是我的本科毕业设计项目“融合大模型技术的数字人智能问答平台”的开源实现。我是项目主要维护者，负责后端、前端、RAG 实验、数字人交互和文档整理。项目面向低成本本地运行场景，整合了校园知识库 RAG、OpenAI-compatible LLM 调用、FastAPI 流式问答、edge-tts 语音合成、Live2D 数字人展示，以及从 AIRI 参考迁移的音频队列、口型同步、动作与调试能力。仓库包含可复现的 Portable RAG v4 实现、评测数据、离线评估脚本、答案级标注结果和最终验收记录。虽然它目前还不是高 star 的成熟社区项目，但它完整公开了一个学生开发者如何把 RAG 研究、工程系统和数字人交互做成可运行平台的过程。后续我计划继续完善安装体验、负例拒答、安全边界、文档和 issue 维护，使其成为可供同类毕业设计、校园知识库助手和数字人 RAG 原型参考的开源项目。

## API 额度使用计划（中文，500 字以内）

如果获得 API 额度，我计划主要用于开源维护和系统改进，而不是个人闲聊。具体包括：1）补充 RAG 回答质量评估，对离线指标、人工标注和 LLM judge 结果进行对照，减少只依赖代理指标带来的误判；2）改进负例拒答、隐私边界、实时信息边界和幻觉检测，降低错误回答风险；3）为项目生成更好的开发文档、测试问题、示例配置和 issue triage 辅助；4）测试不同模型在中文校园知识库问答中的效果，并将结果公开到仓库文档；5）辅助代码审查和安全检查，发现后端接口、环境变量、依赖和前端资源加载中的潜在问题。所有使用都会围绕该公开仓库的维护、评估和文档改进展开。

## 其他说明（中文，500 字以内）

我理解该项目目前仍处于学生开源项目阶段，社区影响力有限，没有大量 star、fork 或外部贡献者。因此申请中不会夸大项目规模。我希望把它作为一个持续维护的公开项目继续完善：补充许可证和贡献说明，清理第三方素材许可边界，改进 README 和运行脚本，增加 smoke test 与安全检查，并逐步把毕业设计材料整理成对其他开发者有参考价值的 RAG + 数字人实践文档。Codex 对我最有帮助的地方，是在有限时间内辅助我完成代码审查、文档维护、实验结果分析和安全边界改进。

## 英文简版

This repository is the open-source implementation of my undergraduate thesis project, a digital human question-answering platform powered by RAG and LLMs. I am the primary maintainer. The system integrates a portable campus-knowledge RAG pipeline, FastAPI streaming chat, OpenAI-compatible LLM providers, edge-tts speech generation, Live2D avatar rendering, lip sync, motion profiles, and reproducible offline evaluation. It is not yet a mature high-star community project, but it publicly documents a complete student-built prototype that connects RAG research, engineering implementation, and digital human interaction. I plan to keep improving setup experience, refusal behavior, safety boundaries, documentation, and evaluation so it can serve as a reference for similar campus assistant, graduation design, and RAG-avatar projects.
