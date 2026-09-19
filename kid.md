# 🎈 NimbleVault: Super-Easy Setup & Run Guide (`kid.md`)

Welcome! This guide is written so simply that **anyone who can read
documentation can set up, test, and run NimbleVault**. 🚀

> **Important:** Follow the steps in order. Step 0 prepares your
> computer and installs the project. The later steps connect Google
> Drive, Gemini AI, and YouTube.

------------------------------------------------------------------------

## 🧸 Level 1: What is NimbleVault?

Imagine you have a **toy box full of video tapes**:

1.  📁 **The Toy Box = Google Drive**\
    It holds your video files inside folders.

2.  🤖 **The Super-Smart Robot = NimbleVault + Google Gemini AI**\
    The robot finds your videos and generates useful YouTube metadata
    such as titles, descriptions, hashtags/tags, and categories from the
    video's Drive path and context.

3.  📺 **The TV Station = YouTube**\
    The robot uploads your videos to your YouTube channel.

4.  🧠 **The Robot's Notebook = SQLite**\
    The robot records each video's state so repeated runs do not
    normally upload the same Drive file again.

------------------------------------------------------------------------

## 🎮 Level 2: What does NimbleVault do?

If you run a YouTube channel, doing everything manually can be slow:

-   Finding videos in Google Drive.
-   Downloading videos to your computer.
-   Creating titles and descriptions.
-   Choosing tags/categories.
-   Uploading videos to YouTube.
-   Tracking which videos were already processed.

**NimbleVault automates this workflow with Python.**

  -----------------------------------------------------------------------
  Step                    What the robot does     Technology
  ----------------------- ----------------------- -----------------------
  **1. Scout**            Recursively searches    Google Drive API v3
                          Google Drive folders    
                          and finds supported     
                          video files.            

  **2. AI Brain**         Uses the file's Drive   Google Gemini AI +
                          path/context to         deterministic fallback
                          generate YouTube        
                          metadata and a          
                          category.               

  **3. Rocket**           Uploads videos to       YouTube Data API v3
                          YouTube using resumable 
                          uploads with retry      
                          handling.               

  **4. Save File**        Stores processing state SQLite + `aiosqlite`
                          in SQLite and           
                          reconciles deleted      
                          YouTube videos.         
  -----------------------------------------------------------------------

------------------------------------------------------------------------

# 🛠️ Step 0: Setup & Installation

**Do this first.** You do not need Google API credentials yet just to
install the project and run the demo.

## 0.1 Prerequisites

Install these on your computer:

-   **Python 3.10 or newer**
-   **Git**
-   A copy/clone of the NimbleVault project

The project uses a local SQLite database, so you do **not** need to
install a separate database server.

------------------------------------------------------------------------

## 0.2 Open the project

Open a terminal inside the NimbleVault project.

Your project should look roughly like this:

``` text
nimblevault/
└── backend/
    ├── app/
    ├── scripts/
    ├── requirements.txt
    └── .env.example
```

Move into the backend folder:

``` bash
cd backend
```

------------------------------------------------------------------------

## 0.3 Create a Python virtual environment

Run:

``` bash
python -m venv venv
```

This creates a private Python environment for NimbleVault.

### Windows PowerShell

``` powershell
.\venv\Scripts\Activate.ps1
```

If PowerShell blocks the activation script, you can run the project
using the Python executable inside `venv` directly, for example:

``` powershell
.\venv\Scripts\python scripts/demo.py
```

### Linux / macOS

``` bash
source venv/bin/activate
```

When activation works, your terminal normally shows something like:

``` text
(venv)
```

------------------------------------------------------------------------

## 0.4 Install the project dependencies

Run:

``` bash
pip install -r requirements.txt
```

Wait until installation finishes.

------------------------------------------------------------------------

## 0.5 Create your `.env` file

NimbleVault uses SQLite locally and reads configuration from `.env`.

### Windows PowerShell

``` powershell
Copy-Item .env.example .env
```

### Linux / macOS

``` bash
cp .env.example .env
```

The important settings are:

``` env
DATABASE_URL=sqlite+aiosqlite:///nimblevault.db

GOOGLE_SERVICE_ACCOUNT_JSON=service_account.json

YOUTUBE_CLIENT_SECRETS_JSON=client_secrets.json
YOUTUBE_TOKEN_JSON=youtube_token.json

YOUTUBE_PRIVACY_STATUS=private
YOUTUBE_VIDEO_CATEGORY_ID=22

GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.5-flash-lite

TEMP_DOWNLOAD_DIR=downloads/temp
```

For the **demo**, you can leave the API credentials unconfigured.

