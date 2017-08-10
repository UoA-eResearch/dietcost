#!/bin/bash

iterations=1000000
name=1M

declare -a personas=("adult man" "adult women" "14 boy" "7 girl")

mkdir -p $name/logs

for i in {1..5};do
  for p in "${personas[@]}";do
    ./meal_planner.py --iterations $iterations --folder $name --dataset dataset_general_0healthy.xlsx --persona "$p" --discretionary 0  --no-takeaways --alcohol 0 > "$name/logs/${p}_${i}.log" &
  done
  for p in "${personas[@]}";do
    p="$p C"
    ./meal_planner.py --iterations $iterations --folder $name --dataset dataset_general_0healthy.xlsx --persona "$p" --discretionary 100  --takeaways --alcohol 0  > "$name/logs/${p}_${i}.log" &
  done
done