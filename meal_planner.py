#!/usr/bin/env python

import csv
import random
from pprint import pprint

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
          if measure in ['Energy MJ', 'fibre g', 'sodium g']:
            row[measure] = float(value)
          else:
            row[measure] = float(value)
        except ValueError:
          pass
      if measure == 'Energy MJ':
        row['Energy kJ'] = row[measure] * 1000
    nutrient_targets[row['Age/gender']] = row

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

reverse_targetmap = {
  'sodium': 'Sodium g/100g',
  'CHO % energy': 'CHO g/100g',
  'protein % energy or grams': 'protein g/100g',
  'Saturated fat % energy': 'Sat fat g/100g',
  'Fat % energy': 'Fat g/100g',
  'Energy kJ': 'Energy kJ/100g',
  'Free sugars % energy': 'Sugars g/100g',
  'fibre': 'Fibre g/100g'
}

# Generate a plan

def get_nutrients(meal):
  nutrients = [foods[item]['nutrition'] for item in meal]
  nutrients_sum = dict([(k.strip(' g/10'), v) for k,v in nutrients[0].items()])

  for n in nutrients[1:]:
    for measure, value in n.items():
      measure = measure.strip(' g/10')
      nutrients_sum[measure] += value

  return nutrients_sum

def get_diff(nutrients, target):
  diff = {}

  for k, v in targetmap.items():
    x = nutrients[k]
    t = target[v]
    v = v.strip(' g*')
    if type(t) is float:
      diff[v] = x - t
    elif type(t) is dict:
      if '%' in v:
        x /= nutrients['Energy kJ']
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

  return diff

def get_meal_plan(person='adult women', selected_person_nutrient_targets=None):

  meal = {}
  
  if not selected_person_nutrient_targets:
    selected_person_nutrient_targets = nutrient_targets[person]

  # Get a random starting meal plan
  
  starting_amounts = 1

  for group_name, items in food_groups.items():
    if len(items) > starting_amounts:
      items = random.sample(items, starting_amounts)
      for item in items:
        meal[item] = 100

  # Iteratively improve
  
  iteration_limit = 100000
  
  for i in range(0, iteration_limit):
    nutrients = get_nutrients(meal)

    diff = get_diff(nutrients, selected_person_nutrient_targets)
    
    # Pick a nutritional measure to improve
    target_nutrient_target_diff = random.choice(diff.keys())
    if diff[target_nutrient_target_diff] == 0:
      # Can't improve on perfection
      continue
    nutrient_target_name = reverse_targetmap[target_nutrient_target_diff]
    # Pick a meal item to improve
    target_meal_item = random.choice(meal.keys())
    target_meal_item_info = foods[target_meal_item]
    # Get an alternative from it's food group
    items_in_food_group = food_groups[target_meal_item_info['Food group']][:]
    items_in_food_group.remove(target_meal_item)
    alternative_meal_item = random.choice(items_in_food_group)
    alternative_meal_item_info = foods[alternative_meal_item]
    # Compare them
    if (diff[target_nutrient_target_diff] < 0 and alternative_meal_item_info['nutrition'][nutrient_target_name] < target_meal_item_info['nutrition'][nutrient_target_name]) or (diff[target_nutrient_target_diff] > 0 and alternative_meal_item_info['nutrition'][nutrient_target_name] > target_meal_item_info['nutrition'][nutrient_target_name]):
      # alternative_meal_item is better - swap it out
      del meal[target_meal_item]
      meal[alternative_meal_item] = 100
  
  return {'meal': meal, 'nutrients': nutrients, 'diff': diff}

if __name__ == "__main__":
  meal_plan = get_meal_plan()
  pprint(meal_plan)