#!/usr/bin/env python

import xlrd
import random
import pprint
import numpy as np
import time
import datetime
import copy
import logging
import os
import csv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('meal_planner')

try:
  os.mkdir('csvs')
except OSError:
  pass

try: # check whether python knows about 'basestring'
   basestring
except NameError: # no, it doesn't (it's Python3); use 'str' instead
   basestring=str

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
  'Sugars': 'Total sugars % energy',
  'Fibre': 'fibre g',
  'Alcohol % energy': 'Alcohol % energy',
  'Discretionary foods % energy': 'Discretionary foods % energy'
}

reverse_targetmap = dict([(v,k) for k,v in targetmap.items()])

target_to_measure = {
  'sodium mg': 'Sodium g/100g',
  'CHO % energy': 'CHO g/100g',
  'protein % energy': 'protein g/100g',
  'Saturated fat % energy': 'Sat fat g/100g',
  'Fat % energy': 'Fat g/100g',
  'Energy kJ': 'Energy kJ/100g',
  'Total sugars % energy': 'Sugars g/100g',
  'fibre g': 'Fibre g/100g'
}

MAX_SCALE = 2

def parse_sheet(sheet, header=0, limit=None):
  headers = []
  for c in range(sheet.ncols):
    key = str(sheet.cell(header, c).value).strip()
    headers.append(key)
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
nutrientsTargetsCSheet = parse_sheet(xl_workbook.sheet_by_name('Nutrient targets'), header=37, limit=8)
foodConstraintsHSheet = parse_sheet(xl_workbook.sheet_by_name('Food constraints H'), header=2)
foodConstraintsCSheet = parse_sheet(xl_workbook.sheet_by_name('Constraints C'), header=1)
foodPricesSheet = parse_sheet(xl_workbook.sheet_by_name('Food prices to use'))
variableFoodPricesSheet = parse_sheet(xl_workbook.sheet_by_name('food prices'))

for row in foodsSheet:
  name = row['Commonly consumed food']
  if row['Food group'] == 'Sauces, dressings, spreads, sugars':
    row['Food group'] = 'Sauces'
  elif row['Food group'] == 'Protein foods: Meat, poultry, seafood, eggs, legumes, nuts':
    row['Food group'] = 'Protein'
  foods[name] = row
  foods[name]['variable prices'] = []
  food_ids[row['Commonly consumed food ID']] = name

  if row['Food group'] not in food_groups:
    food_groups[row['Food group']] = {}

food_groups['Discretionary'] = {}
food_groups['Starchy vegetables'] = {}

isStarchy = False

for row in foodConstraintsHSheet:
  if row['Food ID'] in food_ids:
    name = food_ids[row['Food ID']]
    # per week
    foods[name]['constraints'] = {
      '14 boy': {'min': float(row['Min_1']) * 2, 'max': float(row['Max_1']) * 2 * MAX_SCALE},
      '7 girl': {'min': float(row['Min_2']) * 2, 'max': float(row['max']) * 2 * MAX_SCALE},
      'adult man': {'min': float(row['Min']) * 2, 'max': float(row['Max']) * 2 * MAX_SCALE},
      'adult women': {'min': float(row['']) * 2, 'max': float(row['_1']) * 2 * MAX_SCALE}
    }
    try:
      foods[name]['serve size'] = int(row['serve size'])
    except ValueError:
      pass
    if isStarchy:
      foods[name]['Food group'] = 'Starchy vegetables'
  elif row['Food']:
    partial = row['Food'].split()[0]
    if partial == 'Meat,':
      partial = 'Protein'
    if partial == 'Fats' or partial == 'grams':
      continue
    if partial == 'Starchy':
      isStarchy = True
    else:
      isStarchy = False
    for fg in food_groups:
      if partial in fg:
        food_groups[fg]['constraints_serves'] = {
          'adult man': {'min': row['Min'] / 7.0, 'max': row['Max'] / 7.0},
          'adult women': {'min': row[''] / 7.0, 'max': row['_1'] / 7.0},
          '14 boy': {'min': row['Min_1'] / 7.0, 'max': row['Max_1'] / 7.0},
          '7 girl': {'min': row['Min_2'] / 7.0, 'max': row['max'] / 7.0}
        }

