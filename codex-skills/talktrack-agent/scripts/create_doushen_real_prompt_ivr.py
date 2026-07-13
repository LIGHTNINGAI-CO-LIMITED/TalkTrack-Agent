# -*- coding: utf-8 -*-
import argparse
import copy
import datetime as dt
import hashlib
import json
import re
from urllib.parse import unquote
from pathlib import Path

import requests


BACKENDS = {
    "domestic": {
        "webBase": "https://ai.sd6g.com:1904",
        "apiBase": "https://ai.sd6g.com:1904/api/web",
    },
    "overseas": {
        "webBase": "https://ai.tbot360.com",
        "apiBase": "https://ai.tbot360.com/api/web",
    },
}
RAW_PROMPT_CHAR_LIMIT = 14500
DEFAULT_SMART_AGENT_MODEL_ID = 55
DEFAULT_SMART_AGENT_MODEL_NAME = "闪电26BMoE-fast"
RESERVED_SYSTEM_INTENT_IDS = frozenset({"-1", "-2"})


def extract_access_token(value: str) -> str:
    decoded = unquote((value or "").strip())
    match = re.search(r"[0-9a-fA-F]{32}", decoded)
    if match:
        return match.group(0)
    decoded = re.sub(r"^\s*token\s*=\s*", "", decoded, flags=re.I)
    decoded = re.sub(r"^\s*Bearer\s+", "", decoded, flags=re.I).strip().strip("\"'")
    match = re.search(r"[A-Za-z0-9._-]{20,}", decoded)
    if match:
        return match.group(0)
    raise RuntimeError("No usable access token found. Paste a token, token=Bearer%20..., or -H 'token: Bearer ...'.")


def backend_from_url(value: str) -> str | None:
    lower = (value or "").lower()
    if "ai.sd6g.com:1904" in lower or "sd6g.com:1904" in lower:
        return "domestic"
    if "ai.tbot360.com" in lower or "tbot360.com" in lower:
        return "overseas"
    return None


def probe_backend(region: str, token: str) -> dict:
    meta = BACKENDS[region]
    headers = {"token": f"Bearer {token}", "X-Requested-With": "XMLHttpRequest"}
    try:
        resp = requests.get(f"{meta['apiBase']}/account/findInfo", headers=headers, timeout=20)
        resp.encoding = "utf-8"
        data = resp.json()
    except Exception as exc:
        return {"region": region, "ok": False, "error": type(exc).__name__}
    return {"region": region, "ok": str(data.get("code")) == "0", "code": data.get("code"), "data": data.get("data") or {}}


def resolve_backend(token_text: str, backend_region: str = "auto", backend_url: str = "") -> dict:
    token = extract_access_token(token_text)
    hinted = backend_from_url(backend_url)
    if backend_region != "auto" and hinted and backend_region != hinted:
        raise RuntimeError(f"backend region conflict: --backend-region={backend_region}, --backend-url points to {hinted}")
    if backend_region != "auto":
        candidates = [backend_region]
    elif hinted:
        candidates = [hinted]
    else:
        candidates = list(BACKENDS)
    probes = [probe_backend(region, token) for region in candidates]
    ok = [item for item in probes if item.get("ok")]
    if not ok:
        raise RuntimeError(f"token validation failed for candidate backends: {probes}")
    if len(ok) > 1:
        raise RuntimeError("token validates against multiple backends; pass --backend-region domestic or overseas")
    region = ok[0]["region"]
    meta = BACKENDS[region]
    return {"region": region, "token": token, "webBase": meta["webBase"], "apiBase": meta["apiBase"], "accountInfo": ok[0]}


def compact_prompt(text: str) -> str:
    lines = []
    in_fence = False
    for raw_line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw_line.rstrip()
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        lines.append(line)

    result = "\n".join(lines)
    while "\n\n\n" in result:
        result = result.replace("\n\n\n", "\n\n")
    return result.strip()


