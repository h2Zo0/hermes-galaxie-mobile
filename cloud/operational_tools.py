#!/usr/bin/env python3
"""NOVENS : atelier vérifiable de 100 outils opérationnels Python réutilisables.

Chaque compétence = une fonction d'un domaine identifiable, avec 2 jeux
d'entrée différents, 2 résultats attendus indépendants, déterminisme vérifié,
preuve SHA-256 et API d'exécution réutilisable.

NE revendique PAS la capacité de produire de l'argent, ni une IA entraînée :
ce sont des micro-compétences logicielles locales, de portée explicitement bornée.
"""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import math

from cloud import (skills_text, skills_data, skills_finance, skills_stats,
                   skills_dates, skills_web, skills_operations, skills_validation)
from cloud.verify_capabilities import valid_existing_skills

ROOT=Path(__file__).resolve().parents[1]
STATE=ROOT/"site"/"state.json"
NOW=datetime.now(timezone.utc).isoformat(timespec="seconds")
PACKS={
    "text":skills_text,"data":skills_data,"finance":skills_finance,
    "stats":skills_stats,"dates":skills_dates,"web":skills_web,
    "operations":skills_operations,"validation":skills_validation,
}
CAPABILITIES={}
SAMPLES={}
for domain,pack in PACKS.items():
    for name,func in pack.TOOLS.items():
        if name in CAPABILITIES:
            raise RuntimeError(f"Capacité dupliquée : {name}")
        CAPABILITIES[name]=(domain,func)
        SAMPLES[name]=pack.CASES[name]


def execute(name,payload):
    """Point d'entrée public pour réutiliser une capacité validée dans une mission."""
    if name not in CAPABILITIES:
        raise KeyError("Capacité non supportée")
    if not isinstance(payload,dict):
        raise TypeError("La charge utile doit être un objet JSON")
    return CAPABILITIES[name][1](deepcopy(payload))


def digest(obj):
    serialized=json.dumps(obj,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(",",":"))
    return sha256(serialized.encode("utf-8")).hexdigest()


def evaluate(name):
    tests=SAMPLES[name]
    if len(tests)<2 or len({digest(p) for p,_ in tests})<2:
        raise ValueError("Deux épreuves indépendantes requises")
    reports=[]
    for index,(payload,expected) in enumerate(tests,1):
        before=digest(payload)
        actual=execute(name,payload)
        repeated=execute(name,payload)
        if (actual!=expected or repeated!=expected or digest(payload)!=before):
            raise AssertionError(f"Résultat non conforme à l'étalon : cas {index}")
        result_digest=digest(actual)
        if result_digest!=digest(expected):
            raise AssertionError(f"Empreinte non conforme : cas {index}")
        reports.append({
            "id":f"cas-{index}", "inputSha256":before,
            "expectedSha256":digest(expected), "actualSha256":result_digest,
            "deterministic":True, "passed":True,
        })
    return reports


def run(state):
    already=valid_existing_skills(state.get("skills",[]))
    valid={s["id"]:s for s in already}
    failures=[]
    newly=[]
    validated_at=NOW
    for name,(domain,func) in CAPABILITIES.items():
        skill_id="toolkit-"+name.replace("_","-")+"-v1"
        if skill_id in valid:
            continue
        try:
            reports=evaluate(name)
            proof={
                "skillId":skill_id,
                "title":"Outil opérationnel : "+name.replace("_"," "),
                "status":"validated",
                "testedAt":validated_at,
                "checksPassed":True,
                "scope":"Fonction Python locale testée sur deux épreuves reproductibles; pas de garantie hors jeux de test",
                "domain":domain,
                "implementation":"cloud/skills_"+domain+".py::"+name,
                "reuseApi":'cloud.operational_tools.execute("'+name+'", payload)',
                "method":"Deux attentes fixées indépendamment, exécution réelle répétée, résultats et hachages comparés",
                "reports":reports,
            }
            path=ROOT/"site"/"evidence"/(skill_id+".json")
            path.parent.mkdir(parents=True,exist_ok=True)
            raw=(json.dumps(proof,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
            path.write_bytes(raw)
            skill={
                "id":skill_id,"title":proof["title"],"status":"validated",
                "domain":domain,"validatedAt":validated_at,
                "proofPath":"evidence/"+path.name,"proofSha256":sha256(raw).hexdigest(),
                "resourcesTested":[name+":cas-1",name+":cas-2"],
                "evidenceType":"local-deterministic-function-tests",
                "reuseApi":proof["reuseApi"],
            }
            valid[skill_id]=skill
            newly.append(skill_id)
        except (AssertionError,ValueError,TypeError,KeyError,OverflowError,ZeroDivisionError) as exc:
            failures.append({"name":name,"type":type(exc).__name__,"reason":str(exc)[:160]})
    # Les autres compétences ne sont comptées que si leurs preuves restent valides.
    state["skills"]=list(valid.values())
    state["verifiedSkills"]=len(valid)
    state["operationalToolkit"]={
        "definedTools":len(CAPABILITIES),
        "verifiedTools":sum(s["id"].startswith("toolkit-") for s in valid.values()),
        "newlyValidated":len(newly),
        "rejected":len(failures),
        "lastTestedAt":NOW,
        "scope":"Micro-capacités Python unitaires, pas autonomie économique ni apprentissage de modèles",
        "failures":failures[-20:],
    }
    history=state.get("history")
    if isinstance(history,list) and history and isinstance(history[-1],dict):
        history[-1]["verified"]=len(valid)
    return {"defined":len(CAPABILITIES),"new":len(newly),
            "valid":state["verifiedSkills"],"failures":failures}


def main():
    state=json.loads(STATE.read_text(encoding="utf-8"))
    if not isinstance(state.get("nodes"),list):
        raise ValueError("Catalogue NOVENS manquant")
    result=run(state)
    STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False))
    if result["failures"]:
        print("Certains outils sont rejetés, leurs erreurs ont été enregistrées.")


if __name__=="__main__":
    main()
