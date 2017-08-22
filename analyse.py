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

food_groups = people[people.keys()[0]][0]['per_group'].keys()

for p, runs in people.items():
  target = h_people
  if p[-1] == 'C':
    target = c_people
  target[p] = {
    "total_meal_plans": sum([r['total_meal_plans'] for r in runs]),
    "per_group": {},
    "nutrition": {}
  }
  for k in ["price", "variety"]:
    target[p][k] = {
      "min": min([r[k]['min'] for r in runs]),
      "max": max([r[k]['max'] for r in runs]),
      "mean": np.mean([r[k]['mean'] for r in runs]),
      "std": np.mean([r[k]['std'] for r in runs if 'std' in r[k]])
    }
  for g in runs[0]['per_group']:
    if g not in target[p]['per_group']:
      target[p]['per_group'][g] = {}
    for measure in ["amount", "price", "serves"]:
      target[p]['per_group'][g][measure] = {
        "min": min([r['per_group'][g][measure]['min'] for r in runs]),
        "max": max([r['per_group'][g][measure]['max'] for r in runs]),
        "mean": np.mean([r['per_group'][g][measure]['mean'] for r in runs])
      }
  for measure in runs[0]['nutrition']:
    target[p]['nutrition'][measure] = {
      "min": min([r['nutrition'][measure]['min'] for r in runs]),
      "max": max([r['nutrition'][measure]['max'] for r in runs]),
      "mean": np.mean([r['nutrition'][measure]['mean'] for r in runs])
    }

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
  print("Variable price averages")
  print("Variable\tMin\tMean\tMax\tstdev")


print("Healthy household (adult man, adult woman, 14 boy, 7 girl) - 5 runs each (averaged before combining)")
report(h_people)
