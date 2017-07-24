#!/bin/bash

while IFS='' read -r line || [[ -n "$line" ]]; do
    . build_one_package.sh $line
done < "build_order.txt"