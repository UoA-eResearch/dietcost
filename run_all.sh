#!/bin/bash

iterations="1e6"

declare -a personas=("adult man" "adult women" "14 boy" "7 girl")

for i in {1..40};do
  for p in "${personas[@]}";do
    pv="$p PV"
    pf="$p PF"
    mkdir -p "$pv" "$pf"
    echo "python3.6 meal_planner.py --iterations $iterations --folder \"$pf\" --persona \"$pf\" > \"$pf/$i.log\""
    echo "python3.6 meal_planner.py --iterations $iterations --folder \"$pv\" --persona \"$pv\" > \"$pv/$i.log\""
  done
done
