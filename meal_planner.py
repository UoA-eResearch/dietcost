#!/usr/bin/env python3

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
import json
import argparse

parser = argparse.ArgumentParser(description='Meal planner')
parser.add_argument('-i', '--iterations', dest="iterations", type=lambda x: int(float(x)), nargs='?', default=50000, help='how many times should the algorithm attempt to improve?')
parser.add_argument('-f', '--folder', dest='folder', type=str, nargs='?', default='.', help='a folder to put the csv/json output into')
parser.add_argument('-d', '--dataset', dest='dataset', type=str, nargs='?', default='dataset.xlsx', help='the dataset to use')
parser.add_argument('-p', '--persona', dest='persona', type=str, nargs='?', default='adult man', help='which person to run the algorithm for')

parser.add_argument('-t', '--takeaways', dest='allow_takeaways', action='store_true', help='include takeaways in meal plans')
parser.add_argument('-nt', '--no-takeaways', dest='allow_takeaways', action='store_false', help='forbid takeaways')
parser.set_defaults(allow_takeaways=True)

parser.add_argument('-disc', '--discretionary', dest="discretionary", type=int, nargs='?', default=100, help='Maximum percentage of discretionary foods')
parser.add_argument('-a', '--alcohol', dest="alcohol", type=int, nargs='?', default=100, help='Maximum percentage of Alcohol')
parser.add_argument('-om', '--override-min', dest="override_min", type=int, nargs='?', default=None, help='Override minimum quantity for all food items')

parser.add_argument("-q", "--quiet", action="store_const", dest="loglevel", const=logging.ERROR, default=logging.INFO, help="decrease output verbosity")
parser.add_argument("-v", "--verbose", action="store_const", dest="loglevel", const=logging.DEBUG, default=logging.INFO, help="increase output verbosity")

args, unknown = parser.parse_known_args()

logging.basicConfig(stream=sys.stdout, level=args.loglevel)
logger = logging.getLogger('meal_planner')

csv_folder = os.path.join(args.folder, 'csvs')
try:
  os.mkdir(csv_folder)
except OSError:
  pass

json_folder = os.path.join(args.folder, 'json')
try:
  os.mkdir(json_folder)
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
  'Sodium m': 'sodium mg',
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
  'sodium mg': 'Sodium mg/100g',
  'CHO % energy': 'CHO g/100g',
  'protein % energy': 'protein g/100g',
  'Saturated fat % energy': 'Sat fat g/100g',
  'Fat % energy': 'Fat g/100g',
  'Energy kJ': 'Energy kJ/100g',
  'Total sugars % energy': 'Sugars g/100g',
  'fibre g': 'Fibre g/100g'
}

