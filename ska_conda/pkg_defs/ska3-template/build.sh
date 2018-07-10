#!/bin/bash

for file in flt_envs ska_envs.sh ska_envs.csh
   do
    chmod +x ${RECIPE_DIR}/bin/${file}
    cp -a ${RECIPE_DIR}/bin/${file} ${PREFIX}/bin
    sed -i "s|%{PREFIX}%|${PREFIX}|" ${PREFIX}/bin/${file}
   done
