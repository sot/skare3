---
name: Ska3-matlab Release
about: Release a new version of ska3-matlab
title: Release ska3-matlab <version>
labels: Package update
assignees: ''

---

# Packages to include

- List package name+version or github issue number

### Package and Test

- [ ] Create branch named {version}-branch
- [ ] Create PR titled {version} from {version}-branch into master
- [ ] Create a pre-release `{version}rc{N}` at the latest commit in the branch
- [ ] Check packages are built and copied to test channel.
- [ ] List in PR any data products that need to be promoted to $SKA/data (check PR's interface impacts).
- [ ] Document all changes (`skare3-changes-summary ...`).
- [ ] Document test status (`skare3-test-dashboard ...`).
- [ ] Promote packages from `masters` to `test` channel (`skare3-promote ...`).
- [ ] Add related issues to PR (`skare3-milestone-issues ...`).
- [ ] Write summary + highlight relevant changes.
- [ ] Notify FOT team of candidate release.
- [ ] FOT gives green light to install release candidate.
- [ ] Install on GRETA test as SOT user (`ska3/matlab/test`).
- [ ] `python -m compileall $SKA/lib`
- [ ] `chmod -R g-w ${SKA}/lib`
- [ ] Confirm installed versions of ska3-flight and ska3-perl on HEAD with `conda list` (there should be no `pypi`)
- [ ] Confirm that test data (SKA/data) is appropriate for release testing (any custom test data is set or previous test data cleaned out)
- [ ] FOT Matlab CB approves.
- [ ] Create release `{version}` at the same commit as RC

### Promote:

- [ ] Promote packages to main conda channel (`skare3-promote ...`).
- [ ] FOT gives green light to install release
- [ ] Update ska3/matlab on cheru as SOT user.
- [ ] `python -m compileall $SKA/lib`
- [ ] `chmod -R g-w ${SKA}/lib`
- [ ] Confirm installed versions of ska3-flight and ska3-perl on HEAD with `conda list` (there should be no `pypi`)
- [ ] Make sure $SKA/data is updated on GRETA
- [ ] Run ska_testr on cheru.
- [ ] Document test results (`skare3-test-dashboard ...`).
- [ ] Announce to aca@cfa/slack.
- [ ] Notify FOT.
- [ ] Merge PR.
