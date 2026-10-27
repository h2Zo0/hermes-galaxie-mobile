"""12 routines statistiques réutilisables avec jeux de test indépendants."""
import math
import statistics
from collections import Counter

def mean(p):return round(statistics.mean(p["values"]),4)
def median(p):return statistics.median(p["values"])
def population_std(p):return round(statistics.pstdev(p["values"]),4)
def population_variance(p):return round(statistics.pvariance(p["values"]),4)
def nearest_rank_percentile(p):
    values=sorted(p["values"])
    return values[max(0,math.ceil(len(values)*p["percent"]/100)-1)]
def moving_average(p):
    vals=p["values"]; n=p["window"]
    return [round(sum(vals[i:i+n])/n,4) for i in range(len(vals)-n+1)]
def cumulative_sum(p):
    total=0; out=[]
    for n in p["values"]:total+=n;out.append(total)
    return out
def min_max_scale(p):
    vals=p["values"]; lo=min(vals);hi=max(vals)
    return [round((v-lo)/(hi-lo),4) if hi!=lo else 0 for v in vals]
def z_scores(p):
    vals=p["values"]; mu=statistics.mean(vals);sd=statistics.pstdev(vals)
    return [round((v-mu)/sd,4) if sd else 0 for v in vals]
def histogram_buckets(p):
    width=p["width"]
    return dict(sorted(Counter(str(math.floor(x/width)*width) for x in p["values"]).items(),key=lambda x:float(x[0])))
def correlation(p):
    a=p["x"];b=p["y"]
    ma=statistics.mean(a);mb=statistics.mean(b)
    num=sum((x-ma)*(y-mb) for x,y in zip(a,b))
    den=math.sqrt(sum((x-ma)**2 for x in a)*sum((y-mb)**2 for y in b))
    return round(num/den,4) if den else None
def growth_rates(p):
    vals=p["values"]
    return [round((vals[i]/vals[i-1]-1)*100,2) if vals[i-1] else None for i in range(1,len(vals))]

TOOLS={
"mean":mean,"median":median,"population_std":population_std,"population_variance":population_variance,
"nearest_rank_percentile":nearest_rank_percentile,"moving_average":moving_average,
"cumulative_sum":cumulative_sum,"min_max_scale":min_max_scale,"z_scores":z_scores,
"histogram_buckets":histogram_buckets,"correlation":correlation,"growth_rates":growth_rates,
}
CASES={
"mean":[[{"values":[2,4,6]},4],[{"values":[3,7]},5]],
"median":[[{"values":[1,5,9]},5],[{"values":[1,2,3,4]},2.5]],
"population_std":[[{"values":[2,2,2]},0],[{"values":[0,2]},1]],
"population_variance":[[{"values":[0,2]},1],[{"values":[3,3,3]},0]],
"nearest_rank_percentile":[[{"values":[2,4,6,8],"percent":50},4],[{"values":[1,2,3,4,5],"percent":80},4]],
"moving_average":[[{"values":[1,3,5,7],"window":2},[2,4,6]],[{"values":[3,6,9],"window":3},[6]]],
"cumulative_sum":[[{"values":[1,2,3]},[1,3,6]],[{"values":[5,-2,4]},[5,3,7]]],
"min_max_scale":[[{"values":[2,4,6]},[0,0.5,1]],[{"values":[7,7]},[0,0]]],
"z_scores":[[{"values":[0,2]},[-1,1]],[{"values":[4,4]},[0,0]]],
"histogram_buckets":[[{"values":[1,2,5,11],"width":5},{"0":2,"5":1,"10":1}],[{"values":[0,4,8],"width":4},{"0":1,"4":1,"8":1}]],
"correlation":[[{"x":[1,2,3],"y":[2,4,6]},1],[{"x":[1,2,3],"y":[6,4,2]},-1]],
"growth_rates":[[{"values":[100,110,121]},[10,10]],[{"values":[50,25,50]},[-50,100]]],
}
