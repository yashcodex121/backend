# 🚀 Render Deployment Guide for MusicFlow Backend

Yeh backend **Render.com** par 100% Free Web Service ke roop mein deploy karne ke liye fully configured hai (`render.yaml`, `Procfile`, `runtime.txt`, `Dockerfile`).

---

## ⚡ Method 1: GitHub se 2-Minute Deployment (Recommended)

### Step 1: GitHub par Naya Repo Banayein
1. [github.com/new](https://github.com/new) par jayein.
2. Repository ka naam dalein: e.g. `musicflow-backend`.
3. **Public** ya **Private** select karein aur **Create repository** par click karein.

### Step 2: Code GitHub par Push Karein
Apne computer ke terminal / PowerShell mein yeh commands run karein:

```powershell
cd "C:\Users\saura\.gemini\antigravity\scratch\music-backend"
git branch -M main
git remote add origin https://github.com/<AAPKA_GITHUB_USERNAME>/musicflow-backend.git
git push -u origin main
```

---

### Step 3: Render par Web Service Banayein
1. [dashboard.render.com](https://dashboard.render.com) par login karein.
2. **New +** button click karein aur **Web Service** select karein.
3. Apna GitHub repository (`musicflow-backend`) connect karein.
4. Settings fill karein:
   - **Name**: `musicflow-backend` (ya jo aap chahein)
   - **Region**: `Oregon (US West)` ya `Singapore`
   - **Runtime**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: `Free`
5. **Create Web Service** button par click karein!

🎉 **Render automatic build aur deploy shuru kar dega!**  
1-2 minute baad aapko live URL mil jayega, jaise:  
`https://musicflow-backend.onrender.com`

---

## ⚡ Method 2: Render Blueprint (1-Click Deploy)

Render par repository connect karte waqt agar aap **Blueprint** choose karte hain, toh Render automatically hamari banayi hui `render.yaml` file padh kar saari settings khud setup kar dega!

---

## 🧪 Deploy hone ke baad test karein:

- **Swagger Docs:** `https://<AAPKA-RENDER-URL>.onrender.com/docs`
- **Health Check:** `https://<AAPKA-RENDER-URL>.onrender.com/health`
- **Unified Search:** `https://<AAPKA-RENDER-URL>.onrender.com/api/unified/search?q=Kesariya`
- **JioSaavn Search:** `https://<AAPKA-RENDER-URL>.onrender.com/api/saavn/search?q=Arijit`
