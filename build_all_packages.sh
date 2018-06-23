#!/bin/bash

while IFS='' read -r line || [[ -n "$line" ]]; do
    if [[ ${line:0:1} != '#' ]]; then
        . build_one_package.sh $line
    fi
done < "build_order.txt"