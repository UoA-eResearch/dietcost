#!/usr/bin/env python

import xlrd
import random
import pprint
import numpy as np
import time
import copy
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('meal_planner')

foods = {}
food_ids = {}
nutrient_targets = {}
food_groups = {}

s = time.time()

# Used to match nutritional information to nutritional targets
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

reverse_targetmap = dict([(v,k) for k,v in targetmap.items()])

target_to_measure = {
  'sodium mg': 'Sodium g/100g',
  'CHO % energy': 'CHO g/100g',
  'protein % energy': 'protein g/100g',
  'Saturated fat % energy': 'Sat fat g/100g',
  'Fat % energy': 'Fat g/100g',
  'Energy kJ': 'Energy kJ/100g',
  'Free sugars % energy*': 'Sugars g/100g',
  'fibre g': 'Fibre g/100g'
}

SERVE_SIZE = .5
MAX_SCALE = 2

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
foodConstraintsHSheet = parse_sheet(xl_workbook.sheet_by_name('Food constraints H'), header=2)
#foodConstraintsCSheet = parse_sheet(xl_workbook.sheet_by_name('Constraints C'), header=2)
foodPricesSheet = parse_sheet(xl_workbook.sheet_by_name('Food prices to use'))

for row in foodsSheet:
  name = row['Commonly consumed food']
  foods[name] = row
  food_ids[row['Commonly consumed food ID']] = name

