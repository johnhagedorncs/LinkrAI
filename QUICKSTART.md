# ⚡ QuickStart Guide - LinkrAI

Get your LinkrAI demo deployed in **under 15 minutes**!

---

## 🚀 Deployment Checklist

### 1. Push to GitHub (2 min)
```bash
cd /Users/johnny/LinkrAi/LinkrAI
git add .
git commit -m "Deploy-ready: sanitized data, configs added"
git push origin main
```

---

### 2. Deploy Backend to Render (5 min)

1. Go to https://render.com → Sign up/Login
2. Click **"New +"** → **"Web Service"**
3. Connect GitHub → Select `LinkrAI` repo
4. Configure:
   - **Name**: `linkrai-backend`
   - **Root Directory**: `demo-frontend/backend`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free
5. Click **"Create Web Service"**
6. **Wait ~3 min** for deployment
7. **Copy backend URL**: `https://linkrai-backend-xxxx.onrender.com`

---

### 3. Deploy Frontend to Vercel (5 min)

1. Go to https://vercel.com → Sign up/Login
2. Click **"Add New..."** → **"Project"**
3. Import `LinkrAI` from GitHub
4. Configure:
   - **Root Directory**: Click Edit → `demo-frontend/frontend`
5. Add Environment Variable:
   - **Key**: `VITE_API_URL`
   - **Value**: [Your Render backend URL from step 2.7]
6. Click **"Deploy"**
7. **Wait ~2 min** for build
8. **Copy frontend URL**: `https://linkrai-demo-xxxx.vercel.app`

---

### 4. Update CORS (2 min)

1. Go back to Render Dashboard
2. Select your backend service
3. Go to **"Environment"** tab
4. Click **"Add Environment Variable"**:
   - **Key**: `FRONTEND_URL`
   - **Value**: [Your Vercel frontend URL from step 3.8]
5. Service auto-redeploys

---

### 5. Test & Update README (1 min)

1. **Test**: Visit your Vercel URL → Click "Start Recording"
2. **Update README.md**: Replace `https://your-demo-url.vercel.app` with your actual URL
3. **Push update**:
```bash
git add README.md
git commit -m "Update live demo link"
git push origin main
```

---

## ✅ Done!

Your LinkrAI is now live at:
- **Frontend**: https://linkrai-demo-xxxx.vercel.app
- **Backend**: https://linkrai-backend-xxxx.onrender.com

---

## 📋 Add to Resume

```
LinkrAI - Healthcare AI Agent Platform
• Built multi-agent orchestration system with Claude AI (AWS Bedrock)
• Integrated Athena Health EHR API for medical referrals and scheduling
• Developed full-stack app with React TypeScript and FastAPI
• Deployed on Vercel/Render with automated CI/CD
🔗 Live Demo: https://linkrai-demo.vercel.app
```

---

## 🎯 Next: Share It!

1. ✅ **LinkedIn**: Post about your project with demo link
2. ✅ **Resume**: Add under "Projects" section
3. ✅ **Portfolio**: Feature on your personal website
4. ✅ **Applications**: Include in job applications
5. ✅ **GitHub**: Pin the repository on your profile

---

## 💡 Pro Tips

**Keep backend awake:**
Use [UptimeRobot](https://uptimerobot.com/) to ping every 5 min
→ Prevents 30-second cold start on free tier

**Custom domain:**
Both Vercel and Render support custom domains (free)
→ Makes it even more professional

**Analytics:**
Add Vercel Analytics to track recruiter visits
→ Dashboard → Analytics → Enable

---

## 🆘 Troubleshooting

**Backend sleeping?**
→ Wait 30 seconds for first request (Render free tier)

**CORS errors?**
→ Check `FRONTEND_URL` is set in Render environment

**Build failing?**
→ Verify root directories are set correctly

---

**Questions?** Check [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for detailed instructions.

**Ready to deploy?** Start with Step 1! ⬆️
