# Streamlit apps

One repository, one folder per app. Each app deploys separately on [Streamlit Community Cloud](https://share.streamlit.io) and gets its own URL.

| App | Folder | Live URL |
|---|---|---|
| Search & Support Effectiveness | `apps/search-support-dashboard` | _add after deploy_ |

## Layout

```
apps/
  <app-name>/
    app.py               # entrypoint (set as "Main file path" when deploying)
    requirements.txt     # this app's dependencies only
    .streamlit/config.toml   # this app's theme/config
    ...
```

Each folder is self-contained: its own dependencies, theme and data. Apps don't share code, so updating one can't break another.

## Add a new app

1. Create `apps/<new-app>/` with `app.py` and `requirements.txt` (and optionally `.streamlit/config.toml`).
2. Commit and push.
3. On share.streamlit.io: **Create app → Deploy a public app from GitHub**, pick this repo, branch `main`, main file path `apps/<new-app>/app.py`, and choose a custom subdomain.

## Run an app locally

```powershell
cd apps/search-support-dashboard
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```
