#!/usr/bin/env python

import meal_planner
from bottle import get, post, request, run, static_file

@get('/')
def index():
  return static_file('index.html', '.')

@get('/css/<filename>')
def css(filename):
  return static_file(filename, './css')

@get('/js/<filename>')
def js(filename):
  return static_file(filename, './js')

@post('/get_meal_plan')
def get_meal_plan():
  if 'person' in request.json:
    return meal_planner.get_meal_plan(request.json['person'])
  return meal_planner.get_meal_plan()

@get('/get_nutrient_targets')
def get_nutrient_targets():
  return meal_planner.nutrient_targets

run(host='localhost', port=8080, debug=True)