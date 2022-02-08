# ska3-flight {version}

This PR includes:
- 

## Interface Impacts:

## Testing:

- [Automated tests](https://icxc.cfa.harvard.edu/aspect/skare3/testr/releases/{version}/).

The latest release candidates will be installed in `/proj/sot/ska3/test` on HEAD, and all release candidates will be available for testing from the usual channels:
```
conda create -n ska3-flight-{version}rc# --override-channels \
  -c https://icxc.cfa.harvard.edu/aspect/ska3-conda/flight \
  -c https://icxc.cfa.harvard.edu/aspect/ska3-conda/test \
  ska3-flight=={version}rc#
```

## Review

All operations critical or impacting PR's are independently and carefully reviewed. For other PR's the level of detail for review is calibrated to operations criticality. Some PR's that are confined to aspect-team-specific processing may have little to no independent review.

## Deployment

ska3-flight {version} will be promoted to flight conda channel and installed on HEAD and GRETA Linux upon approval of FSDS Jira ticket.

# Code changes

# Related Issues
