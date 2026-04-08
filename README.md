# FastAPI Todo Backend on Google Cloud

This is a simple FastAPI backend with two APIs:

- `POST /api/todos` to add a todo
- `GET /api/todos` to view todos

There is no local database setup in this project.

You will create the MySQL database in **Cloud SQL**, and both local testing and Cloud Run deployment will use that same cloud database through `DATABASE_URL`.

## Simple project files

```text
.
|-- .github/workflows/ci_cd.yaml
|-- .env.example
|-- api.py
|-- config.py
|-- db.py
|-- Dockerfile
|-- main.py
|-- models.py
|-- Procfile
|-- README.md
|-- requirements.txt
|-- schemas.py
`-- service.py
```

## Backend files

- `main.py`: FastAPI app, startup, CORS, health route
- `api.py`: API routes
- `service.py`: business logic
- `models.py`: SQLAlchemy model
- `schemas.py`: request and response schemas
- `db.py`: MySQL connection
- `config.py`: environment settings

## Local run

Create a virtual environment and install dependencies:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Create `.env` from the example:

```powershell
Copy-Item .env.example .env
```

Put your **Cloud SQL public IP connection string** in `.env`:

```env
APP_NAME=Todo API
APP_ENV=development
DEBUG=true
DATABASE_URL=mysql+pymysql://todo_user:todo_password@YOUR_CLOUD_SQL_PUBLIC_IP:3306/todo_db
```

Run the backend:

```powershell
uvicorn main:app --reload
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

Important:
When you run locally, this backend will insert and read data from your **cloud MySQL database**, not a local DB.

## API examples

Add todo:

```http
POST /api/todos
Content-Type: application/json

{
  "title": "Learn Google Cloud"
}
```

View todos:

```http
GET /api/todos
```

## GitHub push

```powershell
git init
git add .
git commit -m "Create simple FastAPI todo backend"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/todo-google-cloud.git
git push -u origin main
```

## Google Cloud step by step

### 1. Set project

```powershell
gcloud config set project YOUR_PROJECT_ID
```

### 2. Enable services

```powershell
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable sqladmin.googleapis.com
gcloud services enable iam.googleapis.com
gcloud services enable iamcredentials.googleapis.com
```

### 3. Create Cloud SQL MySQL

```powershell
gcloud sql instances create todo-mysql `
  --database-version=MYSQL_8_0 `
  --cpu=1 `
  --memory=3840MiB `
  --region=us-central1
```

Create the database:

```powershell
gcloud sql databases create todo_db --instance=todo-mysql
```

Create the DB user:

```powershell
gcloud sql users create todo_user `
  --instance=todo-mysql `
  --password=YOUR_DB_PASSWORD
```

Get the public IP:

```powershell
gcloud sql instances describe todo-mysql --format="value(ipAddresses.ipAddress)"
```

Allow network access for learning and testing:

```powershell
gcloud sql instances patch todo-mysql --authorized-networks=0.0.0.0/0
```

`0.0.0.0/0` is only for short testing. Remove it later.

### 4. Build the database URL

```text
mysql+pymysql://todo_user:YOUR_DB_PASSWORD@YOUR_CLOUD_SQL_PUBLIC_IP:3306/todo_db
```

### 5. Store it in Secret Manager

```powershell
$dbUrl = "mysql+pymysql://todo_user:YOUR_DB_PASSWORD@YOUR_CLOUD_SQL_PUBLIC_IP:3306/todo_db"
$dbUrl | gcloud secrets create todo-database-url --data-file=-
```

If the secret already exists:

```powershell
$dbUrl | gcloud secrets versions add todo-database-url --data-file=-
```

### 6. Create runtime service account

```powershell
gcloud iam service-accounts create todo-api-runtime `
  --display-name="Todo API Runtime"
```

Grant Secret Manager access:

```powershell
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID `
  --member="serviceAccount:todo-api-runtime@YOUR_PROJECT_ID.iam.gserviceaccount.com" `
  --role="roles/secretmanager.secretAccessor"
```

### 7. First deploy manually to Cloud Run

```powershell
gcloud run deploy todo-api `
  --source . `
  --region=us-central1 `
  --service-account=todo-api-runtime@YOUR_PROJECT_ID.iam.gserviceaccount.com `
  --allow-unauthenticated `
  --set-secrets=DATABASE_URL=todo-database-url:latest
```

Get the Cloud Run URL:

```powershell
gcloud run services describe todo-api --region=us-central1 --format="value(status.url)"
```

