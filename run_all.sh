#!/bin/bash

iterations="1e6"

declare -a personas=("adult man" "adult women" "14 boy" "7 girl")

for i in {1..40};do
  for p in "${personas[@]}";do
    pc="$p C"
    mkdir -p "runs/$p" "runs/$pc"
    echo "python3.6 meal_planner.py --iterations $iterations --folder \"runs/$p\" --persona \"$p\" --alcohol 0 > \"runs/$p/$i.log\""
    echo "python3.6 meal_planner.py --iterations $iterations --folder \"runs/$pc\" --persona \"$pc\" --alcohol 0 > \"runs/$pc/$i.log\""
  done
done
