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

- [ ] Document all changes
- [ ] Build all packages
   - [ ] noarch
   - [ ] linux 64
   - [ ] mac 64
- [ ] Copy Packages to test channel
- [ ] Document test status
- [ ] Get approval
- [ ] Move individual packages to main conda channel
- [ ] Update production systems:
   - [ ] announce to aca@cfa
   - [ ] move ska3-flight package to main conda channel
   - [ ] update HEAD ska3/flight as aca user
   - [ ] run ska_testr on HEAD
   - [ ] update ska3/flight on cheru as sot user
   - [ ] update ska3/flight on chimchim as SOT user
   - [ ] announce to chandracode and mpweekly
