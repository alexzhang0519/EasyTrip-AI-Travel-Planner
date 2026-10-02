# Uploading to GitHub

[Back to README](../README.md)

## Before publishing

The repository excludes `Backend/.env`, personal storage, caches, virtual environments, and local backups. Only the blank `.env.example` belongs in Git.

Review the staged filenames and diff before every commit. `.gitignore` does not protect files already tracked in Git, and it does not filter Finder drag-and-drop uploads or ZIP archives of the entire working folder. Use Git for this project.

Review the [attribution and licensing notes](DEVELOPMENT.md#attribution-and-licensing) before making the repository public.

## First upload

A local Git repository may already be initialized. If `git status` reports that it is not a repository, run `git init -b main` first. Then:

```bash
git status --short --untracked-files=all
git add .
git diff --cached --stat
git diff --cached
```

Confirm no keys or personal data appear. Make the initial commit:

```bash
git commit -m "Prepare EasyTrip travel assistant"
```

Create an empty GitHub repository without an auto-generated README, license, or `.gitignore`. Copy its URL and use it in place of the placeholder below:

```bash
git remote add origin <YOUR_GITHUB_REPOSITORY_URL>
git push -u origin main
```

GitHub authentication is handled by your Git setup. No app API key is needed for uploading. The included Actions workflow runs tests without OpenAI credentials.

## If a secret was ever committed

Ignoring it afterward does not remove it from commit history. Revoke/rotate the exposed key and remove it from the repository history before publishing. Do not put the replacement key in a commit or issue.
