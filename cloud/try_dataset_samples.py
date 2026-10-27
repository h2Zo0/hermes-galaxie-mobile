#!/usr/bin/env python3
"""Première réutilisation effective : consommer des échantillons de datasets publics.

Une ressource n'est approuvée que pour l'usage explicitement testé :
lecture de quelques lignes et extraction du schéma, jamais entraînement ni usage
commercial implicite. Les échantillons ne sont PAS enregistrés, uniquement leur
empreinte et la liste des champs.
"""
from __future__ import annotations
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import json
import re

from cloud.verify_capabilities import valid_existing_skills

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "site" / "state.json"
PROOF = ROOT / "site" / "evidence" / "hf-dataset-sample-ingestion-v1.json"
SKILL_ID = "hf-dataset-sample-ingestion-v1"
SKILL_TITLE = "Lire et contrôler des échantillons de datasets publics"
NOW = datetime.now(timezone.utc).isoformat(timespec="seconds")
DATASET = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
MAX_TRIES = 20
SCOPE = "Lecture API d'échantillons, contrôles de schéma en environnement isolé; ni entraînement de modèle ni réutilisation commerciale garantie"


def get_api(endpoint, params):
    if endpoint not in ("splits", "rows"):
        raise ValueError("Endpoint non autorisé")
    url = "https://datasets-server.huggingface.co/" + endpoint + "?" + urlencode(params)
    with urlopen(Request(url, headers={"User-Agent": "NOVENS-Data-Pilot/1.0",
                                       "Accept": "application/json"}), timeout=10) as response:
        raw = response.read(600001)
    if len(raw) > 600000:
        raise ValueError("Réponse trop volumineuse")
    return json.loads(raw)


def pilot(slug, fetch=get_api):
    if not DATASET.fullmatch(slug):
        raise ValueError("Identifiant invalide")
    splits = fetch("splits", {"dataset": slug})
    if not isinstance(splits, dict) or not isinstance(splits.get("splits"), list):
        raise ValueError("Pas de partition disponible")
    options = [x for x in splits["splits"]
               if isinstance(x, dict) and isinstance(x.get("config"), str)
               and isinstance(x.get("split"), str)
               and x.get("num_examples", 0) is not None
               and x.get("num_examples", 0) > 0]
    if not options:
        raise ValueError("Aucune partition accessible")
    item = options[0]
    rows = fetch("rows", {"dataset": slug, "config": item["config"],
                          "split": item["split"], "offset": 0, "length": 3})
    if not isinstance(rows, dict) or not isinstance(rows.get("rows"), list):
        raise ValueError("Réponse de lignes invalide")
    values = [x["row"] for x in rows["rows"]
              if isinstance(x, dict) and isinstance(x.get("row"), dict)]
    if not values:
        raise ValueError("Aucune ligne structurée reçue")
    columns = sorted({str(k) for row in values for k in row.keys()})
    if not columns or any(len(x) > 180 for x in columns):
        raise ValueError("Schéma de colonnes invalide")
    # Une expérience de transformation réelle, démontrant la lecture et la
    # normalisation du jeu de données. Aucun contenu n'est sauvegardé.
    normalized = json.dumps(values, ensure_ascii=False, sort_keys=True, default=str)
    digest = sha256(normalized.encode("utf-8")).hexdigest()
    return {
        "id": slug, "source": "https://huggingface.co/datasets/" + slug,
        "config": item["config"], "split": item["split"], "columns": columns[:100],
        "rowCount": len(values), "sampleSha256": digest, "observedAt": NOW,
        "approvedFor": "read-only-dataset-sampling", "limitations": SCOPE,
    }


def candidates(state):
    nodes = state.get("nodes", [])
    slugs = [n["name"] for n in nodes if isinstance(n, dict)
             and n.get("category") == "datasets"
             and isinstance(n.get("name"), str)
             and DATASET.fullmatch(n["name"])
             and n.get("url") == "https://huggingface.co/datasets/" + n["name"]]
    start = state.get("discovery", {}).get("cursor", 0)
    shift = max(0, int(start)) if isinstance(start, int) else 0
    if slugs:
        rotation = shift % len(slugs)
        return slugs[rotation:] + slugs[:rotation]
    return []


