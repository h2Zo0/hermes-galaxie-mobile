"""10 capacités de validation et d'hygiène des données ; ne remplace pas un audit de sécurité."""
import hashlib
import hmac
import math
import re
import json

def sha256_text(p):return hashlib.sha256(p["text"].encode("utf-8")).hexdigest()
def hmac_sha256(p):return hmac.new(p["key"].encode(),p["text"].encode(),hashlib.sha256).hexdigest()
def password_entropy_estimate(p):
    text=p["password"]
    alphabet=(26 if re.search("[a-z]",text) else 0)+(26 if re.search("[A-Z]",text) else 0)+(10 if re.search("[0-9]",text) else 0)+(32 if re.search("[^A-Za-z0-9]",text) else 0)
    return round(len(text)*math.log2(alphabet),2) if alphabet else 0
def redact_phone(p):
    return re.sub(r"\b0[1-9](?:[ .-]?\d{2}){4}\b","[téléphone]",p["text"])
def validate_email(p):
    return bool(re.fullmatch(r"[A-Za-z0-9_.+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",p["email"]))
def validate_iban_fr(p):
    iban=re.sub(r"\s+","",p["iban"]).upper()
    if not re.fullmatch(r"FR[0-9]{12}[A-Z0-9]{11}[0-9]{2}",iban):return False
    rearranged=iban[4:]+iban[:4]
    rest=0
    for ch in rearranged:
        for digit in str(ord(ch)-55) if "A"<=ch<="Z" else ch:
            rest=(rest*10+int(digit))%97
    return rest==1
def validate_siret(p):
    s=p["siret"]
    if not re.fullmatch(r"\d{14}",s) or s=="0"*14:return False
    total=0
    for index,ch in enumerate(reversed(s)):
        n=int(ch)
        if index%2==1:n=n*2-9 if n*2>9 else n*2
        total+=n
    return total%10==0
def validate_ean13(p):
    s=p["ean"]
    return bool(re.fullmatch(r"\d{13}",s)) and (sum(int(x)*(3 if i%2 else 1) for i,x in enumerate(s[:12]))+int(s[-1]))%10==0
def compare_semver(p):
    def parse(s):
        if not re.fullmatch(r"\d+\.\d+\.\d+",s):raise ValueError("Version MAJOR.MINOR.PATCH attendue")
        return tuple(map(int,s.split(".")))
    a=parse(p["a"]);b=parse(p["b"])
    return (a>b)-(a<b)
def json_top_level_keys(p):
    data=json.loads(p["text"])
    if not isinstance(data,dict):return []
    return sorted(data.keys())

TOOLS={
"sha256_text":sha256_text,"hmac_sha256":hmac_sha256,
"password_entropy_estimate":password_entropy_estimate,"redact_phone":redact_phone,
"validate_email":validate_email,"validate_iban_fr":validate_iban_fr,
"validate_siret":validate_siret,"validate_ean13":validate_ean13,
"compare_semver":compare_semver,"json_top_level_keys":json_top_level_keys,
}
CASES={
"sha256_text":[[{"text":"abc"},"ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"],[{"text":""},"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"]],
"hmac_sha256":[[{"key":"key","text":"The quick brown fox jumps over the lazy dog"},"f7bc83f430538424b13298e6aa6fb143ef4d59a14946175997479dbc2d1a3cd8"],[{"key":"Jefe","text":"what do ya want for nothing?"},"5bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec3843"]],
"password_entropy_estimate":[[{"password":"1"},3.32],[{"password":"12"},6.64]],
"redact_phone":[[{"text":"Appelez le 06 12 34 56 78."},"Appelez le [téléphone]."],[{"text":"fixe 0123456789"},"fixe [téléphone]"]],
"validate_email":[[{"email":"contact@gobioexo.fr"},true],[{"email":"email-invalide"},false]],
"validate_iban_fr":[[{"iban":"FR1420041010050500013M02606"},true],[{"iban":"FR1420041010050500013M02607"},false]],
"validate_siret":[[{"siret":"73282932000074"},true],[{"siret":"12345678901234"},false]],
"validate_ean13":[[{"ean":"4006381333931"},true],[{"ean":"4006381333932"},false]],
"compare_semver":[[{"a":"1.2.3","b":"1.2.4"},-1],[{"a":"2.0.0","b":"1.9.9"},1]],
"json_top_level_keys":[[{"text":"{\"b\":1,\"a\":2}"},["a","b"]],[{"text":"[1,2]"},[]]],
}
