# Droplet Image Analyzer — Web App

This repository is a simple Flask + OpenCV web application for analyzing droplet coverage shown on paper (uploads images, detects droplets, and calculates coverage metrics).

Quick start (Windows PowerShell):

1. Create and activate an environment (optional but recommended):

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Run the app locally:

```powershell
python app.py
```

4. Open the UI at http://localhost:5000 and upload an image to analyze.

Running the tests:

```powershell
pip install pytest
pytest -q
```

The app is minimal and intentionally self-contained for quick testing.

If you'd like I can help deploy it to a hosting service (Heroku, Render, Azure Web Apps) and add Docker support.
Below are quick deployment instructions and templates (Docker + GitHub Actions + platform examples).

Docker
------

The project now contains a Dockerfile and .dockerignore. To build and run locally with Docker:

```powershell
docker build -t droplet-analyzer .
docker run -p 5000:5000 droplet-analyzer
```

The container exposes port 5000 and runs the app with Gunicorn.

GitHub Actions CI & Deploy
--------------------------

This repository includes GitHub Actions workflow templates:

- `.github/workflows/ci.yml` — Runs tests and builds a Docker image on push / PR.
- `.github/workflows/deploy_heroku.yml` — Deploys to Heroku (requires GitHub repo secrets: `HEROKU_API_KEY`, `HEROKU_APP_NAME`, `HEROKU_EMAIL`).
- `.github/workflows/deploy_azure.yml` — Deploys to Azure Web Apps (requires `AZURE_WEBAPP_NAME` and `AZURE_WEBAPP_PUBLISH_PROFILE` secrets).
- `.github/workflows/deploy_render.yml` — Triggers a Render deploy via API (requires `RENDER_API_KEY` and `RENDER_SERVICE_ID`).

Important: these workflows are **templates** — you'll need to configure the corresponding secrets in the repository's GitHub Settings > Secrets and edit the templates to match your environment (app names, service ids, registry names, etc.).

Heroku
------

This repository includes a `Procfile` so the app can be deployed on Heroku (uses Gunicorn). To deploy manually with the Heroku CLI:

```powershell
heroku create <your-app-name>
git push heroku main
heroku config:set FLASK_ENV=production
```

Azure Web Apps
-------------

Use the Azure Web App publish profile (downloadable from the Azure Portal) and store it in `AZURE_WEBAPP_PUBLISH_PROFILE` repository secret. The GitHub workflow will handle deployment.

Docker-based Azure Web App (ACR -> Web App for Containers)
--------------------------------------------------------

If you prefer to deploy using container images, there's a GitHub Action workflow included that will:

1. Build a Docker image for this repo
2. Push the image to your Azure Container Registry (ACR)
3. Update the Azure Web App for Containers to use the pushed image

To use it you need repository secrets configured in GitHub (Settings -> Secrets):


The included workflow file: `.github/workflows/deploy_azure_docker.yml` contains the required steps. After you push to `main`, the workflow will build and deploy the container image.

Render

There is a `render.yaml` example for Render.com which you can import in Render's UI when creating a service connected to this repository.

Deploy buttons (one-click)

You can add clickable one-click deploy buttons in the README so anyone can quickly create an app in Heroku or Render.

Heroku — Deploy to Heroku button

This repository includes an `app.json` manifest which enables Heroku's deploy button. Add the following line (replace with your GitHub repo):

```md
[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/<your-username>/<your-repo>)
```

Clicking that button lets visitors configure the deployment and create an app on Heroku immediately.

Render — Deploy to Render button

Render supports quick deploy links. Add the button below (replace repo URL):

```md
[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://dashboard.render.com/deploy?repo=https://github.com/itgxxdday/siraphat)

Quick ready-to-click Render import link (use this to create your live app now):

https://dashboard.render.com/deploy?repo=https://github.com/itgxxdday/siraphat
```

This opens Render's dashboard where a user can import the repo and deploy.

Deploying to Render — step-by-step (2 ways)

Option A — Dashboard import (recommended for most users)

1. Go to https://dashboard.render.com and sign in.
2. Click "New" → "Web Service" → "Connect a repository" and authorize GitHub if you haven't already.
3. When prompted you can either:
	- Select this repository from your GitHub account (recommended), or
	- Use the "Import from YAML" / "Import a service from a file" option and upload the `render.yaml` file included in this repo.
4. Review build command and start command (render.yaml defaults are:
	- Build Command: `pip install -r requirements.txt`
	- Start Command: `gunicorn app:app --workers 2 --bind 0.0.0.0:$PORT`)
5. Choose service plan (free or paid tiers) and environment (use the default Python environment).
6. Click Deploy — Render will create the service and do the first build. Future commits to the linked branch will auto-deploy when enabled.

This approach is easy, requires no extra secrets, and works well for most users.

Option B — GitHub Actions trigger (API-based deploy)

