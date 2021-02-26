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
- [ ] Add related issues to PR (`python -m skare3_tools.github.scripts.milestone_issues ...` for now)
- [ ] Write summary + highlight relevant changes
- [ ] Get approval
- [ ] Promote packages to main conda channel
- [ ] Update production systems:
   - [ ] announce to aca@cfa
   - [ ] update HEAD ska3/flight as aca user
   - [ ] run ska_testr on HEAD
   - [ ] update ska3/flight on chimchim as SOT user
   - [ ] announce to chandracode and mpweekly
