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
import sys

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
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
  'Discretionary foods % energy': 'Discretionary foods % energy',
  'Red meat': 'red meat (g)'
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
nutrientsTargetsHSheet = parse_sheet(xl_workbook.sheet_by_name('nutrient targets'), header=14, limit=8)
nutrientsTargetsCSheet = parse_sheet(xl_workbook.sheet_by_name('nutrient targets'), header=24, limit=8)
foodConstraintsHSheet = parse_sheet(xl_workbook.sheet_by_name('Constraints H(3)'), header=2)
foodConstraintsCSheet = parse_sheet(xl_workbook.sheet_by_name('Constraints C (3)'), header=1)
foodPricesSheet = parse_sheet(xl_workbook.sheet_by_name('Food prices to use'))
variableFoodPricesSheet = parse_sheet(xl_workbook.sheet_by_name('food prices'))

for row in foodsSheet:
  name = row['Commonly consumed food']
  if row['Food group'] == 'Sauces, dressings, spreads, sugars':
    row['Food group'] = 'Sauces'
  elif row['Food group'] == 'Protein foods: Meat, poultry, seafood, eggs, legumes, nuts':
    row['Food group'] = 'Protein'

  row['redmeat'] = row['Commonly consumed food ID'] in ["05067", "05069", "05073", "05074", "05089"]

  foods[name] = row
  foods[name]['variable prices'] = []
  food_ids[row['Commonly consumed food ID']] = name
  
  if row['Food group'] == ' Discretionary foods':
    row['Food group'] = 'Discretionary foods'

  if row['Food group'] not in food_groups:
    food_groups[row['Food group']] = {}

food_groups['Starchy vegetables'] = {}

isStarchy = False

