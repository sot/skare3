#!/bin/bash

while IFS='' read -r line || [[ -n "$line" ]]; do
    if [[ line != \#* ]]; then
        . build_one_package.sh $line
    fi
done < "build_order.txt"