for row in foodConstraintsCSheet:
  if row['1.0'] in food_ids:
    name = food_ids[row['1.0']]
    # per week
    c = {
      '14 boy C': {'min': float(row['Min_1']) * 2, 'max': float(row['Max_1']) * 2 * MAX_SCALE},
      '7 girl C': {'min': float(row['Min_2']) * 2, 'max': float(row['Max_2']) * 2 * MAX_SCALE},
      'adult man C': {'min': float(row['Min']) * 2, 'max': float(row['Max']) * 2 * MAX_SCALE},
      'adult women C': {'min': float(row['Min per wk']) * 2, 'max': float(row['Max per day']) * 2 * MAX_SCALE}
    }
    if 'constraints' not in foods[name]:
      foods[name]['constraints'] = c
    else:
      foods[name]['constraints'].update(c)
    try:
      foods[name]['serve size'] = int(row['_4'])
    except ValueError:
      pass
  elif row['']:
    partial = row[''].split()[0]
    if partial == 'Meat,':
      partial = 'Protein'
    if partial == 'Fats':
      continue
    for fg in food_groups:
      if partial in fg:
        c = {
          'adult man C': {'min': 0, 'max': 100},
          'adult women C': {'min': 0, 'max': 100},
          '14 boy C': {'min': 0, 'max': 100},
          '7 girl C': {'min': 0, 'max': 100}
        }
        if 'constraints_serves' not in food_groups[fg]:
          continue
          food_groups[fg]['constraints_serves'] = c
        else:
          food_groups[fg]['constraints_serves'].update(c)

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

for row in nutrientsTargetsSheet:
  n = {}
  for measure, value in row.items():
    if isinstance(value, basestring):
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
  n["Alcohol % energy"] = {'min': 0, 'max': 50}
  n["Discretionary foods % energy"] = {'min': 0, 'max': 50}
  n["Total sugars % energy"] = {'min': 0, 'max': 100}
  n.pop("Free sugars % energy*")
  nutrient_targets[row['Healthy diet per day']] = n

for row in nutrientsTargetsCSheet:
  p = row['Nutrient constraints                      Current diet per day']
  p_strip = p.replace('aduilt', 'adult').replace(' min', '').replace(' max', '').replace('woman', 'women') + ' C'
  if 'min' in p:
    minormax = 'min'
  elif 'max' in p:
    minormax = 'max'
  n = nutrient_targets.get(p_strip, {})
  for measure, value in row.items():
    if measure == 'Total sugars grams' or measure == 'Energy reported from survey':
      continue
    try:
      f = float(value)
      if measure == 'Energy MJ CI (calculated from BMI)':
        measure = 'Energy kJ'
        f *= 1000
      measure = measure.replace('% E CI', '% energy').replace('%E CI', '% energy').replace(' CI', '').replace('fat', 'Fat').replace('saturated Fat', 'Saturated fat').replace('alcohol', 'Alcohol').replace('Sodium', 'sodium')
      if measure not in n:
        n[measure] = {}
      if minormax == 'min':
        f *= .9
      else:
        f *= 1.1
      n[measure][minormax] = f
    except ValueError:
      pass
  n["Discretionary foods % energy"] = {'min': 0, 'max': 50}
  nutrient_targets[p_strip] = n

for row in foodPricesSheet:
  try:
    name = food_ids[row['Commonly consumed food ID']]
    foods[name]['price/100g'] = row['price/100g AP']
  except KeyError:
    pass

for row in variableFoodPricesSheet:
  name = food_ids[row['Food Id']]
  foods[name]['variable prices'].append(row)

#pprint.pprint(foods)
#exit(1)

e = time.time()
logger.debug('load done, took {}s'.format(e-s))

# Generate a plan

