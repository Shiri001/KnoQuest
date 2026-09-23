# Deploying KnoQuest to Render (1-Click Blueprint)

KnoQuest is pre-configured with a Render Blueprint ([`render.yaml`](./render.yaml)) that deploys both the **FastAPI Backend** and the **React Frontend** together under a single Render project.

Repository: [https://github.com/Shiri001/KnoQuest](https://github.com/Shiri001/KnoQuest)

---

## 3-Step Deployment Guide

### Step 1: Open Render Blueprint
1. Log in to your Render account at **[https://dashboard.render.com](https://dashboard.render.com)** (create a free account if you don't have one).
2. Click the blue **"New +"** button in the top navigation bar.
3. Select **"Blueprint"**.

---

### Step 2: Connect the Repository
1. Select your GitHub repository: **`Shiri001/KnoQuest`** (or paste `https://github.com/Shiri001/KnoQuest`).
2. Render will automatically read [`render.yaml`](./render.yaml) and display the two configured services:
   - **`knoquest-backend`** (Python Web Service running FastAPI on Uvicorn)
   - **`knoquest-frontend`** (Static Site running Vite React)
3. Give your Blueprint Instance a name (e.g. `knoquest`).
4. Click **"Apply"**.

---

### Step 3: Automated Build & Link
Render will automatically:
1. Build and launch `knoquest-backend` on port `10000`.
2. Automatically inject the backend's live URL into the frontend build via `VITE_API_URL`.
3. Build and publish `knoquest-frontend` with SPA rewrite rules (`/* -> /index.html`).

Once both show a green **"Live"** checkmark:
- Click the **`knoquest-frontend`** URL to open the live web application!
- Backend Swagger documentation is available at `https://<backend-url>/docs`.
