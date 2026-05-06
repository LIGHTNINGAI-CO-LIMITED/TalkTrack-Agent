# -*- coding: utf-8 -*-
import argparse
import copy
import datetime as dt
import hashlib
import json
from pathlib import Path

import requests


BASE_URL = "https://ai.sd6g.com:1904/api/web"
RAW_PROMPT_CHAR_LIMIT = 10000


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
    def __init__(self, token: str):
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
        return self._json(self.session.get(f"{BASE_URL}{path}", timeout=60))

    def post(self, path: str, body):
        return self._json(self.session.post(f"{BASE_URL}{path}", json=body, timeout=60))


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


def update_smart_node(node, node_name: str, prompt: str):
    node["name"] = node_name
    config = node.setdefault("llmNodeModelConfig", {})
    config.setdefault("id", 55)
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
    config.setdefault("id", 55)
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


def write_scene(client: Client, ivr_id: int, scene_list, scene_front):
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--token", required=True)
    parser.add_argument("--prompt-path", required=True)
    parser.add_argument("--template-ivr-id", type=int, default=3449)
    parser.add_argument("--cleanup-ivr-id", type=int)
    args = parser.parse_args()

    client = Client(args.token)
    prompt_path = Path(args.prompt_path)
    if not prompt_path.exists():
        raise FileNotFoundError(prompt_path)

    info = client.get("/account/findInfo")
    Client.assert_ok(info, "validate token")
    Client.assert_ok(client.get("/industry/findList"), "read industries")
    Client.assert_ok(client.get("/ivr/findAllTtsVoiceBaseInfo"), "read tts voices")
    Client.assert_ok(client.get("/ivr/findModelList"), "read models")

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

    backup_dir = Path.cwd() / "管理后台CLI" / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    template_backup = backup_dir / f"ivr-{args.template_ivr_id}-template-for-real-prompt-{stamp}.json"
    template_backup.write_text(json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8")

    template_scene_list = parse_json_maybe(template["data"]["sceneList"])
    template_scene_front = parse_json_maybe(template["data"]["sceneListFrontend"])
    scene_list = copy.deepcopy(template_scene_list)
    scene_front = copy.deepcopy(template_scene_front)
    apply_prompt(scene_list, scene_front, prompt, scene_name, node_name)

    update = write_scene(client, new_ivr_id, scene_list, scene_front)
    if str(update.get("code")) != "0" and prompt_strategy == "raw":
        scene_list = copy.deepcopy(template_scene_list)
        scene_front = copy.deepcopy(template_scene_front)
        prompt = compacted_prompt
        prompt_strategy = "compact_after_raw_write_failure"
        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        apply_prompt(scene_list, scene_front, prompt, scene_name, node_name)
        update = write_scene(client, new_ivr_id, scene_list, scene_front)
    Client.assert_ok(update, "write scene list")

    readback = client.get(f"/ivr/findSceneList/{new_ivr_id}")
    Client.assert_ok(readback, "read back new scene")
    final_backup = backup_dir / f"ivr-{new_ivr_id}-after-real-prompt-import-{stamp}.json"
    final_backup.write_text(json.dumps(readback, ensure_ascii=False, indent=2), encoding="utf-8")

    rb_scene_list = parse_json_maybe(readback["data"]["sceneList"])
    rb_front = parse_json_maybe(readback["data"]["sceneListFrontend"])
    rb_scene = rb_scene_list[0]
    rb_front_scene = rb_front[0]
    rb_backend = first_smart_node(rb_scene["nodeList"])
    rb_frontend = first_smart_node(rb_front_scene["nodeList"])
    rb_cell = first_smart_graph_cell(rb_front_scene["graph"]["cells"])

    backend_prompt = rb_backend["llmNodeModelConfig"]["prompt"]
    frontend_prompt = rb_frontend["llmNodeModelConfig"]["prompt"]
    graph_prompt = rb_cell["data"]["customData"]["llmNodeModelConfig"]["prompt"]

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
        "backendPromptMatches": backend_prompt == prompt,
        "frontendPromptMatches": frontend_prompt == prompt,
        "graphPromptMatches": graph_prompt == prompt,
        "portLabels": collect_port_labels(rb_cell),
        "terminalNodes": terminal_nodes,
        "templateBackupPath": str(template_backup),
        "finalBackupPath": str(final_backup),
        "cleanup": cleanup,
        "url": f"https://ai.sd6g.com:1904/script-graph?ivrId={new_ivr_id}",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
