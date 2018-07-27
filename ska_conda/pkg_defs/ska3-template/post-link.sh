#!/bin/bash

sed -i.bak -e "s|%{MYPY}%|/bin/python -E|" ${PREFIX}/bin/flt_envs
rm ${PREFIX}/bin/flt_envs.bak