class Client:
    def __init__(self, token: str, backend: dict):
        self.backend = backend
        self.base_url = backend["apiBase"]
        self.web_base = backend["webBase"]
        self.session = requests.Session()
        self.session.headers.update(
            {
                "token": f"Bearer {token}",
                "Accept": "application/json, text/plain, */*",
                "X-Requested-With": "XMLHttpRequest",
            }
        )

    def _json(self, response: requests.Response):
        response.encoding = "utf-8"
        response.raise_for_status()
        return response.json()

    @staticmethod
    def assert_ok(response, step: str):
        if str(response.get("code")) != "0":
            raise RuntimeError(
                f"{step} failed: code={response.get('code')}, "
                f"msg={response.get('msg') or response.get('message')}"
            )

    def get(self, path: str):
        return self._json(self.session.get(f"{self.base_url}{path}", timeout=60))

    def post(self, path: str, body):
        return self._json(self.session.post(f"{self.base_url}{path}", json=body, timeout=60))


def parse_json_maybe(value):
    if isinstance(value, str):
        return json.loads(value)
    return value


def first_smart_node(nodes):
    for node in nodes:
        if int(node.get("type", -1)) == 4:
            return node
    raise RuntimeError("No smart Agent node found")


def first_smart_graph_cell(cells):
    for cell in cells:
        custom = cell.get("data", {}).get("customData") or {}
        if int(custom.get("type", -1)) == 4:
            return cell
    for cell in cells:
        data = cell.get("data", {})
        if int(data.get("nodeType", -1)) == 4:
            return cell
    raise RuntimeError("No smart Agent graph cell found")


def resolve_new_ivr_id(created, client: Client, name: str) -> int:
    data = created.get("data")
    if isinstance(data, int):
        return data
    if isinstance(data, str) and data.isdigit():
        return int(data)
    if isinstance(data, dict):
        for key in ("ivrId", "id"):
            if data.get(key):
                return int(data[key])

    found = client.post(
        "/ivr/findPage",
        {"query": {"searchName": name}, "page": {"current": 1, "size": 20}},
    )
    Client.assert_ok(found, "find created ivr")
    records = (
        found.get("data", {}).get("records")
        or found.get("data", {}).get("list")
        or found.get("data", {}).get("rows")
        or []
    )
    for record in records:
        if record.get("name") == name:
            return int(record["id"])
    raise RuntimeError("Could not resolve new IVR id")


def normalize_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def looks_like_backend_route_row(row):
    if not isinstance(row, dict):
        return False
    if any(key in row for key in ("value", "label", "digitSequence")):
        return False
    if len(row) != 1:
        return False
    key = next(iter(row.keys()))
    value = row.get(key)
    return bool(re.fullmatch(r"-?\d+", str(key))) and (value == "" or isinstance(value, str))


def frontend_intent_list_issues(container, path: str):
    rows = container.get("intentList") if isinstance(container, dict) else None
    if rows is None:
        return []
    if not isinstance(rows, list):
        return [f"{path}.intentList is {type(rows).__name__}, expected list"]

    issues = []
    for index, row in enumerate(rows):
        row_path = f"{path}.intentList[{index}]"
        if not isinstance(row, dict):
            issues.append(f"{row_path} is {type(row).__name__}, expected object")
            continue
        if looks_like_backend_route_row(row):
            issues.append(f"{row_path} uses backend route format; frontend requires value/label/digitSequence")
            continue
        for key in ("value", "label", "digitSequence"):
            if key not in row:
                issues.append(f"{row_path} missing {key}")
    return issues


def validate_frontend_intent_lists(scene_front, phase: str):
    issues = []
    for scene_index, scene in enumerate(scene_front or []):
        for node_index, node in enumerate(scene.get("nodeList") or []):
            node_name = node.get("name") or node.get("id") or node_index
            issues.extend(frontend_intent_list_issues(node, f"{phase}.scene[{scene_index}].node[{node_name}]"))
        for cell in (scene.get("graph") or {}).get("cells") or []:
            custom = (cell.get("data") or {}).get("customData") or {}
            cell_name = custom.get("name") or cell.get("id") or "unknown"
            issues.extend(frontend_intent_list_issues(custom, f"{phase}.scene[{scene_index}].graphCell[{cell_name}].customData"))
    if issues:
        raise RuntimeError("frontend intentList save-safety invalid: " + "; ".join(issues[:12]))


def positive_numeric_intent_id(value):
    text = str(value or "").strip()
    return text if re.fullmatch(r"\d+", text) and int(text) > 0 else None


