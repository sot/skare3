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

- [ ] Check packages are built and copied to test channel.
- [ ] Document all changes (`skare3-changes-summary ...`).
- [ ] Document test status (`skare3-test-dashboard ...`).
- [ ] Promote packages from `masters` to `test` channel (`skare3-promote ...`).
- [ ] Add related issues to PR (`python -m skare3_tools.github.scripts.milestone_issues ...` for now).
- [ ] Write summary + highlight relevant changes.
- [ ] Notify FOT team of candidate release.
- [ ] Install on GRETA test as SOT user (`ska3/matlab/test`).
- [ ] FOT tests and approves.
- [ ] Promote packages to main conda channel (`skare3-promote ...`).
### Promote:

- [ ] Announce to aca@cfa/slack.
- [ ] Update ska3/matlab on chimchim as SOT user.
- [ ] Run ska_testr on chimchim.
- [ ] Announce to aca@cfa/slack.
- [ ] Notify FOT team.