If you want to control deploys from GitHub Actions (for example, to run tests and then trigger a Render deploy), use the included workflow `.github/workflows/deploy_render.yml` which sends a deploy command to Render via API.

Steps to enable API-based deploys:

1. Create a Render API key:
	- Go to Render dashboard → Account Settings → API Keys → Create API Key.
	- Give it a descriptive name (e.g., `github-action-deployer`) and copy the key.
2. Find your Render Service ID:
	- After creating the service via dashboard import (Option A), open the service page. The service ID is in the URL or can be found in the service settings/API tab. It usually looks like a UUID string.
3. Add the repository secrets in GitHub (Repository → Settings → Secrets & variables → Actions):
	- `RENDER_API_KEY` — the API key you generated.
	- `RENDER_SERVICE_ID` — the service identifier for your Render service.
4. Once the secrets are added, push to `main` or trigger the workflow manually in GitHub Actions to run `.github/workflows/deploy_render.yml`.

Note: The action in `.github/workflows/deploy_render.yml` uses a simple helper to call Render's deploy API — this is one of many ways to trigger a deploy. Alternatively you can craft a small curl or use render's REST API directly in your workflow.

Example GitHub Actions step (manual curl -> triggers a deploy)

If you'd prefer not to use a third-party action, add this small step to a GitHub Actions workflow to trigger a Render deploy using the API key secret:

```yaml
	env:
		RENDER_API_KEY: ${{ secrets.RENDER_API_KEY }}
		SERVICE_ID: ${{ secrets.RENDER_SERVICE_ID }}
	run: |
		curl -X POST \
			-H "Authorization: Bearer ${RENDER_API_KEY}" \
			-H "Content-Type: application/json" \
			-d '{"id":"'${SERVICE_ID}'"}' \
			https://api.render.com/v1/services/${SERVICE_ID}/deploys
```

This will call Render's API to create a new deploy for the specified service. Make sure both `RENDER_API_KEY` and `RENDER_SERVICE_ID` are set in your repo secrets.

Common troubleshooting tips:

Publish a Docker image to GitHub Container Registry (GHCR) on release
-----------------------------------------------------------------

If you'd like automated Docker images published when you create a GitHub release, this repository includes a GitHub Actions workflow that builds and pushes an image to GHCR when a release is published.

Workflow: `.github/workflows/publish-ghcr.yml` (runs on `release: published`)

What it does:
- Builds a Docker image using the repository's `Dockerfile`.
- Pushes the image to `ghcr.io/<owner>/<repo>` with several tags:
  - the commit SHA (e.g. `ghcr.io/owner/repo:<sha>`)
  - `release-<tag>` (e.g. `release-v1.2.0`)
  - `latest`

Notes & permissions:
- The workflow uses the `GITHUB_TOKEN` and needs the `packages: write` permission (it's included in the workflow file). No extra manual secret is required in most cases for GHCR with `GITHUB_TOKEN`, but you can create and use a Personal Access Token (PAT) if you prefer more fine-grained control.
- If you want the image to be publicly visible, enable package visibility for the repository or configure GHCR settings in your account.

How to use:
1. Create a GitHub release via the UI (or via `git tag` and `git push --tags`).
2. When the release is published, the workflow will run and push images to GHCR.
3. You can then pull the image with:

```powershell
docker pull ghcr.io/<your-user-or-org>/<repo>:release-<tag>
```

Automatic Release creation from tags
-----------------------------------

If you tag a commit with a semantic tag that starts with `v` (for example `v1.0.0`) and push the tag to GitHub, the repository includes a workflow `.github/workflows/release-on-tag.yml` that will automatically create a GitHub Release from the tag.

Example:

```bash
git tag v1.0.0
git push origin v1.0.0
```

This automatically creates a non-draft release named `Release v1.0.0`. That release will in turn trigger other release-based automations such as the GHCR publish workflow (`.github/workflows/publish-ghcr.yml`).

Changelog generation
--------------------

When a tag is pushed the repository's workflow `release-on-tag.yml` will now automatically generate a changelog for the release using commit messages between the previous tag and the new tag (or the last 200 commits if there is no previous tag). The changelog is added to the created release body so users get a quick summary of changes when releases are created.

The workflow now generates an enriched changelog that includes merged Pull Requests and groups entries into sections. It collects PR titles, author names, linked issues (if the PR body referenced issue numbers like #123) and arranges items into the following categories when possible:

- Features — PRs labeled `feature` / `enhancement` or titles starting with `feat:`
- Bug Fixes — PRs labeled `bug` or titles starting with `fix:`
- Documentation — PRs labeled `docs` or titles starting with `docs:`
- Other — PRs that don't match the above rules

Each entry looks like:

	- PR Title (PR #123) by @author — fixes: [#456](https://github.com/owner/repo/issues/456)

If you'd like a different format or richer release notes (pull request summaries, linked issues, or formatting templates) I can update the generator to use the GitHub API (compare endpoint) or integrate a release-drafter flow.




