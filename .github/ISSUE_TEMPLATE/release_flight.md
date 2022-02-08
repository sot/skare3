---
name: Ska3-flight Release
about: Release a new version of ska3-flight
title: Release ska3-flight <version>
labels: Package update
assignees: ''

---

# Packages to include

- List package name+version or github issue number

### Package and Test

- [ ] Check packages are built and automated tests pass.
- [ ] Promote packages from `masters` to `test` channel (`skare3-promote --to test ...`).
- [ ] Install on HEAD and GRETA Linux test environments (`ska3/test`).
- [ ] Run testr on HEAD and GRETA
- [ ] Add related issues to PR (`python -m skare3_tools.github.scripts.milestone_issues ...` for now).
- [ ] Document all changes (`skare3-changes-summary ...`).
- [ ] Write summary + highlight relevant changes.
- [ ] Document test status (`skare3-test-dashboard ...`).
- [ ] Create FSDS Jira ticket and wait for approval.

### Promote:
- [ ] Promote packages to main conda channel (`skare3-promote ...`).
- [ ] Announce to aca@cfa/slack.
- [ ] Update ska3/flight on HEAD as aca user.
- [ ] Update ska3/flight on GRETA as SOT user.
- [ ] Run ska_testr on HEAD and GRETA.
- [ ] Announce to aca@cfa/slack.
- [ ] Announce to sot@cfa and fot@ipa.
