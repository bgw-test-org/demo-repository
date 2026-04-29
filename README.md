# GitHub Action for Verifying Commit Signing

Test with:

```
GITHUB_TOKEN=$(gh auth token) \
GITHUB_ORG_MEMBERSHIP_READ_TOKEN=$(gh auth token) \
ORG=bgw-test-org \
REPO=bgw-test-org/demo-repository \
BASE_SHA=f214d5c8ce6197e1af844730bd86ce38944748d0 \
HEAD_SHA=5cac740f91d355aae9c295336752742d440bbfa9 \
uv run scripts/verify_signed_commits.py
```

Update workflow with:

```
uv run scripts/build_workflows.py
```