def read_ivr_intent_catalog(client: Client, ivr_id: int):
    response = client.get(f"/ivrIntent/findList/{ivr_id}")
    Client.assert_ok(response, f"read IVR {ivr_id} intent catalog")
    catalog = {
        str(item.get("id")): str(item.get("name") or "")
        for item in response.get("data") or []
        if item.get("id") is not None and positive_numeric_intent_id(item.get("id"))
    }
    return catalog


def intent_ownership_issues(scene_list, scene_front, intent_catalog, phase: str):
    allowed = set(intent_catalog)
    issues = []

    def check_value(value, path):
        intent_id = positive_numeric_intent_id(value)
        if intent_id and intent_id not in allowed:
            issues.append(f"{path} references foreign intent id {intent_id}")

    def check_backend_node(node, path):
        for index, row in enumerate(node.get("intentList") or []):
            if not isinstance(row, dict) or "value" in row:
                continue
            for key in row:
                check_value(key, f"{path}.intentList[{index}]")
        for index, value in enumerate(node.get("interruptedIntentList") or []):
            check_value(value, f"{path}.interruptedIntentList[{index}]")

    def check_frontend_container(container, path):
        for index, row in enumerate(container.get("intentList") or []):
            if isinstance(row, dict):
                check_value(row.get("value"), f"{path}.intentList[{index}].value")
        for index, value in enumerate(container.get("interruptedIntentList") or []):
            check_value(value, f"{path}.interruptedIntentList[{index}]")

    for scene_index, scene in enumerate(scene_list or []):
        for node_index, node in enumerate(scene.get("nodeList") or []):
            node_name = node.get("name") or node.get("id") or node_index
            check_backend_node(node, f"{phase}.sceneList[{scene_index}].node[{node_name}]")

    for scene_index, scene in enumerate(scene_front or []):
        for node_index, node in enumerate(scene.get("nodeList") or []):
            node_name = node.get("name") or node.get("id") or node_index
            check_frontend_container(node, f"{phase}.sceneListFrontend[{scene_index}].node[{node_name}]")
        for cell in (scene.get("graph") or {}).get("cells") or []:
            custom = (cell.get("data") or {}).get("customData") or {}
            if not isinstance(custom, dict):
                continue
            cell_name = custom.get("name") or cell.get("id") or "unknown"
            check_frontend_container(custom, f"{phase}.graphCell[{cell_name}].customData")
    return issues


def validate_intent_ownership(scene_list, scene_front, intent_catalog, phase: str):
    issues = intent_ownership_issues(scene_list, scene_front, intent_catalog, phase)
    if issues:
        raise RuntimeError("current-IVR intent ownership invalid: " + "; ".join(issues[:12]))


def remap_cloned_intent_references(scene_list, scene_front, source_catalog, target_catalog):
    target_ids_by_name = {}
    for target_id, name in target_catalog.items():
        target_ids_by_name.setdefault(name, []).append(target_id)

    mapping = {}
    for source_id, name in source_catalog.items():
        matches = target_ids_by_name.get(name) or []
        if len(matches) == 1:
            mapping[source_id] = matches[0]

    def remap_value(value):
        text = str(value or "")
        if text in source_catalog and text not in mapping:
            name = source_catalog.get(text) or "<unnamed>"
            raise RuntimeError(
                f"cannot remap source intent id {text} ({name}) to one unique target intent with the same name"
            )
        return mapping.get(text, value)

    def remap_backend_node(node):
        rows = []
        for row in node.get("intentList") or []:
            if not isinstance(row, dict) or "value" in row:
                rows.append(row)
                continue
            rows.append({str(remap_value(key)): target for key, target in row.items()})
        if "intentList" in node:
            node["intentList"] = rows
        if "interruptedIntentList" in node:
            node["interruptedIntentList"] = [remap_value(value) for value in node.get("interruptedIntentList") or []]

    def remap_frontend_container(container):
        for row in container.get("intentList") or []:
            if isinstance(row, dict) and row.get("value") is not None:
                row["value"] = str(remap_value(row.get("value")))
        if "interruptedIntentList" in container:
            container["interruptedIntentList"] = [remap_value(value) for value in container.get("interruptedIntentList") or []]

    for scene in scene_list or []:
        for node in scene.get("nodeList") or []:
            remap_backend_node(node)

    for scene in scene_front or []:
        for node in scene.get("nodeList") or []:
            remap_frontend_container(node)
        for cell in (scene.get("graph") or {}).get("cells") or []:
            data = cell.get("data") or {}
            custom = data.get("customData") or {}
            if isinstance(custom, dict):
                remap_frontend_container(custom)
            for row in data.get("ports") or [] if isinstance(data.get("ports"), list) else []:
                if isinstance(row, dict) and row.get("value") is not None:
                    row["value"] = str(remap_value(row.get("value")))
            for item in (cell.get("ports") or {}).get("items") or []:
                if isinstance(item, dict) and item.get("id") is not None:
                    item["id"] = str(remap_value(item.get("id")))
            source = cell.get("source") or {}
            if isinstance(source, dict) and source.get("port") is not None:
                source["port"] = str(remap_value(source.get("port")))
    return mapping


