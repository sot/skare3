# Packages to include

- List package name+version or github issue number

### Package and Test

- [ ] Create branch named {version}-branch
- [ ] Create PR titled {version} from {version}-branch into master
- [ ] Create a pre-release `{version}rc{N}` at the latest commit in the branch
- [ ] Check packages are built and copied to test channel.
- [ ] Document all changes (`skare3-changes-summary ...`).
- [ ] Document test status (`skare3-test-dashboard ...`).
- [ ] Promote packages from `masters` to `test` channel (`skare3-promote ...`).
- [ ] Add related issues to PR (`skare3-milestone-issues ...`).
- [ ] Write summary + highlight relevant changes.
- [ ] Notify FOT team of candidate release.
- [ ] FOT gives green light to install release candidate.
- [ ] Install on GRETA test as SOT user (`ska3/matlab/test`).
- [ ] Confirm that test data (SKA/data) is appropriate for release testing (any custom test data is set or previous test data cleaned out)
- [ ] FOT tests and approves.
- [ ] Promote packages to main conda channel (`skare3-promote ...`).
### Promote:

- [ ] Announce to aca@cfa/slack.
- [ ] Update ska3/matlab on cheru as SOT user.
- [ ] Run ska_testr on cheru.
- [ ] Document test results (`skare3-test-dashboard ...`).
- [ ] Announce to aca@cfa/slack.
- [ ] Notify FOT team.
- [ ] Merge PR.
