#!/usr/bin/env python

import pymysql
import csv

connection = pymysql.connect(host='webdb.cer.auckland.ac.nz',
                             user='dietcost',
                             passwd='25r8yV5f774SKUa',
                             db='dietcost',
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor)
try:
  cursor = connection.cursor()
  
  food_ids = {}
  
  with open('foods.csv') as f:
    reader = csv.DictReader(f)
    values = [];
    for row in reader:
      food_ids[row['Commonly consumed food']] = int(row['Commonly consumed food ID'])
      if not row['Variety']:
        row['Variety'] = 1
      values.append((
        int(row['Food group ID']),
        int(row['Commonly consumed food ID']),
        row['Commonly consumed food'],
        int(row['Variety']),
        int(row['core/disc'] == 'c'),
        int(row['Child'] == 'y')
      ))
    cursor.executemany("REPLACE INTO `foods` (`food_group`, `id`, `name`, `variety`, `is_core`, `child_suitable`) VALUES (%s, %s, %s, %s, %s, %s)", values)
    print("foods: Attempted {} upserts, {} succeded".format(len(values), cursor.rowcount))
    connection.commit()
  
  with open('nutrition.csv') as f:
    reader = csv.DictReader(f)
    values = []
    for row in reader:
      if row['Commonly consumed food'] in food_ids:
        id = food_ids[row['Commonly consumed food']]
        values.append((
          id,
          row['Energy kJ/100g'],
          row['Fat g/100g'],
          row['CHO g/100g'],
          row['protein g/100g'],
          row['Sat fat g/100g'],
          row['Sugars g/100g'],
          row['Fibre g/100g'],
          row['Sodium g/100g'],
        ))
    cursor.executemany("REPLACE INTO `nutrition` (`food`, `energy`, `fat`, `carbohydrates`, `protein`, `sat_fat`, `sugar`, `fibre`, `sodium`) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)", values)
    print("nutrition: Attempted {} upserts, {} succeded".format(len(values), cursor.rowcount))
    connection.commit()
  
  sql = "SELECT * FROM food_groups"
  cursor.execute(sql)
  result = cursor.fetchall()
  print(result)
  
finally:
  connection.close()