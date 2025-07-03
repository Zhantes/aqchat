import re
from pathlib import Path
from threading import Lock
from typing import Callable, Dict, List, Optional
from urllib.parse import urlparse, urlunparse

from git import Repo, GitCommandError


def extract_repo_name(url: str) -> str:
    """
    Extracts the repository name from a GitHub URL.

    Parameters
    ----------
    url : str
        GitHub URL in HTTPS, SSH, or git protocol form.

    Returns
    -------
    str
        The repository name (e.g., "my-repo" from "https://github.com/user/my-repo.git").

    Raises
    ------
    ValueError
        If the repository name cannot be determined.
    """
    # Handle SSH and SCP-like syntax (e.g., git@github.com:user/repo.git)
    scp_match = re.match(r'^(?:[^@]+@)?github\.com[:/](.+?)/([^/]+?)(?:\.git)?/?$', url)
    if scp_match:
        return scp_match.group(2)

    # Handle HTTPS or Git protocol
    parsed = urlparse(url)
    if 'github.com' in parsed.netloc:
        path_parts = parsed.path.strip('/').split('/')
        if len(path_parts) >= 2:
            repo = path_parts[1]
            if repo.endswith('.git'):
                repo = repo[:-4]
            return repo

    raise ValueError(f"Could not extract repository name from URL: {url}")


class GitHubRepo:
    """
    Abstraction for a local Git repository that tracks a remote GitHub repo,
    with optional support for private repos via HTTPS + Personal-Access Token
    (PAT) authentication.

    Parameters
    ----------
    remote_url : str
        HTTPS **or** SSH URL of the repository on GitHub.
    local_path : str | Path
        Filesystem location where the repository should live.
    username : str, optional
        GitHub account name used for HTTPS authentication.
    token : str, optional
        Personal-Access Token that pairs with *username*.  Ignored unless
        *remote_url* starts with "https://".

    Notes
    -----
    • If *local_path* does not yet contain a Git repo, the remote is cloned
      there.  
    • When both *username* and *token* are provided **and** the URL is HTTPS,
      credentials are injected into the URL as
      ``https://{username}:{token}@github.com/owner/repo.git`` so every future
      network operation (clone, pull, fetch, push) is automatically
      authenticated.  
    • Callbacks may be registered for the events ``"added"``, ``"modified"``,
      and ``"removed"``.  Each callback receives **one** argument: the path
      (str) of the file relative to *local_path* that changed.

    Security
    --------
    The credential-injected URL is written to the repo's local ``.git/config``.
    Anyone with read access to that file could see the PAT in plaintext.  
    If that is unacceptable, prefer an SSH remote with an SSH key, or configure
    a credential helper instead of embedding the token.
    """

    #: Callback type alias
    Callback = Callable[[str], None]

    # ------------------------------------------------------------------ #
    #  Construction / initialisation                                     #
    # ------------------------------------------------------------------ #
    def __init__(
        self,
        remote_url: str,
        local_path: str | Path,

        *,
        username: Optional[str] = None,
        token: Optional[str] = None,
    ):
        self.lock: Lock = Lock()
        self.remote_url: str = remote_url
        self.local_path: Path = Path(local_path).expanduser().resolve()
        self.repo_name: str = extract_repo_name(remote_url)

        # Compute an authenticated URL if requested and applicable
        self._auth_url: str = self._with_auth(remote_url, username, token)

        # Clone or open the repository
        if not (self.local_path / ".git").exists():
            self.repo: Repo = Repo.clone_from(self._auth_url, self.local_path)
        else:
            self.repo = Repo(self.local_path)

            # Ensure the 'origin' remote exists and points at the right URL
            try:
                origin = self.repo.remotes.origin
            except AttributeError:
                origin = self.repo.create_remote("origin", self._auth_url)

            if origin.url != self._auth_url:
                origin.set_url(self._auth_url)

        # Remember the commit we’re on; used to diff on pull()
        self._last_commit_sha: str = self.repo.head.commit.hexsha

    # ------------------------------------------------------------------ #
    #  Public API                                                        #
    # ------------------------------------------------------------------ #
    def pull(self, callbacks: Dict[str, List[Callback]]) -> None:
        """
        Fast-forward from *origin* (``git pull``) and invoke callbacks for any
        file additions / modifications / removals since the previous pull (or
        since construction).

        Args:
        --
            callbacks - A set of callbacks to be invoked for every file added,
            deleted or modified in the diff. Note that the GitHubRepo's internal
            lock is retained while callbacks are invoked. This means callbacks are
            FORBIDDEN from calling ANY method of GitHubRepo, otherwise a deadlock
            may occur.
        """
        with self.lock:
            old_sha = self._last_commit_sha

            try:
                self.repo.remotes.origin.pull(rebase=False)  # default behaviour
            except GitCommandError as exc:
                raise RuntimeError(f"Pull failed: {exc}") from exc

            new_sha = self.repo.head.commit.hexsha
            if new_sha == old_sha:          # Nothing changed
                return

            # Diff the previous commit against the new one
            diff_index = self.repo.commit(old_sha).diff(new_sha)

            self._last_commit_sha = new_sha

            # Since pull, diff and saving latest commit SHA
            # were performed while the lock was acquired,
            # it should be impossible to corrupt the repo state with
            # concurrent pulls.

            # Now we need to fire callbacks.
            # We should retain the lock while doing this, otherwise
            # callbacks may be fired in an incorrect order.
            # Since the lock is retained, this means any callbacks are *forbidden*
            # from accessing the GitHubRepo, otherwise a deadlock *will* occur.
            for change in diff_index:
                match change.change_type:
                    case "A":                               # added
                        self._fire(callbacks, "added", change.b_path)
                    case "D":                               # deleted
                        self._fire(callbacks, "removed", change.a_path)
                    case "M" | "R" | "T":                   # modified / renamed / mode change
                        self._fire(callbacks, "modified", change.b_path)
                    case _:                                 # "C" (copy) or "U" (unmerged) etc.
                        self._fire(callbacks, "modified", change.b_path)

    # ------------------------------------------------------------------ #
    #  Private helpers                                                   #
    # ------------------------------------------------------------------ #
    @staticmethod
    def _with_auth(
        url: str, username: Optional[str], token: Optional[str]
    ) -> str:
        """
        Return *url* unchanged if (username, token) are not **both** provided
        **or** the scheme is not HTTPS. Otherwise, inject the credentials.
        """
        if not (username and token):
            return url

        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            # SSH remotes (git@github.com:owner/repo.git) handled by ssh-agent
            return url

        # If credentials are already present, trust them
        if parsed.username or parsed.password:
            return url

        # Build netloc with embedded credentials
        netloc = f"{username}:{token}@{parsed.hostname}"
        if parsed.port:
            netloc += f":{parsed.port}"

        authed = parsed._replace(netloc=netloc)
        return urlunparse(authed)

    def _fire(self, callbacks: Dict[str, List[Callback]], event: str, rel_path: str) -> None:
        """Invoke all callbacks registered for *event*, swallowing exceptions.

        NOTE: This method is called WITH the lock retained. This means that any
        callbacks are FORBIDDEN from calling any methods of GitHubRepo, otherwise
        a deadlock *will* occur."""
        abs_path = str(self.local_path / rel_path)
        for cb in list(callbacks[event]):
            try:
                cb(abs_path)
            except Exception as exc:
                print(f"[GitHubRepo] {event} callback failed: {exc}")
