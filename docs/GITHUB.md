# Uploading to GitHub

[Back to README](../README.md)

## Upload the latest changes

Run these commands from EasyTrip. This project already has a Git repository, so
there is no need to initialize it again or add another `origin`.

```bash
cd /Users/alexzhang/Desktop/EasyTrip
git status --short --untracked-files=all
git add .
git diff --cached --stat
git diff --cached
```

Review the changes, then commit and push:

```bash
git commit -m "Add modular backend, weather agents, and integrated meal planning"
git push -u origin main
```

If the remote still contains a placeholder or points to the wrong repository,
correct it before pushing:

```bash
git remote set-url origin https://github.com/alexzhang0519/EasyTrip.git
```

Use your GitHub authentication when Git requests it. The OpenAI key is only for
running EasyTrip; it is never needed to upload code. If the remote has newer
commits and Git rejects the push, fetch and reconcile them; do not force-push.

## What belongs in the upload

Include the backend, frontend, tests, documentation, dependency files, `run.py`,
`.github/`, `.gitignore`, `.gitattributes`, and blank `Backend/.env.example`.
Include the new `Backend/app/` directory: it contains the current implementation.
Older backend modules are compatibility shims and should remain for now.

Git excludes `Backend/.env`, personal `Backend/storage/`, virtual environments,
Python caches, local backups, logs, and macOS metadata. Keep those locally.
`.gitignore` does not filter Finder drag-and-drop uploads or ZIP archives of the
whole working folder. Use the Git commands above, and do not force-add ignored files.

## Verify before publishing

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
node tests/test_frontend.mjs
git diff --check
```

Activate your `.venv` first. GitHub Actions runs the tests without real API keys.
Tests mock provider requests, so they do not spend OpenAI credits.

Review the [attribution and licensing notes](DEVELOPMENT.md#attribution-and-licensing)
before choosing a distribution license. No new license has been applied.

If a secret was ever committed, ignoring it afterward does not remove it from
history. Rotate an exposed key and remove it from history before publishing.
