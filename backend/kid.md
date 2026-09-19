# 🎈 NimbleVault for 5-Year-Olds: The Super-Easy Setup & Run Guide (`kid.md`)

Welcome! This guide is written so simply that **anyone** (even a 5-year-old!) can set up the APIs and run NimbleVault like a champion! 🚀

---

## 🧸 Level 1: What is NimbleVault? (The 5-Year-Old Toy Box Story)

Imagine you have a **toy box** full of video tapes:
1. 📁 **The Toy Box** is **Google Drive**. It holds all your video files inside folders.
2. 🤖 **The Super-Smart Robot** is **NimbleVault + Google Gemini AI**. The robot opens the toy box, picks up each video, and writes a super cool, smart title on it with shiny stickers (tags and categories)!
3. 📺 **The TV Station** is **YouTube**. The robot puts your video up on YouTube so the world (or just you) can watch it!
4. 🧠 **The Robot's Notebook** is a small database (**SQLite**). The robot writes down every video it already uploaded so it never makes duplicate copies or forgets anything!

---

## 🎮 Level 2: What is NimbleVault? (The 10-Year-Old YouTube Studio Bot)

Think of NimbleVault like an **automated redstone farm in Minecraft**, but built for YouTube channels! 🕹️

If you run a YouTube channel, doing all this by hand is super slow and boring:
- Clicking and downloading 20 videos from Google Drive.
- Brainstorming titles, typing descriptions, guessing hashtags, and picking categories.
- Waiting for YouTube upload progress bars.
- Keeping a spreadsheet so you don't accidentally upload the same video twice.

**NimbleVault is an automated Python bot that runs the whole studio for you:**

| Step | How It Works in Real Life | The Cool Tech Behind It |
| :--- | :--- | :--- |
| **1. The Scout** | Dives through all your Google Drive folders (even if nested 10 folders deep) and finds every single video file (`.mp4`, `.mov`, `.mkv`). | **Google Drive API v3** with recursive traversal and cycle protection |
| **2. The AI Brain** | Reads the file path (e.g. `Drive/Gaming/Minecraft/Speedrun_v2.mp4`) and generates a catchy YouTube title (`"Minecraft Gaming: Speedrun (v2)"`), 3 SEO hashtags (`#Gaming #Minecraft #Speedrun`), and picks the YouTube Category (**Gaming / ID 20**). | **Google Gemini AI (`gemini-3.5-flash-lite`)** + Offline regex fallback |
| **3. The Rocket** | Uploads the video straight to YouTube. Instead of eating all your computer's RAM, it feeds the video to YouTube in **8 MB slices** (chunks) with auto-retry if your Wi-Fi drops. | **YouTube Data API v3** Resumable Upload Session |
| **4. The Save File** | Remembers every video's status so it never duplicates. If a video is deleted on YouTube, it automatically detects it and re-uploads! | **Async SQLite (`aiosqlite`)** State Machine |

---

## ⚡ Step 0: The 10-Second Instant Demo (NO Setup Required!)

If you just want to see the robot in action right now **without** creating any Google or YouTube accounts:

1. Open your terminal in the `backend` folder.
2. Run this single command:
   ```bash
   python scripts/demo.py
   ```