### 8. GitHub Actions setup for deploy

Create deployer service account:

```powershell
gcloud iam service-accounts create github-actions-deployer `
  --display-name="GitHub Actions Deployer"
```

Grant roles:

```powershell
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID `
  --member="serviceAccount:github-actions-deployer@YOUR_PROJECT_ID.iam.gserviceaccount.com" `
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID `
  --member="serviceAccount:github-actions-deployer@YOUR_PROJECT_ID.iam.gserviceaccount.com" `
  --role="roles/serviceusage.serviceUsageConsumer"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID `
  --member="serviceAccount:github-actions-deployer@YOUR_PROJECT_ID.iam.gserviceaccount.com" `
  --role="roles/secretmanager.secretAccessor"
```

Let the deployer use the runtime service account:

```powershell
gcloud iam service-accounts add-iam-policy-binding `
  todo-api-runtime@YOUR_PROJECT_ID.iam.gserviceaccount.com `
  --member="serviceAccount:github-actions-deployer@YOUR_PROJECT_ID.iam.gserviceaccount.com" `
  --role="roles/iam.serviceAccountUser"
```

Grant builder role:

```powershell
$projectNumber = gcloud projects describe YOUR_PROJECT_ID --format="value(projectNumber)"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID `
  --member="serviceAccount:$projectNumber-compute@developer.gserviceaccount.com" `
  --role="roles/run.builder"
```

Create workload identity pool:

```powershell
gcloud iam workload-identity-pools create github-pool `
  --project=YOUR_PROJECT_ID `
  --location=global `
  --display-name="GitHub Pool"
```

Create provider:

```powershell
gcloud iam workload-identity-pools providers create-oidc github-provider `
  --project=YOUR_PROJECT_ID `
  --location=global `
  --workload-identity-pool=github-pool `
  --display-name="GitHub Provider" `
  --issuer-uri="https://token.actions.githubusercontent.com" `
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.actor=assertion.actor" `
  --attribute-condition="assertion.repository=='YOUR_GITHUB_USERNAME/todo-google-cloud'"
```

Allow GitHub repo to use the deployer:

```powershell
$projectNumber = gcloud projects describe YOUR_PROJECT_ID --format="value(projectNumber)"

gcloud iam service-accounts add-iam-policy-binding `
  github-actions-deployer@YOUR_PROJECT_ID.iam.gserviceaccount.com `
  --project=YOUR_PROJECT_ID `
  --role="roles/iam.workloadIdentityUser" `
  --member="principalSet://iam.googleapis.com/projects/$projectNumber/locations/global/workloadIdentityPools/github-pool/attribute.repository/YOUR_GITHUB_USERNAME/todo-google-cloud"
```

Get provider name:

```powershell
gcloud iam workload-identity-pools providers describe github-provider `
  --project=YOUR_PROJECT_ID `
  --location=global `
  --workload-identity-pool=github-pool `
  --format="value(name)"
```

### 9. GitHub repo variables and secrets

GitHub Secrets:

- `GCP_WORKLOAD_IDENTITY_PROVIDER`
- `GCP_SERVICE_ACCOUNT`

GitHub Variables:

- `GCP_PROJECT_ID`
- `GCP_REGION`
- `CLOUD_RUN_SERVICE`
- `CLOUD_RUN_RUNTIME_SA`

Values:

- `GCP_SERVICE_ACCOUNT`: `github-actions-deployer@YOUR_PROJECT_ID.iam.gserviceaccount.com`
- `CLOUD_RUN_SERVICE`: `todo-api`
- `CLOUD_RUN_RUNTIME_SA`: `todo-api-runtime@YOUR_PROJECT_ID.iam.gserviceaccount.com`

## Single GitHub workflow

The file `.github/workflows/ci_cd.yaml` does both:

- CI: only prints a simple message
- CD: deploys to Cloud Run on push to `main`

## Postman test

Health:

```http
GET https://YOUR_CLOUD_RUN_URL/health
```

Add todo:

```http
POST https://YOUR_CLOUD_RUN_URL/api/todos
Content-Type: application/json

{
  "title": "Test from Postman"
}
```

View todos:

```http
GET https://YOUR_CLOUD_RUN_URL/api/todos
```

## Important note

This project uses Cloud SQL **public IP** because you want the simple learning flow first.

That means:

- local backend connects directly to Cloud SQL with public IP
- Cloud Run also connects using the same `DATABASE_URL` from Secret Manager
- both local and cloud can read and write the same data


