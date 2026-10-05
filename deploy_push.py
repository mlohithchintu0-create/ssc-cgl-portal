"""
Helper script to push the Git repository to GitHub or any cloud remote
Uses pure-Python Dulwich (no local git executable required).
"""
import sys
import os
import dulwich.porcelain as porcelain

def push_to_remote(remote_url, branch="main"):
    repo_path = os.path.dirname(os.path.abspath(__file__))
    print(f"Opening repository at: {repo_path}")
    repo = porcelain.open_repo(repo_path)

    # Check status and commit any new changes
    status = porcelain.status(repo)
    staged = False
    for group in [status.untracked, status.unstaged]:
        for item in group:
            porcelain.add(repo, item)
            staged = True

    if staged:
        commit_id = porcelain.commit(repo, message=b"Update files for cloud deployment")
        print(f"Committed new changes: {commit_id.decode() if isinstance(commit_id, bytes) else commit_id}")

    print(f"Pushing branch '{branch}' to: {remote_url}")
    try:
        porcelain.push(repo, remote_url, refspecs=[f"refs/heads/{branch}:refs/heads/{branch}"])
        print("Successfully pushed to remote!")
    except Exception as e:
        # Try pushing master/main
        try:
            porcelain.push(repo, remote_url, refspecs=["refs/heads/master:refs/heads/main"])
            print("Successfully pushed master -> main to remote!")
        except Exception as e2:
            print("Push failed:", e2)
            print("\nTip: If authentication is required, include your GitHub Personal Access Token in the URL:")
            print("Example: https://<token>@github.com/<username>/<repo>.git")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python deploy_push.py <github_repo_url>")
        print("Example: python deploy_push.py https://github.com/myuser/ssc-cgl-portal.git")
        sys.exit(1)

    url = sys.argv[1].strip()
    push_to_remote(url)
