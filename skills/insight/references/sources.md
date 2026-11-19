# 方法来源与取舍

外部来源核对日期：2026-11-17；本地交互集成日期：2026-11-18。以下来源用于方法借鉴，规则由本项目按用户需求重新编写；未整包复制第三方 skill，也不把其原生工具指令作为当前环境指令执行。

| 来源 | 本版本采用的思想 | 适配位置与取舍 |
| --- | --- | --- |
| [Kiterlin/anti-defensive-writing](https://github.com/Kiterlin/anti-defensive-writing/blob/main/SKILL.md) | 依句子功能消除空泛防御；正面表达范围；保持技术含义、局部编辑与证据强度 | expression.md；非阻断说明按用户偏好集中引用块，任务定义所需条件留正文 |
| [Adkid-Zephyr](https://github.com/Adkid-Zephyr/anti-defensive-writing-Skill/blob/main/skills/anti-defensive-writing/SKILL.md) | 发掘真实贡献，以主张组织材料，使每项证据承担论证职责并解释意义 | argument.md；不采用隐藏不利结果、事后更换比较目标或绝不承认局部劣势的强规则 |
| [s4h-writing-argument](https://github.com/human-avatar/skills-for-humanity/blob/main/skills/s4h-writing-argument/SKILL.md) | 主张、证据、连接理由；显化前提，重构缺少连接的论证 | argument.md 与 protocol.md；反对意见交给独立审查，不强制每篇正文反驳；不移植多次固定问答 |
| 用户与本地 V1 | 独立蓝红/全新 writer、人工裁决、说明块；专业直觉、共同形成主张、轻量任务直接做 | SKILL.md 任务分流及 protocol.md；保留一阶段与两阶段裁决 |
| 用户批准的 grill-me 组合设计与本机 grill-me | 原生卡片、同维度候选、异步等待、实际答复驱动接续 | coordination.md 管理何时交互；grill-me 提供如何交互，不构成两个 skill 相互启动的循环 |

按用户决定，V2 不新增 Gpt-anti-defensive 的工作流；现有红蓝信息隔离继续来自本项目 V1。

范围限定、原意保留、直觉发现与测试设计是本版本的组合实现。没有直接证据证明这个组合优于每个上游方法，效果以本地实例和后续使用检验。仓库星标、格式校验和开发测试不等于写作效果 benchmark。此前会话中的论文数值未作为本版本有效性的验证结果。

宿主适配依据：

- [OpenAI：Build skills](https://learn.chatgpt.com/docs/build-skills)：按需加载参考文件、技能发现位置与 UI 元数据。
- [OpenAI：Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)：skill 可要求子代理，子代理共享宿主权限。
- 本会话实际工具 schema：`collaboration.spawn_agent` 的 `fork_turns: "none"`；原生 `functions.request_user_input_async`。参数以当前宿主为准，不将其声称为所有 Codex 客户端的固定 API。
