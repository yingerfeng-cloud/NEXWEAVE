"""Stage D actual HTTP checks on existing explicitly synthetic records."""

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import httpx
from verify_m95 import _login

ROOT = Path(__file__).resolve().parents[1]


def main():
    state = json.loads((ROOT / ".nexweave-data/stage-c-e2e.json").read_text())
    reference = json.loads((ROOT / ".nexweave-data/stage-c-reference.json").read_text())
    with httpx.Client(
        base_url="http://127.0.0.1:8080/api/v1", trust_env=False, timeout=60
    ) as client:
        api = _login(client, "local-admin")
        release = state["context"]["release_id"]
        path = f"/releases/{release}/queries"
        body = {
            "question": "lubrication vibration",
            "strategy": "HYBRID",
            "top_k": 5,
            "filters": {},
            "client_request_id": "stage-d-" + uuid4().hex,
        }
        answer = api.request("POST", path, json=body).json()
        assert answer["status"] == "COMPLETED" and answer["citations"]
        assert all(h["object_type"] == "CLAIM" for h in answer["retrieval_hits"])
        replay = api.request("POST", path, json=body).json()
        assert replay["id"] == answer["id"] and replay["read_checked_at"]
        for patch in [
            {"question": "different"},
            {"strategy": "KEYWORD"},
            {"top_k": 3},
            {"filters": {"different": True}},
        ]:
            api.request("POST", path, expected=409, json={**body, **patch})
        api.request(
            "POST", f"/releases/{state['second_release_id']}/queries", expected=409, json=body
        )
        old_id = "01a084fc-bab4-7275-ac7a-4001ee2a2de7"
        old = api.request("GET", f"/query-answers/{old_id}").json()
        assert old["status"] == "REFUSED" and not old["citations"] and old["read_filtered"]
        assert not old["key_basis"] and not old["conflicts"]
        graph_path = f"/releases/{release}/graph/traverse"
        entity = reference["claim"]["subject_entity_id"]
        graph = api.request("GET", graph_path, params={"start_entity_id": entity}).json()
        assert graph["nodes"][0]["id"] == entity
        for params in [
            {"start_entity_id": str(uuid4())},
            {"start_entity_id": entity, "target_entity_id": str(uuid4())},
        ]:
            api.request("GET", graph_path, expected=404, params=params)
        for date in ["not-a-date", "2026-09-09T00:00:00"]:
            api.request(
                "GET", graph_path, expected=422, params={"start_entity_id": entity, "as_of": date}
            )
        cpath = f"/forecast-artifacts/{state['artifact_id']}/knowledge-context"
        context = api.request(
            "POST", cpath, json={"release_id": release, "question": body["question"]}
        ).json()
        assert (
            context["items"]
            and context["artifact_checksum"] == state["artifact_checksum_unchanged"]
        )
        runtime = api.request("GET", f"/spaces/{state['space_id']}/forecast-runtime").json()
        report = {
            "completed_at": datetime.now(UTC).isoformat(),
            "query_answer_id": answer["id"],
            "historical_answer_id": old_id,
            "historical_read_status": old["status"],
            "historical_read_filtered": True,
            "replay_conflicts": 5,
            "graph_member_node": entity,
            "graph_nonmember_denials": 2,
            "graph_date_rejections": 2,
            "stage_c_context": "PASSED",
            "runtime": runtime,
            "data_kind": "SYNTHETIC",
            "industrial_acceptance": False,
        }
        (ROOT / ".nexweave-data/stage-d-e2e.json").write_text(json.dumps(report, indent=2))
        print(json.dumps(report))


if __name__ == "__main__":
    main()