linked_foods = {
  'milk-cereal': {
     # The total number of serves of milk is higher than or equal to the total number of serves of breakfast cereals
    'lower': ["03046", "03047", "03048", "03065", "03068", "03050"], # cereal
    'higher' : ["04059", "04060", "04058", "04065", "04068"], # milk
  },
  'spread-bread': {
    # The total number of serves of spread is equal to or lower than the total number of serves of bread and crackers
    'lower': ["05083", "06088", "06089", "08110", "08098", "08108", "08097"], # spread
    'higher': ["03036", "03037", "03038", "03040", "03044", "03062"], # bread/crackers
  }
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

f = args.dataset
xl_workbook = xlrd.open_workbook(f)
sheet_names = xl_workbook.sheet_names()

foodsSheet = parse_sheet(xl_workbook.sheet_by_name('common foods'))
nutrientsSheet = parse_sheet(xl_workbook.sheet_by_name('nutrients'))
nutrientsTargetsPFSheet = parse_sheet(xl_workbook.sheet_by_name('nutrient targets'), header=28, limit=8)
nutrientsTargetsPVSheet = parse_sheet(xl_workbook.sheet_by_name('nutrient targets'), header=39, limit=8)
nutrientsTargetsHSheet = parse_sheet(xl_workbook.sheet_by_name('nutrient targets'), header=50, limit=8)
nutrientsTargetsCSheet = parse_sheet(xl_workbook.sheet_by_name('nutrient targets'), header=60, limit=8)
foodConstraintsHSheet = parse_sheet(xl_workbook.sheet_by_name('Constraints Healthy'), header=2)
foodConstraintsCSheet = parse_sheet(xl_workbook.sheet_by_name('Constraints Current'), header=2)
foodConstraintsPFSheet = parse_sheet(xl_workbook.sheet_by_name('Constraints Planetary_F'), header=2)
foodConstraintsPVSheet = parse_sheet(xl_workbook.sheet_by_name('Constraints Planetary_V'), header=2)
foodPricesSheet = parse_sheet(xl_workbook.sheet_by_name('food prices to use'))
variableFoodPricesSheet = parse_sheet(xl_workbook.sheet_by_name('food prices'))
foodWasteSheet = parse_sheet(xl_workbook.sheet_by_name('food waste'))

f = "cpiprices.xlsx"
xl_workbook = xlrd.open_workbook(f)
cpiPricesSheet = parse_sheet(xl_workbook.sheet_by_name('food prices'))

variableFoodPricesSheet += cpiPricesSheet

f = "NZ Food Emissions Database.xlsx"
xl_workbook = xlrd.open_workbook(f)
emissions = parse_sheet(xl_workbook.sheet_by_name('database_common_foods'), header = 2)

for row in foodsSheet:
  name = row['Commonly consumed food']
  if not name:
    print("Missing name on row:", row)
    exit(1)
  if row['Food group'] == 'Sauces, dressings, spreads, sugars':
    row['Food group'] = 'Sauces'
  elif "Protein" in row['Food group']:
    row['Food group'] = 'Protein'

  row['redmeat'] = row['Commonly consumed food ID'] in ["05065", "05067", "05073", "05074", "05089"]

  foods[name] = row
  foods[name]['variable prices'] = []
  foods[name]["constraints"] = {}
  food_ids[int(row['Commonly consumed food ID'])] = name

  if row['Food group'] == ' Discretionary foods':
    row['Food group'] = 'Discretionary foods'

  if row['Food group'] not in food_groups:
    food_groups[row['Food group']] = {
      "constraints_serves": {}
    }

# kgCO2e/kg
emissions_keys = ['Farming & processing (100-year GWP)', 'Farming & processing (20-year GWP)', 'Transit packaging', 'Consumer packaging', 'Transport', 'Warehouse/ distribution', 'Refrigeration', 'Overheads', '100-year GWP', '20-year GWP']

for row in emissions:
  if row["Match ID"]:
    for fid in str(row["Match ID"]).split():
      try:
        name = food_ids[int(float(fid))]
        foods[name]["emissions"] = row
      except:
        logger.warning(f"{fid} in emissions sheet not known")

for row in foodWasteSheet:
  if row["Commonly consumed food ID"]:
    try:
      name = food_ids[int(row["Commonly consumed food ID"])]
    except:
      logger.warning("{} in food waste sheet not known".format(row["Commonly consumed food ID"]))
    try:
      foods[name]["waste_multiplier"] = float(row["food waste multiple (avoidable)"])
    except ValueError:
      pass

food_groups['Starchy vegetables'] = {
  "constraints_serves": {}
}

def parseFoodConstraints(sheet, suffix = ""):
  isStarchy = False
  for row in sheet:
    # This row contains constraints for a given food item
    if "Food ID" in row:
      row["Commonly consumed food ID"] = row["Food ID"]
    if "Food group" not in row or not row["Food group"]:
      row["Food group"] = row["Commonly consumed food"]
    if row['Commonly consumed food ID'] and int(row['Commonly consumed food ID']) in food_ids:
      name = food_ids[int(row['Commonly consumed food ID'])]
      if row["Commonly consumed food"] != name:
        logger.warning("name mismatch: name in {} sheet {} != name in common foods sheet {}".format(suffix, row["Commonly consumed food"], name))
      # convert day to per week
      c = {
        'adult man' + suffix: {'min': float(row['Min per week'] or 0) * 2, 'max': float(row['Max per week'] or 0) * 2 * MAX_SCALE},
        'adult women' + suffix: {'min': float(row['Min per week_1'] or 0) * 2, 'max': float(row['Max per week_1'] or 0) * 2 * MAX_SCALE},
        '14 boy' + suffix: {'min': float(row['Min per week_2'] or 0) * 2, 'max': float(row['Max per week_2'] or 0) * 2 * MAX_SCALE},
        '7 girl' + suffix: {'min': float(row['Min per week_3'] or 0) * 2, 'max': float(row['Max per week_3'] or 0) * 2 * MAX_SCALE},
      }
      if args.override_min != None:
        logger.warning(f"Override {name} min to {args.override_min}")
        for person in c:
          c[person]["min"] = args.override_min
      foods[name]['constraints'].update(c)
      try:
        foods[name]['serve size'] = int(row['serve size'])
      except ValueError:
        pass
      if isStarchy:
        foods[name]['Food group'] = 'Starchy vegetables'

      if suffix == " C":
        foods[name]['Variety_C'] = row['Variety']
        if partial != 'Discretionary' and foods[name]['Food group'] == 'Discretionary foods':
          if partial == 'Grains':
            fg_header = 'Grains'
          elif partial == 'starchy':
            fg_header = 'Starchy vegetables'
          elif partial == 'Sauces':
            fg_header = 'Sauces'
          elif partial == 'Protein':
            fg_header = 'Protein'
          foods[name]['Food group_C'] = fg_header
      else:
        foods[name]['Variety'] = row['Variety']

    # This row contains constraints for a given food group
    elif row['Food group']:
      # Use the first word to uniquely identify food group
      fg_header = row['Food group'].strip()
      partial = fg_header.replace(",", " ").split()[0]
      if partial == 'Meat':
        partial = 'Protein'
      if partial == 'grams':
        continue
      if partial == 'Starchy':
        isStarchy = True
      else:
        isStarchy = False
      if partial == "Alcohol":
        continue
      for fg in food_groups:
        if partial in fg and type(row["Min per week"]) == float:
          food_groups[fg]['constraints_serves'].update({
            'adult man' + suffix: {'min': row['Min per week'] / 7.0, 'max': row['Max per week'] / 7.0},
            'adult women' + suffix: {'min': row['Min per week_1'] / 7.0, 'max': row['Max per week_1'] / 7.0},
            '14 boy' + suffix: {'min': row['Min per week_2'] / 7.0, 'max': row['Max per week_2'] / 7.0},
            '7 girl' + suffix: {'min': row['Min per week_3'] / 7.0, 'max': row['Max per week_3'] / 7.0}
          })

parseFoodConstraints(foodConstraintsHSheet)
parseFoodConstraints(foodConstraintsCSheet, " C")
parseFoodConstraints(foodConstraintsPFSheet, " PF")
parseFoodConstraints(foodConstraintsPVSheet, " PV")

food_groups['Starchy vegetables']['constraints_serves'].update({
          'adult man C': {'min': 0, 'max': 100},
          'adult women C': {'min': 0, 'max': 100},
          '14 boy C': {'min': 0, 'max': 100},
          '7 girl C': {'min': 0, 'max': 100}
})

for row in nutrientsSheet:
  fid = int(row['Commonly consumed food ID'])
  if fid not in food_ids:
    logger.warning("nutrition defined, but {} not known!".format(fid))
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

def parseNutrientTargets(sheet, suffix = ""):
  for row in sheet:
    personkey = [k for k in row.keys() if "diet per day" in k][0]
    p = row[personkey]
    p_strip = p.replace('aduilt', 'adult').replace(' min', '').replace(' max', '').replace('woman', 'women') + suffix
    n = nutrient_targets.get(p_strip, {})
    if 'min' in p:
      minormax = 'min'
    elif 'max' in p:
      minormax = 'max'

    for measure, value in row.items():
      if 'grams' in measure and measure != 'fibre grams':
        continue
      try:
        if value == "max":
          value = 100
        f = float(value)
        if '(s)' in measure:
          measure = measure.replace("vege", "Vegetables").replace(" (s)", "").replace("+-30%", "").replace("dairy", "Dairy/alternatives").capitalize()
          if food_groups[measure]['constraints_serves'][p_strip][minormax] != f:
            logger.warning("Override {} {} for {} from {} to {}".format(measure, minormax, p_strip, food_groups[measure]['constraints_serves'][p_strip][minormax], f))
            food_groups[measure]['constraints_serves'][p_strip][minormax] = f
        else:
          if measure == 'Energy MJ':
            measure = 'Energy kJ'
            f *= 1000
          if measure == "fat %":
            measure = "Fat % energy"
          measure = measure.replace("carb%", "CHO % energy").replace("sat fat %", "Saturated fat % energy").replace("protein %", "protein % energy").replace("grams", "g")
          measure = measure.replace('% E CI', '% energy').replace(' CI', '').replace('Sat fat', 'Saturated fat').replace('alcohol E%', 'Alcohol % energy').replace('Sodium', 'sodium').replace("+-30%", "").replace("grams", "g").replace('total', 'Total').strip()
          if measure not in n:
            n[measure] = {}
          n[measure][minormax] = f
      except ValueError:
        pass
    n["Discretionary foods % energy"] = {'min': 0, 'max': args.discretionary}
    n["Alcohol % energy"] = {'min': 0, 'max': args.alcohol}
    if "Total sugars % energy" not in n:
      n["Total sugars % energy"] = {'min': 0, 'max': 100}
  #  n['fibre g']['max'] = n['fibre g']['min'] * 4
    nutrient_targets[p_strip] = n

parseNutrientTargets(nutrientsTargetsHSheet)
parseNutrientTargets(nutrientsTargetsCSheet, " C")
parseNutrientTargets(nutrientsTargetsPFSheet, " PF")
parseNutrientTargets(nutrientsTargetsPVSheet, " PV")


for row in foodPricesSheet:
  try:
    name = food_ids[int(row['Commonly consumed food ID'])]
    foods[name]['price/100g'] = float(row['price/100g AP'])
  except KeyError:
    logger.warning("{} has a price but is not defined!".format(row['Commonly consumed food ID']))
  except ValueError:
    logger.warning("{} is not a valid price for {} - must be float".format(row['price/100g AP'], name))

# Sanity check

for food in foods:
  if 'price/100g' not in foods[food]:
    logger.error("No price for {}!".format(food))
  if 'nutrition' not in foods[food] or len(foods[food]['nutrition']) == 0:
    logger.error("No nutrition for {}!".format(food))
  elif 'Energy kJ/100g' not in foods[food]['nutrition'] or foods[food]['nutrition']['Energy kJ/100g'] == 0:
    logger.error("{} doesn't have energy".format(food))

for row in variableFoodPricesSheet:
  if not row['Commonly consumed food ID']:
    continue
  if int(row['Commonly consumed food ID']) not in food_ids:
    logger.warning("{} has a variable price but is not defined!".format(row['Commonly consumed food ID']))
    continue
  if not row['price/100g AP']:
    continue
  name = food_ids[int(row['Commonly consumed food ID'])]
  foods[name]['variable prices'].append({
    'outlet type': row['outlet type'],
    'region': row['region'],
    #'deprivation': int(row['deprivation'] or 0),
    'discount': 'discount' if row['discount'] == 'yes' else 'non-discount',
    'population group': row['population group'],
    'season': row['season'],
    'type': row['type'],
    'urban': 'urban' if row['urban'] == 'yes' else 'rural',
    'price/100g': row['price/100g AP'],
    'year': int(row.get('year') or 0)
  })

variable_prices = {}
vp_combos = set()

for food in foods:
  vp = foods[food]['variable prices']
  vp_by_id = {}
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
    if type(entry["price/100g"]) == float:
      if vp_id not in vp_by_id:
        vp_by_id[vp_id] = []
      vp_by_id[vp_id].append(entry['price/100g'])
  for vp, entries in vp_by_id.items():
    if entries:
      vp_by_id[vp] = np.mean(entries)
  foods[food]['variable prices'] = vp_by_id

for food in foods:
  sm = []
  fp = []
  for vp, price in foods[food]['variable prices'].items():
    if "supermarket" in vp:
      sm.append(price)
    if "fresh produce store" in vp:
      fp.append(price)
  if sm and fp:
    sm = sum(sm) / len(sm)
    fp = sum(fp) / len(fp)
    if fp > sm:
      print("{} costs ${} at a supermarket and ${} at a fresh produce store".format(food, round(sm, 2), round(fp, 2)))

for entry in variable_prices:
  variable_prices[entry].sort()

vp_keys = sorted(variable_prices.keys())
vp_values = [variable_prices[k] for k in vp_keys]

e = time.time()
logger.info('load done, took {}s'.format(e-s))

def get_fg_for_p(details, person):
  if person.endswith('C') and 'Food group_C' in details:
    return details['Food group_C']
  return details['Food group']

def get_v_for_p(details, person):
  if person.endswith('C') and 'Variety_C' in details:
    return details['Variety_C']
  return details['Variety']

# Generate a plan

def get_nutrients(meal, person = ''):
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
    if get_fg_for_p(foods[food], person) == 'Alcohol':
      nutrients_sum['Alcohol % energy'] += (foods[food]['nutrition']['Energy kJ/100g'] / 100) * amount
    if get_fg_for_p(foods[food], person) == 'Discretionary foods':
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

def get_random_meal_plan(person, selected_person_nutrient_targets, min_serve_size_difference, allowed_varieties, allow_takeaways):
  meal = {}
  combinations = 1

  for food, details in foods.items():
    try:
      variety = get_v_for_p(details, person)
      if variety in allowed_varieties:
        if get_fg_for_p(details, person) == 'Takeaway' and not allow_takeaways:
          continue
        if get_fg_for_p(details, person) == 'Alcohol' and selected_person_nutrient_targets['Alcohol % energy']['max'] == 0:
          continue
        if get_fg_for_p(details, person) == 'Discretionary foods' and selected_person_nutrient_targets['Discretionary foods % energy']['max'] == 0:
          continue
        if 'price/100g' not in details:
          logger.warning('not including {} due to missing price'.format(food))
          continue
        t = details['constraints'][person]
        r = list(np.arange(t['min'], t['max'], details['serve size'] * min_serve_size_difference))
        if len(r) > 0:
          if (get_fg_for_p(details, person) == 'Discretionary foods' or get_fg_for_p(details, person) == 'Takeaway') and not person.endswith('C'):
            if random.random() > .4:
              continue
          meal[food] = random.choice(r)
          combinations *= len(r)
      else:
        logger.warning("not including {} as {} is not in allowed varieties {}".format(food, variety, allowed_varieties))
    except KeyError as e:
      logger.warning('not including {} due to missing {}'.format(food, e))
  return meal, combinations

def convert_to_fortnightly(selected_person_nutrient_targets):
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
  return selected_person_nutrient_targets

def get_meal_plans(person='adult man', selected_person_nutrient_targets=None, iteration_limit = 50000, min_serve_size_difference=.5, allowed_varieties=[1,2,3], allow_takeaways=False, selected_person_food_group_serve_targets={}):
  s = time.time()

  meal_plans = {}
  vp_keys_effecting = set()

  if not selected_person_nutrient_targets:
    # per day
    selected_person_nutrient_targets = copy.deepcopy(nutrient_targets[person])

  if not selected_person_food_group_serve_targets:
    selected_person_food_group_serve_targets = dict([(fg,copy.deepcopy(food_groups[fg]['constraints_serves'][person])) for fg in food_groups if 'constraints_serves' in food_groups[fg] and person in food_groups[fg]['constraints_serves']])

  selected_person_nutrient_targets = convert_to_fortnightly(selected_person_nutrient_targets)

  for fg in selected_person_food_group_serve_targets:
    selected_person_food_group_serve_targets[fg]['max'] *= 14
    selected_person_food_group_serve_targets[fg]['min'] *= 14

  logger.info('{} selected. nutritional targets: {}'.format(person, selected_person_nutrient_targets))
  # Get a random starting meal plan
  meal, combinations = get_random_meal_plan(person, selected_person_nutrient_targets, min_serve_size_difference, allowed_varieties, allow_takeaways)
  comb_str = str(combinations)

  if len(meal) == 0:
    logger.error("0 items in menu!!!")
  logger.info('{} items in menu. {}E+{} distinct possible menus'.format(len(meal), comb_str[0], len(comb_str)-1))

  iterations_spent_optimising_constraint = {}

  # Iteratively improve

  for i in range(iteration_limit):
    nutrients = get_nutrients(meal, person)
    diff = get_diff(nutrients, selected_person_nutrient_targets)
    logger.debug('Iteration: {}'.format(i))
    target_measure = None
    target_fg = None
    target_link = None

    if check_nutritional_diff(diff):
      h = hash(frozenset(meal.items()))
      if h in meal_plans:
        logger.debug('Already recorded {}'.format(h))
      else:
        # Check food group serve targets
        per_group = dict([(x,{'amount': 0, 'price': 0, 'serves': 0, 'variable prices': {}}) for x in food_groups])

        # Check link constraints
        per_link = dict([(name, {'lsum': 0, 'hsum': 0, 'low': [], 'high': []}) for name in linked_foods])

        per_item_serves = {}

        for item, amount in meal.items():
          fg = get_fg_for_p(foods[item], person)
          serves = amount / foods[item]['serve size']
          per_item_serves[item] = serves
          per_group[fg]['serves'] += serves
          fid = foods[item]['Commonly consumed food ID']
          for name, link in linked_foods.items():
            if fid in link['lower']:
              per_link[name]['lsum'] += serves
              per_link[name]['low'].append(item)
            if fid in link['higher']:
              per_link[name]['hsum'] += serves
              per_link[name]['high'].append(item)

        off_food_groups = []
        for fg in per_group:
          if fg in selected_person_food_group_serve_targets:
            c = selected_person_food_group_serve_targets[fg]
            v = per_group[fg]['serves']
            if v < c['min'] or v > c['max']:
              off_food_groups.append(fg)

        off_link_items = []
        for name, link in per_link.items():
          if link['lsum'] > link['hsum']:
            off_link_items.append(name)

        if off_food_groups:
          target_fg = random.choice(off_food_groups)
        elif off_link_items:
          target_link = random.choice(off_link_items)
        else:
          # Passed both nutritional check and fg serve check, lets do some compute heavy stuff

          vp_dict = {}
          total_price = 0
          varieties = []
          amounts = []
          emissions = dict([(k, 0) for k in emissions_keys])
          for item, amount in meal.items():
            price = foods[item]['price/100g'] / 100 * amount
            total_price += price
            variety = get_v_for_p(foods[item], person)
            varieties.append(variety)
            amounts.append(amount)

            if "emissions" not in foods[item]:
              logger.warning("No emissions data for " + item)
            else:
              for k in emissions_keys:
                emissions[k] += foods[item]["emissions"][k] / 1000 * amount * foods[item].get("waste_multiplier", 1)

            fg = foods[item]['Food group']
            per_group[fg]['amount'] += amount
            per_group[fg]['price'] += price

            for vp_id in vp_combos:
              match = foods[item]['variable prices'].get(vp_id, foods[item]['price/100g'])
              match = match / 100 * amount
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
          meal_plans[h] = {'meal': copy.copy(meal), 'serves': copy.copy(per_item_serves), 'price': total_price, 'variable prices': copy.copy(vp_dict), 'nutrition': copy.copy(nutrients), 'variety': variety, 'per_group': copy.copy(per_group), "emissions": emissions}
          logger.info('Hit!')
          meal, combinations = get_random_meal_plan(person, selected_person_nutrient_targets, min_serve_size_difference, allowed_varieties, allow_takeaways)
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
            if get_fg_for_p(foods[item], person) == 'Alcohol':
              foods_that_impact_this_measure.append(item)
          elif target_measure == 'Discretionary foods % energy':
            if get_fg_for_p(foods[item], person) == 'Discretionary foods':
              foods_that_impact_this_measure.append(item)
          elif target_measure == 'red meat (g)':
            if foods[item]['redmeat']:
              foods_that_impact_this_measure.append(item)
          elif foods[item]['nutrition'][reverse_target_measure] != 0:
            foods_that_impact_this_measure.append(item)
        except KeyError as e:
          # Nutrional info for this food/target not known
          pass
      if not foods_that_impact_this_measure:
        raise ValueError("No foods impact {}!".format(target_measure))
      food = random.choice(foods_that_impact_this_measure)
      t = foods[food]['constraints'][person]
      nt = selected_person_nutrient_targets[target_measure]
      if diff[target_measure] > 0:
        logger.debug("We're too high on {} - {} > {}".format(target_measure, nutrients[reverse_targetmap[target_measure]], nt['max']))
        r = list(np.arange(t['min'], meal[food], foods[food]['serve size'] * min_serve_size_difference))[-10:]
        target_measure += " too high"
      else:
        logger.debug("We're too low on {} - {} < {}".format(target_measure, nutrients[reverse_targetmap[target_measure]], nt['min']))
        r = list(np.arange(meal[food], t['max'], foods[food]['serve size'] * min_serve_size_difference))[:10]
        target_measure += " too low"
      if target_measure not in iterations_spent_optimising_constraint:
        iterations_spent_optimising_constraint[target_measure] = 0
      iterations_spent_optimising_constraint[target_measure] += 1
      logger.debug('{} has {} {} and must be between {}g-{}g. Options {} - current {}g'.format(food, foods[food]['nutrition'][reverse_target_measure], reverse_target_measure, t['min'], t['max'], r, meal[food]))
    elif target_fg:
      c = selected_person_food_group_serve_targets[target_fg]
      v = per_group[target_fg]['serves']
      foods_that_impact_this_measure = []
      for item in meal:
        if get_fg_for_p(foods[item], person) == target_fg:
          foods_that_impact_this_measure.append(item)
      if not foods_that_impact_this_measure:
        raise ValueError("No foods impact {}!".format(target_fg))
      food = random.choice(foods_that_impact_this_measure)
      t = foods[food]['constraints'][person]
      if v > c['max']:
        logger.debug("Food group {} has too many serves - {} > {}".format(target_fg,v,c['max']))
        r = list(np.arange(t['min'], meal[food], foods[food]['serve size'] * min_serve_size_difference))
        target_fg += " too high"
      elif v < c['min']:
        logger.debug("Food group {} has too few serves - {} < {}".format(target_fg,v,c['min']))
        r = list(np.arange(meal[food], t['max'], foods[food]['serve size'] * min_serve_size_difference))
        target_fg += " too low"
      if target_fg not in iterations_spent_optimising_constraint:
        iterations_spent_optimising_constraint[target_fg] = 0
      iterations_spent_optimising_constraint[target_fg] += 1
      logger.debug('{} has {} serves and must be between {}g-{}g. Options {} - current {}g'.format(food, foods[item]['serve size'], t['min'], t['max'], r, meal[food]))
    elif target_link:
      if target_link not in iterations_spent_optimising_constraint:
        iterations_spent_optimising_constraint[target_link] = 0
      iterations_spent_optimising_constraint[target_link] += 1
      link = per_link[target_link]
      direction = random.choice(['<', '>'])
      if direction == '<':
        food = random.choice(link['low'])
      else:
        food = random.choice(link['high'])
      t = foods[food]['constraints'][person]
      if direction == '>':
        r = list(np.arange(meal[food], t['max'], foods[food]['serve size'] * min_serve_size_difference))
        logger.debug("Food link {} is off - {} affects this link on the upper half and must be between {}g-{}g. Options {} - current {}g".format(target_link, food, t['min'], t['max'], r, meal[food]))
      else:
        r = list(np.arange(t['min'], meal[food], foods[food]['serve size'] * min_serve_size_difference))
        logger.debug("Food link {} is off - {} affects this link on the lower half and must be between {}g-{}g. Options {} - current {}g".format(target_link, food, t['min'], t['max'], r, meal[food]))
    else:
      # Randomly move off a hit
      food = random.choice(list(meal.keys()))
      t = foods[food]['constraints'][person]
      r = list(np.arange(t['min'], t['max'], foods[food]['serve size'] * min_serve_size_difference))

    if len(r) > 0:
      new_val = random.choice(r)
      logger.debug("Changing {} from {}g to {}g".format(food, meal[food], new_val))
      meal[food] = new_val

  logger.info('last meal: {}\nnutritional diff: {}\nnutrients: {}'.format(pprint.pformat(meal), pprint.pformat(diff), pprint.pformat(nutrients)))
  logger.info("iterations_spent_optimising_constraint: {}".format(pprint.pformat(iterations_spent_optimising_constraint)))

  # Calculate statistics
  prices = [m['price'] for h,m in meal_plans.items()]
  varieties = [m['variety'] for h,m in meal_plans.items()]
  em100 = [m["emissions"]["100-year GWP"] for h,m in meal_plans.items()]
  em20 = [m["emissions"]["20-year GWP"] for h,m in meal_plans.items()]
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
      'emissions': {
        "100-year GWP": {
          "min": min(em100),
          "max": max(em100),
          "mean": sum(em100) / len(em100)
        },
        "20-year GWP": {
          "min": min(em20),
          "max": max(em20),
          "mean": sum(em20) / len(em20)
        }
      },
      'total_meal_plans': len(meal_plans),
      'per_group': {},
      'nutrition': {},
      'variable_prices': {},
      'variable_prices_by_var': dict([(k, {}) for k in vp_keys])
    }
    for vp in vp_keys_effecting:
      vp_all = [m['variable prices'].get(vp, m['price']) for h,m in meal_plans.items()]
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
  logger.debug('Stats: {}'.format(pprint.pformat(stats)))

  # Write to csv
  s = time.time()
  dt = str(datetime.datetime.now()).replace(':', '_')
  filename = os.path.join(csv_folder, '{}.csv'.format(dt))
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
    keys = sorted(foods.keys())
    writer.writerow(
      ["unique id", "price", "variety"] +
      keys +
      [x + ' ' + y for x in food_groups for y in ['amount', 'price', 'serves']] +
      [v for k,v in targetmap.items()] +
      [k + ' price' for k in vp_keys_effecting] +
      [x + ' ' + y + ' price' for x in food_groups for y in vp_keys_effecting] +
      emissions_keys
    )
    for h,m in meal_plans.items():
      writer.writerow(
        [h, m['price'], m['variety']] +
        [m['meal'].get(k, 0) for k in keys] +
        [m['per_group'][x][y] for x in food_groups for y in ['amount', 'price', 'serves']] +
        [m['nutrition'][k] for k,v in targetmap.items()] +
        [m['variable prices'].get(k, m['price']) for k in vp_keys_effecting] +
        [m['per_group'][x]['variable prices'].get(y, m['per_group'][x]['price']) for x in food_groups for y in vp_keys_effecting] +
        [m["emissions"][k] for k in emissions_keys]
      )
  e = time.time()
  logger.info('write done, took {}s'.format(e-s))
  inputs = {'person': person, 'nutrient_targets': selected_person_nutrient_targets, 'iteration_limit': iteration_limit, 'min_serve_size_difference': min_serve_size_difference, 'allowed_varieties': allowed_varieties, 'allow_takeaways': allow_takeaways, 'selected_person_food_group_serve_targets': selected_person_food_group_serve_targets}
  results = {'meal_plans': meal_plans, 'csv_file': filename, 'timestamp': dt, 'inputs': inputs, 'stats': stats, "iterations_spent_optimising_constraint": iterations_spent_optimising_constraint}
  filename = os.path.join(json_folder, '{}.json'.format(dt))
  with open(filename, 'w') as f:
    json.dump(results, f)
  return results

if __name__ == "__main__":
  get_meal_plans(args.persona, iteration_limit=args.iterations, allow_takeaways=args.allow_takeaways)
