"""12 opérations calendaires testées, en dates explicites, sans dépendance externe."""
from datetime import date, datetime, timedelta, timezone
import calendar

def parse_fr_date(p):return datetime.strptime(p["text"],"%d/%m/%Y").date().isoformat()
def format_fr_date(p):return date.fromisoformat(p["date"]).strftime("%d/%m/%Y")
def days_between(p):return (date.fromisoformat(p["end"])-date.fromisoformat(p["start"])).days
def business_days_between(p):
    a=date.fromisoformat(p["start"]);b=date.fromisoformat(p["end"]);count=0
    while a<b:
        if a.weekday()<5:count+=1
        a+=timedelta(days=1)
    return count
def add_business_days(p):
    day=date.fromisoformat(p["date"])
    for _ in range(p["days"]):
        day+=timedelta(days=1)
        while day.weekday()>4:day+=timedelta(days=1)
    return day.isoformat()
def iso_week(p):return date.fromisoformat(p["date"]).isocalendar().week
def calendar_quarter(p):return (date.fromisoformat(p["date"]).month-1)//3+1
def last_day_of_month(p):
    d=date.fromisoformat(p["date"])
    return d.replace(day=calendar.monthrange(d.year,d.month)[1]).isoformat()
def ordinal_day(p):return date.fromisoformat(p["date"]).timetuple().tm_yday
def shift_days(p):return (date.fromisoformat(p["date"])+timedelta(days=p["days"])).isoformat()
def age_years(p):
    born=date.fromisoformat(p["born"]);asof=date.fromisoformat(p["asof"])
    return asof.year-born.year-((asof.month,asof.day)<(born.month,born.day))
def epoch_seconds(p):return int(datetime.fromisoformat(p["date"]).replace(tzinfo=timezone.utc).timestamp())

TOOLS={
"parse_fr_date":parse_fr_date,"format_fr_date":format_fr_date,"days_between":days_between,
"business_days_between":business_days_between,"add_business_days":add_business_days,
"iso_week":iso_week,"calendar_quarter":calendar_quarter,"last_day_of_month":last_day_of_month,
"ordinal_day":ordinal_day,"shift_days":shift_days,"age_years":age_years,"epoch_seconds":epoch_seconds,
}
CASES={
"parse_fr_date":[[{"text":"27/10/2026"},"2026-10-27"],[{"text":"01/01/2025"},"2025-01-01"]],
"format_fr_date":[[{"date":"2026-10-27"},"27/10/2026"],[{"date":"2025-01-01"},"01/01/2025"]],
"days_between":[[{"start":"2026-10-01","end":"2026-10-11"},10],[{"start":"2026-10-27","end":"2026-10-26"},-1]],
"business_days_between":[[{"start":"2026-10-26","end":"2026-11-02"},5],[{"start":"2026-10-30","end":"2026-11-03"},2]],
"add_business_days":[[{"date":"2026-10-30","days":1},"2026-11-02"],[{"date":"2026-10-26","days":3},"2026-10-29"]],
"iso_week":[[{"date":"2026-01-01"},1],[{"date":"2026-10-27"},44]],
"calendar_quarter":[[{"date":"2026-02-02"},1],[{"date":"2026-10-27"},4]],
"last_day_of_month":[[{"date":"2024-02-05"},"2024-02-29"],[{"date":"2026-04-01"},"2026-04-30"]],
"ordinal_day":[[{"date":"2026-01-01"},1],[{"date":"2024-03-01"},61]],
"shift_days":[[{"date":"2026-01-01","days":7},"2026-01-08"],[{"date":"2026-03-01","days":-1},"2026-02-28"]],
"age_years":[[{"born":"2000-10-28","asof":"2026-10-27"},25],[{"born":"2000-01-01","asof":"2026-10-27"},26]],
"epoch_seconds":[[{"date":"1970-01-01T00:00:00"},0],[{"date":"1970-01-02T00:00:00"},86400]],
}
