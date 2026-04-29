import json
import os
import sys
from contextlib import contextmanager
from urllib.error import HTTPError
from urllib.request import urlopen, Request
from urllib.parse import quote, urljoin

API_URL = "https://api.github.com/"
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GITHUB_ORG_MEMBERSHIP_READ_TOKEN = os.environ["GITHUB_ORG_MEMBERSHIP_READ_TOKEN"]
REPO = os.environ["REPO"]
ORG = os.environ["ORG"]
BASE_SHA = os.environ["BASE_SHA"]
HEAD_SHA = os.environ["HEAD_SHA"]
PAGE_SIZE = 100


def quote_segment(segment):
    return quote(segment, safe="")

def gh_get_raw(path, token=None):
    req = Request(
        urljoin(API_URL, path),
        headers={
            "Authorization": f"Bearer {token or GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2026-03-10",
            "User-Agent": "vercel-labs/verify-signed-commits",
        },
    )
    return urlopen(req)

@contextmanager
def gh_get(path, token=None):
    with gh_get_raw(path, token) as resp:
        body = resp.read().decode("utf-8")
        print(resp.status, body)
        yield json.loads(body)


def fail(msg):
    print(f"::error::{msg}")
    sys.exit(1)


if not GITHUB_ORG_MEMBERSHIP_READ_TOKEN:
    fail(
        "ORG_MEMBERSHIP_TOKEN secret must be set. "
        "Required to detect private org members. "
        "Provide a token with 'read:org' / 'Members: Read'."
    )

compare_url = (
    f"repos/{quote(REPO)}/compare/"
    + f"{quote_segment(BASE_SHA)}...{quote_segment(HEAD_SHA)}"
)

# Compare API reports total_commits regardless of page size,
# so a per_page=1 request is the cheapest way to learn the
# size before paginating.
with gh_get(f"{compare_url}?per_page=1") as resp:
    total = resp.get("total_commits", 0)
if total > 1000:
    fail(
        f"PR contains {total} commits in {BASE_SHA}..{HEAD_SHA}, "
        "exceeding the 1000-commit limit for this check."
    )

commits = []
page = 1
while True:
    with gh_get(f"{compare_url}?per_page={PAGE_SIZE}&page={page}") as resp:
        page_commits = resp.get("commits", [])
    commits.extend(page_commits)
    if len(page_commits) < PAGE_SIZE:
        break
    page += 1

by_committer = {}
unidentified = []
for c in commits:
    login = (c.get("committer") or {}).get("login")
    if not login:
        unidentified.append(c["sha"])
    else:
        by_committer.setdefault(login, []).append(c)

if unidentified:
    print(
        "::error::These commits have a committer email that "
        "does not map to a GitHub user; cannot determine "
        "org membership:"
    )
    for sha in unidentified:
        print(f"  {sha}")
    sys.exit(1)

if len(by_committer) > 10:
    fail(
        f"PR has {len(by_committer)} unique committers, "
        "exceeding the 10-committer limit."
    )

org_members = set()
for login in sorted(by_committer):
    url = f"orgs/{ORG}/members/{login}"
    with gh_get_raw(url, token=GITHUB_ORG_MEMBERSHIP_READ_TOKEN) as r:
        if r.status == 204:
            org_members.add(login)
    if login in org_members:
        print(f"  {login}: org member (signature required)")
    else:
        print(f"  {login}: not an org member (signature not required)")

failed = False
for login in sorted(org_members):
    bad = [
        c for c in by_committer[login] if not c["commit"]["verification"]["verified"]
    ]
    if not bad:
        continue
    print(f"::error::Commits by org member '{login}' do not have verified signatures:")
    for c in bad:
        reason = c["commit"]["verification"].get("reason", "")
        print(f"  {c['sha']}\t{reason}")
    failed = True

if failed:
    sys.exit(1)

print(f"All commits by org members in {BASE_SHA}..{HEAD_SHA} are signed and verified.")