def get_nutrients(meal):
  nutrients_sum = {'Discretionary foods % energy': 0, 'Alcohol % energy': 0}

  for food, amount in meal.items():
    for measure, value in foods[food]['nutrition'].items():
      measure = measure.strip(' g/10')
      # Nutrient values are per 100g, amount is how many g
      value = (value / 100) * amount
      if measure in nutrients_sum:
        nutrients_sum[measure] += value
      else:
        nutrients_sum[measure] = value
    if foods[food]['Food group'] == 'Alcohol':
      nutrients_sum['Alcohol % energy'] += (foods[food]['nutrition']['Energy kJ/100g'] / 100) * amount
    if foods[food]['core/disc'] == 'd':
      nutrients_sum['Discretionary foods % energy'] += (foods[food]['nutrition']['Energy kJ/100g'] / 100) * amount

  # Convert g to % E
  for k, v in nutrients_sum.items():
    if k == 'Fat' or k == 'Sat fat':
      nutrients_sum[k] = ((v * 37.7) / nutrients_sum['Energy kJ']) * 100
    if k == 'CHO' or k == 'protein' or k == 'Sugars':
      nutrients_sum[k] = ((v * 16.7) / nutrients_sum['Energy kJ']) * 100
    if k == 'Alcohol % energy':
      nutrients_sum[k] = (v / nutrients_sum['Energy kJ']) * 100
    if k == 'Discretionary foods % energy':
      nutrients_sum[k] = (v / nutrients_sum['Energy kJ']) * 100

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

