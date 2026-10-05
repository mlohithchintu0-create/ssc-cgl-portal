"""
Helper script to push the Git repository to GitHub or any cloud remote
Uses pure-Python Dulwich (no local git executable required).
"""
import sys
import os
import dulwich.porcelain as porcelain

def push_to_remote(remote_url, token=None, branch="main"):
    repo_path = os.path.dirname(os.path.abspath(__file__))
    try:
        repo = porcelain.open_repo(repo_path)
    except Exception as e:
        return False, f"Could not open repository at {repo_path}: {e}"

    # Stage all untracked and modified files
    try:
        status = porcelain.status(repo)
        staged = False
        for group in [status.untracked, status.unstaged]:
            for item in group:
                porcelain.add(repo, item)
                staged = True

        if staged:
            commit_id = porcelain.commit(repo, message=b"Deploy update: SSC CGL production portal")
            print(f"Committed changes: {commit_id}")
    except Exception as e:
        print("Note on staging:", e)

    # Format URL with token if provided
    final_url = remote_url.strip()
    if token and token.strip():
        tok = token.strip()
        if '@' not in final_url and final_url.startswith('https://github.com/'):
            final_url = final_url.replace('https://github.com/', f'https://{tok}@github.com/')

    print(f"Pushing to remote URL...")
    try:
        # Try pushing to main branch
        porcelain.push(repo, final_url, refspecs=[f"refs/heads/master:refs/heads/main"])
        return True, "Successfully pushed repository to GitHub 'main' branch!"
    except Exception as err1:
        try:
            # Fallback to main:main
            porcelain.push(repo, final_url, refspecs=[f"refs/heads/main:refs/heads/main"])
            return True, "Successfully pushed repository to GitHub 'main' branch!"
        except Exception as err2:
            try:
                # Fallback default refspec
                porcelain.push(repo, final_url)
                return True, "Successfully pushed repository to GitHub!"
            except Exception as err3:
                return False, f"Push failed: {err1} | {err2} | {err3}"

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python deploy_push.py <github_repo_url> [optional_personal_access_token]")
        print("Example: python deploy_push.py https://github.com/mlohithchintu0/ssc-cgl-portal.git ghp_yourtoken123")
        sys.exit(1)

    url_arg = sys.argv[1].strip()
    token_arg = sys.argv[2].strip() if len(sys.argv) > 2 else None
    success, msg = push_to_remote(url_arg, token=token_arg)
    print(msg)
