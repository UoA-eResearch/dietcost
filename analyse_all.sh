#!/bin/bash

for folder in "$@";do
  ./analyse.py $folder/json/* > ${folder}_analysis.txt &
done
