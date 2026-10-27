"""15 calculs commerciaux, applicables à des opérations réelles, hors comptabilité certifiée."""
import math

def vat_amount(p):return round(p["net"]*p["vat"]/100,2)
def price_with_vat(p):return round(p["net"]*(1+p["vat"]/100),2)
def price_without_vat(p):return round(p["gross"]/(1+p["vat"]/100),2)
def margin_euros(p):return round(p["sell"]-p["buy"],2)
def margin_rate(p):return round(100*(p["sell"]-p["buy"])/p["sell"],2)
def markup_rate(p):return round(100*(p["sell"]-p["buy"])/p["buy"],2)
def discount_amount(p):return round(p["price"]*p["discount"]/100,2)
def discounted_price(p):return round(p["price"]*(1-p["discount"]/100),2)
def break_even_units(p):return math.ceil(p["fixed"]/(p["sell"]-p["variable"]))
def runway_months(p):return round(p["cash"]/p["burn"],2)
def net_profit(p):return round(p["revenue"]-p["costs"]-p["taxes"],2)
def recurring_monthly_revenue(p):return round(p["subscriptions"]*p["monthly_price"],2)
def recurring_annual_revenue(p):return round(p["monthly_revenue"]*12,2)
def roi_percent(p):return round(100*(p["gain"]-p["investment"])/p["investment"],2)
def compound_growth(p):return round(p["initial"]*(1+p["rate"]/100)**p["periods"],2)

TOOLS={
"vat_amount":vat_amount,"price_with_vat":price_with_vat,"price_without_vat":price_without_vat,
"margin_euros":margin_euros,"margin_rate":margin_rate,"markup_rate":markup_rate,
"discount_amount":discount_amount,"discounted_price":discounted_price,
"break_even_units":break_even_units,"runway_months":runway_months,"net_profit":net_profit,
"recurring_monthly_revenue":recurring_monthly_revenue,"recurring_annual_revenue":recurring_annual_revenue,
"roi_percent":roi_percent,"compound_growth":compound_growth,
}
CASES={
"vat_amount":[[{"net":100,"vat":20},20],[{"net":250,"vat":10},25]],
"price_with_vat":[[{"net":100,"vat":20},120],[{"net":50,"vat":10},55]],
"price_without_vat":[[{"gross":120,"vat":20},100],[{"gross":110,"vat":10},100]],
"margin_euros":[[{"sell":120,"buy":80},40],[{"sell":10,"buy":12},-2]],
"margin_rate":[[{"sell":100,"buy":75},25],[{"sell":200,"buy":100},50]],
"markup_rate":[[{"sell":125,"buy":100},25],[{"sell":60,"buy":40},50]],
"discount_amount":[[{"price":100,"discount":20},20],[{"price":250,"discount":10},25]],
"discounted_price":[[{"price":100,"discount":20},80],[{"price":250,"discount":10},225]],
"break_even_units":[[{"fixed":1000,"sell":100,"variable":50},20],[{"fixed":105,"sell":30,"variable":10},6]],
"runway_months":[[{"cash":12000,"burn":3000},4],[{"cash":5000,"burn":2000},2.5]],
"net_profit":[[{"revenue":1000,"costs":700,"taxes":100},200],[{"revenue":200,"costs":250,"taxes":0},-50]],
"recurring_monthly_revenue":[[{"subscriptions":10,"monthly_price":49},490],[{"subscriptions":3,"monthly_price":99},297]],
"recurring_annual_revenue":[[{"monthly_revenue":100},1200],[{"monthly_revenue":99},1188]],
"roi_percent":[[{"gain":150,"investment":100},50],[{"gain":80,"investment":100},-20]],
"compound_growth":[[{"initial":100,"rate":10,"periods":2},121],[{"initial":200,"rate":0,"periods":5},200]],
}
