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

## Proactive Configuration Rule

When creating, importing, or optimizing a smart Agent from a prompt, source document, or business scenario, smart information collection is not only a check item. Treat it as a configuration surface that can be prepared ahead of time.

Default behavior:

1. Infer only the useful dialogue fields required by the current business goal and prompt, such as customer identity, contact method, company, appointment time, budget, selected service, or follow-up preference when those values are truly part of the scenario.
2. Add a `Smart Information Collection Plan` to the prompt package.
3. Prefer standard configuration: enable the front-page `智能信息采集` switch (`llmNodeCollectParamEnabled=1`), configure dialogue fields in `llmNodeCollectParamList`, and insert `{collectParam}` once in the prompt.
4. If the user has explicitly authorized backend changes for the target IVR / smart node, create or select the approved fields, enable collection, update the prompt, and verify readback.
5. If the task is read-only validation, do not auto-fix missing fields; report the gap and provide the exact field plan needed for the next write pass.

PII rule: names, phone numbers, company names, addresses, and account identifiers can be configured only when the business scenario requires them and the user has authorized collecting them. Use synthetic examples in reports and tests.

Field-list rule: there is no fixed default field set. `客户姓名` / `客户手机号` / `公司名称` are common lead-qualification examples, not mandatory fields. A recruitment call, service-handling call, product-demo call, course call, and quality-review call should each get a different field plan derived from the prompt and follow-up use case.

## Supported Configuration Modes

### Mode 1: Standard Configuration, Preferred

Use this as the default path.

1. In the smart Agent node page, set `智能信息采集` to `采集`.
2. Backend field mapping for that front switch is `llmNodeCollectParamEnabled=1`.
3. Click `添加对话字段`; backend field mapping is `llmNodeCollectParamList`.
4. Select fields from the existing variable library or create new fields.
5. For every field, write a concise `desc` / `字段描述` that explains extraction logic and business use.
6. Insert `{collectParam}` once into the prompt, usually under the core task or information-collection section.

Important field distinction:

- Front-page `智能信息采集` = `llmNodeCollectParamEnabled` + `llmNodeCollectParamList`; this controls the radio group users see beside the task prompt and the `{collectParam}` field list.
- Lower-page `信息采集` = `infoCollectEnabled` + `infoCollectConfigList`; this is a separate section with model-analysis field configs and should not be used as the only proof that the visible `智能信息采集` switch is enabled.
- When a user says the visible `智能信息采集` still shows `不采集`, read and patch `llmNodeCollectParamEnabled`, not only `infoCollectEnabled`.

Important:

- Insert `{collectParam}` only once, no matter how many fields are configured.
- The model reads all field definitions from the configured table.
- The main smart-Agent output format can stay as `回复内容{"intent":"当前意图"}`.

Acceptance gate:

- If the page should show `智能信息采集 = 采集`, `llmNodeCollectParamEnabled` must be `1` in all three copies: backend node, `sceneListFrontend.nodeList`, and graph `customData`.
- `llmNodeCollectParamList` must contain the approved scenario-derived fields in all three copies.
- `{collectParam}` must appear exactly once in the prompt.
- `infoCollectEnabled=1` alone is not a pass for the visible `智能信息采集` radio group. It only proves the lower `信息采集` section is enabled.

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

### Dynamic Field Principle

Design the field list from the current scenario. Start from the business decision the caller wants after the call:

- Product demo / B2B lead: company name, demand scenario, current system status, demo interest, contact method.
- Recruitment: city, target role, availability, expected salary, whether willing to add WeChat.
- Property / sales lead: area, budget, location preference, viewing time, contact method.
- Service handling: complaint reason, chosen solution, refund / replacement preference, follow-up time.
- Quality review: identity match status, consent status, whether voice assistant answered.

Do not copy a fixed list from another IVR. Add names, phone numbers, company names, or other PII only when the current prompt and business flow genuinely need them.

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

### Optional Lead-Collection Field Templates

Use these only when the scenario needs customer identity or follow-up qualification. They are examples, not default fields. Adjust names to match the backend variable library and remove any field that the current prompt does not need.

```text
字段名：客户姓名
字段描述：仅当用户明确说出姓名、称呼或“我叫...”时填写用户姓名或称呼；未表达时留空或写“未提及”；不得从手机号、公司名或语气猜测。

字段名：客户手机号
字段描述：仅当用户明确说出完整手机号或可合并的分段手机号时填写 11 位手机号；进入手机号采集中状态后，支持客户分2次、分8次、甚至一位一位慢速报号，并在本次手机号采集会话内持续累积数字片段、中文数字、幺/一/零等号码表达；未完整表达时留空或写“未完整”；不得编造缺失数字，不得把时间、金额、业务量拼入手机号。

字段名：公司名称
字段描述：仅当用户明确说出公司、单位、机构或店铺名称时填写原话中的名称；未表达时留空或写“未提及”；不得把职位、行业或项目名误当作公司名称。
```

### Phone Number Multi-Round Collection

Phone numbers are often split by ASR into multiple user turns, especially when the user speaks slowly or pauses between number groups.

When the scenario collects phone numbers:

- Treat `客户手机号` as a session-based accumulation field, not a single-turn exact-match field.
- In the main prompt, add a `手机号采集中状态` rule: after the Agent asks for a phone number, short digit fragments in the next several user turns should be accumulated instead of treated as failures.
- In `llmNodeCollectParamList.desc`, say that the field supports slow, segmented, multi-round reporting, including 2-part, 8-part, and one-digit-at-a-time reporting.
- If the lower `infoCollectConfigList` model extractor is also configured, set the phone extractor's `recognitionRound` high enough for one-by-one reporting. Use `11` when the flow must tolerate a user speaking one digit per turn.
- Do not force the user to restart after every incomplete fragment. Use continuation prompts such as: `好的，我先听到前面这一段了，您继续往后报就行。`
- Only ask the user to restart when they explicitly say the previous digits were wrong, the accumulated digits exceed 11 and cannot be resolved, or repeated attempts still cannot form a valid number.
- Do not merge time or scheduling expressions into the phone number, such as `六点之前`, `下午三点`, `明天`, or `一会儿`.

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

- Front visible information collection is intentionally enabled or intentionally absent: `llmNodeCollectParamEnabled=1` and `llmNodeCollectParamList` contains the approved fields.
- If the lower `信息采集` section is also used, `infoCollectEnabled` and `infoCollectConfigList` should be checked separately and named separately in reports.
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
