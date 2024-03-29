---
name: Release
about: Release a meta-package
title: Release ska3-<name> <version>
labels: Package update
assignees: ''

---

# Packages to include

- List package name+version or github issue number

# Checklist

- [ ] Check packages are built and copied to test channel
- [ ] Document all changes (`skare3-changes-summary ...`)
- [ ] Document test status (`skare3-test-dashboard ...`)
- [ ] promote packages from `masters` to `test` channel (`skare3-promote ...`)
- [ ] Add related issues to PR (`python -m skare3_tools.github.scripts.milestone_issues ...` for now)
- [ ] Write summary + highlight relevant changes
- [ ] matlab only: Notify FOT team of candidate release
- [ ] matlab only: Install on GRETA test as SOT user (`ska3/matlab/test`)
- [ ] flight only: Install on HEAD test environment (`ska3/test`)
- [ ] Get approval
   - [ ]  FOT tests and approves
   - [ ]  Load review
- [ ] Promote packages to main conda channel (`skare3-promote ...`)
- [ ] Update production systems:
   - [ ] announce to aca@cfa/slack
   - [ ] flight:
      - [ ] update HEAD ska3/flight as aca user
      - [ ] run ska_testr on HEAD
      - [ ] announce to chandracode and mpweekly
   - [ ] matlab:
      - [ ] update ska3/flight on chimchim as SOT user
      - [ ] update ska3/matlab on chimchim as SOT user
      - [ ] run ska_testr on chimchim
      - [ ] announce to FOT team
   - [ ] announce to aca@cfa/slack

