#!/bin/bash

mkdir ${PREFIX}/bin

for file in flt_envs ska_envs.sh ska_envs.csh ska_version skare arc5gl conda_wrapper
   do
    cp -a ${RECIPE_DIR}/bin/${file} ${PREFIX}/bin
    chmod +x ${PREFIX}/bin/${file}
    # Replace %{PREFIX}% with the conda build prefix.
    sed -i.bak -e "s|%{PREFIX}%|${PREFIX}|" ${PREFIX}/bin/${file}
    rm ${PREFIX}/bin/${file}.bak
   done
