#!/usr/bin/env python3
"""NOVENS : missions de qualification sur de vraies ressources Hugging Face.

Une capacité est la réussite répétée d'une *tâche distincte*, et non le
nombre de liens répertoriés. Ne télécharge ni n'exécute les modèles/datasets.
L'échec, le manque de métadonnées ou un API hors ligne ne valide rien.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import json
import re

from cloud.verify_capabilities import valid_existing_skills

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "site/state.json"
NOW = datetime.now(timezone.utc).isoformat(timespec="seconds")
SLUG = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
ALLOWED_SDKS = {"gradio", "streamlit", "docker", "static"}
DATA_EXTS = (".parquet", ".csv", ".jsonl", ".json", ".arrow", ".tsv", ".txt", ".zip")
MAX_CANDIDATES = 18

MISSIONS = {
    "models": {
        "id": "hf-model-task-classification-v1",
        "title": "Classer des modèles IA par tâche et licence déclarée",
        "challenge": "Classer 2 modèles différents à partir de leur fiche API, avec tâche et licence déclarée vérifiées.",
        "method": "API Hugging Face models, pipeline_tag et cardData/tags; aucun chargement de poids ni inférence",
        "scope": "Qualification des métadonnées de modèles, pas exécution ni comparaison de performances.",
    },
    "datasets": {
        "id": "hf-dataset-usage-assessment-v1",
        "title": "Qualifier licence et format de jeux de données IA",
        "challenge": "Qualifier 2 jeux de données distincts, leur licence déclarée et au moins un format de fichier réellement inventorié.",
        "method": "API Hugging Face datasets, cardData/tags et siblings; aucune donnée confidentielle téléchargée",
        "scope": "Inventaire de formats et droits déclarés, pas audit juridique ni contrôle du contenu.",
    },
    "spaces": {
        "id": "hf-space-runtime-diagnostics-v1",
        "title": "Diagnostiquer le runtime de démonstrations IA",
        "challenge": "Diagnostiquer 2 Spaces distincts, leur SDK déclaré et leur stade d'exécution fourni par l'API.",
        "method": "API Hugging Face spaces, sdk/cardData et runtime.stage; état observé à un instant donné",
        "scope": "Diagnostic déclaratif du runtime, pas test d'interaction avec le produit ni garantie de disponibilité future.",
    },
}


def fetch_hf(category, slug):
    endpoints = {"models": "models", "datasets": "datasets", "spaces": "spaces"}
    if category not in endpoints or not SLUG.fullmatch(slug):
        raise ValueError("Catégorie ou identifiant HF invalide")
    encoded = "/".join(quote(part, safe="") for part in slug.split("/"))
    url = "https://huggingface.co/api/" + endpoints[category] + "/" + encoded
    req = Request(url, headers={"User-Agent": "NOVENS-Verified-Capabilities/2.0",
                                "Accept": "application/json"})
    with urlopen(req, timeout=12) as response:
        return json.loads(response.read(1_000_000))


def candidates(state, category, limit=None):
    prefixes = {
        "models": "https://huggingface.co/",
        "datasets": "https://huggingface.co/datasets/",
        "spaces": "https://huggingface.co/spaces/",
    }
    seen, slugs = set(), []
    for n in state.get("nodes", []):
        if not isinstance(n, dict) or n.get("category") != category:
            continue
        slug = n.get("name")
        if not isinstance(slug, str) or not SLUG.fullmatch(slug):
            continue
        # Une URL n'est jamais utilisée pour former la requête réseau : HTTPS fixe.
        if n.get("url") != prefixes[category] + slug or slug.lower() in seen:
            continue
        seen.add(slug.lower())
        slugs.append(slug)
    if not slugs:
        return
    cursor = state.get("discovery", {}).get("cursor", 0)
    step = max(0, cursor) * MAX_CANDIDATES if isinstance(cursor, int) else 0
    offset = step % len(slugs)
    ordered = slugs[offset:] + slugs[:offset]
    yield from ordered[:limit] if limit is not None else ordered


def declared_license(meta):
    card = meta.get("cardData")
    if isinstance(card, dict):
        license_value = card.get("license")
        if isinstance(license_value, str) and license_value.strip():
            return license_value.strip()[:80]
        if isinstance(license_value, list):
            values = [s for s in license_value if isinstance(s, str) and s.strip()]
            if values:
                return ", ".join(values[:3])[:80]
    tags = meta.get("tags")
    if isinstance(tags, list):
        for tag in tags:
            if isinstance(tag, str) and tag.startswith("license:") and tag[8:]:
                return tag[8:88]
    return None


def assess(category, slug, meta):
    if not SLUG.fullmatch(slug) or not isinstance(meta, dict):
        raise ValueError("Métadonnées invalides")
    identity = meta.get("id") or meta.get("modelId")
    if not isinstance(identity, str) or identity.casefold() != slug.casefold():
        raise ValueError("Identité API différente de la ressource")
    if meta.get("private") or meta.get("disabled"):
        raise ValueError("Ressource privée ou désactivée")
    report = {
        "id": slug,
        "source": ("https://huggingface.co/" +
                   ("datasets/" if category == "datasets" else "spaces/" if category == "spaces" else "") + slug),
        "observedAt": NOW,
    }
    license_name = declared_license(meta)
    if category == "models":
        task = meta.get("pipeline_tag")
        if not isinstance(task, str) or not re.fullmatch(r"[a-z0-9_-]{3,90}", task):
            raise ValueError("Tâche du modèle non identifiée")
        if not license_name or license_name.casefold() in {"unknown", "other", "none"}:
            raise ValueError("Licence de modèle non qualifiable")
        report.update(task=task, declaredLicense=license_name,
                      access="restreint" if meta.get("gated") else "public",
                      modelFiles=len(meta.get("siblings", [])) if isinstance(meta.get("siblings"), list) else None)
    elif category == "datasets":
        if not license_name or license_name.casefold() in {"unknown", "other", "none"}:
            raise ValueError("Licence du dataset non documentée")
        files = meta.get("siblings")
        if not isinstance(files, list):
            raise ValueError("Aucun inventaire de fichiers")
        formats = sorted({extension[1:] for entry in files if isinstance(entry, dict)
                          for extension in DATA_EXTS
                          if isinstance(entry.get("rfilename"), str)
                          and entry["rfilename"].lower().endswith(extension)})
        if not formats:
            raise ValueError("Aucun format exploitable documenté")
        report.update(declaredLicense=license_name, formats=formats,
                      listedFiles=len(files), access="restreint" if meta.get("gated") else "public")
    elif category == "spaces":
        card = meta.get("cardData")
        sdk = card.get("sdk") if isinstance(card, dict) else None
        if not sdk:
            sdk = meta.get("sdk")
        runtime = meta.get("runtime")
        stage = runtime.get("stage") if isinstance(runtime, dict) else None
        if not isinstance(sdk, str) or sdk.lower() not in ALLOWED_SDKS:
            raise ValueError("SDK non identifié")
        if not isinstance(stage, str) or not re.fullmatch(r"[A-Z_]{3,40}", stage):
            raise ValueError("Runtime non observable")
        report.update(sdk=sdk.lower(), runtimeStage=stage,
                      availableNow=stage == "RUNNING",
                      note="La disponibilité est un instantané, pas une promesse de service")
    else:
        raise ValueError("Mission inconnue")
    return report


def mission(state, category, fetch=fetch_hf):
    """Chaque mission teste deux nouvelles ressources, même si le savoir-faire existe."""
    spec = MISSIONS[category]
    current = {s["id"]: s for s in valid_existing_skills(state.get("skills", []))}
    previous = current.get(spec["id"])
    prior_reports = []
    if previous:
        proof_path = ROOT / "site" / previous["proofPath"]
        prior_proof = json.loads(proof_path.read_text(encoding="utf-8"))
        prior_reports = prior_proof["reports"]
    already_tested = {r["id"].casefold() for r in prior_reports}
    trials = state.get("capabilityTrials", [])
    if not isinstance(trials, list):
        trials = []
    reports, failures = [], []
    attempted = 0
    for slug in candidates(state, category):
        if len(reports) >= 2 or attempted >= MAX_CANDIDATES:
            break
        if slug.casefold() in already_tested:
            continue
        attempted += 1
        try:
            reports.append(assess(category, slug, fetch(category, slug)))
        except (HTTPError, URLError, TimeoutError, ValueError, TypeError, KeyError, OSError) as exc:
            failures.append({"id": slug, "reason": type(exc).__name__})

    combined = prior_reports + reports
    unique = len({r["id"].casefold() for r in combined}) == len(combined)
    if unique and len(combined) >= 2 and reports:
        proof = {
            "skillId": spec["id"], "title": spec["title"], "status": "validated",
            "testedAt": previous["validatedAt"] if previous else NOW,
            "lastPracticedAt": NOW, "challenge": spec["challenge"],
            "method": spec["method"], "scope": spec["scope"],
            "checksPassed": True, "reports": combined,
        }
        path = ROOT / "site" / "evidence" / (spec["id"] + ".json")
        path.parent.mkdir(parents=True, exist_ok=True)
        serialized = json.dumps(proof, ensure_ascii=False, indent=2) + "\n"
        path.write_text(serialized, encoding="utf-8")
        current[spec["id"]] = {
            "id": spec["id"], "title": spec["title"], "status": "validated",
            "validatedAt": previous["validatedAt"] if previous else NOW,
            "lastPracticedAt": NOW, "practiceCount": len(combined),
            "proofPath": "evidence/" + path.name,
            "proofSha256": sha256(serialized.encode("utf-8")).hexdigest(),
            "resourcesTested": [r["source"] for r in combined],
        }
        result = "reinforced" if previous else "validated"
    else:
        result = "no-new-evidence" if previous else "failed"
    trials.append({
        "date": NOW, "skillId": spec["id"], "result": result,
        "reportsPassed": len(reports), "reportsRequired": 2 if not previous else 1,
        "totalVerifiedExercises": len(combined) if previous or (len(reports) == 2 and unique) else 0,
        "failures": failures[-MAX_CANDIDATES:],
    })
    state["skills"] = list(current.values())
    state["verifiedSkills"] = len(current)
    state["capabilityTrials"] = trials[-100:]
    state["lastCapabilityVerification"] = {"date": NOW, "skillId": spec["id"], "result": result}
    history = state.get("history")
    if isinstance(history, list) and history and isinstance(history[-1], dict):
        history[-1]["verified"] = len(current)
    return result

def run_all(state, fetch=fetch_hf):
    outcomes = {}
    for category in MISSIONS:
        outcomes[category] = mission(state, category, fetch)
    return outcomes


def main():
    state = json.loads(STATE.read_text(encoding="utf-8"))
    if not isinstance(state.get("nodes"), list):
        raise ValueError("Catalogue absent")
    outcomes = run_all(state)
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"outcomes": outcomes, "verifiedSkills": state["verifiedSkills"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
