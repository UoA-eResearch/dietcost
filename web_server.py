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
  food_group_targets = request.json.get('food_group_targets') 
  logger.info('request recieved, person={}, nutrient_targets={}, iterations={}, min_serve_size_difference={}, allowed_varieties={}, food_group_targets={}'.format(person, nutrient_targets, iterations, min_serve_size_difference, allowed_varieties, food_group_targets))
  return meal_planner.get_meal_plans(person, nutrient_targets, int(iterations), float(min_serve_size_difference), allowed_varieties, bool(allow_takeaways), food_group_targets)

@get('/get_nutrient_targets')
def get_nutrient_targets():
  return meal_planner.nutrient_targets

@get('/get_food_group_targets')
def get_foods():
  return food_groups

port = int(os.environ.get('PORT', 8080))
run(host='0.0.0.0', port=port, debug=True)
