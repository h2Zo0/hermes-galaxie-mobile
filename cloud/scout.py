#!/usr/bin/env python3
"""NOVENS — éclaireur tournant et cumulatif, sans confondre découverte et savoir-faire."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import json
import os
import time

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "site" / "state.json"
JOURNAL = ROOT / "site" / "missions.json"
NOW = datetime.now(timezone.utc)
TOKEN = os.environ.get("GH_TOKEN", "")
MAX_NODES = 20000
# Diversité volontaire : compétences transversales, mais aussi projets à potentiel réel.
GITHUB_SEARCHES = [
    "agent orchestration llm in:name,description",
    "ai agent tools framework in:name,description",
    "model context protocol mcp servers in:name,description",
    "workflow automation self hosted in:name,description",
    "multi agent planning tools in:name,description",
    "agent memory vector retrieval in:name,description",
    "llm evaluation benchmark in:name,description",
    "ai software testing agents in:name,description",
    "business process automation in:name,description",
    "open source crm erp automation in:name,description",
    "invoice reconciliation bookkeeping in:name,description",
    "accounting anomaly detection in:name,description",
    "commercial vehicle parts catalog in:name,description",
    "vehicle fitment vin decoder in:name,description",
    "bus fleet maintenance in:name,description",
    "video editing automation subtitles in:name,description",
    "short video clipping transcription in:name,description",
    "social media scheduling automation in:name,description",
    "lead generation b2b open source in:name,description",
    "agent browser computer use in:name,description",
    "python automation libraries in:name,description",
    "open source payment integration in:name,description",
    "retrieval augmented generation rag in:name,description",
    "agent security sandbox evaluation in:name,description",
]
HUGGINGFACE_SEARCHES = {
    "models": ["agent", "embedding", "reranker", "text-classification", "translation", "speech", "transcription", "text-generation", "vision"],
    "datasets": ["agent", "document", "invoice", "accounting", "vehicle", "transcript", "french", "tool"],
    "spaces": ["agent", "automation", "ocr", "transcription", "video", "search", "rag", "document"],
}
SEARCH_BATCH = 4
HF_LIMIT = 50
GH_LIMIT = 50


def get_json(url, authenticated=False):
    headers = {
        "User-Agent": "NOVENS-Explorer/3.0 (+continuous-discovery)",
        "Accept": "application/vnd.github+json" if authenticated else "application/json",
    }
    if authenticated and TOKEN:
        headers["Authorization"] = "Bearer " + TOKEN
        headers["X-GitHub-Api-Version"] = "2022-11-28"
    request = Request(url, headers=headers)
    with urlopen(request, timeout=13) as response:
        return json.loads(response.read(3_000_000))


def valid_url(url):
    try:
        parsed = urlparse(url)
        return parsed.scheme == "https" and parsed.hostname in ("github.com", "huggingface.co") and not parsed.username
    except (ValueError, AttributeError, TypeError):
        return False


def clean(value, limit=160):
    return " ".join(str(value or "").split())[:limit]


def prepare_node(category, name, url, old=None):
    if not valid_url(url) or not name or not isinstance(name, str):
        return None
    return {
        "id": category + ":" + name, "category": category,
        "name": clean(name), "url": url,
        "firstSeen": old.get("firstSeen") if isinstance(old, dict) and old.get("firstSeen")
            else NOW.isoformat(timespec="seconds"),
    }


def plan(cursor):
    """La recherche change à chaque mission ; pages 1 à 5 tournantes."""
    index = int(cursor) if isinstance(cursor, int) and cursor >= 0 else 0
    searches = []
    for step in range(SEARCH_BATCH):
        sequence = index * SEARCH_BATCH + step
        term = GITHUB_SEARCHES[sequence % len(GITHUB_SEARCHES)]
        page = 1 + (sequence // len(GITHUB_SEARCHES)) % 5
        searches.append(("github", term, page))
    for category, terms in HUGGINGFACE_SEARCHES.items():
        searches.append((category, terms[index % len(terms)], 1))
    return searches


def collect(state, get=get_json):
    nodes = state.get("nodes")
    if not isinstance(nodes, list):
        raise RuntimeError("Catalogue invalide")
    records = {n["id"]: n for n in nodes
               if isinstance(n, dict) and n.get("id") and valid_url(n.get("url"))}
    start_count = len(records)
    previous = state.get("discovery", {})
    if not isinstance(previous, dict):
        previous = {}
    cursor = previous.get("cursor", 0)
    searches = plan(cursor)
    failures = []
    additions = {k: 0 for k in ("github", "models", "datasets", "spaces")}
    for category, term, page in searches:
        if len(records) >= MAX_NODES:
            break
        try:
            if category == "github":
                url = ("https://api.github.com/search/repositories?q=" + quote(term)
                       + "&sort=updated&order=desc&per_page=" + str(GH_LIMIT)
                       + "&page=" + str(page))
                response = get(url, True)
                items = response.get("items", [])
                pairs = ((entry.get("full_name"), entry.get("html_url")) for entry in items
                         if isinstance(entry, dict) and not entry.get("private") and not entry.get("archived"))
            else:
                url = ("https://huggingface.co/api/" + category
                       + "?search=" + quote(term) + "&limit=" + str(HF_LIMIT))
                response = get(url)
                prefix = {"models": "", "datasets": "datasets/", "spaces": "spaces/"}[category]
                pairs = ((entry.get("id") or entry.get("modelId"),
                          "https://huggingface.co/" + prefix + str(entry.get("id") or entry.get("modelId") or ""))
                         for entry in response if isinstance(entry, dict))
            for name, link in pairs:
                if not isinstance(name, str) or "/" not in name or not isinstance(link, str):
                    continue
                node = prepare_node(category, name, link)
                if node is None or node["id"] in records:
                    continue
                if len(records) >= MAX_NODES:
                    break
                records[node["id"]] = node
                additions[category] += 1
        except (HTTPError, URLError, TimeoutError, ValueError, KeyError, TypeError, OSError) as exc:
            failures.append({"source": category, "term": term, "error": type(exc).__name__,
                             "code": clean(getattr(exc, "code", ""), 12)})
        time.sleep(.12)
    all_nodes = sorted(records.values(), key=lambda item: (item["category"], item["name"].casefold()))
    category_counts = {
        category: sum(n["category"] == category for n in all_nodes)
        for category in ("github", "models", "datasets", "spaces")
    }
    history = [x for x in state.get("history", []) if isinstance(x, dict) and "date" in x][-399:]
    history.append({
        "date": NOW.isoformat(timespec="seconds"),
        "resources": len(all_nodes), "verified": int(state.get("verifiedSkills", 0)),
        "profit": float(state.get("netProfitEuro", 0)),
    })
    prior = None
    for measurement in history[:-1]:
        try:
            timestamp = datetime.fromisoformat(str(measurement["date"]).replace("Z", "+00:00"))
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            if timestamp <= NOW - timedelta(hours=24):
                prior = measurement
        except (ValueError, TypeError, KeyError):
            pass
    growth = max(0, len(all_nodes) - int(prior["resources"])) if prior else None
    state.update({
        "name": "NOVENS CORE — GALAXIE VIVANTE",
        "asOf": NOW.isoformat(timespec="seconds"),
        "polledAt": NOW.isoformat(timespec="seconds"),
        "resourceCount": len(all_nodes),
        "categoryCounts": category_counts,
        "nodes": all_nodes,
        "history": history,
        "growth24h": growth,
        "disclaimer": "Les découvertes ne sont pas des compétences. Chaque usage approuvé exige des tests indépendants.",
        "discovery": {
            "cursor": (int(cursor) if isinstance(cursor, int) and cursor >= 0 else 0) + 1,
            "capacity": MAX_NODES, "lastBatch": len(all_nodes) - start_count,
            "newByCategory": additions, "queriesLastRun": len(searches),
            "totalSearchCycles": int(previous.get("totalSearchCycles", 0)) + 1,
            "lastErrors": failures[-12:],
        },
        "cloud": {
            "agent": "Éclaireur NOVENS CORE", "execution": "GitHub Actions",
            "lastMissionAt": NOW.isoformat(timespec="seconds"),
            "missionStatus": "succès" if not failures else "partiel",
            "newResources": len(all_nodes) - start_count,
            "errors": len(failures), "nextScheduled": "Toutes les 10 minutes si GitHub Actions disponible",
            "machineIndependence": True,
        },
    })
    return {
        "at": NOW.isoformat(), "previous": start_count,
        "current": len(all_nodes), "new": len(all_nodes) - start_count,
        "byCategory": additions, "errors": failures, "queries": len(searches),
    }


def main():
    state = json.loads(STATE.read_text(encoding="utf-8"))
    result = collect(state)
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    old_runs = []
    if JOURNAL.exists():
        try:
            old_runs = json.loads(JOURNAL.read_text(encoding="utf-8")).get("runs", [])
        except (json.JSONDecodeError, OSError, TypeError):
            pass
    old_runs.append({
        "date": NOW.isoformat(timespec="seconds"),
        "mission": "Éclaireur tournant multithématique",
        "sourcesSearched": result["queries"],
        "newResources": result["new"],
        "total": result["current"],
        "errors": result["errors"],
    })
    JOURNAL.write_text(json.dumps({"runs": old_runs[-300:]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    if len(result["errors"]) == result["queries"]:
        raise RuntimeError("Toutes les recherches ont échoué")


if __name__ == "__main__":
    main()
