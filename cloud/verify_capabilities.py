#!/usr/bin/env python3
"""Valider une capacité uniquement après une tâche réelle et des preuves consultables.

Les découvertes ne sont pas des compétences. Ce module n'exécute jamais du code
dépôt tiers : il teste des intégrations en lecture seule et publie un audit.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import hashlib
import json
import os
import re

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "site" / "state.json"
EVIDENCE = ROOT / "site" / "evidence" / "github-repository-audit.json"
SKILL_ID = "github-repository-technical-audit-v1"
SKILL_TITLE = "Analyser techniquement un dépôt GitHub public"
NOW = datetime.now(timezone.utc).isoformat(timespec="seconds")
SLUG = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def fetch_github(path):
    """Connexion exclusivement à l'API GitHub ; aucune URL provenant d'un dépôt."""
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "NOVENS-Capability-Verification/1.0"}
    token = os.environ.get("GH_TOKEN", "")
    if token:
        headers["Authorization"] = "Bearer " + token
    url = "https://api.github.com/" + path
    with urlopen(Request(url, headers=headers), timeout=15) as response:
        return json.loads(response.read(1_000_000))


def analyze_repository(expected_slug, metadata, languages):
    """Une tâche d'audit reproductible, pas une simple vérification d'URL."""
    if not SLUG.fullmatch(expected_slug):
        raise ValueError("Identifiant de dépôt invalide")
    if not isinstance(metadata, dict) or metadata.get("full_name", "").lower() != expected_slug.lower():
        raise ValueError("L'API ne correspond pas au dépôt choisi")
    if metadata.get("html_url", "").rstrip("/").lower() != ("https://github.com/" + expected_slug).lower():
        raise ValueError("Adresse du dépôt incohérente")
    if metadata.get("archived") or metadata.get("disabled") or metadata.get("private"):
        raise ValueError("Dépôt non disponible pour l'essai public")
    if not isinstance(languages, dict) or not languages:
        raise ValueError("Aucune statistique linguistique exploitable")
    if not all(isinstance(k, str) and k and type(v) is int and v >= 0 for k, v in languages.items()):
        raise ValueError("Statistiques linguistiques incorrectes")
    total = sum(languages.values())
    if total <= 0:
        raise ValueError("Aucun octet de code mesurable")
    dominant = max(sorted(languages), key=lambda language: languages[language])
    proportion = round(100 * languages[dominant] / total, 2)
    if not (0 < proportion <= 100):
        raise ValueError("Calcul de répartition incohérent")
    return {
        "repository": expected_slug,
        "url": metadata["html_url"],
        "defaultBranch": metadata.get("default_branch"),
        "primaryLanguage": dominant,
        "primaryLanguageSharePercent": proportion,
        "languageBytes": dict(sorted(languages.items(), key=lambda item: (-item[1], item[0]))),
        "totalLanguageBytes": total,
        "archived": False,
        "starsAtTest": metadata.get("stargazers_count"),
        "pushedAt": metadata.get("pushed_at"),
    }


def github_candidates(nodes):
    seen = set()
    for node in nodes:
        if not isinstance(node, dict) or node.get("category") != "github":
            continue
        slug = node.get("name", "")
        if not isinstance(slug, str) or not SLUG.fullmatch(slug) or slug.lower() in seen:
            continue
        if node.get("url", "").lower().rstrip("/") != ("https://github.com/" + slug).lower():
            continue
        seen.add(slug.lower())
        yield slug


def valid_existing_skills(items):
    """Ne retenir que des capacités ayant encore une preuve positive sur disque."""
    valid = []
    if not isinstance(items, list):
        return valid
    for item in items:
        if not isinstance(item, dict) or item.get("status") != "validated":
            continue
        proof = item.get("proofPath", "")
        if not isinstance(proof, str) or not re.fullmatch(r"evidence/[a-z0-9-]+\.json", proof):
            continue
        path = ROOT / "site" / proof
        try:
            evidence = json.loads(path.read_text(encoding="utf-8"))
            if evidence.get("skillId") == item.get("id") and evidence.get("status") == "validated":
                if len(evidence.get("reports", [])) >= 2 and evidence.get("checksPassed") is True:
                    valid.append(item)
        except (OSError, ValueError, AttributeError):
            continue
    return valid


def run(state, fetch=fetch_github):
    existing = valid_existing_skills(state.get("skills", []))
    trials = state.get("capabilityTrials", [])
    if not isinstance(trials, list):
        trials = []
    previous = next((item for item in existing if item["id"] == SKILL_ID), None)
    if previous is None:
        audits, failures = [], []
        for slug in github_candidates(state.get("nodes", [])):
            if len(audits) >= 2 or len(failures) >= 8:
                break
            try:
                encoded = "/".join(quote(part, safe="") for part in slug.split("/"))
                metadata = fetch("repos/" + encoded)
                languages = fetch("repos/" + encoded + "/languages")
                report = analyze_repository(slug, metadata, languages)
                audits.append(report)
            except (HTTPError, URLError, TimeoutError, ValueError, TypeError, KeyError, OSError) as exc:
                failures.append({"repository": slug, "reason": type(exc).__name__})
        if len(audits) == 2:
            proof = {
                "skillId": SKILL_ID, "title": SKILL_TITLE,
                "status": "validated", "testedAt": NOW,
                "challenge": "Auditer indépendamment deux dépôts publics découverts, identifier leur langage dominant et calculer sa part réelle.",
                "method": "GET /repos/{owner}/{repo} et GET /repos/{owner}/{repo}/languages via api.github.com; calcul local vérifié",
                "checksPassed": True, "reports": audits,
                "scope": "Lecture et analyse de métadonnées GitHub; aucune installation ou exécution de code tiers.",
            }
            EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
            serialized = json.dumps(proof, ensure_ascii=False, indent=2) + "\n"
            EVIDENCE.write_text(serialized, encoding="utf-8")
            existing.append({
                "id": SKILL_ID, "title": SKILL_TITLE, "status": "validated",
                "validatedAt": NOW, "proofPath": "evidence/github-repository-audit.json",
                "proofSha256": hashlib.sha256(serialized.encode("utf-8")).hexdigest(),
                "resourcesTested": [audit["url"] for audit in audits],
            })
            outcome = "validated"
        else:
            outcome = "failed"
        trials.append({
            "date": NOW, "skillId": SKILL_ID, "result": outcome,
            "reportsPassed": len(audits), "reportsRequired": 2, "failures": failures,
        })
    else:
        outcome = "already-validated"
    state["skills"] = existing
    state["verifiedSkills"] = len(existing)
    state["capabilityTrials"] = trials[-30:]
    state["lastCapabilityVerification"] = {"date": NOW, "skillId": SKILL_ID, "result": outcome}
    history = state.get("history")
    if isinstance(history, list) and history and isinstance(history[-1], dict):
        history[-1]["verified"] = len(existing)
    return outcome


def main():
    state = json.loads(STATE.read_text(encoding="utf-8"))
    if not isinstance(state.get("nodes"), list):
        raise ValueError("Catalogue manquant : aucune compétence n'est présumée")
    outcome = run(state)
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"verification": outcome, "verifiedSkills": state["verifiedSkills"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