def model_display_name(model: dict) -> str:
    return (
        model.get("modelName")
        or model.get("name")
        or model.get("model")
        or model.get("displayName")
        or ""
    )


def find_default_model_name(model_response) -> str:
    for model in model_response.get("data") or []:
        if normalize_int(model.get("id")) == DEFAULT_SMART_AGENT_MODEL_ID:
            return model_display_name(model)
    raise RuntimeError(
        f"Default smart-Agent model missing: "
        f"id={DEFAULT_SMART_AGENT_MODEL_ID} name={DEFAULT_SMART_AGENT_MODEL_NAME}"
    )


def update_smart_node(node, node_name: str, prompt: str):
    node["name"] = node_name
    config = node.setdefault("llmNodeModelConfig", {})
    config["id"] = DEFAULT_SMART_AGENT_MODEL_ID
    config["prompt"] = prompt
    config["enableThinking"] = 0
    config["enable_thinking"] = 0


def update_smart_cell(cell, node_name: str, prompt: str, description: str):
    data = cell.setdefault("data", {})
    data["label"] = node_name
    data["title"] = node_name
    if description:
        data["description"] = description
    custom = data.setdefault("customData", {})
    custom["name"] = node_name
    config = custom.setdefault("llmNodeModelConfig", {})
    config["id"] = DEFAULT_SMART_AGENT_MODEL_ID
    config["prompt"] = prompt
    config["enableThinking"] = 0
    config["enable_thinking"] = 0


def apply_prompt(scene_list, scene_front, prompt: str, scene_name: str, node_name: str):
    scene = scene_list[0]
    front_scene = scene_front[0]
    scene["name"] = scene_name
    front_scene["name"] = scene_name

    backend_smart = first_smart_node(scene["nodeList"])
    frontend_smart = first_smart_node(front_scene["nodeList"])
    smart_cell = first_smart_graph_cell(front_scene["graph"]["cells"])

    update_smart_node(backend_smart, node_name, prompt)
    update_smart_node(frontend_smart, node_name, prompt)
    update_smart_cell(smart_cell, node_name, prompt, backend_smart.get("text") or "")


def write_scene(client: Client, ivr_id: int, scene_list, scene_front, intent_catalog):
    validate_frontend_intent_lists(scene_front, "pre_write")
    validate_intent_ownership(scene_list, scene_front, intent_catalog, "pre_write")
    return client.post(
        "/ivr/updateSceneList",
        {
            "ivrId": ivr_id,
            "sceneList": json.dumps(scene_list, ensure_ascii=False, separators=(",", ":")),
            "sceneListFrontend": json.dumps(scene_front, ensure_ascii=False, separators=(",", ":")),
        },
    )


def collect_port_labels(cell):
    labels = []
    data = cell.get("data", {})
    custom = data.get("customData") or {}
    for item in custom.get("intentList") or []:
        label = item.get("label") or item.get("name")
        if label:
            labels.append(label)
    ports = data.get("ports") or {}
    for group in ports.values() if isinstance(ports, dict) else []:
        for item in group.get("items") or []:
            name = item.get("name")
            if name and name not in labels:
                labels.append(name)
    return labels


