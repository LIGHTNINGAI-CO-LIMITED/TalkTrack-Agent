# Smart-Agent Output Format Constraint

Use this reference when creating, importing, migrating, auditing, or debugging a smart Agent prompt that emits `intent`, `param`, or `waitAsk`.

## Backend Contract

The domestic smart-Agent node has two output-constraint fields:

```json
{
  "llmNodeOutputFormatConstraintEnabled": 1,
  "llmNodeOutputFormatConstraintPrompt": "<platform constraint>"
}
```

Write and read back both fields in all three copies:

- backend `sceneList` smart node
- `sceneListFrontend.nodeList` smart node
- graph `data.customData` smart node

The Debug UI only controls whether the editor is visible. It does not remove the backend fields or prevent API read/write.

## Ownership Rule

The business prompt owns role, task, business facts, conversation flow, collection behavior, compliance, and intent trigger semantics. It must not duplicate the platform-owned serialization contract.

For new domestic smart Agents:

- default `llmNodeOutputFormatConstraintEnabled=1`
- store the canonical prompt below
- keep `{Agentintentlist}` literal and present exactly once
- do not expand the placeholder in the Skill or business prompt
- do not append a second output-format section to `llmNodeModelConfig.prompt`

For overseas smart Agents, preserve existing output-constraint fields until the overseas product behavior is separately verified. Do not apply the domestic default automatically.

## Canonical Domestic Prompt

```text
<当前节点跳转意图池与触发条件开始>
{Agentintentlist}
<当前节点跳转意图池与触发条件结束>

<意图与格式输出规范开始>

1. 意图分类与核心逻辑：
- 任何业务节点的意图均分为两类：【跳转意图】和【留守意图】。
- 【跳转意图】：当用户明确触发跨节点流转、业务结束、转交等边界条件时，`intent` 的值必须且只能从上述 `<当前节点跳转意图池与触发条件>` 中严格提取。
- 【留守意图】：当对话处于正常问答、信息收集、闲聊等不需要跳出当前节点的状态时，`intent` 应该输出当前语境的具体意图（例如 "继续沟通"、"沟通中"）。

2. intent 字段赋值铁律：
- 只要满足跳转意图的触发条件，必须一字不差地输出意图池中的对应词汇。
- 在【留守意图】状态下，允许输出合理的归纳意图，但**绝对禁止**捏造并输出“占位符”、“测试”这种毫无意义的系统级占位词。

3. 格式规范与尾部干净要求（最高优先级）：
- 每次回复必须且只能是：自然语言回复内容 + 单个合法的结果 JSON。
- **字段包容性**：该 JSON 必须包含 `intent` 字段。如果当前业务存在变量采集指令（如 `param`）或追问指令（如 `waitAsk`），**必须将所有要求的字段合并到这唯一的一个 JSON 结构内部**，绝不允许输出多个 JSON。
- JSON 必须放置在自然语言回复内容的最后。允许自然语言与 JSON 之间存在换行。
- **致命禁令**：该单一 JSON 的右括号 `}` 必须是整个大模型输出的**最后一个字符**。在 `}` 之后**绝对禁止**出现任何标点符号（包括句号、逗号）、换行符、空格、备注或分析过程。禁止使用代码块（如 ```json）包裹结果。

4. 兜底与分析过程禁令：
- 即使“兜底”作为一个词碰巧存在于意图池或系统设定中，也**绝对禁止**输出 `{"intent":"兜底"}`。
- 绝对禁止在自然语言回复中输出 JSON 占位符、意图解析过程或任何调试说明。

5. 正确与错误格式示例参考：
- 正确（触发意图池中的跳转意图，允许换行）：
[这里是连贯自然的回复内容]
{"intent":"上述意图池中定义的某个具体意图"}
- 正确（不触发跳转，直接留空）：
[这里是连贯自然的回复内容]{"intent":""}
- 正确（不触发跳转，输出具体留守意图）：
[这里是连贯自然的回复内容]
{"intent":"继续沟通"}
- 错误（捏造了系统级禁止词汇，禁止）：
[这里是连贯自然的回复内容]{"intent":"当前意图"} （错误原因：输出了绝对禁止的系统占位词）
- 错误（JSON 尾部多出标点，致命错误）：
[这里是连贯自然的回复内容]
{"intent":"继续沟通"}。 （错误原因：右括号 `}` 后面多出了句号，会导致系统 JSON 解析崩溃）

<意图与格式输出规范结束>
```

## Existing-Prompt Migration

When updating an existing domestic smart Agent, enable the platform constraint and migrate the business prompt automatically only when the legacy format block has a clear boundary:

- an exact canonical constraint block
- `<意图与格式输出规范开始>` through `<意图与格式输出规范结束>`
- a Markdown section whose heading clearly names `输出格式`, `格式约束`, `结果格式`, `JSON 输出`, or equivalent, ending at the next same-or-higher-level heading or end of file

Preserve business intent triggers, terminal-closing ownership, collection rules, compliance rules, and terminal examples. Do not delete isolated JSON examples merely because they contain `intent`.

If the existing constraint prompt is non-empty and was intentionally customized, preserve it unless the user explicitly asks to reset it to the canonical default. It must still contain `{Agentintentlist}` exactly once and satisfy the single-JSON, clean-tail, merged-field, and no-`兜底` invariants. Fill the canonical default only when the field is empty or when creating a new domestic node.

If format instructions remain outside a safely bounded section, stop before `updateSceneList` and report manual review. Do not guess which text is business logic.

## Acceptance

- enabled state and constraint text match across backend, frontend, and graph
- enabled domestic constraint contains `{Agentintentlist}` exactly once
- business prompt contains no duplicate platform-format block or `{Agentintentlist}`
- jump intent comes from the dynamic current-node intent pool
- non-jump turns may use an empty or concrete stay intent
- `兜底` is never emitted as an intent
- `intent`, `param`, and `waitAsk`, when required together, are merged into one result JSON
