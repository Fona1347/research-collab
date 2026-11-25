# 方法来源与取舍

外部来源核对日期：2026-11-17；跨宿主与体裁修订日期：2026-11-23；V2.4 跨学科范式校准与兜底可靠性修订日期：2026-11-23；V2.5 英文学术写作层修订日期：2026-11-25。以下来源用于方法借鉴，规则由本项目按用户需求重新编写；未整包复制第三方 skill，也不把其原生工具指令作为当前环境指令执行。

| 来源 | 本版本采用的思想 | 适配位置与取舍 |
| --- | --- | --- |
| [Kiterlin/anti-defensive-writing](https://github.com/Kiterlin/anti-defensive-writing/blob/main/SKILL.md) | 依句子功能消除空泛防御；正面表达范围；保持技术含义、局部编辑与证据强度 | expression.md；内部审阅稿可将非阻断说明集中为文末引用块，正式稿将必要范围与限制置于自然正文位置 |
| [Adkid-Zephyr](https://github.com/Adkid-Zephyr/anti-defensive-writing-Skill/blob/main/skills/anti-defensive-writing/SKILL.md) | 发掘真实贡献，以主张组织材料，使每项证据承担论证职责并解释意义 | argument.md；不采用隐藏不利结果、事后更换比较目标或绝不承认局部劣势的强规则 |
| [s4h-writing-argument](https://github.com/human-avatar/skills-for-humanity/blob/main/skills/s4h-writing-argument/SKILL.md) | 主张、证据、连接理由；显化前提，重构缺少连接的论证 | argument.md 与 protocol.md；反对意见交给独立审查，不强制每篇正文反驳；不移植多次固定问答 |
| 见微 V1 原始设计 | 独立蓝红/全新 writer、人工裁决、说明块；专业直觉、共同形成主张、轻量任务直接做 | SKILL.md 任务分流及 protocol.md；保留一阶段与两阶段裁决 |
| [Google Antigravity 的公开交互规则](https://antigravity.google/docs/commands/grill-me)（参考 `grill-me` 交互模式） | 先查事实、一次一题、推荐优先、自填与跳过、实际答复驱动接续 | V2.1 曾以独立 Skill 协作；V2.3 将所需单项决策规则内置进 [decision-interaction.md](decision-interaction.md)，不再依赖外部 Skill |
| Gopen & Swan (1990) *The Science of Scientific Writing*；Williams & Bizup *Style: Lessons in Clarity and Grace*；Hyland 学术 hedging 研究；Nature Summary Paragraph 指南 | Given–New 信息流、主谓紧邻、去名词化、证据强度精确 hedging、期刊语体微校准 | [english-prose.md](english-prose.md)（仅在英文交付时按需加载）；方法借鉴，不构成效果 benchmark |

按用户决定，V2 起不新增 Gpt-anti-defensive 的工作流；现有红蓝信息隔离继续来自本项目 V1。

范围限定、原意保留、直觉发现与测试设计是本版本的组合实现。没有直接证据证明这个组合优于每个上游方法，效果以实际使用检验。仓库星标、格式校验和开发测试不等于写作效果 benchmark。历史试运行记录不构成当前版本的写作效果验证。V2.4 针对实测暴露的跨范式副作用与隔离成稿兜底边界，在入口与参考文档中补入非实验范式豁免、零检索与 PRISMA 边界，以及成稿方推理展开与表达强度有限核查规则。V2.5 新增按需加载的 [english-prose.md](english-prose.md) 并完善英文成稿交接与终审约束，纯中文任务不加载该文件。

宿主适配依据：

- [OpenAI：Build skills](https://learn.chatgpt.com/docs/build-skills)：按需加载参考文件、技能发现位置与 UI 元数据。
- [OpenAI：Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)：skill 可要求子代理，子代理共享宿主权限。
- Codex 运行时工具约定：`fork_turns: "none"` 和 `request_user_input_async`。具体能力以当前会话的工具定义为准。
- [Claude Code：子代理和工具约束](https://code.claude.com/docs/en/sub-agents)、[DeepSeek Harness：原生问答工具](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/interaction/tool-ask-user/README.md)，用于核对宿主的问答边界。
