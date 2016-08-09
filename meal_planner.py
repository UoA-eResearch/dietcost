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
  'CHO': 'CHO % energy',
  'protein':  'protein % energy',
  'Sat fat': 'Saturated fat % energy',
  'Fat': 'Fat % energy',
  'Energy kJ': 'Energy kJ',
  'Sugars': 'Free sugars % energy*',
  'Fibre': 'fibre g'
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
    headers.append(str(key))
  rows = []
  if not limit:
    limit = sheet.nrows
  else:
    limit += header + 1
  for r in range(header+1, limit):
    row = {}
    for c in range(len(headers)):
      header = headers[c]
      index = 1
      while header in row:
        header = '{}_{}'.format(headers[c], index)
        index += 1
      row[header] = sheet.cell(r,c).value
    rows.append(row)
  return rows

# Load knowledge

f = "dataset.xlsx"
xl_workbook = xlrd.open_workbook(f)
sheet_names = xl_workbook.sheet_names()

foodsSheet = parse_sheet(xl_workbook.sheet_by_name('common foods'))
nutrientsSheet = parse_sheet(xl_workbook.sheet_by_name('nutrients'))
nutrientsTargetsSheet = parse_sheet(xl_workbook.sheet_by_name('Nutrient targets'), header=0, limit=4)
foodConstraintsSheet = parse_sheet(xl_workbook.sheet_by_name('Food constraints H'), header=2)
foodPricesSheet = parse_sheet(xl_workbook.sheet_by_name('Food prices to use'))

for row in foodsSheet:
  name = row['Commonly consumed food']
  foods[name] = row
  foods[name]['prices'] = []
  food_ids[row['Commonly consumed food ID']] = name

for row in foodConstraintsSheet:
  try:
    name = food_ids[row['Food ID']]
    # per week
    foods[name]['constraints'] = {
      '14 boy': {'min': row['Min_1'], 'max': row['Max_1']},
      '7 girl': {'min': row['Min_2'], 'max': row['max']},
      'adult man': {'min': row['Min'], 'max': row['Max']},
      'adult women': {'min': row[''], 'max': row['_1']}
    }
    try:
      foods[name]['serve size'] = int(row['serve size'])
    except ValueError:
      pass
  except KeyError:
    pass

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

for row in nutrientsTargetsSheet:
  for measure, value in row.items():
    if type(value) is unicode:
      if '-' in value and '%' in value:
        bits = [float(x) for x in value.strip('% ').split('-')]
        row[measure] = {'min': bits[0], 'max': bits[1]}
      elif '<' in value:
        value = value.strip('<% E')
        row[measure] = {'min': float(value)}
    if measure == 'Energy MJ':
      row['Energy kJ'] = row[measure] * 1000
  nutrient_targets[row['Healthy diet per day']] = row

for row in foodPricesSheet:
  try:
    name = food_ids[row['Commonly consumed food ID']]
    foods[name]['price/100g'] = row['price/100g']
  except KeyError:
    pass

# Generate a plan

def get_nutrients(meal):
  nutrients_sum = {}

  for food, amount in meal.items():
    for measure, value in foods[food]['nutrition'].items():
      measure = measure.strip(' g/10')
      value *= amount
      if measure in nutrients_sum:
        nutrients_sum[measure] += value
      else:
        nutrients_sum[measure] = value

  return nutrients_sum

def get_diff(nutrients, target):
  diff = {}

  for k, v in targetmap.items():
    x = nutrients[k]
    t = target[v]
    if v == 'sodium mg':
      v = 'sodium g'
      t /= 1000
    #v = v.strip(' g*')
    if type(t) is float:
      diff[v] = x - t
    elif type(t) is dict:
      # Convert g to % E
      if k == 'Fat' or k == 'Sat fat':
        x = (x * 37.7) / nutrients['Energy kJ']
      if k == 'CHO' or k == 'protein' or k == 'Sugars':
        x = (x * 16.7) / nutrients['Energy kJ']
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
    # per day
    selected_person_nutrient_targets = nutrient_targets[person]
  
  for measure in selected_person_nutrient_targets:
    try:
      selected_person_nutrient_targets[measure] *= 7
    except TypeError:
      pass

  # Get a random starting meal plan

  for food, details in foods.items():
    try:
      meal[food] = details['constraints'][person]['min']
    except KeyError:
      pass

  # Iteratively improve
  
  pprint(selected_person_nutrient_targets)
  
  nutrients = get_nutrients(meal)

  diff = get_diff(nutrients, selected_person_nutrient_targets)
  
  return {'meal': meal, 'nutrients': nutrients, 'diff': diff}

if __name__ == "__main__":
  meal_plan = get_meal_plan()
  pprint(meal_plan)