*(Or if you haven't activated your virtual environment: `.\venv\Scripts\python scripts/demo.py` on Windows!)*

🎉 **That's it!** You'll see the robot simulate all 4 test scenarios right before your eyes!

---

## 🧩 Setting Up the 3 Magic Keys (APIs)

To connect NimbleVault to your **real** Google Drive and **real** YouTube channel, you only need to collect **3 Magic Keys**, like plugging in 3 Lego blocks!

```
 ┌─────────────────┐       ┌──────────────────────┐       ┌────────────────────┐
 │  Magic Key 1    │       │     Magic Key 2      │       │    Magic Key 3     │
 │  The AI Brain   │       │   The Toy Box Key    │       │     The TV Key     │
 │  (Gemini API)   │       │ (Drive Service Acct) │       │  (YouTube OAuth)   │
 └────────┬────────┘       └──────────┬───────────┘       └─────────┬──────────┘
          │                           │                             │
          ▼                           ▼                             ▼
   Paste in .env             Save as JSON file              Save as JSON file
 (GEMINI_API_KEY)         (service_account.json)          (client_secrets.json)
```

---

### 🧩 Magic Key 1: The AI Brain (Google Gemini AI)
*Time needed: 60 seconds • 100% Free*

1. Open your browser and go to: **[Google AI Studio](https://aistudio.google.com/)**
2. Sign in with any Google account.
3. Click the big blue button: **"Get API key"** (top left).
4. Click **"Create API key"** $\rightarrow$ select any project $\rightarrow$ copy the key! (It looks like `AIzaSy...`).
5. Open your `backend/.env` file with any text editor (Notepad, VS Code).
6. Find the line that says `GEMINI_API_KEY=` and paste your key there:
   ```env
   GEMINI_API_KEY=AIzaSyYourSecretKeyHere12345
   ```
✅ **Lego Block 1 is plugged in!**

---

### 🧩 Magic Key 2: The Toy Box Key (Google Drive)
*Time needed: 2 minutes • 100% Free*

We need to make a little "Robot Email" that has permission to peek into your Google Drive folder.

1. Open your browser and go to: **[Google Cloud Console](https://console.cloud.google.com/)**
2. Create a new project (or pick an existing one) named `NimbleVault`.
3. **Turn on Google Drive**:
   - In the top search bar, type `Google Drive API`.
   - Click on it and click the blue **"ENABLE"** button.
4. **Create the Robot (Service Account)**:
   - Go to **APIs & Services** $\rightarrow$ **Credentials** (left menu).
   - Click **"+ CREATE CREDENTIALS"** (at top) $\rightarrow$ select **"Service account"**.
   - Type a name like `drive-robot` $\rightarrow$ click **"CREATE AND CONTINUE"** $\rightarrow$ click **"DONE"**.
5. **Download the Robot's Key**:
   - On the Credentials page, look under **"Service Accounts"** and click on your new robot's email.
   - Click the **"KEYS"** tab (near the top).
   - Click **"ADD KEY"** $\rightarrow$ **"Create new key"**.
   - Choose **JSON** $\rightarrow$ click **"CREATE"**.
   - A file will download to your computer!
6. **Put it in the backend folder**:
   - Rename that downloaded file to: `service_account.json`
   - Move it directly into your `nimblevault/backend/` folder.
7. ⭐ **CRITICAL STEP (Don't skip!): Give the robot the key to your folder**:
   - Open that `service_account.json` in Notepad.
   - Look for `"client_email": "drive-robot@your-project.iam.gserviceaccount.com"` and copy that email address.
   - Open your Google Drive in your web browser.
   - Right-click the folder you want to upload videos from $\rightarrow$ click **Share**.
   - Paste the robot's email address and make sure its role is **Viewer**! Click Send.

✅ **Lego Block 2 is plugged in!**

---

### 🧩 Magic Key 3: The TV Key (YouTube Uploads)
*Time needed: 2 minutes • 100% Free*

Now we give the robot permission to upload videos to your YouTube channel!

1. In that same **[Google Cloud Console](https://console.cloud.google.com/)**:
2. **Turn on YouTube**:
   - In the top search bar, type `YouTube Data API v3`.
   - Click on it and click the blue **"ENABLE"** button.
3. **Configure Consent Screen** (if you haven't yet):
   - Go to **APIs & Services** $\rightarrow$ **OAuth consent screen**.
   - Choose **External** $\rightarrow$ click **Create**.
   - Type App Name: `NimbleVault` $\rightarrow$ enter your email address.
   - Click **Save and Continue** until finished.
   - In **Test users**, click **"+ ADD USERS"** and add your own Google email!
4. **Create the Client ID**:
   - Go to **APIs & Services** $\rightarrow$ **Credentials**.
   - Click **"+ CREATE CREDENTIALS"** $\rightarrow$ choose **"OAuth client ID"**.
   - ⚠️ **IMPORTANT**: Under **Application type**, select **Desktop app**! (Do NOT choose Web).
   - Name it `youtube-uploader` $\rightarrow$ click **"CREATE"**.
5. **Download the Client Secrets file**:
   - A box will pop up. Click **"DOWNLOAD JSON"** (or click the little download arrow next to it).
   - Rename that downloaded file to: `client_secrets.json`
   - Move it directly into your `nimblevault/backend/` folder.
6. **Log in to YouTube (One-Click!)**:
   - In your terminal inside `backend/`, run:
     ```bash
     python scripts/auth_youtube.py
     ```
   - A web browser tab will automatically pop open!
   - Click your Google account $\rightarrow$ click **Continue** / **Allow**.
   - The terminal will say `[OK] OAuth token successfully saved to: youtube_token.json`!

✅ **Lego Block 3 is plugged in! You are 100% ready!**

---

## 🚦 Step 3: Check If Everything Works (Pre-Flight)

Before you fly your spaceship, test your dashboard with this command:

```bash
python scripts/run_pipeline.py --status
```

Look for the 4 green checks:
```
=================================================================
 NIMBLEVAULT - PRE-FLIGHT SYSTEM READINESS CHECK
=================================================================
  [OK]   Database: SQLite engine active & schema verified.
  [OK]   Google Drive: Service Account valid (drive-robot@...)
  [OK]   YouTube API: OAuth2 credentials active (ready for live uploads)
  [OK]   Gemini AI: Gemini API key active (AQ.Ab8..., model: gemini-3.5-flash-lite)
=================================================================
```

If you see all four `[OK]` lines, give yourself a high-five! ✋ Everything is perfect!

---

## 🎮 Step 4: Run the Robot!

### 1. Test Safely First (Dry-Run Mode)
This downloads your videos, uses Gemini AI to give them amazing titles, but **pretends** to upload to YouTube so you don't use up your daily YouTube limit:
```bash
python scripts/run_pipeline.py --folder-id YOUR_FOLDER_ID --dry-run
```

### 2. Live Upload to Real YouTube!
When you're ready to put your videos live on your YouTube channel:
```bash
python scripts/run_pipeline.py --folder-id YOUR_FOLDER_ID
```
*(Replace `YOUR_FOLDER_ID` with the folder ID from your Google Drive URL. If you don't specify one, it uses the default assignment folder!)*

### 3. Check What's Uploaded Anytime
```bash
python scripts/run_pipeline.py --status
```
It shows a clean table of all videos:
```
Tracked Video Jobs in Database:
Status           | File Name                 | Route                             | YouTube Link
----------------------------------------------------------------------------------------------------------------
COMPLETED        | exploring earth day 2     | ...th2/exploring the earth day 2  | https://youtube.com/watch?v=...
COMPLETED        | exploring earth day1      | ...th2/exploring earth day1       | https://youtube.com/watch?v=...
```

---

## 🎮 The Cheat Sheet (Copy & Paste Commands)

| What You Want To Do | Type This Command |
| :--- | :--- |
| **Play the fake demo (zero setup)** | `python scripts/demo.py` |
| **Check if all APIs & logins are happy** | `python scripts/run_pipeline.py --status` |
| **Verify your YouTube login** | `python scripts/auth_youtube.py --check` |
| **Scan Google Drive for newly added files** | `python scripts/run_pipeline.py --sync` |
| **Safe practice run (no real upload)** | `python scripts/run_pipeline.py --dry-run` |
| **Full live run on your Drive folder** | `python scripts/run_pipeline.py --folder-id <YOUR_FOLDER_ID>` |
| **Re-process and re-upload everything** | `python scripts/run_pipeline.py --force` |

---

## 🩹 Ouchie! What If Something Goes Wrong? (Easy Fixes)

### ❓ "It says: Google Drive Access Denied (HTTP 403)"
- **What happened**: You forgot to invite the robot to your Google Drive folder!
- **How to fix**: Open your Google Drive folder in your browser, click **Share**, copy the `client_email` from your `service_account.json` file, and paste it with **Viewer** permission.

### ❓ "It says: YouTube 403 quotaExceeded"
- **What happened**: Google's free tier only lets you upload around 6 videos per day.
- **How to fix**: Don't panic! Use `--dry-run` to test your code as much as you want without using quota. The upload quota resets automatically every day at midnight Pacific Time.

### ❓ "I deleted a video on YouTube, will NimbleVault notice?"
- **What happened**: Yes! NimbleVault has a superpower called **Self-Healing Reconciliation**.
- **How to fix**: Just run `python scripts/run_pipeline.py --status` or run the pipeline again. It will spot that the video was deleted on YouTube, change its status back to `PENDING`, and re-upload it for you!

### ❓ "I renamed a video or moved it into a new folder in Google Drive"
- **What happened**: NimbleVault automatically detects renames and folder changes!
- **How to fix**: Just run `python scripts/run_pipeline.py`. It notices the new name, asks Gemini AI for a fresh new title matching the new name, and uploads it cleanly.

---

🎉 **You are now a certified NimbleVault Master! Have fun automating your videos!** 🚀
