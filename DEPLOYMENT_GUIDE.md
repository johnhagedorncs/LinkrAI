# 🚀 Deployment Guide - LinkrAI

This guide will walk you through deploying LinkrAI to Vercel (frontend) and Render (backend) using their free tiers.

---

## Prerequisites

- GitHub account
- Vercel account (sign up at [vercel.com](https://vercel.com))
- Render account (sign up at [render.com](https://render.com))
- Your GitHub repository pushed to GitHub

---

## Step 1: Deploy Backend to Render

### 1.1 Create New Web Service

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Select the `LinkrAI` repository

### 1.2 Configure Service

**Basic Settings:**
- **Name**: `linkrai-backend` (or your preferred name)
- **Region**: Choose closest to your users
- **Branch**: `main`
- **Root Directory**: `demo-frontend/backend`

**Build Settings:**
- **Runtime**: `Python 3`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

**Plan:**
- Select **Free** tier

### 1.3 Environment Variables (Optional)

For mock mode, you don't need any environment variables! The backend will automatically run in demo mode.

If you want to add AWS integration later:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`
- `TRANSCRIBE_OUTPUT_BUCKET`

### 1.4 Deploy

1. Click **"Create Web Service"**
2. Wait for deployment to complete (~2-3 minutes)
3. **Copy your backend URL** (e.g., `https://linkrai-backend.onrender.com`)

### 1.5 Verify

Test your backend is running:
```bash
curl https://your-backend-url.onrender.com/
```

You should see:
```json
{
  "status": "healthy",
  "service": "Healthcare Agent Demo API",
  "mode": "mock"
}
```

---

## Step 2: Deploy Frontend to Vercel

### 2.1 Import Project

1. Go to [Vercel Dashboard](https://vercel.com/dashboard)
2. Click **"Add New..."** → **"Project"**
3. Import your GitHub repository
4. Select the `LinkrAI` repository

### 2.2 Configure Project

**Framework Preset:**
- Vercel should auto-detect **Vite**

**Root Directory:**
- Click **"Edit"** next to Root Directory
- Enter: `demo-frontend/frontend`
- Click **"Continue"**

**Build Settings** (auto-configured):
- **Build Command**: `npm run build`
- **Output Directory**: `dist`
- **Install Command**: `npm install`

### 2.3 Environment Variables

Add environment variable:
- **Key**: `VITE_API_URL`
- **Value**: Your Render backend URL (from Step 1.4)
  - Example: `https://linkrai-backend.onrender.com`

### 2.4 Deploy

1. Click **"Deploy"**
2. Wait for build to complete (~1-2 minutes)
3. **Copy your frontend URL** (e.g., `https://linkrai-demo.vercel.app`)

---

## Step 3: Update CORS Settings

### 3.1 Add Frontend URL to Backend

1. Go back to your **Render Dashboard**
2. Select your `linkrai-backend` service
3. Go to **"Environment"** tab
4. Add new environment variable:
   - **Key**: `FRONTEND_URL`
   - **Value**: Your Vercel URL (from Step 2.4)
     - Example: `https://linkrai-demo.vercel.app`
5. Click **"Save Changes"**
6. Your service will automatically redeploy

---

## Step 4: Test Your Deployment

### 4.1 Open Your App

Visit your Vercel URL: `https://your-app.vercel.app`

### 4.2 Test the Workflow

1. Click **"Start Recording"** (or just wait, it will use mock mode)
2. The UI will show:
   - ✅ Uploading audio...
   - ✅ Transcribing...
   - ✅ Processing through agents...
3. You should see:
   - Medical transcript displayed
   - Agent actions listed
   - Results from each agent

### 4.3 Troubleshooting

**Frontend can't reach backend:**
- Check `VITE_API_URL` is set correctly in Vercel
- Verify backend is running: visit `https://your-backend-url.onrender.com/`
- Check browser console for CORS errors

**Backend not responding:**
- Check Render logs: Dashboard → Your Service → "Logs"
- Verify build succeeded
- Free tier services sleep after 15 min of inactivity (first request may be slow)

---

## Step 5: Update Your README

### 5.1 Add Live Demo Links

Update your [README.md](README.md):

```markdown
## 🚀 Live Demo

**[Try the Live Demo →](https://your-app.vercel.app)**
```

### 5.2 Update Badge

Replace the demo badge URL:
```markdown
[![Live Demo](https://img.shields.io/badge/demo-live-brightgreen)](https://your-app.vercel.app)
```

---

## 🎉 You're Done!

Your LinkrAI demo is now live and accessible to recruiters!

### What You Have:

✅ **Frontend**: Fast, responsive React app on Vercel
✅ **Backend**: Reliable FastAPI server on Render
✅ **Mock Mode**: Works without AWS credentials
✅ **Professional URL**: Easy to share on resume/LinkedIn

### Next Steps:

1. **Test on mobile** - Verify it works on phones/tablets
2. **Share the link** - Add to your resume, LinkedIn, portfolio
3. **Monitor usage** - Check Render/Vercel dashboards
4. **Customize** - Update README with your contact info

---

## 📊 Free Tier Limits

### Render (Backend)
- ✅ 750 hours/month (more than enough)
- ⚠️ Sleeps after 15 min inactivity
- ⚠️ First request after sleep: ~30 seconds

### Vercel (Frontend)
- ✅ 100 GB bandwidth/month
- ✅ Unlimited projects
- ✅ Always-on (no sleeping)

---

## 🔄 Updating Your Deployment

### Update Frontend
```bash
git add .
git commit -m "Update frontend"
git push origin main
```
Vercel auto-deploys on push!

### Update Backend
```bash
git add .
git commit -m "Update backend"
git push origin main
```
Render auto-deploys on push!

---

## 🆘 Common Issues

### Issue: "This site can't be reached"
**Solution**: Wait 30 seconds - Render free tier wakes from sleep

### Issue: CORS errors in browser console
**Solution**: Verify `FRONTEND_URL` is set in Render environment variables

### Issue: Build fails on Vercel
**Solution**: Check `demo-frontend/frontend` is set as root directory

### Issue: Build fails on Render
**Solution**: Verify `demo-frontend/backend` is set as root directory

---

## 💡 Pro Tips

1. **Keep backend warm**: Use [UptimeRobot](https://uptimerobot.com/) to ping your backend every 5 minutes (prevents sleeping)

2. **Custom domain**: Both Vercel and Render support custom domains on free tier

3. **Environment secrets**: Never commit `.env` files - always use platform environment variables

4. **Monitoring**: Check logs regularly during first week to catch issues early

---

**Need help?** Open an issue on GitHub or check the logs in Render/Vercel dashboards.
