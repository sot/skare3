Requirements
============

These packages are required to create the dashboard:
- jinja2

These are normally included in ska3, but I find the package versions in ska3-[flight|matlab] by running `conda install --dry-run`, which fails if one is in a conflicting environment. For this reason, I added jinja2 to the root environment. Perhaps there is a better way.

Procedure
=========

After having the password in the keyring or as the environment variable GITHUB_PASSWORD:

 export PYTHONPATH=`pwd`
 ./skare3/dashboard/ska_github_info.py -u chandra-xray
 ./skare3/dashboard/dashboard.py -o skare3/dashboard/static/index.html
 scp skare3/dashboard/static/index.html presto:/proj/sot/ska/www/ASPECT_ICXC/skare3/dashboard/