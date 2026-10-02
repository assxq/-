"""Topic collection: manual file first, then Hacker News (Algolia) as an auto source. Deduplicated against past episodes."""
from __future__ import annotations
import json, urllib.parse, urllib.request
from pathlib import Path
from . import store


def from_file(path: Path) -> list[tuple[str, str]]:
    if not path.exists():
        return []
    return [(l.strip(), "manual") for l in path.read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.startswith("#")]


def from_hn(queries: list[str], limit: int = 10) -> list[tuple[str, str]]:
    out = []
    for q in queries:
        url = "https://hn.algolia.com/api/v1/search_by_date?tags=story&hitsPerPage=%d&query=%s" % (
            limit, urllib.parse.quote(q))
        try:
            with urllib.request.urlopen(url, timeout=15) as r:
                hits = json.load(r)["hits"]
        except Exception as e:  # network is best-effort
            print(f"[topics] HN query {q!r} failed: {e}")
            continue
        out += [(h["title"], "hn:" + (h.get("url") or "")) for h in hits if h.get("title")]
    return out


def collect(cfg: dict, root: Path = store.ROOT) -> list[tuple[str, str]]:
    t = cfg["topics"]
    cands = from_file(root / t.get("manual_file", "topics.txt")) + from_hn(t.get("hn_queries", []))
    seen = {store.slug(read["topic"]) for read in
            (store.read_json(d / "state.json") for d in store.episodes())}
    uniq, out = set(seen), []
    for title, src in cands:
        k = store.slug(title)
        if k not in uniq:
            uniq.add(k)
            out.append((title, src))
    return out[: t.get("per_run", 5)]
