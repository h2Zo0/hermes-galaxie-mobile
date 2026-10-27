"""15 outils textuels réutilisables pour NOVENS. Entrées et sorties JSON."""
import re
import unicodedata
from collections import Counter

def normalize_spaces(p):
    return " ".join(p["text"].split())

def strip_accents(p):
    return "".join(ch for ch in unicodedata.normalize("NFD",p["text"]) if unicodedata.category(ch)!="Mn")

def slugify(p):
    s=strip_accents(p).lower()
    return re.sub(r"^-|-$","",re.sub(r"[^a-z0-9]+","-",s))

def count_words(p):
    return len(re.findall(r"\b[\w'-]+\b",p["text"],re.UNICODE))

def unique_words(p):
    return sorted(set(re.findall(r"\b\w+\b",p["text"].lower(),re.UNICODE)))

def frequency_words(p):
    return dict(sorted(Counter(re.findall(r"\b\w+\b",p["text"].lower(),re.UNICODE)).items()))

def mask_email(p):
    return re.sub(r"([\w.+-])[\w.+-]*(@[\w.-]+)",r"\1***\2",p["text"])

def extract_emails(p):
    return re.findall(r"[A-Za-z0-9_.+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",p["text"])

def extract_urls(p):
    return re.findall(r"https?://[^\s<>]+",p["text"])

def title_case(p):
    return p["text"].title()

def reverse_words(p):
    return " ".join(reversed(p["text"].split()))

def initials(p):
    return "".join(x[0].upper() for x in p["text"].split() if x)

def snake_case(p):
    return re.sub(r"[^a-z0-9]+","_",strip_accents(p).lower()).strip("_")

def kebab_case(p):
    return slugify(p)

def truncate_text(p):
    text=p["text"]; n=p["length"]; return text if len(text)<=n else text[:max(0,n-1)]+"…"

TOOLS={
"normalize_spaces":normalize_spaces,"strip_accents":strip_accents,"slugify":slugify,
"count_words":count_words,"unique_words":unique_words,"frequency_words":frequency_words,
"mask_email":mask_email,"extract_emails":extract_emails,"extract_urls":extract_urls,
"title_case":title_case,"reverse_words":reverse_words,"initials":initials,
"snake_case":snake_case,"kebab_case":kebab_case,"truncate_text":truncate_text,
}
CASES={
"normalize_spaces":[[{"text":"  hello \n world  "},"hello world"],[{"text":"un\tdeux  trois"},"un deux trois"]],
"strip_accents":[[{"text":"été à Noël"},"ete a Noel"],[{"text":"École française"},"Ecole francaise"]],
"slugify":[[{"text":"L'École des Arts !"},"l-ecole-des-arts"],[{"text":"Devis 2026 / Client"},"devis-2026-client"]],
"count_words":[[{"text":"Bonjour le monde"},3],[{"text":"Un, deux et trois."},4]],
"unique_words":[[{"text":"Chat chat chien"},["chat","chien"]],[{"text":"A b A C"},["a","b","c"]]],
"frequency_words":[[{"text":"a b a"},{"a":2,"b":1}],[{"text":"Chat chat Chien"},{"chat":2,"chien":1}]],
"mask_email":[[{"text":"Contact : alice@example.com"},"Contact : a***@example.com"],[{"text":"b@site.fr"},"b***@site.fr"]],
"extract_emails":[[{"text":"a@b.fr, c@d.com"},["a@b.fr","c@d.com"]],[{"text":"aucun email"},[]]],
"extract_urls":[[{"text":"Visitez https://example.org/docs"},["https://example.org/docs"]],[{"text":"http://test.fr et https://chat.fr"},["http://test.fr","https://chat.fr"]]],
"title_case":[[{"text":"bonjour MONDE"},"Bonjour Monde"],[{"text":"PARIS france"},"Paris France"]],
"reverse_words":[[{"text":"un deux trois"},"trois deux un"],[{"text":"salut monde"},"monde salut"]],
"initials":[[{"text":"Jean Pierre Martin"},"JPM"],[{"text":"gobio exo"},"GE"]],
"snake_case":[[{"text":"Jean-Pierre à Paris"},"jean_pierre_a_paris"],[{"text":"Devis 2026 !"},"devis_2026"]],
"kebab_case":[[{"text":"Bon Jour à Tous"},"bon-jour-a-tous"],[{"text":"Prix / Vente"},"prix-vente"]],
"truncate_text":[[{"text":"bonjour", "length":5},"bonj…"],[{"text":"salut","length":6},"salut"]],
}
