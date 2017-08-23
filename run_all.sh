#!/bin/bash

iterations=1000000
name=1M
dataset=dataset_general.xlsx
#dataset=dataset_Maori.xlsx
#dataset=dataset_Pacific.xlsx

declare -a personas=("adult man" "adult women" "14 boy" "7 girl")

mkdir -p $name/logs

for i in {1..5};do
  for p in "${personas[@]}";do
    ./meal_planner.py --iterations $iterations --folder $name --dataset $dataset --persona "$p" --discretionary 0  --no-takeaways --alcohol 0 > "$name/logs/${p}_${i}.log" &
  done
  for p in "${personas[@]}";do
    p="$p C"
    ./meal_planner.py --iterations $iterations --folder $name --dataset $dataset --persona "$p" --discretionary 100  --takeaways --alcohol 0  > "$name/logs/${p}_${i}.log" &
  done
done
