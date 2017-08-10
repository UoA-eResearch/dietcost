#!/bin/bash

iterations=1000000

declare -a personas=("adult man" "adult women" "14 boy" "7 girl")

for i in {1..5};do
  for p in "${personas[@]}";do
    echo ./meal_planner.py --iterations $iterations --folder 1M --dataset dataset_general_0healthy.xlsx --persona "$p" --discretionary 0  --no-takeaways --alcohol 0
  done
  for p in "${personas[@]}";do
    p="$p C"
    echo ./meal_planner.py --iterations $iterations --folder 1M --dataset dataset_general_0healthy.xlsx --persona "$p" --discretionary 100  --takeaways --alcohol 0
  done
done
