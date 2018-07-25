#!/bin/bash

echo "Updating flt_envs to use python -E with sed via post-link.sh" > $PREFIX/.messages.txt
sed -i.bak -e "s|%{MYPY}%|/bin/python -E|" ${PREFIX}/bin/flt_envs
rm ${PREFIX}/bin/flt_envs.bak