def get_meal_plans(person='adult man', selected_person_nutrient_targets=None, iteration_limit = 10000, min_serve_size_difference=.5, allowed_varieties=[1,2,3], allow_takeaways=False, selected_person_food_group_serve_targets={}):
  s = time.time()

  meal = {}
  meal_plans = {}
  
  if not selected_person_nutrient_targets:
    # per day
    selected_person_nutrient_targets = copy.deepcopy(nutrient_targets[person])

  if not selected_person_food_group_serve_targets:
    selected_person_food_group_serve_targets = dict([(fg,copy.deepcopy(food_groups[fg]['constraints_serves'][person])) for fg in food_groups if 'constraints_serves' in food_groups[fg] and person in food_groups[fg]['constraints_serves']])

  for measure in selected_person_nutrient_targets:
    try:
      # convert to fortnightly
      if '%' not in measure:
        selected_person_nutrient_targets[measure]['max'] *= 14
        try:
          selected_person_nutrient_targets[measure]['min'] *= 14
        except KeyError:
          pass
    except TypeError:
      pass

  for fg in selected_person_food_group_serve_targets:
    selected_person_food_group_serve_targets[fg]['max'] *= 14
    selected_person_food_group_serve_targets[fg]['min'] *= 14

  logger.info('{} selected. nutritional targets: {}'.format(person, selected_person_nutrient_targets))
  # Get a random starting meal plan

  combinations = 1

  for food, details in foods.items():
    try:
      if details['Variety'] in allowed_varieties:
        if details['Food group'] == 'Takeaway' and not allow_takeaways:
          continue
        t = details['constraints'][person]
        r = list(np.arange(t['min'], t['max'], details['serve size'] * min_serve_size_difference))
        if len(r) > 0:
          meal[food] = random.choice(r)
          combinations *= len(r)
    except KeyError as e:
      logger.debug('not including {} due to missing {}'.format(food, e))

  logger.debug('{} items in menu. {} distinct possible menus'.format(len(meal), combinations))
  # Iteratively improve
  
  for i in range(iteration_limit):
    nutrients = get_nutrients(meal)
    diff = get_diff(nutrients, selected_person_nutrient_targets)
    logger.debug('Iteration: {}'.format(i))
    target_measure = None
    target_fg = None

    if check_nutritional_diff(diff):
      h = hash(frozenset(meal.items()))
      if h in meal_plans:
        logger.debug('Already recorded {}'.format(h))
      else:
        total_price = 0
        varieties = []
        amounts = []
        per_group = dict([(x,{'amount': 0, 'price': 0, 'serves': 0}) for x in food_groups])
        for item, amount in meal.items():
          price = foods[item]['price/100g'] / 100 * amount
          total_price += price
          varieties.append(foods[item]['Variety'])
          amounts.append(amount)
          fg = foods[item]['Food group']
          per_group[fg]['amount'] += amount
          per_group[fg]['serves'] += amount / foods[item]['serve size']
          per_group[fg]['price'] += price
          if foods[item]['core/disc'] == 'd':
            per_group['Discretionary']['amount'] += amount
            per_group['Discretionary']['serves'] += amount / foods[item]['serve size']
            per_group['Discretionary']['price'] += price
        off_food_groups = []
        for fg in per_group:
          if fg in selected_person_food_group_serve_targets:
            c = selected_person_food_group_serve_targets[fg]
            v = per_group[fg]['serves']
            if v < c['min'] or v > c['max']:
              off_food_groups.append(fg)
        if off_food_groups:
          target_fg = random.choice(off_food_groups)
        else:
          variety = np.average(varieties, weights=amounts)
          meal_plans[h] = {'meal': copy.copy(meal), 'price': total_price, 'nutrition': nutrients, 'variety': variety, 'per_group': per_group}
          logger.debug('Hit!')
    else:
      off_measures = []
      for measure, value in diff.items():
        if value != 0:
          off_measures.append(measure)
      target_measure = random.choice(off_measures)
      reverse_target_measure = target_to_measure.get(target_measure, 'Energy kJ/100g')

    if target_measure:
      foods_that_impact_this_measure = []
      for item in meal:
        try:
          if target_measure == 'Alcohol % energy':
            if foods[item]['Food group'] == 'Alcohol':
              foods_that_impact_this_measure.append(item)
          elif target_measure == 'Discretionary foods % energy':
            if foods[item]['core/disc'] == 'd':
              foods_that_impact_this_measure.append(item)
          elif foods[item]['nutrition'][reverse_target_measure] != 0:
            foods_that_impact_this_measure.append(item)
        except KeyError as e:
          # Nutrional info for this food/target not known
          pass
      food = random.choice(foods_that_impact_this_measure)
      t = foods[food]['constraints'][person]
      nt = selected_person_nutrient_targets[target_measure]
      if diff[target_measure] > 0:
        logger.debug("We're too high on {} - {} > {}".format(target_measure, nutrients[reverse_targetmap[target_measure]], nt['max']))
        r = list(np.arange(t['min'], meal[food], foods[food]['serve size'] * min_serve_size_difference))
      else:
        logger.debug("We're too low on {} - {} < {}".format(target_measure, nutrients[reverse_targetmap[target_measure]], nt['min']))
        r = list(np.arange(meal[food], t['max'], foods[food]['serve size'] * min_serve_size_difference))
      logger.debug('{} has {} {} and must be between {}g-{}g. Options {} - current {}g'.format(food, foods[food]['nutrition'][reverse_target_measure], reverse_target_measure, t['min'], t['max'], r, meal[food]))
    elif target_fg:
      c = selected_person_food_group_serve_targets[target_fg]
      v = per_group[target_fg]['serves']
      foods_that_impact_this_measure = []
      for item in meal:
        if foods[item]['Food group'] == target_fg:
          foods_that_impact_this_measure.append(item)
      food = random.choice(foods_that_impact_this_measure)
      t = foods[food]['constraints'][person]
      if v > c['max']:
        logger.debug("Food group {} has too many serves - {} > {}".format(target_fg,v,c['max']))
        r = list(np.arange(t['min'], meal[food], foods[food]['serve size'] * min_serve_size_difference))
      elif v < c['min']:
        logger.debug("Food group {} has too few serves - {} < {}".format(target_fg,v,c['min']))
        r = list(np.arange(meal[food], t['max'], foods[food]['serve size'] * min_serve_size_difference))
      logger.debug('{} has {} serves and must be between {}g-{}g. Options {} - current {}g'.format(food, foods[item]['serve size'], t['min'], t['max'], r, meal[food]))
    else:
      # Randomly move off a hit
      food = random.choice(list(meal.keys()))
      t = foods[food]['constraints'][person]
      r = list(np.arange(t['min'], t['max'], foods[food]['serve size'] * min_serve_size_difference))
    
    if len(r) > 0:
      new_val = random.choice(r)
      logger.debug("Changing {} from {}g to {}g".format(food, meal[food], new_val))
      meal[food] = new_val

  logger.debug('last meal: {}\nnutritional diff: {}\nnutrients: {}'.format(pprint.pformat(meal), pprint.pformat(diff), pprint.pformat(nutrients)))
  
  prices = [m['price'] for h,m in meal_plans.items()]
  varieties = [m['variety'] for h,m in meal_plans.items()]
  stats = {'total_meal_plans': len(meal_plans)}
  if prices and varieties:
    stats = {
      'price': {
        'min': min(prices),
        'max': max(prices),
        'mean': sum(prices) / len(prices),
        'std': np.std(prices)
      },
      'variety': {
        'min': min(varieties),
        'max': max(varieties),
        'mean': sum(varieties) / len(varieties)
      },
      'total_meal_plans': len(meal_plans),
      'per_group': {},
      'nutrition': {}
    }
    for g in food_groups:
      prices = [m['per_group'][g]['price'] for h,m in meal_plans.items()]
      serves = [m['per_group'][g]['serves'] for h,m in meal_plans.items()]
      amount = [m['per_group'][g]['amount'] for h,m in meal_plans.items()]
      stats['per_group'][g] = {
        'price': {
          'min': min(prices),
          'max': max(prices),
          'mean': sum(prices) / len(prices)
        },
        'serves': {
          'min': min(serves),
          'max': max(serves),
          'mean': sum(serves) / len(serves)
        },
        'amount': {
          'min': min(amount),
          'max': max(amount),
          'mean': sum(amount) / len(amount)
        }
      }
    for k,v in targetmap.items():
      values = [m['nutrition'][k] for h,m in meal_plans.items()]
      stats['nutrition'][v] = {
        'min': min(values),
        'max': max(values),
        'mean': sum(values) / len(values)
      }
  
  e = time.time()
  logger.info('iterations done, took {}s'.format(e-s))
  logger.debug('Matched meals: {}'.format(pprint.pformat(meal_plans)))
  logger.info('{} matched meals'.format(len(meal_plans)))
  s = time.time()
  dt = str(datetime.datetime.now()).replace(':', '_')
  filename = 'csvs/{}.csv'.format(dt)
  with open(filename, 'w') as f:
    writer = csv.writer(f)
    writer.writerow(["Persona", "min/max"] + list(selected_person_nutrient_targets.keys()) + list(selected_person_food_group_serve_targets.keys()))
    writer.writerow([person, "min"] + [x['min'] for x in selected_person_nutrient_targets.values()] + [x['min'] for x in selected_person_food_group_serve_targets.values()])
    writer.writerow([person, "max"] + [x['max'] for x in selected_person_nutrient_targets.values()] + [x['max'] for x in selected_person_food_group_serve_targets.values()])
    writer.writerow([])
    writer.writerow(["Timestamp", "Iteration limit", "Min serve size difference", "Allowed varieties", "Allow takeaways"])
    writer.writerow([dt, iteration_limit, min_serve_size_difference, allowed_varieties, allow_takeaways])
    writer.writerow([])
    writer.writerow(["Results"])
    keys = sorted(meal.keys())
    writer.writerow(["unique id", "price", "variety"] + keys + [x + ' ' + y for x in food_groups for y in ['amount', 'price', 'serves']] + [v for k,v in targetmap.items()])
    for h,m in meal_plans.items():
      writer.writerow([h, m['price'], m['variety']] + [m['meal'][k] for k in keys] + [m['per_group'][x][y] for x in food_groups for y in ['amount', 'price', 'serves']] + [m['nutrition'][k] for k,v in targetmap.items()])
  e = time.time()
  logger.debug('write done, took {}s'.format(e-s))
  inputs = {'person': person, 'nutrient_targets': selected_person_nutrient_targets, 'iteration_limit': iteration_limit, 'min_serve_size_difference': min_serve_size_difference, 'allowed_varieties': allowed_varieties, 'allow_takeaways': allow_takeaways, 'selected_person_food_group_serve_targets': selected_person_food_group_serve_targets}
  return {'meal_plans': meal_plans, 'csv_file': filename, 'timestamp': dt, 'inputs': inputs, 'stats': stats}

if __name__ == "__main__":
  logger.setLevel(logging.DEBUG)
  meal_plans = get_meal_plans("adult man")