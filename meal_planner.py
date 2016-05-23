#!/usr/bin/env python

import csv
import random

foods = {}
food_ids = {}
nutrient_targets = {}
food_groups = {}

# Load knowledge

with open('data/foods.csv') as f:
  reader = csv.DictReader(f)
  for row in reader:
    name = row['Commonly consumed food']
    foods[name] = row
    foods[name]['prices'] = []
    food_ids[row['Commonly consumed food ID']] = name
    if row['Food group'] not in food_groups:
      food_groups[row['Food group']] = []
    food_groups[row['Food group']].append(name)

with open('data/nutrition.csv') as f:
  reader = csv.DictReader(f)
  for row in reader:
    if row['Commonly consumed food'] in foods:
      floats = {}
      for k,v, in row.items():
        try:
          floats[k] = float(v)
        except ValueError:
          pass
      foods[row['Commonly consumed food']]['nutrition'] = floats

with open('data/prices.csv') as f:
  reader = csv.DictReader(f)
  for row in reader:
    if row['Food Id '] in food_ids:
      name = food_ids[row['Food Id ']]
      foods[name]['prices'].append(row)

with open('data/nutrient_targets.csv') as f:
  reader = csv.DictReader(f)
  for row in reader:
    for measure, value in row.items():
      if '-' in value and '%' in value:
        bits = [float(x) for x in value.strip('% ').split('-')]
        row[measure] = {'min': bits[0], 'max': bits[1]}
      elif '<' in value:
        value = value.strip('<% E')
        row[measure] = {'min': float(value)}
      else:
        try:
          row[measure] = float(value)
        except ValueError:
          pass
      if measure == 'Energy MJ':
        row['Energy kJ'] = float(value) / 1000
    nutrient_targets[row['Age/gender']] = row

# Generate a plan

def get_meal_plan(person='adult women', selected_person_nutrient_targets=None):

  meal = []

  for group_name, items in food_groups.items():
    if len(items) > 3:
      meal.extend(random.sample(items, 1))

  # Assess meal suitability

  nutrients = [foods[item]['nutrition'] for item in meal]
  nutrients_sum = dict([(k.strip(' g/10'), v) for k,v in nutrients[0].items()])

  for n in nutrients[1:]:
    for measure, value in n.items():
      measure = measure.strip(' g/10')
      nutrients_sum[measure] += value

  if not selected_person_nutrient_targets:
    selected_person_nutrient_targets = nutrient_targets[person]

  diff = {}

  targetmap = {
    'Sodium': 'sodium g',
    'CHO': 'CHO % energy',
    'protein':  'protein % energy or grams',
    'Sat fat': 'Saturated fat % energy',
    'Fat': 'Fat % energy',
    'Energy kJ': 'Energy kJ',
    'Sugars': 'Free sugars % energy*',
    'Fibre': 'fibre g'
  }

  for k, v in targetmap.items():
    x = nutrients_sum[k]
    t = selected_person_nutrient_targets[v]
    v = v.strip(' g*')
    if type(t) is float:
      diff[v] = x - t
    elif type(t) is dict:
      if '%' in v:
        x /= nutrients_sum['Energy kJ']
      if 'min' in t and 'max' in t:
        if x > t['min'] and x < t['max']:
          diff[v] = 0
        elif x < t['min']:
          diff[v] = x - t['min']
        elif x > t['max']:
          diff[v] = x - t['max']
      elif 'min' in t:
        if x < t['min']:
          diff[v] = 0
        else:
          diff[v] = x - t['min']

  return {'meal': meal, 'nutrients': nutrients_sum, 'diff': diff}

if __name__ == "__main__":
  meal_plan = get_meal_plan()
  print(meal_plan)