------------------------------------------------------------------------

## 0.6 Run the zero-credential demo

You can now test NimbleVault without connecting Google Drive, Gemini, or
YouTube.

From the `backend` folder, run:

``` bash
python scripts/run_pipeline.py --demo
```

Or:

``` bash
python scripts/demo.py
```

If your virtual environment is not activated on Windows:

``` powershell
.\venv\Scripts\python scripts/demo.py
```

🎉 If the demo runs successfully, your local Python installation,
dependencies, and project setup are working.

> **This is the safest first test.** Do this before setting up the real
> Google APIs.

------------------------------------------------------------------------

# 🔑 Step 1: Connect the 3 Magic Keys

To connect NimbleVault to your **real Google Drive, Gemini AI, and
YouTube channel**, configure these three services.

``` text
┌─────────────────────┐
│     Magic Key 1     │
│      Gemini AI      │
│    GEMINI_API_KEY   │
└──────────┬──────────┘
           │
           ▼
       .env file


┌─────────────────────┐
│     Magic Key 2     │
│    Google Drive     │
│ service_account.json│
└──────────┬──────────┘
           │
           ▼
      backend folder


┌─────────────────────┐
│     Magic Key 3     │
│      YouTube        │
│ client_secrets.json │
└──────────┬──────────┘
           │
           ▼
      backend folder
```

------------------------------------------------------------------------

## 🧩 Magic Key 1: Gemini AI

**Time needed: about 1 minute**

1.  Open Google AI Studio: https://aistudio.google.com/

2.  Sign in with your Google account.

3.  Create an API key.

4.  Copy the key.

5.  Open:

``` text
backend/.env
```

6.  Find:

``` env
GEMINI_API_KEY=
```

7.  Paste your key:

``` env
GEMINI_API_KEY=YOUR_REAL_GEMINI_API_KEY
```

Do not share this key publicly.

✅ **Magic Key 1 is ready.**

------------------------------------------------------------------------

# 🧩 Magic Key 2: Google Drive

NimbleVault needs permission to read the Drive folder containing your
videos.

## 2.1 Create a Google Cloud project

1.  Open: https://console.cloud.google.com/

2.  Create a new project, or select an existing project.

3.  Give it a name such as:

``` text
NimbleVault
```

------------------------------------------------------------------------

## 2.2 Enable Google Drive API

1.  In Google Cloud Console, search for:

``` text
Google Drive API
```

2.  Open it.

3.  Click **Enable**.

------------------------------------------------------------------------

## 2.3 Create a Service Account

1.  Go to:

**APIs & Services → Credentials**

2.  Click:

**+ CREATE CREDENTIALS**

3.  Select:

**Service account**

4.  Give it a name such as:

``` text
drive-robot
```

5.  Click **Create and Continue**.

6.  Finish the creation process.

------------------------------------------------------------------------

## 2.4 Download the Service Account key

1.  On the Credentials page, find your new service account.

2.  Open it.

3.  Go to the **Keys** tab.

4.  Click:

**ADD KEY → Create new key**

5.  Select:

**JSON**

6.  Click **Create**.

A JSON file will download.

------------------------------------------------------------------------

## 2.5 Put the key into the project

Rename the downloaded file to:

``` text
service_account.json
```

Put it directly inside:

``` text
nimblevault/backend/
```

So you have:

``` text
backend/
├── service_account.json
├── requirements.txt
├── .env
└── ...
```

⚠️ **Never upload `service_account.json` to GitHub.**

------------------------------------------------------------------------

## 2.6 Give the Service Account access to your Drive folder

This is very important.

1.  Open `service_account.json` with a text editor.

2.  Find:

``` json
"client_email": "..."
```

3.  Copy the email address.

4.  Open Google Drive.

5.  Find the folder containing the videos you want NimbleVault to
    process.

6.  Right-click the folder.

7.  Click **Share**.

8.  Paste the Service Account email.

9.  Give it **Viewer** access.

10. Click **Send**.

The robot can now read that folder.

✅ **Magic Key 2 is ready.**

------------------------------------------------------------------------

# 🧩 Magic Key 3: YouTube

Now give NimbleVault permission to upload videos to your YouTube
channel.

## 3.1 Enable YouTube Data API v3

In the same Google Cloud project:

1.  Open:

**APIs & Services**

2.  Search for:

``` text
YouTube Data API v3
```

3.  Open it.

4.  Click **Enable**.

------------------------------------------------------------------------

## 3.2 Configure the OAuth consent screen

If your project has not configured OAuth yet:

1.  Go to the Google Cloud OAuth consent screen area.

