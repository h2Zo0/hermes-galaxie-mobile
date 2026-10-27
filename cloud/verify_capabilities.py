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
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != item.get("proofSha256"):
                continue
            evidence = json.loads(raw)
            reports = evidence.get("reports")
            identifiers = [r.get("repository") or r.get("id") for r in reports] if isinstance(reports, list) else []
            if (evidence.get("skillId") == item.get("id") and evidence.get("status") == "validated"
                    and evidence.get("checksPassed") is True and len(identifiers) >= 2
                    and all(isinstance(identifier, str) and identifier for identifier in identifiers)
                    and len(set(identifier.casefold() for identifier in identifiers)) == len(identifiers)
                    and item["id"] not in {skill["id"] for skill in valid}):
                valid.append(item)
        except (OSError, ValueError, AttributeError):
            continue
    return valid


def run(state, fetch=fetch_github):
    """Tâche de validation, puis pratique continue sur de nouveaux dépôts."""
    existing = valid_existing_skills(state.get("skills", []))
    previous = next((item for item in existing if item["id"] == SKILL_ID), None)
    prior_reports = json.loads(EVIDENCE.read_text(encoding="utf-8"))["reports"] if previous else []
    already_tested = {r["repository"].casefold() for r in prior_reports}
    trials = state.get("capabilityTrials", [])
    if not isinstance(trials, list):
        trials = []
    audits, failures = [], []
    attempted = 0
    slugs = list(github_candidates(state.get("nodes", [])))
    cursor = state.get("discovery", {}).get("cursor", 0)
    offset = (max(0, cursor) * 12) % len(slugs) if isinstance(cursor, int) and slugs else 0
    slugs = slugs[offset:] + slugs[:offset]
    for slug in slugs:
        if len(audits) >= 2 or attempted >= 12:
            break
        if slug.casefold() in already_tested:
            continue
        attempted += 1
        try:
            encoded = "/".join(quote(part, safe="") for part in slug.split("/"))
            metadata = fetch("repos/" + encoded)
            languages = fetch("repos/" + encoded + "/languages")
            audits.append(analyze_repository(slug, metadata, languages))
        except (HTTPError, URLError, TimeoutError, ValueError, TypeError, KeyError, OSError) as exc:
            failures.append({"repository": slug, "reason": type(exc).__name__})

    combined = prior_reports + audits
    if len(combined) >= 2 and audits:
        proof = {
            "skillId": SKILL_ID, "title": SKILL_TITLE, "status": "validated",
            "testedAt": previous["validatedAt"] if previous else NOW,
            "lastPracticedAt": NOW,
            "challenge": "Auditer plusieurs dépôts publics découverts, identifier leur langage dominant et calculer sa part réelle.",
            "method": "GET /repos/{owner}/{repo} et /languages via api.github.com; calcul local vérifié",
            "checksPassed": True, "reports": combined,
            "scope": "Lecture et analyse de métadonnées GitHub, sans exécuter de code tiers.",
        }
        EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
        serialized = json.dumps(proof, ensure_ascii=False, indent=2) + "\n"
        EVIDENCE.write_text(serialized, encoding="utf-8")
        updated = {
            "id": SKILL_ID, "title": SKILL_TITLE, "status": "validated",
            "validatedAt": previous["validatedAt"] if previous else NOW,
            "lastPracticedAt": NOW, "practiceCount": len(combined),
            "proofPath": "evidence/github-repository-audit.json",
            "proofSha256": hashlib.sha256(serialized.encode("utf-8")).hexdigest(),
            "resourcesTested": [audit["url"] for audit in combined],
        }
        existing = [item for item in existing if item["id"] != SKILL_ID]
        existing.append(updated)
        outcome = "reinforced" if previous else "validated"
    else:
        outcome = "no-new-evidence" if previous else "failed"
    trials.append({
        "date": NOW, "skillId": SKILL_ID, "result": outcome,
        "reportsPassed": len(audits), "reportsRequired": 1 if previous else 2,
        "totalVerifiedExercises": len(combined) if previous or (len(audits) == 2) else 0,
        "failures": failures,
    })
    state["skills"] = existing
    state["verifiedSkills"] = len(existing)
    state["capabilityTrials"] = trials[-100:]
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
