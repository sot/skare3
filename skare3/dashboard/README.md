Requirements
============

These packages are required to create the dashboard:
- jinja2

These are normally included in ska3, but I find the package versions
in ska3-[flight|matlab] by running `conda install --dry-run`, which
fails if one is in a conflicting environment. For this reason, I added
jinja2 to the root environment. Perhaps there is a better way.

Cron job
========

Right now, the cron job runs on a root conda environment where I also
have this package, ska3_builder and ska3-template. The job runs a
script I have not checked in that does:

 skare3_github_info -c /home/jgonzale/.chandra_xray_github -o /proj/sot/ska/jgonzalez/skare3_repository_info.json
 skare3_dashboard -i /proj/sot/ska/jgonzalez/skare3_repository_info.json -o /proj/sot/ska/jgonzalez/index.html
 mv /proj/sot/ska/jgonzalez/index.html /proj/sot/ska/www/ASPECT_ICXC/skare3/dashboard/

The authentication information is in a json file.

Using keyring
=============

After having the password in the keyring or as the environment variable GITHUB_PASSWORD:

 export PYTHONPATH=`pwd`
 ./skare3/dashboard/ska_github_info.py -u chandra-xray
 ./skare3/dashboard/dashboard.py -o skare3/dashboard/static/index.html
 scp skare3/dashboard/static/index.html presto:/proj/sot/ska/www/ASPECT_ICXC/skare3/dashboard/
