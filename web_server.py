#!/usr/bin/env python

import meal_planner
from bottle import *
import logging

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

@get('/get_meal_plans')
@post('/get_meal_plans')
def get_meal_plan():
  person = request.params.person or 'adult man'
  nutrient_targets = request.params.nutrient_targets
  iterations = request.params.iterations or 10000
  logger.info('request recieved, person={}, nutrient_targets={}, iterations={}'.format(person, nutrient_targets, iterations))
  return meal_planner.get_meal_plans(person, nutrient_targets, iterations)

@get('/get_nutrient_targets')
def get_nutrient_targets():
  return meal_planner.nutrient_targets

run(host='0.0.0.0', port=8080, debug=True)
