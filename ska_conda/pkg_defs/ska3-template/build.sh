#!/bin/bash

for file in flt_envs ska_envs.sh ska_envs.csh ska_version
   do
    chmod +x ${RECIPE_DIR}/bin/${file}
    cp -a ${RECIPE_DIR}/bin/${file} ${PREFIX}/bin
    # Replace %{PREFIX}% with the conda build prefix.
    sed -i.bak -e "s|%{PREFIX}%|${PREFIX}|" ${PREFIX}/bin/${file}
    rm ${PREFIX}/bin/${file}.bak
   done
