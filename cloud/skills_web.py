"""10 outils de traitement d'URL et d'identifiants réseau sans requête distante."""
from urllib.parse import urlsplit,urlunsplit,parse_qs,parse_qsl,urlencode,quote
import ipaddress
import re

def url_hostname(p):return urlsplit(p["url"]).hostname
def normalize_url(p):
    u=urlsplit(p["url"])
    return urlunsplit((u.scheme.lower(),u.netloc.lower(),u.path or "/",u.query,u.fragment))
def query_params(p):return parse_qs(urlsplit(p["url"]).query)
def remove_tracking(p):
    u=urlsplit(p["url"])
    pairs=[(k,v) for k,v in parse_qsl(u.query) if not k.lower().startswith("utm_") and k.lower() not in ("fbclid","gclid")]
    return urlunsplit((u.scheme,u.netloc,u.path,urlencode(pairs),u.fragment))
def query_encode(p):return urlencode(sorted(p["pairs"].items()))
def path_segments(p):return [x for x in urlsplit(p["url"]).path.split("/") if x]
def is_https(p):
    u=urlsplit(p["url"])
    return u.scheme.lower()=="https" and bool(u.hostname)
def sort_query(p):
    u=urlsplit(p["url"])
    return urlunsplit((u.scheme,u.netloc,u.path,urlencode(sorted(parse_qsl(u.query))),u.fragment))
def valid_ipv4(p):
    try:return str(ipaddress.IPv4Address(p["address"]))==p["address"]
    except ipaddress.AddressValueError:return False
def email_domain(p):return p["email"].rsplit("@",1)[-1].lower() if "@" in p["email"] else None

TOOLS={
"url_hostname":url_hostname,"normalize_url":normalize_url,"query_params":query_params,
"remove_tracking":remove_tracking,"query_encode":query_encode,"path_segments":path_segments,
"is_https":is_https,"sort_query":sort_query,"valid_ipv4":valid_ipv4,"email_domain":email_domain,
}
CASES={
"url_hostname":[[{"url":"https://Example.COM/a"},"example.com"],[{"url":"http://sub.domain.fr:8080/"}, "sub.domain.fr"]],
"normalize_url":[[{"url":"HTTPS://EXAMPLE.ORG"},"https://example.org/"],[{"url":"http://SITE.FR/path?q=1"},"http://site.fr/path?q=1"]],
"query_params":[[{"url":"https://a.fr/?x=1&x=2"},{"x":["1","2"]}],[{"url":"https://a.fr/?a=abc&b=z"},{"a":["abc"],"b":["z"]}]],
"remove_tracking":[[{"url":"https://a.fr/p?utm_source=ads&id=2"},"https://a.fr/p?id=2"],[{"url":"https://a.fr/p?fbclid=x&ok=1"},"https://a.fr/p?ok=1"]],
"query_encode":[[{"pairs":{"z":"hello world","a":"1"}},"a=1&z=hello+world"],[{"pairs":{"q":"été"}},"q=%C3%A9t%C3%A9"]],
"path_segments":[[{"url":"https://a.fr/a/b/c"},["a","b","c"]],[{"url":"https://a.fr/"},[]]],
"is_https":[[{"url":"https://a.fr"},true],[{"url":"http://a.fr"},false]],
"sort_query":[[{"url":"https://a.fr/?z=2&a=1"},"https://a.fr/?a=1&z=2"],[{"url":"https://a.fr/p?b=3&a=2"},"https://a.fr/p?a=2&b=3"]],
"valid_ipv4":[[{"address":"192.168.1.1"},true],[{"address":"300.1.2.3"},false]],
"email_domain":[[{"email":"a@EXAMPLE.COM"},"example.com"],[{"email":"no-at"},null]],
}
