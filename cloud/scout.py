#!/usr/bin/env python3
"""Agent HERMES cloud: collecte vérifiable de ressources publiques; aucune fausse compétence ni revenu."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import json, os, time

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "site" / "state.json"
JOURNAL = ROOT / "site" / "missions.json"
NOW = datetime.now(timezone.utc)
TOKEN = os.environ.get("GH_TOKEN", "")
MAX_NODES = 1500
SEARCHES = [
    ("github", "autonomous ai agent orchestration in:name,description"),
    ("github", "llm multi agent tools in:name,description"),
    ("github", "ai automation workflow in:name,description"),
    ("github", "business agents crm in:name,description"),
    ("models", "agent"),
    ("datasets", "agent"),
    ("spaces", "agent"),
]

def get_json(url, authenticated=False):
    headers = {"User-Agent":"Hermes-Galaxie-Cloud/1.0 (+public discovery)",
               "Accept":"application/vnd.github+json" if authenticated else "application/json"}
    if authenticated and TOKEN:
        headers["Authorization"] = "Bearer " + TOKEN
        headers["X-GitHub-Api-Version"] = "2022-11-28"
    req = Request(url, headers=headers)
    with urlopen(req, timeout=18) as resp:
        raw = resp.read(1_800_000)
    return json.loads(raw)

def valid_url(url):
    try:
        parsed = urlparse(url)
        return parsed.scheme=="https" and parsed.hostname in ("github.com","huggingface.co") and not parsed.username
    except (ValueError,AttributeError):
        return False

def clean(value, limit=140):
    return " ".join(str(value or "").split())[:limit]

def prepare_node(cat, name, url, old=None):
    if not valid_url(url) or not name:
        return None
    return {"id":cat+":"+name, "category":cat, "name":clean(name),
            "url":url, "firstSeen":old.get("firstSeen") if isinstance(old, dict) and old.get("firstSeen") else NOW.isoformat(timespec="seconds")}

def main():
    old=json.loads(STATE.read_text(encoding="utf-8"))
    if not isinstance(old.get("nodes"),list): raise RuntimeError("État invalide: nodes absents")
    records={n["id"]:n for n in old["nodes"] if isinstance(n,dict) and n.get("id") and valid_url(n.get("url",""))}
    base_count=len(records)
    counts={cat:0 for cat in ("github","models","datasets","spaces")}
    failures=[]
    for category, term in SEARCHES:
        try:
            if category=="github":
                url="https://api.github.com/search/repositories?q="+quote(term)+"&sort=updated&order=desc&per_page=12"
                items=get_json(url,True).get("items",[])
                pairs=((clean(x.get("full_name")),x.get("html_url")) for x in items if not x.get("private") and not x.get("archived"))
            else:
                endpoint={"models":"models","datasets":"datasets","spaces":"spaces"}[category]
                url="https://huggingface.co/api/"+endpoint+"?search="+quote(term)+"&limit=20"
                items=get_json(url)
                pairs=((clean(x.get("id") or x.get("modelId")), "https://huggingface.co/"+ ("spaces/" if category=="spaces" else "datasets/" if category=="datasets" else "") + str(x.get("id") or x.get("modelId") or "")) for x in items if isinstance(x,dict))
            for name,resource in pairs:
                if not name or not resource: continue
                key=category+":"+name
                if key not in records and len(records)<MAX_NODES:
                    n=prepare_node(category,name,resource)
                    if n: records[key]=n; counts[category]+=1
        except (HTTPError,URLError,TimeoutError,ValueError,KeyError,TypeError) as e:
            failures.append(category+": "+type(e).__name__+" "+clean(getattr(e,"code",""),16))
        time.sleep(.18)
    all_nodes=sorted(records.values(),key=lambda n:(n["category"],n["name"].casefold()))
    catcounts={cat:sum(n["category"]==cat for n in all_nodes) for cat in ("github","models","datasets","spaces")}
    history=[x for x in old.get("history",[]) if isinstance(x,dict) and "date" in x][-400:]
    measure={"date":NOW.isoformat(timespec="seconds"),"resources":len(all_nodes),
             "verified":int(old.get("verifiedSkills",0)), "profit":float(old.get("netProfitEuro",0))}
    history.append(measure)
    latest_prior=None
    for x in history[:-1]:
        try:
            stamp=datetime.fromisoformat(x["date"].replace("Z","+00:00"))
            if stamp.tzinfo is None:stamp=stamp.replace(tzinfo=timezone.utc)
            if stamp <= NOW-timedelta(hours=24):latest_prior=x
        except (ValueError,TypeError):pass
    delta=max(0,len(all_nodes)-int(latest_prior["resources"])) if latest_prior else None
    old.update({
        "name":"HERMES — GALAXIE VIVANTE",
        "asOf":NOW.isoformat(timespec="seconds"),"polledAt":NOW.isoformat(timespec="seconds"),
        "resourceCount":len(all_nodes),"categoryCounts":catcounts,
        "nodes":all_nodes,"history":history[-400:],"growth24h":delta,
        "disclaimer":"Ressources publiques réellement référencées. Aucun point ne prouve une compétence, un bénéfice ou une action commerciale.",
        "cloud":{"agent":"Éclaireur HERMES","execution":"GitHub Actions","lastMissionAt":NOW.isoformat(timespec="seconds"),
                 "missionStatus":"succès" if not failures else "partiel",
                 "newResources":len(all_nodes)-base_count,"errors":len(failures),
                 "nextScheduled":"Chaque heure, sous réserve de disponibilité GitHub Actions",
                 "machineIndependence":True}
    })
    STATE.write_text(json.dumps(old,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    log=[]
    if JOURNAL.exists():
        try:log=json.loads(JOURNAL.read_text(encoding="utf-8")).get("runs",[])
        except (json.JSONDecodeError,OSError):pass
    log.append({"date":NOW.isoformat(timespec="seconds"),"mission":"Recherche et dédoublonnage de ressources publiques",
                "sourcesSearched":len(SEARCHES),"newResources":len(all_nodes)-base_count,
                "total":len(all_nodes),"errors":failures})
    JOURNAL.write_text(json.dumps({"runs":log[-200:]},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"at":NOW.isoformat(),"previous":base_count,"current":len(all_nodes),
                      "new":len(all_nodes)-base_count,"failures":failures},ensure_ascii=False))
    if failures and len(failures)==len(SEARCHES):
        raise RuntimeError("Toutes les sources distantes ont échoué : données sauvegardées, mission en erreur")

if __name__=="__main__":
    main()