2.  Create/configure the consent screen.

3.  Use:

``` text
App name: NimbleVault
```

4.  Provide the required contact information.

5.  If the application is configured as **External**, add your Google
    account as a **test user** when Google Cloud asks for test users.

> Google Cloud's interface can change over time. Follow the current
> labels shown in the console.

------------------------------------------------------------------------

## 3.3 Create the YouTube OAuth client

1.  Go to:

**APIs & Services → Credentials**

2.  Click:

**+ CREATE CREDENTIALS**

3.  Select:

**OAuth client ID**

4.  For application type, choose:

**Desktop app**

5.  Give it a name such as:

``` text
youtube-uploader
```

6.  Click **Create**.

------------------------------------------------------------------------

## 3.4 Download the client secrets

Download the OAuth client JSON file.

Rename it:

``` text
client_secrets.json
```

Put it inside:

``` text
nimblevault/backend/
```

⚠️ **Never publish this credential file.**

------------------------------------------------------------------------

## 3.5 Log in to YouTube

From the `backend` folder, run:

``` bash
python scripts/auth_youtube.py
```

A browser window should open.

1.  Select your Google account.
2.  Continue through the Google permission screen.
3.  Allow the requested YouTube access.

After successful authorization, NimbleVault saves:

``` text
youtube_token.json
```

This token is used for later YouTube API requests.

⚠️ Keep `youtube_token.json` private.

✅ **Magic Key 3 is ready.**

------------------------------------------------------------------------

# 🚦 Step 2: Check Everything Before a Real Upload

Before uploading real videos, run:

``` bash
python scripts/run_pipeline.py --status
```

The command checks the application's current state and configuration.

You want the required services to report as working, for example:

``` text
NIMBLEVAULT - PRE-FLIGHT SYSTEM READINESS CHECK

[OK] Database: SQLite engine active & schema verified.
[OK] Google Drive: Service Account valid
[OK] YouTube API: OAuth2 credentials active
[OK] Gemini AI: Gemini API key active
```

If something reports an error, fix that item before running a live
upload.

------------------------------------------------------------------------

# 🎮 Step 3: Run NimbleVault

## 3.1 Test safely first: Dry Run

A dry run is the safest way to test the real Drive workflow.

Run:

``` bash
python scripts/run_pipeline.py --folder-id YOUR_FOLDER_ID --dry-run
```

Replace:

``` text
YOUR_FOLDER_ID
```

with your Google Drive folder ID.

For example, if your Drive URL looks like:

``` text
https://drive.google.com/drive/folders/1AbCdEfGh123
```

the folder ID is:

``` text
1AbCdEfGh123
```

The dry run can process the Drive side and metadata generation while
simulating the YouTube upload instead of performing the real upload.

------------------------------------------------------------------------

## 3.2 Upload to YouTube for real

When you are ready for a real upload:

``` bash
python scripts/run_pipeline.py --folder-id YOUR_FOLDER_ID
```

NimbleVault will process the selected Drive folder and upload eligible
videos according to the configured workflow.

The default privacy setting comes from:

``` env
YOUTUBE_PRIVACY_STATUS=private
```

So check your `.env` before doing a live run.

------------------------------------------------------------------------

## 3.3 Check the upload status

Run:

``` bash
python scripts/run_pipeline.py --status
```

This shows the tracked video jobs and their current state.

A completed job can include information such as:

``` text
Status       File Name              YouTube Link
COMPLETED    example_video.mp4      https://youtube.com/watch?v=...
```

------------------------------------------------------------------------

# 🧰 Step 4: Useful Commands

  -------------------------------------------------------------------------------------------------------------
  What you want to do                 Command
  ----------------------------------- -------------------------------------------------------------------------
  Run the zero-credential demo        `python scripts/demo.py`

  Run the demo through the main CLI   `python scripts/run_pipeline.py --demo`

  Check system/status                 `python scripts/run_pipeline.py --status`

  Check YouTube authorization         `python scripts/auth_youtube.py --check`

  Scan/sync Google Drive              `python scripts/run_pipeline.py --sync`

  Safe real-Drive test                `python scripts/run_pipeline.py --folder-id YOUR_FOLDER_ID --dry-run`

  Live process a Drive folder         `python scripts/run_pipeline.py --folder-id YOUR_FOLDER_ID`

  Scan only, without processing       `python scripts/run_pipeline.py --folder-id YOUR_FOLDER_ID --scan-only`
  uploads                             

  Process pending jobs                `python scripts/run_pipeline.py --batch`

  Force re-processing                 `python scripts/run_pipeline.py --folder-id YOUR_FOLDER_ID --force`
  -------------------------------------------------------------------------------------------------------------

