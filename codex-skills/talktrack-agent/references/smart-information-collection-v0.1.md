# Smart Information Collection v0.1

Use this reference when a Shandian smart Agent task involves 智能信息采集, 对话字段, information collection, dialogue fields, `{collectParam}`, or inline `param` JSON.

Source basis: Feishu document `【智能信息采集】功能说明书` read through `lark-cli docs +fetch --api-version v2` on 2026-05-15.

## What It Does

智能信息采集 is a smart-Agent-node capability.

When enabled, after each round of conversation between the smart Agent and the user, the system calls a model to analyze the conversation content and the model output, extracts configured business fields, and writes the extracted results to:

```text
通话详情 -> 对话字段
```

This is different from intent routing:

- `intent` drives IVR graph routing.
- information collection writes structured business fields for reporting, follow-up, or CRM-like downstream review.

Do not use collected fields as a substitute for valid `intent` / port mappings.

## Supported Configuration Modes

### Mode 1: Standard Configuration, Preferred

Use this as the default path.

1. In the smart Agent node page, set `智能信息采集` to `采集`.
2. Click `添加对话字段`.
3. Select fields from the existing variable library or create new fields.
4. For every field, write a concise `字段描述` that explains extraction logic and business use.
5. Insert `{collectParam}` once into the prompt, usually under the core task or information-collection section.

Important:

- Insert `{collectParam}` only once, no matter how many fields are configured.
- The model reads all field definitions from the configured table.
- The main smart-Agent output format can stay as `回复内容{"intent":"当前意图"}`.

Recommended prompt line:

```text
信息采集：从用户原话和当前对话上下文中提取下方对话字段；仅基于明确证据填写，不确定时留空或写“未提及”。{collectParam}
```

### Mode 2: Custom Prompt / Inline Param JSON

Use only when the user explicitly wants full prompt control or the backend workflow requires the Agent to output collected fields inline.

Output shape:

```text
回复内容{"intent":"当前意图","param":[{"name":"字段名","value":"字段值"}]}
```

Rules:

- `name` must exactly match configured dialogue field names.
- `value` must come from user wording or clear conversation evidence.
- Use empty string, `未提及`, or a user-approved null convention when no evidence exists.
- Do not invent missing values.
- Do not add explanations outside the JSON.

If a terminal intent maps to a downstream speaking end node, terminal-closing ownership still applies:

```text
好的，我记下了。{"intent":"有意向或同意","param":[{"name":"微信确认状态","value":"已确认"}]}
```

## Field Design Rules

Good fields are:

- action-oriented: `是否同意加微信`, `预约时间`, `处理方案`, `退款方式`
- evidence-friendly: the value can be grounded in something the user said
- stable across calls: not over-specific to one test utterance
- useful for follow-up, reporting, or quality review

Avoid fields that are:

- duplicate of routing intent without extra business value
- impossible to infer from call content
- too broad, such as `客户情况`
- sensitive without business necessity
- dependent on hallucination or business facts not mentioned in the call

Recommended field description shape:

```text
字段名：<short name>
字段描述：仅当用户明确表达 <condition> 时填写 <value convention>；未表达时留空 / 未提及；不得根据语气猜测。
```

## Recommended Use Cases

- Lead qualification: interest level, budget, location, property size, appointment time, contact preference.
- Hiring / recruitment calls: city, job interest, availability, expected salary, whether willing to add WeChat.
- Service handling: selected solution, refund choice, complaint reason, replacement preference.
- Education / course calls: grade, subject, pain point, follow-up time, whether accepted materials.
- Quality review: whether user consented, whether identity matched, whether voice assistant answered.

## When Not To Use

- If the only required result is route selection; use `intent` alone.
- If a field cannot be observed from conversation evidence.
- If collecting sensitive personal information is not required for the business flow.
- If the field would encourage the model to ask unnecessary questions and hurt conversion.

## Privacy And Safety

- Minimize personal data. Only collect PII when the user or business workflow explicitly requires it.
- Prefer status fields over raw identifiers, for example `微信已确认` instead of storing a full WeChat ID unless truly needed.
- Do not store phone numbers, ID numbers, addresses, or private identifiers in prompt examples unless explicitly approved.
- Collected values must be evidence-based. Do not infer demographics, income, intent level, or identity from tone alone.

## Interaction With Existing TalkTrack-Agent Rules

### Intent Rules

Information collection does not change intent semantics.

The Agent still outputs the current matched intent / terminal label according to `intent-usage-rules.md`.

### Terminal-Closing Ownership

If the Agent's terminal intent leads to a downstream hangup / end node that speaks, the Agent must use short acknowledgement copy. Information collection may still be emitted via `{collectParam}` or inline `param`, but the Agent must not repeat the downstream closing sentence.

### Prompt Length

Standard `{collectParam}` is preferred because it keeps the prompt shorter. Inline `param` JSON examples can make the prompt longer and should be used sparingly.

### Readback And Audit

When auditing or importing a smart Agent with information collection, verify:

- Information collection is intentionally enabled or intentionally absent.
- `{collectParam}` appears exactly once when using standard mode.
- Field descriptions are precise and evidence-based.
- Inline `param` JSON, if used, has field names matching configured dialogue fields.
- Intent output format remains valid.
- Terminal-closing ownership remains valid.

## Human Confirmation Required

Ask for confirmation before backend write / import when:

- choosing the list of dialogue fields
- creating new fields in the variable library
- collecting PII or sensitive values
- choosing standard `{collectParam}` vs custom inline `param` JSON
- changing an existing prompt's output format from `{"intent":"..."}` to `{"intent":"...","param":[...]}`

## Prompt Package Add-On

When generating a prompt package with information collection, include:

```markdown
## Smart Information Collection Plan
| Field | Description | Value convention | Evidence source | Required? |
| --- | --- | --- | --- | --- |

Recommended mode: Standard `{collectParam}` / Custom inline `param`
Prompt insertion point:
Privacy risk:
Human confirmation needed:
```
