# -*- coding: utf-8 -*-
import copy
import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("create_doushen_real_prompt_ivr.py")
SPEC = importlib.util.spec_from_file_location("talktrack_agent_creator", MODULE_PATH)
TARGET = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TARGET)


def fixture():
    backend = {
        "type": 4,
        "name": "旧节点",
        "llmNodeModelConfig": {"id": 41, "prompt": "旧 Prompt"},
    }
    frontend = copy.deepcopy(backend)
    graph_custom = copy.deepcopy(backend)
    scene_list = [{"name": "旧场景", "nodeList": [backend]}]
    scene_front = [{
        "name": "旧场景",
        "nodeList": [frontend],
        "graph": {"cells": [{"id": "smart", "data": {"customData": graph_custom}}]},
    }]
    return scene_list, scene_front


def expect_runtime_error(callable_, expected_text):
    try:
        callable_()
    except RuntimeError as exc:
        assert expected_text in str(exc), str(exc)
    else:
        raise AssertionError("expected RuntimeError")


def main():
    default = TARGET.DEFAULT_OUTPUT_FORMAT_CONSTRAINT_PROMPT
    assert default.count(TARGET.OUTPUT_FORMAT_INTENT_PLACEHOLDER) == 1
    assert "`param`" in default and "`waitAsk`" in default
    assert "唯一的一个 JSON" in default

    business = "# 角色\n你是业务助理。\n\n## 业务规则\n命中拒绝时进入拒绝分支。"
    migrated, removed = TARGET.migrate_legacy_output_format_rules(
        business + "\n\n" + default
    )
    assert migrated == business
    assert removed == 1

    markdown_legacy = (
        "# 角色\n你是业务助理。\n\n"
        "## 输出格式规则\n回复内容后紧贴单个 JSON。\n"
        "JSON 必须放置在回复末尾。\n\n"
        "## 业务意图\n客户拒绝时进入拒绝分支。"
    )
    migrated, removed = TARGET.migrate_legacy_output_format_rules(markdown_legacy)
    assert removed == 1
    assert "输出格式规则" not in migrated
    assert "客户拒绝时进入拒绝分支" in migrated

    fenced_business = (
        "# 业务示例\n```text\n保留这段业务示例。\n```\n\n"
        "## 输出格式限制\nJSON 必须放置在回复末尾。"
    )
    migrated, removed = TARGET.migrate_legacy_output_format_rules(fenced_business)
    assert removed == 1
    assert "```text" in migrated and "保留这段业务示例" in migrated

    expect_runtime_error(
        lambda: TARGET.migrate_legacy_output_format_rules(
            "# 业务规则\n客户拒绝时进入拒绝分支；JSON 必须放置在回复末尾。"
        ),
        "manual review",
    )

    scene_list, scene_front = fixture()
    TARGET.apply_prompt(
        scene_list,
        scene_front,
        business,
        "新场景",
        "新节点",
        "enable",
    )
    enabled = TARGET.validate_output_format_constraint(scene_list, scene_front, "enable")
    assert enabled == {
        "enabled": 1,
        "promptMatches": True,
        "placeholderCount": 1,
        "businessPromptHasDuplicateFormatRules": False,
    }

    scene_list, scene_front = fixture()
    TARGET.apply_prompt(
        scene_list,
        scene_front,
        markdown_legacy,
        "新场景",
        "新节点",
        "disable",
    )
    disabled = TARGET.validate_output_format_constraint(scene_list, scene_front, "disable")
    assert disabled["enabled"] == 0
    assert disabled["placeholderCount"] == 1
    assert disabled["businessPromptHasDuplicateFormatRules"] is True

    scene_list, scene_front = fixture()
    for container in TARGET.output_constraint_surfaces(scene_list, scene_front).values():
        container["llmNodeOutputFormatConstraintEnabled"] = 0
        container["llmNodeOutputFormatConstraintPrompt"] = ""
    TARGET.apply_prompt(
        scene_list,
        scene_front,
        business,
        "海外场景",
        "海外节点",
        "preserve",
    )
    preserved = TARGET.validate_output_format_constraint(scene_list, scene_front, "preserve")
    assert preserved["enabled"] == 0
    assert preserved["placeholderCount"] == 0

    print("TALKTRACK_AGENT_OUTPUT_FORMAT_CONSTRAINT_TEST=PASS")


if __name__ == "__main__":
    main()
