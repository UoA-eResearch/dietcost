#!/usr/bin/env python

import xlrd
import random
from pprint import pprint

foods = {}
food_ids = {}
nutrient_targets = {}
food_groups = {}

targetmap = {
  'Sodium': 'sodium mg',
  'CHO': 'CHO grams',
  'protein':  'protein grams',
  'Sat fat': 'saturated fat grams',
  'Fat': 'fat grams',
  'Energy kJ': 'Energy kJ',
  'Sugars': 'total sugar grams',
  'Fibre': 'fibre grams'
}

reverse_targetmap = {
  'sodium mg': 'Sodium g/100g',
  'CHO grams': 'CHO g/100g',
  'protein grams': 'protein g/100g',
  'saturated fat grams': 'Sat fat g/100g',
  'fat grams': 'Fat g/100g',
  'Energy kJ': 'Energy kJ/100g',
  'total sugar grams': 'Sugars g/100g',
  'fibre grams': 'Fibre g/100g'
}

def parse_sheet(sheet, header=0, limit=None):
  headers = []
  for c in range(sheet.ncols):
    key = sheet.cell(header, c).value.strip()
    if key:
      headers.append(str(key))
  rows = []
  if not limit:
    limit = sheet.nrows
  else:
    limit += header + 1
  for r in range(header+1, limit):
    row = {}
    for c in range(len(headers)):
      row[headers[c]] = sheet.cell(r,c).value
    rows.append(row)
  return rows

# Load knowledge

f = "Food prices datasets ehealth 30 May 2016 .xlsx"
xl_workbook = xlrd.open_workbook(f)
sheet_names = xl_workbook.sheet_names()

foodsSheet = parse_sheet(xl_workbook.sheet_by_name('common foods'))
nutrientsSheet = parse_sheet(xl_workbook.sheet_by_name('nutrients'))
nutrientsTargetsSheet = parse_sheet(xl_workbook.sheet_by_name('Nutrient targets'), header=14, limit=8)
foodPricesSheet = parse_sheet(xl_workbook.sheet_by_name('food prices'))

for row in foodsSheet:
  name = row['Commonly consumed food']
  foods[name] = row
  foods[name]['prices'] = []
  food_ids[row['Commonly consumed food ID']] = name

for row in nutrientsSheet:
  if row['Commonly consumed food ID'] in food_ids:
    floats = {}
    for k,v, in row.items():
      try:
        if k in reverse_targetmap.values():
          floats[k] = float(v)
      except ValueError:
        floats[k] = 0
    name = food_ids[row['Commonly consumed food ID']]
    foods[name]['nutrition'] = floats

#foods = dict([(k,v) for k,v in foods.items() if 'nutrition' in v])

for name, data in foods.items():
  if data['Food group'] not in food_groups:
    food_groups[data['Food group']] = []
  food_groups[data['Food group']].append(name)

for i in range(0, len(nutrientsTargetsSheet), 2):
  minrow = nutrientsTargetsSheet[i]
  maxrow = nutrientsTargetsSheet[i+1]
  minrow['Energy kJ'] = minrow['Energy MJ'] * 1000
  maxrow['Energy kJ'] = maxrow['Energy MJ'] * 1000
  age_gender = minrow['Healthy diet per day'].replace(' min', '')
  nutrient_targets[age_gender] = {'min': minrow, 'max': maxrow}

for row in foodPricesSheet:
  try:
    name = food_ids[row['Food Id']]
    foods[name]['prices'].append(row)
  except KeyError:
    pass



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
    mn = target['min'][v]
    mx = target['max'][v]
    if x > mn and x < mx:
      diff[v] = 0
    elif x < mn:
      diff[v] = x - mn
    elif x > mx:
      diff[v] = x - mx

  return diff

def get_meal_plan(person='adult woman', selected_person_nutrient_targets=None):

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
  
  iteration_limit = 10000
  
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