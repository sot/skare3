#!/bin/bash

chmod +x ${RECIPE_DIR}/bin/skare
chmod +x ${RECIPE_DIR}/bin/flt_envs
cp -a ${RECIPE_DIR}/bin/skare ${PREFIX}/bin
cp -a ${RECIPE_DIR}/bin/flt_envs ${PREFIX}/bin
cp -a ${RECIPE_DIR}/bin/ska_envs.sh ${PREFIX}/bin
cp -a ${RECIPE_DIR}/bin/ska_envs.csh ${PREFIX}/bin
sed -i "s|PREFIXPYTHON|${PREFIX}/bin/python|" ${PREFIX}/bin/flt_envs






