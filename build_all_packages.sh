#!/bin/bash

CONDA_ROOT="$HOME/Projects/ska/builds"

while IFS='' read -r line || [[ -n "$line" ]]; do
    echo "Building $line."
    conda-build --croot $CONDA_ROOT --old-build-string $line
done < "build_order.txt"