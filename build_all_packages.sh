#!/bin/bash


SKA_CONDA_ROOT="$HOME/Projects/ska"
export SKA_TOP_SRC_DIR="${SKA_CONDA_ROOT}/src"

while IFS='' read -r line || [[ -n "$line" ]]; do
    echo "Building $line."
    conda-build --croot ${SKA_CONDA_ROOT}/builds $line
done < "build_order.txt"