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
- [ ] Packages copied to test channel
- [ ] test status documented
- [ ] get approval 
- [ ] Individual packages moved to main conda channel
- [ ] Update production systems:
   - [ ] announce to aca@cfa
   - [ ] ska3-flight package moved to main conda channel
   - [ ] update aca@HEAD
   - [ ] run testr@HEAD
   - [ ] update sot@cheru
   - [ ] update sot@chimchim
   - [ ] announce to chandracode and mpweekly