for row in foodConstraintsHSheet:
  if row['Food ID'] in food_ids:
    name = food_ids[row['Food ID']]
    # per week
    foods[name]['constraints'] = {
      '14 boy': {'min': float(row['Min per week_2']) * 2, 'max': float(row['Max per week_2']) * 2 * MAX_SCALE},
      '7 girl': {'min': float(row['Min per week_3']) * 2, 'max': float(row['Max per week_3']) * 2 * MAX_SCALE},
      'adult man': {'min': float(row['Min per week']) * 2, 'max': float(row['Max per week']) * 2 * MAX_SCALE},
      'adult women': {'min': float(row['Min per week_1']) * 2, 'max': float(row['Max per week_1']) * 2 * MAX_SCALE}
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
      if partial in fg and row['Min per week']:
        food_groups[fg]['constraints_serves'] = {
          'adult man': {'min': row['Min per week'] / 7.0, 'max': row['Max per week'] / 7.0},
          'adult women': {'min': row['Min per week_1'] / 7.0, 'max': row['Max per week_1'] / 7.0},
          '14 boy': {'min': row['Min per week_2'] / 7.0, 'max': row['Max per week_2'] / 7.0},
          '7 girl': {'min': row['Min per week_3'] / 7.0, 'max': row['Max per week_3'] / 7.0}
        }

for row in foodConstraintsCSheet:
  if row['_2'] in food_ids:
    name = food_ids[row['_2']]
    # per week
    c = {
      '14 boy C': {'min': float(row['Min per wk_2']) * 2, 'max': float(row['Max per week_2']) * 2 * MAX_SCALE},
      '7 girl C': {'min': float(row['Min per wk_3']) * 2, 'max': float(row['Max per week_3']) * 2 * MAX_SCALE},
      'adult man C': {'min': float(row['Min per wk']) * 2, 'max': float(row['Max per week']) * 2 * MAX_SCALE},
      'adult women C': {'min': float(row['Min per wk_1']) * 2, 'max': float(row['Max per week_1']) * 2 * MAX_SCALE}
    }
    if 'constraints' not in foods[name]:
      h_defaults = dict([(k.strip(' C'), v) for k,v in c.items()])
      c.update(h_defaults)
      foods[name]['constraints'] = c
    else:
      foods[name]['constraints'].update(c)
    try:
      foods[name]['serve size'] = int(row['_4'])
    except ValueError:
      pass
  elif row['per week']:
    partial = row['per week'].split()[0]
    if partial == 'Meat,':
      partial = 'Protein'
    if partial == 'Fats':
      continue
    for fg in food_groups:
      if partial in fg and row['Min per wk']:
        c = {
          'adult man C': {'min': row['Min per wk'] / 7.0, 'max': row['Max per week'] / 7.0},
          'adult women C': {'min': row['Min per wk_1'] / 7.0, 'max': row['Max per week_1'] / 7.0},
          '14 boy C': {'min': row['Min per wk_2'] / 7.0, 'max': row['Max per week_2'] / 7.0},
          '7 girl C': {'min': row['Min per wk_3'] / 7.0, 'max': row['Max per week_3'] / 7.0}
        }
        if 'constraints_serves' not in food_groups[fg]:
          continue
          food_groups[fg]['constraints_serves'] = c
        else:
          food_groups[fg]['constraints_serves'].update(c)

food_groups['Starchy vegetables']['constraints_serves'].update({
          'adult man C': {'min': 0, 'max': 100},
          'adult women C': {'min': 0, 'max': 100},
          '14 boy C': {'min': 0, 'max': 100},
          '7 girl C': {'min': 0, 'max': 100}
})

for row in nutrientsSheet:
  fid = row['Common food ID']
  if fid not in food_ids:
    logger.debug("nutrition defined, but {} not known!".format(fid))
    continue

  floats = {}
  for k,v, in row.items():
    try:
      if k != 'Common food ID':
        floats[k] = float(v)
    except ValueError:
      pass
  name = food_ids[fid]
  foods[name]['nutrition'] = floats

for row in nutrientsTargetsHSheet:
  p = row['Healthy diet per day']
  p_strip = p.replace('aduilt', 'adult').replace(' min', '').replace(' max', '').replace('woman', 'women')
  n = nutrient_targets.get(p_strip, {})
  if 'min' in p:
    minormax = 'min'
  elif 'max' in p:
    minormax = 'max'

  for measure, value in row.items():
    if 'grams' in measure and measure != 'fibre grams' or '(s)' in measure:
      continue
    try:
      f = float(value)
      if measure == 'Energy MJ':
        measure = 'Energy kJ'
        f *= 1000
      measure = measure.replace("carb%", "CHO % energy").replace("fat %", "Fat % energy").replace("sat Fat", "Saturated fat").replace("protein %", "protein % energy").replace("grams", "g")
      if measure not in n:
        n[measure] = {}
      n[measure][minormax] = f
    except ValueError:
      pass
  n["Discretionary foods % energy"] = {'min': 0, 'max': 0}
  n["Alcohol % energy"] = {'min': 0, 'max': 50}
  n["Total sugars % energy"] = {'min': 0, 'max': 100}
  n['fibre g']['max'] = n['fibre g']['min'] * 4
  nutrient_targets[p_strip] = n

for row in nutrientsTargetsCSheet:
  p = row['Nutrient constraints                      Current diet per day']
  p_strip = p.replace('aduilt', 'adult').replace(' min', '').replace(' max', '').replace('woman', 'women') + ' C'
  n = nutrient_targets.get(p_strip, {})
  if 'min' in p:
    minormax = 'min'
  elif 'max' in p:
    minormax = 'max'

  for measure, value in row.items():
    if 'grams' in measure and measure != 'fibre grams' or '(s)' in measure:
      continue
    try:
      f = float(value)
      if measure == 'Energy MJ':
        measure = 'Energy kJ'
        f *= 1000
      measure = measure.replace('% E CI', '% energy').replace('%E CI', '% energy').replace(' CI', '').replace('fat', 'Fat').replace('Sat Fat', 'Saturated fat').replace('alcohol', 'Alcohol').replace('Sodium', 'sodium').replace(" +-10%", "").replace("protein %", "protein % energy").replace("Alcohol", "Alcohol % energy").replace("grams", "g").replace('total', 'Total')
      if measure not in n:
        n[measure] = {}
      #if minormax == 'min':
      #  f *= .9
      #else:
      #  f *= 1.1
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
  if row['Food Id'] not in food_ids:
    logger.debug("{} has a variable price but is not defined!".format(row['Food Id']))
    continue
  name = food_ids[row['Food Id']]
  foods[name]['variable prices'].append({
    'outlet type': row['outlet type'],
    'region': row['region'],
    'deprivation': int(row['deprivation']),
    'discount': 'discount' if row['discount'] == 'yes' else 'non-discount',
    'population group': row['population group'],
    'season': row['season'],
    'type': row['type'],
    'urban': 'urban' if row['urban'] == 'yes' else 'rural',
    'price/100g': row['price/100g']
  })

variable_prices = {}
vp_combos = set()

for food in foods:
  vp = foods[food]['variable prices']
  for entry in vp:
    for v in entry:
      if v == 'price/100g':
        continue
      if not v in variable_prices:
        variable_prices[v] = []
      if not entry[v] in variable_prices[v]:
        variable_prices[v].append(entry[v])
    vp_id = '_'.join([str(entry[k]) for k in sorted(entry.keys()) if k != 'price/100g'])
    vp_combos.add(vp_id)

for entry in variable_prices:
  variable_prices[entry].sort()

vp_keys = sorted(variable_prices.keys())
vp_values = [variable_prices[k] for k in vp_keys]

e = time.time()
logger.debug('load done, took {}s'.format(e-s))

# Generate a plan

def get_nutrients(meal):
  nutrients_sum = {'Discretionary foods % energy': 0, 'Alcohol % energy': 0, 'Red meat': 0}

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
    if foods[food]['Food group'] == 'Discretionary foods':
      nutrients_sum['Discretionary foods % energy'] += (foods[food]['nutrition']['Energy kJ/100g'] / 100) * amount
    if foods[food]['redmeat']:
      nutrients_sum['Red meat'] += amount

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
    if v not in target:
      continue
    t = target[v]
    if type(t) is float:
      diff[v] = x - t
    elif type(t) is dict:
      if 'min' in t and x < t['min']:
        diff[v] = x - t['min']
      elif 'max' in t and x > t['max']:
        diff[v] = x - t['max']
      else:
        diff[v] = 0

  return diff

def check_nutritional_diff(diff):
  return all(v == 0 for v in diff.values())

def get_meal_plans(person='adult man', selected_person_nutrient_targets=None, iteration_limit = 10000, min_serve_size_difference=.5, allowed_varieties=[1,2,3], allow_takeaways=False, selected_person_food_group_serve_targets={}):
  s = time.time()

  meal = {}
  meal_plans = {}
  vp_keys_effecting = set()
  
  if not selected_person_nutrient_targets:
    # per day
    selected_person_nutrient_targets = copy.deepcopy(nutrient_targets[person])

  if not selected_person_food_group_serve_targets:
    selected_person_food_group_serve_targets = dict([(fg,copy.deepcopy(food_groups[fg]['constraints_serves'][person])) for fg in food_groups if 'constraints_serves' in food_groups[fg] and person in food_groups[fg]['constraints_serves']])

  for measure in selected_person_nutrient_targets:
    try:
      # convert to fortnightly
      if '%' not in measure:
        if 'min' in selected_person_nutrient_targets[measure]:
          selected_person_nutrient_targets[measure]['min'] *= 14
        if 'max' in selected_person_nutrient_targets[measure]:
          selected_person_nutrient_targets[measure]['max'] *= 14
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
        if details['Food group'] == 'Alcohol' and selected_person_nutrient_targets['Alcohol % energy']['max'] == 0:
          continue
        if details['Food group'] == 'Discretionary foods' and selected_person_nutrient_targets['Discretionary foods % energy']['max'] == 0:
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
        # Check food group serve targets
        per_group = dict([(x,{'amount': 0, 'price': 0, 'serves': 0, 'variable prices': {}}) for x in food_groups])

        for item, amount in meal.items():
          fg = foods[item]['Food group']
          per_group[fg]['serves'] += amount / foods[item]['serve size']

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
          # Passed both nutritional check and fg serve check, lets do some compute heavy stuff

          vp_dict = {}
          total_price = 0
          varieties = []
          amounts = []
          for item, amount in meal.items():
            price = foods[item]['price/100g'] / 100 * amount
            total_price += price
            varieties.append(foods[item]['Variety'])
            amounts.append(amount)

            fg = foods[item]['Food group']
            per_group[fg]['amount'] += amount
            per_group[fg]['price'] += price

            for vp_id in vp_combos:
              match = None
              for row in foods[item]['variable prices']:
                row_id = '_'.join([str(row[k]) for k in vp_keys])
                if vp_id == row_id:
                  match = row['price/100g'] / 100 * amount
              if not match:
                match = price
              if vp_id not in vp_dict:
                vp_dict[vp_id] = 0
              vp_dict[vp_id] += match
              if vp_id not in per_group[fg]['variable prices']:
                per_group[fg]['variable prices'][vp_id] = 0
              per_group[fg]['variable prices'][vp_id] += match

          vp_dict = dict([(k,v) for k,v in vp_dict.items() if v != total_price])
          vp_keys_effecting.update(vp_dict.keys())
          for fg in per_group:
            per_group[fg]['variable prices'] = dict([(k,v) for k,v in per_group[fg]['variable prices'].items() if v != per_group[fg]['price']])
            vp_keys_effecting.update(per_group[fg]['variable prices'].keys())

          variety = np.average(varieties, weights=amounts)
          meal_plans[h] = {'meal': copy.copy(meal), 'price': total_price, 'variable prices': vp_dict, 'nutrition': nutrients, 'variety': variety, 'per_group': per_group}
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
            if foods[item]['Food group'] == 'Discretionary foods':
              foods_that_impact_this_measure.append(item)
          elif target_measure == 'Red meat g':
            if foods[item]['redmeat']:
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
        r = list(np.arange(t['min'], meal[food], foods[food]['serve size'] * min_serve_size_difference))[-10:]
      else:
        logger.debug("We're too low on {} - {} < {}".format(target_measure, nutrients[reverse_targetmap[target_measure]], nt['min']))
        r = list(np.arange(meal[food], t['max'], foods[food]['serve size'] * min_serve_size_difference))[:10]
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

  # Calculate statistics
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
      'nutrition': {},
      'variable_prices': {},
      'variable_prices_by_var': dict([(k, {}) for k in vp_keys])
    }
    for vp in vp_keys_effecting:
      vp_all = [m['variable prices'][vp] for h,m in meal_plans.items()]
      vp_min = min(vp_all)
      vp_max = max(vp_all)
      vp_mean = sum(vp_all) / len(vp_all)
      vp_std = np.std(vp_all)
      stats['variable_prices'][vp] = {
        'min': vp_min,
        'max': vp_max,
        'mean': vp_mean,
        'std': vp_std,
      }
      for k in vp_keys:
        for v in variable_prices[k]:
          test = str(v)
          if test == 'discount':
            test = '_discount'
          if test in vp:
            if v not in stats['variable_prices_by_var'][k]:
              stats['variable_prices_by_var'][k][v] = {
                'min': vp_min,
                'max': vp_max,
                'mean': vp_mean,
                'std': vp_std
              }
            else:
              stats['variable_prices_by_var'][k][v]['min'] = (stats['variable_prices_by_var'][k][v]['min'] + vp_min) / 2
              stats['variable_prices_by_var'][k][v]['max'] = (stats['variable_prices_by_var'][k][v]['max'] + vp_max) / 2
              stats['variable_prices_by_var'][k][v]['mean'] = (stats['variable_prices_by_var'][k][v]['mean'] + vp_mean) / 2
              stats['variable_prices_by_var'][k][v]['std'] = (stats['variable_prices_by_var'][k][v]['std'] + vp_std) / 2
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
        },
        'variable_prices': {}
      }
      for vp in vp_keys_effecting:
        vp_all = [m['per_group'][g]['variable prices'][vp] for h,m in meal_plans.items() if vp in m['per_group'][g]['variable prices']]
        if vp_all:
          stats['per_group'][g]['variable_prices'][vp] = {
            'min': min(vp_all),
            'max': max(vp_all),
            'mean': sum(vp_all) / len(vp_all),
            'std': np.std(vp_all),
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

  # Write to csv
  s = time.time()
  dt = str(datetime.datetime.now()).replace(':', '_')
  filename = 'csvs/{}.csv'.format(dt)
  with open(filename, 'w') as f:
    writer = csv.writer(f)
    writer.writerow(["Persona", "min/max"] + list(selected_person_nutrient_targets.keys()) + list(selected_person_food_group_serve_targets.keys()))
    writer.writerow([person, "min"] + [x.get('min') for x in selected_person_nutrient_targets.values()] + [x.get('min') for x in selected_person_food_group_serve_targets.values()])
    writer.writerow([person, "max"] + [x.get('max') for x in selected_person_nutrient_targets.values()] + [x.get('max') for x in selected_person_food_group_serve_targets.values()])
    writer.writerow([])
    writer.writerow(["Timestamp", "Iteration limit", "Min serve size difference", "Allowed varieties", "Allow takeaways"])
    writer.writerow([dt, iteration_limit, min_serve_size_difference, allowed_varieties, allow_takeaways])
    writer.writerow([])
    writer.writerow(["Results"])
    keys = sorted(meal.keys())
    writer.writerow(
      ["unique id", "price", "variety"] +
      keys +
      [x + ' ' + y for x in food_groups for y in ['amount', 'price', 'serves']] +
      [v for k,v in targetmap.items()] +
      [k + ' price' for k in vp_keys_effecting] +
      [x + ' ' + y + ' price' for x in food_groups for y in vp_keys_effecting]
    )
    for h,m in meal_plans.items():
      writer.writerow(
        [h, m['price'], m['variety']] +
        [m['meal'][k] for k in keys] +
        [m['per_group'][x][y] for x in food_groups for y in ['amount', 'price', 'serves']] +
        [m['nutrition'][k] for k,v in targetmap.items()] +
        [m['variable prices'][k] for k in vp_keys_effecting] +
        [m['per_group'][x]['variable prices'].get(y, m['per_group'][x]['price']) for x in food_groups for y in vp_keys_effecting]
      )
  e = time.time()
  logger.debug('write done, took {}s'.format(e-s))
  inputs = {'person': person, 'nutrient_targets': selected_person_nutrient_targets, 'iteration_limit': iteration_limit, 'min_serve_size_difference': min_serve_size_difference, 'allowed_varieties': allowed_varieties, 'allow_takeaways': allow_takeaways, 'selected_person_food_group_serve_targets': selected_person_food_group_serve_targets}
  return {'meal_plans': meal_plans, 'csv_file': filename, 'timestamp': dt, 'inputs': inputs, 'stats': stats}

if __name__ == "__main__":
  get_meal_plans("adult man")