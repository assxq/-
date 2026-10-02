"""YouTube Data API v3 upload + stats. Auth once (browser) with `python -m shorts_pipeline.cli auth` on a machine that has a browser,
then copy token.json next to client_secret.json."""
from __future__ import annotations
import csv, time
from pathlib import Path
from . import store

SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.readonly"]


def service(root: Path = store.ROOT):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    tok = root / "token.json"
    creds = Credentials.from_authorized_user_file(tok, SCOPES) if tok.exists() else None
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(root / "client_secret.json", SCOPES)
        creds = flow.run_local_server(port=0)
    tok.write_text(creds.to_json())
    return build("youtube", "v3", credentials=creds)


def body(script: dict, cfg: dict, publish_at: str | None = None) -> dict:
    ch = cfg["channel"]
    desc = script["description"] + "\n\n" + (script.get("disclaimer") or "") + "\n" + ch.get("affiliate_disclosure", "") + "\n#Shorts"
    status = {"privacyStatus": cfg["upload"]["privacy"], "selfDeclaredMadeForKids": False,
              "containsSyntheticMedia": bool(cfg["upload"].get("contains_synthetic_media", False))}
    if publish_at:
        status.update(privacyStatus="private", publishAt=publish_at)   # RFC3339; YouTube requires private + publishAt
    return {"snippet": {"title": script["title"][:95], "description": desc.strip(), "tags": script["tags"],
                        "categoryId": cfg["upload"]["category_id"], "defaultLanguage": ch.get("language", "en")},
            "status": status}


def upload(d: Path, cfg: dict, publish_at: str | None = None) -> str:
    from googleapiclient.http import MediaFileUpload
    script = store.read_json(d / "script.json")
    yt = service()
    req = yt.videos().insert(part="snippet,status", body=body(script, cfg, publish_at),
                             media_body=MediaFileUpload(str(d / "final.mp4"), chunksize=-1, resumable=True))
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    store.write_json(d / "upload.json", {"video_id": resp["id"], "at": time.time(), "publish_at": publish_at})
    return resp["id"]


def uploaded_today(work: Path = store.WORK) -> int:
    cutoff = time.time() - 86400
    return sum(1 for d in store.episodes(work) if (d / "upload.json").exists()
               and store.read_json(d / "upload.json")["at"] > cutoff)


def fetch_stats(root: Path = store.ROOT) -> list[dict]:
    ids = {store.read_json(d / "upload.json")["video_id"]: d.name for d in store.episodes() if (d / "upload.json").exists()}
    if not ids:
        return []
    yt, rows = service(), []
    for i in range(0, len(ids), 50):
        batch = list(ids)[i:i + 50]
        r = yt.videos().list(part="statistics", id=",".join(batch)).execute()
        for it in r["items"]:
            s = it["statistics"]
            rows.append({"ts": int(time.time()), "episode": ids[it["id"]], "video_id": it["id"],
                         "views": s.get("viewCount", 0), "likes": s.get("likeCount", 0), "comments": s.get("commentCount", 0)})
    path = root / "stats.csv"
    new = not path.exists()
    with path.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        if new:
            w.writeheader()
        w.writerows(rows)
    return rows
