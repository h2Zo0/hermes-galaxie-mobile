"""11 routines opérationnelles achats, stock, ventes et fidélisation."""
import math

def stock_value(p):return round(p["quantity"]*p["unit_cost"],2)
def reorder_point(p):return math.ceil(p["daily_demand"]*p["lead_days"]+p["safety"])
def replenishment_quantity(p):return max(0,math.ceil(p["target"]-p["on_hand"]))
def inventory_turnover(p):return round(p["cost_of_sales"]/p["average_inventory"],2)
def sell_through_percent(p):return round(100*p["sold"]/(p["sold"]+p["remaining"]),2)
def lead_conversion_percent(p):return round(100*p["won"]/p["leads"],2)
def acquisition_cost_per_lead(p):return round(p["spend"]/p["leads"],2)
def customer_lifetime_value(p):return round(p["order_value"]*p["orders_year"]*p["years"]*p["margin"]/100,2)
def customer_churn_percent(p):return round(100*p["lost"]/p["customers_start"],2)
def net_revenue_retention(p):return round(100*(p["starting"]+p["expansion"]-p["contraction"]-p["churn"])/p["starting"],2)
def weighted_pipeline(p):return round(sum(d["amount"]*d["probability"]/100 for d in p["deals"]),2)

TOOLS={
"stock_value":stock_value,"reorder_point":reorder_point,
"replenishment_quantity":replenishment_quantity,"inventory_turnover":inventory_turnover,
"sell_through_percent":sell_through_percent,"lead_conversion_percent":lead_conversion_percent,
"acquisition_cost_per_lead":acquisition_cost_per_lead,"customer_lifetime_value":customer_lifetime_value,
"customer_churn_percent":customer_churn_percent,"net_revenue_retention":net_revenue_retention,
"weighted_pipeline":weighted_pipeline,
}
CASES={
"stock_value":[[{"quantity":10,"unit_cost":125},1250],[{"quantity":3,"unit_cost":49},147]],
"reorder_point":[[{"daily_demand":4,"lead_days":5,"safety":8},28],[{"daily_demand":1.5,"lead_days":3,"safety":2},7]],
"replenishment_quantity":[[{"target":100,"on_hand":55},45],[{"target":20,"on_hand":25},0]],
"inventory_turnover":[[{"cost_of_sales":30000,"average_inventory":10000},3],[{"cost_of_sales":5000,"average_inventory":2000},2.5]],
"sell_through_percent":[[{"sold":80,"remaining":20},80],[{"sold":3,"remaining":9},25]],
"lead_conversion_percent":[[{"won":5,"leads":100},5],[{"won":1,"leads":4},25]],
"acquisition_cost_per_lead":[[{"spend":1000,"leads":50},20],[{"spend":120,"leads":8},15]],
"customer_lifetime_value":[[{"order_value":100,"orders_year":2,"years":3,"margin":50},300],[{"order_value":200,"orders_year":1,"years":2,"margin":25},100]],
"customer_churn_percent":[[{"lost":10,"customers_start":100},10],[{"lost":3,"customers_start":60},5]],
"net_revenue_retention":[[{"starting":1000,"expansion":200,"contraction":50,"churn":50},110],[{"starting":200,"expansion":0,"contraction":10,"churn":10},90]],
"weighted_pipeline":[[{"deals":[{"amount":1000,"probability":50},{"amount":2000,"probability":25}]},1000],[{"deals":[{"amount":500,"probability":20}]},100]],
}
