#!/usr/bin/env python

import meal_planner
from bottle import *
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('web_server')

@get('/')
def index():
  return static_file('index.html', '.')

@get('/css/<filename>')
def css(filename):
  return static_file(filename, './css')

@get('/js/<filename>')
def js(filename):
  return static_file(filename, './js')

@get('/csvs/<filename>')
def csvs(filename):
  return static_file(filename, './csvs', download=True)

@get('/get_meal_plans')
def get_meal_plans_get():
  return meal_planner.get_meal_plans()

@post('/get_meal_plans')
def get_meal_plans_post():
  person = request.json.get('person') or 'adult man'
  nutrient_targets = request.json.get('nutrient_targets')
  iterations = request.json.get('iterations') or 10000
  min_serve_size_difference = request.json.get('min_serve_size_difference') or .5
  allowed_varieties = request.json.get('variety') or [1,2,3]
  allow_takeaways = request.json.get('takeaways')
  food_group_targets = request.json.get('food_group_targets') or {}
  logger.info('request recieved, person={}, nutrient_targets={}, iterations={}, min_serve_size_difference={}, allowed_varieties={}, food_group_targets={}'.format(person, nutrient_targets, iterations, min_serve_size_difference, allowed_varieties, food_group_targets))
  return meal_planner.get_meal_plans(person, nutrient_targets, int(iterations), float(min_serve_size_difference), allowed_varieties, bool(allow_takeaways), food_group_targets)

@get('/get_nutrient_targets')
def get_nutrient_targets():
  return meal_planner.nutrient_targets

@get('/get_food_group_targets')
def get_food_group_targets():
  return meal_planner.food_groups

@get('/get_var_price')
def get_variable_price_options():
  unique_set = {}
  for food in meal_planner.foods:
    vp = meal_planner.foods[food]['variable prices']
    for entry in vp:
      for v in entry:
        if v == 'price':
          continue
        if not v in unique_set:
          unique_set[v] = []
        if not entry[v] in unique_set[v]:
          unique_set[v].append(entry[v])
  return unique_set

port = int(os.environ.get('PORT', 8080))

if __name__ == "__main__":
  run(host='0.0.0.0', port=port, debug=True, server='gunicorn', workers=8)

app = default_app()
