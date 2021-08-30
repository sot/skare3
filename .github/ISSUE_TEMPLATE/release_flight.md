---
name: Ska3-flight Release
about: Release a new version of ska3-flight
title: Release ska3-flight <version>
labels: Package update
assignees: ''

---

# Packages to include

- List package name+version or github issue number

# Checklist

- [ ] Check packages are built and copied to test channel.
- [ ] Document all changes (`skare3-changes-summary ...`).
- [ ] Document test status (`skare3-test-dashboard ...`).
- [ ] Promote packages from `masters` to `test` channel (`skare3-promote ...`).
- [ ] Add related issues to PR (`python -m skare3_tools.github.scripts.milestone_issues ...` for now).
- [ ] Write summary + highlight relevant changes.
- [ ] Install on HEAD test environment (`ska3/test`).
- [ ] Get approval at load review.
- [ ] Promote packages to main conda channel (`skare3-promote ...`).
- [ ] Update production systems:
   - [ ] Announce to aca@cfa/slack.
   - [ ] Update ska3/flight on HEAD as aca user.
   - [ ] Update ska3/flight on chimchim as SOT user.
   - [ ] Run ska_testr on HEAD.
   - [ ] Announce to chandracode and mpweekly.
   - [ ] Announce to aca@cfa/slack.
