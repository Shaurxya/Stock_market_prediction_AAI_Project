# 🚢 Deployment Guide

## Architecture Overview

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  Vercel/Netlify  │────▶│  Render/Railway   │────▶│  Saved Models    │
│  (Frontend)      │◀────│  (Backend API)    │◀────│  (In Backend)    │
│  React + Vite    │     │  FastAPI + Python  │     │  LSTM + XGBoost  │
└──────────────────┘     └──────────────────┘     └──────────────────┘
```

---

## 1. Frontend Deployment (Vercel)

### Option A: Vercel (Recommended)

1. **Push to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/your-username/stock-prediction.git
   git push -u origin main
   ```

2. **Connect to Vercel**
   - Go to [vercel.com](https://vercel.com) and sign up with GitHub
   - Click "Import Project" → Select your repository
   - Configure:
     - **Framework**: Vite
     - **Root Directory**: `frontend`
     - **Build Command**: `npm run build`
     - **Output Directory**: `dist`
   - Add environment variable:
     - `VITE_API_URL` = `https://your-backend-url.onrender.com/api`
   - Click **Deploy**

3. **Custom Domain (Optional)**
   - Go to Settings → Domains → Add your domain

### Option B: Netlify

1. Same GitHub setup as above
2. Go to [netlify.com](https://netlify.com) → "New site from Git"
3. Configure:
   - **Base directory**: `frontend`
   - **Build command**: `npm run build`
   - **Publish directory**: `frontend/dist`
4. Add environment variable: `VITE_API_URL`
5. Add `_redirects` file in `frontend/public/`:
   ```
   /*    /index.html   200
   ```

---

## 2. Backend Deployment (Render)

### Option A: Render (Recommended)

1. **Create `render.yaml`** in project root:
   ```yaml
   services:
     - type: web
       name: stock-prediction-api
       env: python
       buildCommand: pip install -r backend/requirements.txt
       startCommand: cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT
       envVars:
         - key: CORS_ORIGINS
           value: https://your-frontend.vercel.app
   ```

2. **Connect to Render**
   - Go to [render.com](https://render.com) → "New Web Service"
   - Connect your GitHub repository
   - Configure:
     - **Root Directory**: `backend`
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - Add environment variables:
     - `CORS_ORIGINS` = `https://your-frontend.vercel.app`
   - Click **Create Web Service**

### Option B: Railway

1. Go to [railway.app](https://railway.app) → "New Project"
2. Connect GitHub repository
3. Add a `Procfile` in `backend/`:
   ```
   web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```
4. Set root directory to `backend`
5. Add environment variables
6. Deploy!

---

## 3. Model Files Storage

### Where Models Live
- Models are stored in `/models/saved_models/`
- The backend reads models from `../models/saved_models/` relative to itself

### For Deployment
Since model files can be large, you have several options:

#### Option 1: Include in Repository (Small Models)
If model files are < 100MB total, include them in the Git repository:

```bash
# Make sure models are tracked
git add models/saved_models/*.keras
git add models/saved_models/*.pkl
git add models/saved_models/*.json
```

#### Option 2: Git LFS (Large Models)
For larger models, use Git Large File Storage:

```bash
git lfs install
git lfs track "*.keras"
git lfs track "*.pkl"
git add .gitattributes
git add models/saved_models/
git commit -m "Add trained models via LFS"
```

#### Option 3: Cloud Storage
Store models in cloud storage and download on startup:

- **AWS S3**: Store in a bucket, download on boot
- **Google Cloud Storage**: Similar approach
- **Hugging Face Hub**: Free model hosting

Add download logic to your backend startup:
```python
# backend/app/main.py
@app.on_event("startup")
async def download_models():
    # Download from cloud storage if not present locally
    pass
```

---

## 4. Environment Variables

### Frontend (.env)
```
VITE_API_URL=https://your-backend-url.onrender.com/api
```

### Backend (.env)
```
HOST=0.0.0.0
PORT=8000
CORS_ORIGINS=https://your-frontend.vercel.app
MODEL_DIR=../models/saved_models
```

---

## 5. Pre-Deployment Checklist

- [ ] Train models locally and generate saved model files
- [ ] Test backend locally with `uvicorn app.main:app --reload`
- [ ] Test frontend locally with `npm run dev`
- [ ] Build frontend: `cd frontend && npm run build`
- [ ] Verify API endpoints work: `http://localhost:8000/docs`
- [ ] Update CORS origins for production
- [ ] Set `VITE_API_URL` in frontend env
- [ ] Push code to GitHub
- [ ] Deploy backend first (get the URL)
- [ ] Deploy frontend with backend URL
- [ ] Test end-to-end in production

---

## 6. Monitoring

### Backend Health Check
Your API has a built-in health check endpoint:
```
GET https://your-backend.onrender.com/api/health
```

### Render Health Check
Configure in Render dashboard:
- **Health Check Path**: `/api/health`
- **Health Check Timeout**: 30s

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| CORS errors | Verify `CORS_ORIGINS` includes your frontend URL |
| Model not found | Ensure models are in `models/saved_models/` or update `MODEL_DIR` |
| Timeout on prediction | Increase Render timeout or optimize model loading |
| Frontend API 404 | Check `VITE_API_URL` matches your backend URL |
| Cold start delays | Render free tier sleeps after inactivity — first request is slow |