------------------------------------------------------------------------

# 🧠 How NimbleVault Remembers Videos

NimbleVault uses SQLite to keep track of video jobs.

A simplified state flow is:

``` text
PENDING
   ↓
DOWNLOADING
   ↓
TITLING
   ↓
UPLOADING
   ↓
COMPLETED
```

If something fails, a job can enter:

``` text
FAILED
```

The database also stores information needed for auditing and retrying
work.

This prevents a normal repeated scan from blindly uploading the same
Drive file again.

------------------------------------------------------------------------

# ❤️ Self-Healing: What If a YouTube Video Is Deleted?

NimbleVault can check whether previously uploaded YouTube videos are
still available.

If an uploaded video is later deleted from YouTube:

1.  NimbleVault detects that the YouTube video is no longer available.
2.  The database record is changed back to `PENDING`.
3.  The stored YouTube video ID is cleared.
4.  The video becomes eligible for another upload.

Run:

``` bash
python scripts/run_pipeline.py --status
```

or run the pipeline/sync again to perform the reconciliation workflow.

------------------------------------------------------------------------

# 📁 Project Structure

Your project should roughly look like this:

``` text
nimblevault/
│
├── README.md
│
└── backend/
    │
    ├── app/
    │   ├── core/
    │   │   ├── config.py
    │   │   └── database.py
    │   │
    │   ├── models/
    │   │   └── video.py
    │   │
    │   └── services/
    │       ├── drive_service.py
    │       ├── gemini_service.py
    │       └── youtube_service.py
    │
    ├── scripts/
    │   ├── run_pipeline.py
    │   ├── demo.py
    │   ├── auth_youtube.py
    │   └── generate_metadata.py
    │
    ├── requirements.txt
    ├── .env.example
    ├── .env
    ├── service_account.json
    ├── client_secrets.json
    └── youtube_token.json
```

The credential files and `.env` should remain private and should not be
committed to a public repository.

------------------------------------------------------------------------

# 🩹 Step 5: Common Problems

## ❓ Google Drive says `403 Access Denied`

### What happened?

The Google Drive Service Account probably does not have access to the
target folder.

### Fix

1.  Open `service_account.json`.
2.  Copy the `client_email`.
3.  Open the target Google Drive folder.
4.  Click **Share**.
5.  Add the Service Account email.
6.  Give it **Viewer** access.
7.  Run the pipeline again.

------------------------------------------------------------------------

## ❓ YouTube says `403 quotaExceeded`

### What happened?

The YouTube Data API has quota limits.

### Fix

Do not repeatedly perform live uploads while testing.

Use:

``` bash
python scripts/run_pipeline.py --folder-id YOUR_FOLDER_ID --dry-run
```

for safe testing.

If the live API quota has been exhausted, wait for the applicable quota
reset or review the quota information for your Google Cloud project.

------------------------------------------------------------------------

## ❓ I deleted a video on YouTube. What happens?

NimbleVault can detect the missing YouTube video during its
reconciliation process and return the corresponding database job to
`PENDING`.

Run:

``` bash
python scripts/run_pipeline.py --status
```

or run the pipeline again.

------------------------------------------------------------------------

## ❓ I renamed or moved a video in Google Drive. What should I do?

Run the pipeline again:

``` bash
python scripts/run_pipeline.py --folder-id YOUR_FOLDER_ID
```

NimbleVault scans the Drive hierarchy and uses the available Drive
path/context when generating metadata.

------------------------------------------------------------------------

# 🏁 Final Checklist

Before a **real** upload, make sure:

-   [ ] Python is installed.
-   [ ] You created the virtual environment.
-   [ ] Dependencies are installed.
-   [ ] `.env` exists.
-   [ ] Gemini API key is configured if you want Gemini metadata
    generation.
-   [ ] Google Drive API is enabled.
-   [ ] `service_account.json` is inside `backend/`.
-   [ ] The Service Account can view the target Drive folder.
-   [ ] YouTube Data API v3 is enabled.
-   [ ] `client_secrets.json` is inside `backend/`.
-   [ ] You ran `python scripts/auth_youtube.py`.
-   [ ] YouTube authorization completed successfully.
-   [ ] You tested the workflow with `--dry-run`.
-   [ ] Your YouTube privacy setting in `.env` is what you want.
-   [ ] You are using the correct Google Drive folder ID.

Then run:

``` bash
python scripts/run_pipeline.py --folder-id YOUR_FOLDER_ID
```

🎉 **You are ready to run NimbleVault!**
