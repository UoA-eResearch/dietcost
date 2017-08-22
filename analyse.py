#!/usr/bin/env python

import json
import sys
import pprint
import numpy as np
import scipy.stats as st

people = {}

for filename in sys.argv[1:]:
  with open(filename) as f:
    results = json.load(f)
  p = results['inputs']['person']
  s = results['stats']
  if p not in people:
    people[p] = []
  people[p].append(s)

h_people = {}
c_people = {}

food_groups = sorted(people[people.keys()[0]][0]['per_group'].keys())
nutrient_measures = sorted(people[people.keys()[0]][0]['nutrition'].keys())
vpv_keys = set()

for p, runs in people.items():
  runs = [r for r in runs if r['total_meal_plans'] > 0]
  if len(runs) == 0:
    continue
  target = h_people
  if p[-1] == 'C':
    target = c_people
  target[p] = {
    "total_meal_plans": sum([r['total_meal_plans'] for r in runs]),
    "per_group": {},
    "nutrition": {},
    "vpv": {}
  }
  for k in ["price", "variety"]:
    target[p][k] = {
      "min": min([r[k]['min'] for r in runs]),
      "max": max([r[k]['max'] for r in runs]),
      "mean": np.mean([r[k]['mean'] for r in runs]),
      "std": np.mean([r[k]['std'] for r in runs if 'std' in r[k]])
    }
  for g in food_groups:
    if g not in target[p]['per_group']:
      target[p]['per_group'][g] = {}
    for measure in ["amount", "price", "serves"]:
      target[p]['per_group'][g][measure] = {
        "min": min([r['per_group'][g][measure]['min'] for r in runs]),
        "max": max([r['per_group'][g][measure]['max'] for r in runs]),
        "mean": np.mean([r['per_group'][g][measure]['mean'] for r in runs])
      }
  for measure in nutrient_measures:
    target[p]['nutrition'][measure] = {
      "min": min([r['nutrition'][measure]['min'] for r in runs]),
      "max": max([r['nutrition'][measure]['max'] for r in runs]),
      "mean": np.mean([r['nutrition'][measure]['mean'] for r in runs])
    }
  for k in runs[0]['variable_prices_by_var']:
    for v in runs[0]['variable_prices_by_var'][k]:
      ck = "{}: {}".format(k, v)
      vpv_keys.add(ck)
      target[p]['vpv'][ck] = {
        "min": min([r['variable_prices_by_var'][k][v]['min'] for r in runs]),
        "max": max([r['variable_prices_by_var'][k][v]['max'] for r in runs]),
        "mean": np.mean([r['variable_prices_by_var'][k][v]['mean'] for r in runs]),
        "std": np.mean([r['variable_prices_by_var'][k][v]['std'] for r in runs])
      }

vpv_keys = sorted(vpv_keys)

# Form a household
def report(people):
  total_meal_plans = np.prod([s["total_meal_plans"] for p,s in people.items()])
  print("Total combined meal plans: {:.2E}".format(total_meal_plans))
  price_std = np.mean([s['price']['std'] for p, s in people.items()])
  price_mean = np.mean([s['price']['mean'] for p, s in people.items()])
  moe = 1.96 * price_std / np.sqrt(len(people))
  print("Price range: ${:.2f} - ${:.2f} (${:.2f} average). stdev = {:.2f}, 95% CI range = ${:.2f} - ${:.2f}".format(
    min(s['price']['min'] for p, s in people.items()),
    max(s['price']['max'] for p, s in people.items()),
    price_mean,
    price_std,
    price_mean - moe,
    price_mean + moe
  ))
  print("Variety range: {:.2f} - {:.2f} ({:.2f} average)".format(
    min(s['variety']['min'] for p, s in people.items()),
    max(s['variety']['max'] for p, s in people.items()),
    np.mean([s['variety']['mean'] for p, s in people.items()])
  ))
  print("Food group breakdown")
  print("Category\tAmount\tPrice\tServes")
  for g in food_groups:
    print("{}\t{:.2f}g-{:.2f}g ({:.2f} avg)\t${:.2f}-${:.2f} (${:.2f} avg)\t{:.2f}-{:.2f} ({:.2f} avg)".format(
      g,
      sum([s['per_group'][g]["amount"]["min"] for p, s in people.items()]),
      sum([s['per_group'][g]["amount"]["max"] for p, s in people.items()]),
      sum([s['per_group'][g]["amount"]["mean"] for p, s in people.items()]),
      sum([s['per_group'][g]["price"]["min"] for p, s in people.items()]),
      sum([s['per_group'][g]["price"]["max"] for p, s in people.items()]),
      sum([s['per_group'][g]["price"]["mean"] for p, s in people.items()]),
      sum([s['per_group'][g]["serves"]["min"] for p, s in people.items()]),
      sum([s['per_group'][g]["serves"]["max"] for p, s in people.items()]),
      sum([s['per_group'][g]["serves"]["mean"] for p, s in people.items()]),
    ))
  print("Average nutrition")
  print("Measure\tMin\tMean\tMax")
  for m in nutrient_measures:
    print("{}\t{:.2f}\t{:.2f}\t{:.2f}".format(
      m,
      np.mean([s['nutrition'][m]['min'] for p, s in people.items()]),
      np.mean([s['nutrition'][m]['mean'] for p, s in people.items()]),
      np.mean([s['nutrition'][m]['max'] for p, s in people.items()])
    ))
  print("Variable price averages")
  print("Variable\tMin\tMean\tMax\tstdev")
  for ck in vpv_keys:
    print("{}\t${:.2f}\t${:.2f}\t${:.2f}\t{:.2f}".format(
      ck,
      sum([s['vpv'][ck]['min'] for p, s in people.items() if ck in s['vpv']]),
      sum([s['vpv'][ck]['mean'] for p, s in people.items() if ck in s['vpv']]),
      sum([s['vpv'][ck]['max'] for p, s in people.items() if ck in s['vpv']]),
      sum([s['vpv'][ck]['std'] for p, s in people.items() if ck in s['vpv']])
    ))

print("Healthy household (adult man: {} meal plans, adult woman: {} meal plans, 14 boy: {} meal plans, 7 girl: {} meal plans) - 5 runs each (averaged before combining)\n".format(
h_people.get('adult man', {}).get('total_meal_plans', 0),
h_people.get('adult women', {}).get('total_meal_plans', 0),
h_people.get('14 boy', {}).get('total_meal_plans', 0),
h_people.get('7 girl', {}).get('total_meal_plans', 0),
))
report(h_people)
print("\n\nCurrent household (adult man: {} meal plans, adult woman: {} meal plans, 14 boy: {} meal plans, 7 girl: {} meal plans) - 5 runs each (averaged before combining)\n".format(
c_people.get('adult man C', {}).get('total_meal_plans', 0),
c_people.get('adult women C', {}).get('total_meal_plans', 0),
c_people.get('14 boy C', {}).get('total_meal_plans', 0),
c_people.get('7 girl C', {}).get('total_meal_plans', 0),
))
report(c_people)

