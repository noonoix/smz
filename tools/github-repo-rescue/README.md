# GitHub repository rescue and ZIP import tools

These tools are kept in the project for repository recovery and migration.

## Tools

- `transfer-github-private.ps1`: complete migration between accounts/repositories. Uses separate hidden source and target PATs, mirror history, branches, tags, Git LFS, and a verified offline bundle.
- `upload-zip-to-github.ps1`: fallback when Git history/authentication is unavailable. Extracts a ZIP, creates a fresh Git commit, and pushes the project to the target `main` branch using Basic Authorization.

The `.bat` launchers are intended for Windows. Never commit a real PAT, put one in a URL, or send one in chat. Revoke tokens after a one-time rescue if they are no longer needed.

## Recovery order

1. Prefer `transfer-github-private.ps1` when the source Git repository can be authenticated. This preserves history, branches, tags, and LFS objects.
2. If the source repository cannot be cloned, use `upload-zip-to-github.ps1`. This preserves the project files only, not the original Git history.
3. Keep the generated `.bundle` backup from the mirror transfer in a safe user-owned backup folder.

For fine-grained PATs, source needs Contents read-only and target needs Contents read/write. GitHub Actions secrets, environments, deploy keys, and branch protection rules are separate from Git history and must be recreated.