def try_delete(client: Client, ivr_id: int):
    attempts = [
        {"id": ivr_id},
        {"ivrId": ivr_id},
        {"ids": [ivr_id]},
        [ivr_id],
    ]
    last = None
    for body in attempts:
        try:
            response = client.post("/ivr/delete", body)
            last = response
            if str(response.get("code")) == "0":
                return {"status": "deleted", "payload": body}
        except Exception as exc:
            last = {"error": str(exc), "payload": body}
    return {"status": "not_confirmed", "last": last}


def assert_model_readback(model_ids):
    bad = {
        key: value
        for key, value in model_ids.items()
        if normalize_int(value) != DEFAULT_SMART_AGENT_MODEL_ID
    }
    if bad:
        raise RuntimeError(
            f"smart-Agent model readback mismatch; expected "
            f"{DEFAULT_SMART_AGENT_MODEL_NAME} id={DEFAULT_SMART_AGENT_MODEL_ID}, "
            f"got={bad}"
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--token", required=True)
    parser.add_argument("--backend-region", choices=["auto", "domestic", "overseas"], default="auto")
    parser.add_argument("--backend-url", default="", help="Optional page/API URL hint such as https://ai.tbot360.com/script-graph?ivrId=...")
    parser.add_argument("--prompt-path", required=True)
    parser.add_argument("--template-ivr-id", type=int, default=3449)
    parser.add_argument("--cleanup-ivr-id", type=int)
    args = parser.parse_args()

    backend = resolve_backend(args.token, args.backend_region, args.backend_url)
    client = Client(backend["token"], backend)
    prompt_path = Path(args.prompt_path)
    if not prompt_path.exists():
        raise FileNotFoundError(prompt_path)

    info = {"code": backend["accountInfo"].get("code"), "data": backend["accountInfo"].get("data") or {}}
    Client.assert_ok(info, "validate token")
    Client.assert_ok(client.get("/industry/findList"), "read industries")
    Client.assert_ok(client.get("/ivr/findAllTtsVoiceBaseInfo"), "read tts voices")
    model_response = client.get("/ivr/findModelList")
    Client.assert_ok(model_response, "read models")
    default_model_name = find_default_model_name(model_response)

    raw_prompt = prompt_path.read_text(encoding="utf-8")
    compacted_prompt = compact_prompt(raw_prompt)
    prompt = raw_prompt if len(raw_prompt) < RAW_PROMPT_CHAR_LIMIT else compacted_prompt
    prompt_strategy = "raw" if prompt == raw_prompt else "compact"
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()

    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    new_name = f"豆神AI Voice Agent_真人经验蒸馏版_intent配置版_{stamp}"
    scene_name = "豆神AI Voice Agent 真人经验蒸馏版主流程"
    node_name = "豆神智能Agent"

    created = client.post(
        "/ivr/insert",
        {
            "voiceType": 1,
            "ttsVoiceId": 1,
            "speechRate": 1,
            "name": new_name,
            "industryId": 42,
        },
    )
    Client.assert_ok(created, "create ivr")
    new_ivr_id = resolve_new_ivr_id(created, client, new_name)

    template = client.get(f"/ivr/findSceneList/{args.template_ivr_id}")
    Client.assert_ok(template, "read template scene")
    source_intent_catalog = read_ivr_intent_catalog(client, args.template_ivr_id)
    target_intent_catalog = read_ivr_intent_catalog(client, new_ivr_id)

    backup_dir = Path.cwd() / "管理后台CLI" / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    template_backup = backup_dir / f"ivr-{args.template_ivr_id}-template-for-real-prompt-{stamp}.json"
    template_backup.write_text(json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8")

    template_scene_list = parse_json_maybe(template["data"]["sceneList"])
    template_scene_front = parse_json_maybe(template["data"]["sceneListFrontend"])
    validate_intent_ownership(
        template_scene_list,
        template_scene_front,
        source_intent_catalog,
        "source_template",
    )
    scene_list = copy.deepcopy(template_scene_list)
    scene_front = copy.deepcopy(template_scene_front)
    intent_id_mapping = remap_cloned_intent_references(
        scene_list,
        scene_front,
        source_intent_catalog,
        target_intent_catalog,
    )
    apply_prompt(scene_list, scene_front, prompt, scene_name, node_name)

    update = write_scene(client, new_ivr_id, scene_list, scene_front, target_intent_catalog)
    if str(update.get("code")) != "0" and prompt_strategy == "raw":
        scene_list = copy.deepcopy(template_scene_list)
        scene_front = copy.deepcopy(template_scene_front)
        intent_id_mapping = remap_cloned_intent_references(
            scene_list,
            scene_front,
            source_intent_catalog,
            target_intent_catalog,
        )
        prompt = compacted_prompt
        prompt_strategy = "compact_after_raw_write_failure"
        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        apply_prompt(scene_list, scene_front, prompt, scene_name, node_name)
        update = write_scene(client, new_ivr_id, scene_list, scene_front, target_intent_catalog)
    Client.assert_ok(update, "write scene list")

    readback = client.get(f"/ivr/findSceneList/{new_ivr_id}")
    Client.assert_ok(readback, "read back new scene")
    final_backup = backup_dir / f"ivr-{new_ivr_id}-after-real-prompt-import-{stamp}.json"
    final_backup.write_text(json.dumps(readback, ensure_ascii=False, indent=2), encoding="utf-8")

    rb_scene_list = parse_json_maybe(readback["data"]["sceneList"])
    rb_front = parse_json_maybe(readback["data"]["sceneListFrontend"])
    validate_frontend_intent_lists(rb_front, "readback")
    target_intent_catalog = read_ivr_intent_catalog(client, new_ivr_id)
    validate_intent_ownership(rb_scene_list, rb_front, target_intent_catalog, "readback")
    rb_scene = rb_scene_list[0]
    rb_front_scene = rb_front[0]
    rb_backend = first_smart_node(rb_scene["nodeList"])
    rb_frontend = first_smart_node(rb_front_scene["nodeList"])
    rb_cell = first_smart_graph_cell(rb_front_scene["graph"]["cells"])

    backend_prompt = rb_backend["llmNodeModelConfig"]["prompt"]
    frontend_prompt = rb_frontend["llmNodeModelConfig"]["prompt"]
    graph_prompt = rb_cell["data"]["customData"]["llmNodeModelConfig"]["prompt"]
    model_ids = {
        "backend": rb_backend["llmNodeModelConfig"].get("id"),
        "frontend": rb_frontend["llmNodeModelConfig"].get("id"),
        "graph": rb_cell["data"]["customData"]["llmNodeModelConfig"].get("id"),
    }
    assert_model_readback(model_ids)

    cleanup = None
    if args.cleanup_ivr_id:
        cleanup = try_delete(client, args.cleanup_ivr_id)

    terminal_nodes = [
        {"id": node.get("id"), "name": node.get("name"), "nextType": node.get("nextType")}
        for node in rb_scene.get("nodeList", [])
        if int(node.get("type", -1)) == 2
    ]

    result = {
        "ok": True,
        "ivrId": new_ivr_id,
        "name": new_name,
        "sceneName": rb_scene.get("name"),
        "smartNodeName": rb_backend.get("name"),
        "promptRawChars": len(raw_prompt),
        "promptWrittenChars": len(prompt),
        "promptCompactedChars": len(compacted_prompt),
        "promptStrategy": prompt_strategy,
        "promptSha256": prompt_hash,
        "expectedModelId": DEFAULT_SMART_AGENT_MODEL_ID,
        "expectedModelName": DEFAULT_SMART_AGENT_MODEL_NAME,
        "modelNameFromCatalog": default_model_name,
        "modelIds": model_ids,
        "modelIdMatches": True,
        "frontendIntentListSaveSafe": True,
        "intentOwnershipSafe": True,
        "targetIntentCount": len(target_intent_catalog),
        "remappedIntentCount": len(intent_id_mapping),
        "backendPromptMatches": backend_prompt == prompt,
        "frontendPromptMatches": frontend_prompt == prompt,
        "graphPromptMatches": graph_prompt == prompt,
        "portLabels": collect_port_labels(rb_cell),
        "terminalNodes": terminal_nodes,
        "templateBackupPath": str(template_backup),
        "finalBackupPath": str(final_backup),
        "cleanup": cleanup,
        "backendRegion": backend["region"],
        "apiBase": backend["apiBase"],
        "url": f"{backend['webBase']}/script-graph?ivrId={new_ivr_id}",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