for row in foodConstraintsHSheet:
  try:
    name = food_ids[row['Food ID']]
    # per week
    foods[name]['constraints'] = {
      '14 boy': {'min': row['Min_1'], 'max': row['Max_1'] * MAX_SCALE},
      '7 girl': {'min': row['Min_2'], 'max': row['max'] * MAX_SCALE},
      'adult man': {'min': row['Min'], 'max': row['Max'] * MAX_SCALE},
      'adult women': {'min': row[''], 'max': row['_1'] * MAX_SCALE}
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
        if k != 'Commonly consumed food ID':
          floats[k] = float(v)
      except ValueError:
        pass
    name = food_ids[row['Commonly consumed food ID']]
    foods[name]['nutrition'] = floats

for name, data in foods.items():
  if data['Food group'] not in food_groups:
    food_groups[data['Food group']] = []
  food_groups[data['Food group']].append(name)

for row in nutrientsTargetsSheet:
  n = {}
  for measure, value in row.items():
    if type(value) is unicode:
      if '-' in value and '%' in value:
        bits = [float(x) for x in value.strip('% ').split('-')]
        n[measure] = {'min': bits[0], 'max': bits[1]}
      elif '<' in value:
        value = value.strip('<% E')
        n[measure] = {'min': 0, 'max': float(value)}
    if measure == 'Energy MJ':
      n['Energy kJ'] = {'min': (value - (value * 0.015)) * 1000, 'max': (value + (value * 0.015)) * 1000}
    elif measure == 'sodium mg':
      n[measure] = {'min': 0, 'max': value}
    elif measure == 'fibre g':
      n[measure] = {'min': value - (value*0.015), 'max': value + (value*0.5)}
  nutrient_targets[row['Healthy diet per day']] = n

for row in foodPricesSheet:
  try:
    name = food_ids[row['Commonly consumed food ID']]
    foods[name]['price/100g'] = row['price/100g']
  except KeyError:
    pass

e = time.time()
logger.debug('load done, took {}s'.format(e-s))

# Generate a plan

def get_nutrients(meal):
  nutrients_sum = {}

  for food, amount in meal.items():
    for measure, value in foods[food]['nutrition'].items():
      measure = measure.strip(' g/10')
      # Nutrient values are per 100g, amount is how many g
      value = (value / 100) * amount
      if measure in nutrients_sum:
        nutrients_sum[measure] += value
      else:
        nutrients_sum[measure] = value

  # Convert g to % E
  for k, v in nutrients_sum.items():
    if k == 'Fat' or k == 'Sat fat':
      nutrients_sum[k] = ((v * 37.7) / nutrients_sum['Energy kJ']) * 100
    if k == 'CHO' or k == 'protein' or k == 'Sugars':
      nutrients_sum[k] = ((v * 16.7) / nutrients_sum['Energy kJ']) * 100

  return nutrients_sum

def get_diff(nutrients, target):
  diff = {}

  for k, v in targetmap.items():
    x = nutrients[k]
    t = target[v]
    if type(t) is float:
      diff[v] = x - t
    elif type(t) is dict:
      if 'min' in t and 'max' in t:
        if x > t['min'] and x < t['max']:
          diff[v] = 0
        elif x < t['min']:
          diff[v] = x - t['min']
        elif x > t['max']:
          diff[v] = x - t['max']
      elif 'max' in t:
        if x < t['max']:
          diff[v] = 0
        else:
          diff[v] = x - t['max']

  return diff

def check_nutritional_diff(diff):
  return all(v == 0 for v in diff.values())

def get_meal_plans(person='adult man', selected_person_nutrient_targets=None, iteration_limit = 10000):
  s = time.time()

  meal = {}
  meal_plans = {}
  
  if not selected_person_nutrient_targets:
    # per day
    selected_person_nutrient_targets = copy.deepcopy(nutrient_targets[person])
  
  for measure in selected_person_nutrient_targets:
    try:
      # convert to weekly
      if '%' not in measure:
        selected_person_nutrient_targets[measure]['max'] *= 7
        try:
          selected_person_nutrient_targets[measure]['min'] *= 7
        except KeyError:
          pass
    except TypeError:
      pass

  logger.info('{} selected. nutritional targets: {}'.format(person, selected_person_nutrient_targets))
  # Get a random starting meal plan

  combinations = 1

  for food, details in foods.items():
    try:
      t = foods[food]['constraints'][person]
      r = list(np.arange(t['min'], t['max'], foods[food]['serve size'] * SERVE_SIZE))
      if len(r) > 0:
        meal[food] = random.choice(r)
        combinations *= len(r)
    except KeyError:
      pass

  logger.debug('{} items in menu. {} distinct possible menus'.format(len(meal), combinations))
  # Iteratively improve
  
  for i in range(iteration_limit):
    nutrients = get_nutrients(meal)
    diff = get_diff(nutrients, selected_person_nutrient_targets)
    diff['Free sugars % energy*'] = 0 # Disable sugar check
    logger.debug('Iteration: {}'.format(i))
    if check_nutritional_diff(diff):
      h = hash(frozenset(meal.items()))
      price = 0
      varieties = []
      amounts = []
      for item, amount in meal.items():
        price += foods[item]['price/100g'] / 100 * amount
        varieties.append(foods[item]['Variety'])
        amounts.append(amount)
      variety = np.average(varieties, weights=amounts)
      meal_plans[h] = {'meal': copy.copy(meal), 'price': price, 'variety': variety}
      target_measure = None
      logger.debug('Hit!')
    else:
      off_measures = []
      for measure, value in diff.items():
        if value != 0:
          off_measures.append(measure)
      target_measure = random.choice(off_measures)
      reverse_target_measure = target_to_measure[target_measure]

    if target_measure:
      foods_that_impact_this_measure = []
      for item in meal:
        try:
          if foods[item]['nutrition'][reverse_target_measure] != 0:
            foods_that_impact_this_measure.append(item)
        except KeyError as e:
          # Nutrional info for this food/target not known
          pass
      food = random.choice(foods_that_impact_this_measure)
      t = foods[food]['constraints'][person]
      nt = selected_person_nutrient_targets[target_measure]
      if diff[target_measure] > 0:
        logger.debug("We're too high on {} - {} > {}".format(target_measure, nutrients[reverse_targetmap[target_measure]], nt['max']))
        r = list(np.arange(t['min'], meal[food], foods[food]['serve size'] * SERVE_SIZE))
      else:
        logger.debug("We're too low on {} - {} < {}".format(target_measure, nutrients[reverse_targetmap[target_measure]], nt['min']))
        r = list(np.arange(meal[food], t['max'], foods[food]['serve size'] * SERVE_SIZE))
    else:
      food = random.choice(meal.keys())
      t = foods[food]['constraints'][person]
      r = list(np.arange(t['min'], t['max'], foods[food]['serve size'] * SERVE_SIZE))
    
    logger.debug('{} has {} {} and must be between {}g-{}g. Options {} - current {}g'.format(food, foods[item]['nutrition'][reverse_target_measure], reverse_target_measure, t['min'], t['max'], r, meal[food]))
    if len(r) > 0:
      new_val = random.choice(r)
      logger.debug("Changing {} from {}g to {}g".format(food, meal[food], new_val))
      meal[food] = new_val

  logger.debug('last meal: {}\nnutritional diff: {}\nnutrients: {}'.format(pprint.pformat(meal), pprint.pformat(diff), pprint.pformat(nutrients)))
  
  e = time.time()
  logger.info('iterations done, took {}s'.format(e-s))
  logger.debug('Matched meals: {}'.format(pprint.pformat(meal_plans)))
  logger.info('{} matched meals'.format(len(meal_plans)))
  return meal_plans

if __name__ == "__main__":
  logger.setLevel(logging.DEBUG)
  meal_plans = get_meal_plans()