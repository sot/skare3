#!/bin/bash

for file in flt_envs ska_envs.sh ska_envs.csh
   do
    chmod +x ${RECIPE_DIR}/bin/${file}
    cp -a ${RECIPE_DIR}/bin/${file} ${PREFIX}/bin
    # Replace %{PREFIX}% with the conda build prefix.  It looks like it would
    # be simpler to just make these three files with the standard conda prefix_placeholder
    # hard-coded in the template files but this sed operation should be robust if the 
    # prefix_placehold changes in future versions of conda
    sed -i.bak -e "s|%{PREFIX}%|${PREFIX}|" ${PREFIX}/bin/${file}
    rm ${PREFIX}/bin/${file}.bak
   done
