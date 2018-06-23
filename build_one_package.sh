#!/bin/bash

SKA_CONDA_ROOT="$HOME/Projects/ska"
export SKA_TOP_SRC_DIR="${SKA_CONDA_ROOT}/src"
export MACOSX_DEPLOYMENT_TARGET="10.9"

echo "Building $1."
conda-build --croot ${SKA_CONDA_ROOT}/builds --no-anaconda-upload $1