def run(state, fetch=get_api):
    existing = {s["id"]: s for s in valid_existing_skills(state.get("skills", []))}
    previous = existing.get(SKILL_ID)
    prior_reports = json.loads(PROOF.read_text(encoding="utf-8"))["reports"] if previous else []
    seen = {r["id"].casefold() for r in prior_reports}
    reports, failed = [], []
    attempted = 0
    for slug in candidates(state):
        if len(reports) >= 2 or attempted >= MAX_TRIES:
            break
        if slug.casefold() in seen:
            continue
        attempted += 1
        try:
            reports.append(pilot(slug, fetch))
        except (HTTPError, URLError, TimeoutError, ValueError, TypeError, KeyError, OSError) as error:
            failed.append({"id": slug, "error": type(error).__name__})
    combined = prior_reports + reports
    status = "failed" if not previous else "no-new-evidence"
    if len(combined) >= 2 and reports and len({r["id"] for r in combined}) == len(combined):
        proof = {
            "skillId": SKILL_ID, "title": SKILL_TITLE, "status": "validated",
            "testedAt": previous["validatedAt"] if previous else NOW,
            "lastPracticedAt": NOW, "method": "Datasets Server splits + rows; exercice réel de normalisation JSON",
            "challenge": "Lire effectivement 2 datasets, contrôler leurs schémas, calculer une empreinte sans conserver leurs données",
            "checksPassed": True, "reports": combined, "scope": SCOPE,
        }
        PROOF.parent.mkdir(parents=True, exist_ok=True)
        raw = (json.dumps(proof, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        PROOF.write_bytes(raw)
        existing[SKILL_ID] = {
            "id": SKILL_ID, "title": SKILL_TITLE, "status": "validated",
            "validatedAt": previous["validatedAt"] if previous else NOW,
            "lastPracticedAt": NOW, "practiceCount": len(combined),
            "proofPath": "evidence/" + PROOF.name,
            "proofSha256": sha256(raw).hexdigest(),
            "resourcesTested": [r["source"] for r in combined],
        }
        status = "reinforced" if previous else "validated"
    state["skills"] = list(existing.values())
    state["verifiedSkills"] = len(existing)
    trials = state.get("capabilityTrials", [])
    if not isinstance(trials, list):
        trials = []
    trials.append({
        "date": NOW, "skillId": SKILL_ID, "result": status,
        "reportsPassed": len(reports), "reportsRequired": 1 if previous else 2,
        "failedResources": failed, "totalVerifiedExercises": len(combined) if previous or len(reports) >= 2 else 0,
    })
    state["capabilityTrials"] = trials[-100:]
    # L'approbation ne porte QUE sur la capacité de lire l'échantillon.
    previous_approved = state.get("approvedResources", [])
    if not isinstance(previous_approved, list):
        previous_approved = []
    approved = {r["id"]: r for r in previous_approved if isinstance(r, dict) and r.get("id")}
    if status in ("validated", "reinforced"):
        for report in reports:
            approved[report["id"]] = {
                "id": report["id"], "source": report["source"],
                "approvedFor": "read-only-dataset-sampling",
                "proofPath": "evidence/" + PROOF.name,
                "testedAt": NOW,
            }
    state["approvedResources"] = list(approved.values())
    state["approvedResourceCount"] = len(approved)
    history = state.get("history")
    if isinstance(history, list) and history and isinstance(history[-1], dict):
        history[-1]["verified"] = len(existing)
    state["lastCapabilityVerification"] = {"date": NOW, "skillId": SKILL_ID, "result": status}
    return status


def main():
    state = json.loads(STATE.read_text(encoding="utf-8"))
    if not isinstance(state.get("nodes"), list):
        raise ValueError("Catalogue manquant")
    result = run(state)
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"dataPilot": result, "approvedResources": state["approvedResourceCount"],
                      "verifiedSkills": state["verifiedSkills"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
