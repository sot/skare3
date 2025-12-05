---
name: Ska3-aca Release
about: Release a new version of ska3-aca
title: Release ska3-aca <version>
labels: Package update
assignees: ''

---

# Packages to include

- List package name+version or github issue number

### Package and Test

- [ ] Create branch named {version}-branch
- [ ] Create PR titled {version} from {version}-branch into master
- [ ] Create a pre-release `{version}rc{N}` at the latest commit in the branch
- [ ] Check packages are built.
- [ ] Promote packages from `masters` to `test` conda channel as kadi user (`skare3-promote --ska3-conda /proj/sot/ska/www/ASPECT/ska3-conda --to test ...`).
- [ ] List in PR any data products that need to be promoted to $SKA/data (check PR's interface impacts).
- [ ] Install on HEAD and GRETA Linux test environments (`ska3/aca-test`).
- [ ] `python -m compileall $SKA/lib`
- [ ] `chmod -R g-w ${SKA}/lib`
- [ ] Confirm installed versions of ska3-flight and ska3-perl on HEAD with `conda list` (there should be no `pypi`)
- [ ] Confirm that test data (SKA/data) is appropriate for release testing (any custom test data is set or previous test data cleaned out)
- [ ] Run testr on HEAD.
- [ ] Add related issues to PR (`skare3-milestone-issues ...`).
- [ ] Document all changes (`skare3-changes-summary ...`).
- [ ] Write summary + highlight relevant changes.
- [ ] Document test results (`skare3-test-dashboard ...`).
- [ ] Wait for PR approval.
- [ ] Create release `{version}` at the same commit as RC

### Promote:
- [ ] Promote packages to `flight` conda channel (`skare3-promote ...`).
- [ ] Announce to aca@cfa/slack.
- [ ] Update ska3/aca on HEAD as aca user.
- [ ] Confirm installed versions of ska3-aca and ska3-perl on HEAD with `conda list`
- [ ] `python -m compileall $SKA/lib`
- [ ] `chmod -R g-w ${SKA}/lib`
- [ ] Run testr on HEAD.
- [ ] Document test results (`skare3-test-dashboard ...`).
- [ ] Announce to aca@cfa/slack.
- [ ] Merge PR.
