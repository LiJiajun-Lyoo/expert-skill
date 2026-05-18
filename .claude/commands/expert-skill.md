---
description: Start the enterprise expert skill workflow for standard or discovery mode
argument-hint: [standard|discovery] [expert-name-or-goal]
---

请读取并遵循以下项目文件作为当前命令的权威说明：

- @README.md
- @SKILL.md

用户通过 `/expert-skill` 触发了企业专家知识蒸馏流程。

用户附加参数为：`$ARGUMENTS`

你的任务：

1. 先确认当前工作目录是否位于本仓库根目录。
2. 先用 3-6 行简要说明本项目支持的两条路径：
   - `standard`：快速蒸馏显性知识
   - `discovery`：在基础 Skill 上继续做隐性知识挖掘
3. 如果用户已经在参数或上下文里明确说了 `standard` 或 `discovery`，直接进入对应流程。
4. 如果用户没有明确模式，只问一个简短问题让用户选择模式，不要一次抛出很多问题。
5. 从 Step 1 基础信息录入开始，按 `SKILL.md` 和 `README.md` 的实际流程推进。
6. 需要用户回答时，一次只问一个问题；需要用户确认时，尽量给出可直接粘贴的内容。
7. 需要执行仓库脚本时，按仓库中的真实命令、真实文件路径和真实状态流转执行，不要编造不存在的参数。
8. 需要模型参与的阶段（通常是 P2 / P3 / P4 / P6）：
   - 先生成 prompt 文件
   - 明确告诉用户 prompt 写到了哪里
   - 明确告诉用户下一步是“把该 prompt 发给模型，并把回复保存为 JSON 或 YAML 文件”
   - 然后再指导用户执行 `--parse-output`
9. 如果用户是在练习或演示流程，且没有提供真实材料，可以建议使用 `mock_expert/` 作为参考样例，但不要直接复制其中最终答案。
10. 每完成一步，都要明确说明：
   - 这一步的目标
   - 输入是什么
   - 写入了哪些文件
   - `meta.discovery.status` 是否发生变化

执行风格要求：

- 不要只讲概念，要尽量推动真实落盘
- 不要跳过状态检查
- 不要假设存在 `/expert-skill` 之外的额外命令系统
- 如果发现仓库当前状态和文档有差异，以实际代码行为为准，并向用户说明

现在开始：先确认当前仓库根目录，然后进入基础信息录入。
