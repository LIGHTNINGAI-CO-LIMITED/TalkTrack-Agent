# TalkTrack-Agent

Formerly `sd-admin-ivr-config`.

`TalkTrack-Agent` is the TalkTrack-series Codex skill for Shandian Intelligent smart-Agent work:

- arbitrary source-document to outbound smart-Agent prompt drafting
- smart Agent / smart-node prompt import and readback validation
- `llmNodeModelConfig` inspection
- smart information collection design using dialogue fields and `{collectParam}`
- intent / port / terminal / hangup governance
- terminal-closing ownership checks so smart-Agent terminal examples do not duplicate downstream hangup / end-node copy
- smart-Agent read-only audit scoring

Companion skills:

- `talktrack-master`: ordinary nodes, jump/end nodes, system TTS, knowledge-base answers, NLP / KB matching, ordinary-node 2.0, and text-debug regression
- `talktrack-distillation`: transcript and call-material distillation into reusable AI Voice Agent assets

Install/use path in this repository:

```text
codex-skills/talktrack-agent
```

The old skill path `codex-skills/sd-admin-ivr-config` should be removed from the package to avoid duplicate skill discovery.
