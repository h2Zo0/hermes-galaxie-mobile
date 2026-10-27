"""15 capacités de transformation des données : CSV, JSON et tableaux."""
import csv
import io
import json
from collections import Counter, defaultdict

def parse_csv(p):
    return list(csv.reader(io.StringIO(p["text"])))

def csv_to_records(p):
    return list(csv.DictReader(io.StringIO(p["text"])))

def records_to_csv(p):
    buffer=io.StringIO(newline="")
    writer=csv.DictWriter(buffer,fieldnames=p["fields"],lineterminator="\n")
    writer.writeheader();writer.writerows(p["rows"])
    return buffer.getvalue()

def parse_jsonl(p):
    return [json.loads(s) for s in p["text"].splitlines() if s.strip()]

def flatten_dict(p):
    output={}
    def visit(obj,prefix=""):
        for k,v in obj.items():
            path=f"{prefix}.{k}" if prefix else k
            if isinstance(v,dict):visit(v,path)
            else:output[path]=v
    visit(p["data"])
    return output

def dedup_rows(p):
    seen=set(); out=[]
    for row in p["rows"]:
        key=json.dumps(row,sort_keys=True,ensure_ascii=False)
        if key not in seen:seen.add(key);out.append(row)
    return out

def filter_records(p):
    return [r for r in p["rows"] if r.get(p["column"])==p["equals"]]

def sort_records(p):
    return sorted(p["rows"],key=lambda r:r[p["column"]],reverse=p.get("reverse",False))

def group_count(p):
    return dict(sorted(Counter(str(r[p["column"]]) for r in p["rows"]).items()))

def sum_column(p):
    return sum(r[p["column"]] for r in p["rows"])

def mean_column(p):
    rows=p["rows"]
    return sum(r[p["column"]] for r in rows)/len(rows) if rows else None

def extract_columns(p):
    return [{k:r.get(k) for k in p["columns"]} for r in p["rows"]]

def rename_columns(p):
    return [{p["map"].get(k,k):v for k,v in r.items()} for r in p["rows"]]

def join_inner(p):
    idx=defaultdict(list)
    for r in p["right"]:idx[r[p["key"]]].append(r)
    return [{**l,**r} for l in p["left"] for r in idx.get(l[p["key"]],[])]

def pivot_sum(p):
    results=defaultdict(int)
    for r in p["rows"]:results[str(r[p["group"]])]+=r[p["value"]]
    return dict(sorted(results.items()))

TOOLS={
"parse_csv":parse_csv,"csv_to_records":csv_to_records,"records_to_csv":records_to_csv,
"parse_jsonl":parse_jsonl,"flatten_dict":flatten_dict,"dedup_rows":dedup_rows,
"filter_records":filter_records,"sort_records":sort_records,"group_count":group_count,
"sum_column":sum_column,"mean_column":mean_column,"extract_columns":extract_columns,
"rename_columns":rename_columns,"join_inner":join_inner,"pivot_sum":pivot_sum,
}
CASES={
"parse_csv":[[{"text":"a,b\n1,2\n"},[["a","b"],["1","2"]]],[{"text":"x;y\n3;4","unused":0},[["x;y"],["3;4"]]]],
"csv_to_records":[[{"text":"a,b\n1,2"},[{"a":"1","b":"2"}]],[{"text":"name,qty\nexos,3"},[{"name":"exos","qty":"3"}]]],
"records_to_csv":[[{"fields":["a","b"],"rows":[{"a":1,"b":2}]},"a,b\n1,2\n"],[{"fields":["x"],"rows":[{"x":"ok"}]},"x\nok\n"]],
"parse_jsonl":[[{"text":"{\"a\":1}\n{\"a\":2}"},[{"a":1},{"a":2}]],[{"text":"\n[1,2]\n"},[[1,2]]]],
"flatten_dict":[[{"data":{"a":{"b":2},"c":3}},{"a.b":2,"c":3}],[{"data":{"x":{"y":{"z":1}}}},{"x.y.z":1}]],
"dedup_rows":[[{"rows":[{"a":1},{"a":1},{"a":2}]},[{"a":1},{"a":2}]],[{"rows":[{"x":"b"},{"x":"a"},{"x":"b"}]},[{"x":"b"},{"x":"a"}]]],
"filter_records":[[{"rows":[{"ok":true},{"ok":false}],"column":"ok","equals":true},[{"ok":true}]],[{"rows":[{"n":2},{"n":4},{"n":2}],"column":"n","equals":2},[{"n":2},{"n":2}]]],
"sort_records":[[{"rows":[{"n":5},{"n":2}],"column":"n"},[{"n":2},{"n":5}]],[{"rows":[{"n":1},{"n":3}],"column":"n","reverse":true},[{"n":3},{"n":1}]]],
"group_count":[[{"rows":[{"t":"a"},{"t":"b"},{"t":"a"}],"column":"t"},{"a":2,"b":1}],[{"rows":[{"t":1},{"t":2},{"t":2}],"column":"t"},{"1":1,"2":2}]],
"sum_column":[[{"rows":[{"x":4},{"x":6}],"column":"x"},10],[{"rows":[{"x":-2},{"x":1}],"column":"x"},-1]],
"mean_column":[[{"rows":[{"x":4},{"x":6}],"column":"x"},5],[{"rows":[],"column":"x"},null]],
"extract_columns":[[{"rows":[{"a":1,"b":2}],"columns":["b"]},[{"b":2}]],[{"rows":[{"a":2}],"columns":["a","c"]},[{"a":2,"c":null}]]],
"rename_columns":[[{"rows":[{"a":1}],"map":{"a":"b"}},[{"b":1}]],[{"rows":[{"a":1,"c":3}],"map":{"a":"x"}},[{"x":1,"c":3}]]],
"join_inner":[[{"left":[{"id":1,"a":"A"},{"id":2,"a":"B"}],"right":[{"id":1,"b":"X"}],"key":"id"},[{"id":1,"a":"A","b":"X"}]],[{"left":[{"id":1}],"right":[{"id":2}],"key":"id"},[]]],
"pivot_sum":[[{"rows":[{"a":"A","v":2},{"a":"B","v":3},{"a":"A","v":4}],"group":"a","value":"v"},{"A":6,"B":3}],[{"rows":[{"t":"x","v":-1},{"t":"x","v":4}],"group":"t","value":"v"},{"x":3}]],
}
