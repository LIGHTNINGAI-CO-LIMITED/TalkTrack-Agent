from __future__ import annotations

import copy

import create_doushen_real_prompt_ivr as target


def fixture() -> tuple[list[dict], list[dict]]:
    scene = [{"nodeList": [{"name": "开场白", "intentList": [{"34642": "node-next"}], "interruptedIntentList": ["34642"]}]}]
    front = [{
        "nodeList": [{"name": "开场白", "intentList": [{"value": "34642", "label": "普通拒绝", "digitSequence": ""}]}],
        "graph": {"cells": [{"id": "node-opening", "data": {"customData": {"name": "开场白", "intentList": [{"value": "34642", "label": "普通拒绝", "digitSequence": ""}]}}}]},
    }]
    return scene, front


def main() -> None:
    scene, front = fixture()
    target_catalog = {"34627": "普通拒绝"}
    issues = target.intent_ownership_issues(scene, front, target_catalog, "fixture")
    assert issues and all("34642" in issue for issue in issues)

    remapped_scene = copy.deepcopy(scene)
    remapped_front = copy.deepcopy(front)
    mapping = target.remap_cloned_intent_references(
        remapped_scene,
        remapped_front,
        {"34642": "普通拒绝"},
        target_catalog,
    )
    assert mapping == {"34642": "34627"}
    assert not target.intent_ownership_issues(remapped_scene, remapped_front, target_catalog, "remapped")
    print("TALKTRACK_AGENT_INTENT_OWNERSHIP_TEST=PASS")


if __name__ == "__main__":
    main()
