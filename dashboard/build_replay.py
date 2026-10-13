"""Paperclip에서 읽은 JSON 스냅샷으로 재생 전용 replay.html을 만든다.
사용: python3 build_replay.py <스냅샷 폴더> [출력 파일]
스냅샷 폴더에는 company/agents/issues/runs/comments(.json)가 있어야 한다."""
import json, sys, pathlib
src = pathlib.Path(sys.argv[1]); out = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else "replay.html")
here = pathlib.Path(__file__).parent
L = lambda n: json.load(open(src / n))
company, agents, issues, runs, comments = L("company.json"), L("agents.json"), L("issues.json"), L("runs.json"), L("comments.json")
goals = L("goals.json") if (src / "goals.json").exists() else []
data = {
  "company": {"name": company["name"], "budgetMonthlyCents": company["budgetMonthlyCents"]},
  "goalTitle": next((g["title"] for g in goals if g.get("level") == "company"), "체험"),
  "agents": [{"id": a["id"], "name": a["name"], "title": a.get("title"), "role": a.get("role"),
              "budgetMonthlyCents": a.get("budgetMonthlyCents", 0), "status": "idle",
              "reportsTo": a.get("reportsTo"), "createdAt": a.get("createdAt")} for a in agents],
  "issues": [{"id": i["id"], "identifier": i["identifier"], "title": i["title"], "assigneeAgentId": i.get("assigneeAgentId"),
              "createdAt": i["createdAt"], "completedAt": i.get("completedAt"), "issueNumber": i.get("issueNumber")} for i in issues],
  "runs": [{"agentId": r["agentId"], "issueId": (r.get("contextSnapshot") or {}).get("issueId"), "startedAt": r["startedAt"], "finishedAt": r["finishedAt"],
            "usageJson": {k: (r.get("usageJson") or {}).get(k) for k in ("costUsd", "inputTokens", "outputTokens")}} for r in runs],
  "comments": {k: [{"id": c["id"], "authorAgentId": c.get("authorAgentId"), "body": c["body"], "createdAt": c["createdAt"]} for c in v] for k, v in comments.items()},
}
html = (here / "index.html").read_text(encoding="utf8")
marker = "<script>\n/* ===== 캐릭터 정의"
assert marker in html
payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
out.write_text(html.replace(marker, "<script>window.__REPLAY__=" + payload + ";</script>\n" + marker, 1), encoding="utf8")
print(out, len(out.read_text(encoding="utf8")), "bytes")
