# Google Service Account Setup Guide

## Overview
G9 Schedule Manager uses Google Service Account to access Sheets and Calendar APIs without OAuth2 user consent flow.

---

## Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Name: `G9-Schedule-Manager`
4. Click "Create"

---

## Step 2: Enable APIs

1. In the Cloud Console, go to **APIs & Services** → **Library**
2. Search and enable:
   - **Google Sheets API**
   - **Google Calendar API**

---

## Step 3: Create Service Account

1. Go to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **Service Account**
3. Fill in:
   - Service account name: `g9-scheduler`
   - Service account ID: `g9-scheduler` (auto-filled)
   - Description: `G9 Schedule Manager Service Account`
4. Click **Create and Continue**
5. Grant role: **Editor** (or leave blank for now)
6. Click **Continue** → **Done**

---

## Step 4: Create JSON Key

1. In **Credentials** page, find your service account
2. Click on the service account email
3. Go to **Keys** tab
4. Click **Add Key** → **Create New Key**
5. Choose **JSON** format
6. Click **Create**
7. A JSON file will download automatically

**Save this file as:**
```
/opt/g9/scheduler/credentials/google_service_account.json
```

---

## Step 5: Share Google Sheet

1. Create a new Google Sheet or use existing one
2. Copy the **Sheet ID** from URL:
   ```
   https://docs.google.com/spreadsheets/d/[SHEET_ID]/edit
   ```
3. Click **Share** button
4. Add your service account email (found in JSON file):
   ```
   g9-scheduler@g9-schedule-manager.iam.gserviceaccount.com
   ```
5. Grant **Editor** permission
6. Click **Done**

---

## Step 6: Calendar Setup

### Option A: Use Primary Calendar
- Set `GOOGLE_CALENDAR_ID=primary` in `.env`
- Share your primary calendar with service account email (Editor access)

### Option B: Create Dedicated Calendar
1. Go to [Google Calendar](https://calendar.google.com/)
2. Create new calendar: **G9_Schedule**
3. In calendar settings, get **Calendar ID**:
   ```
   Settings → [Your Calendar] → Integrate calendar → Calendar ID
   ```
4. Share with service account email (Make changes to events permission)
5. Set `GOOGLE_CALENDAR_ID=your_calendar_id` in `.env`

---

## Step 7: Update .env File

```bash
# Update these values in /opt/g9/scheduler/.env

GOOGLE_SERVICE_ACCOUNT_JSON=/opt/g9/scheduler/credentials/google_service_account.json
GOOGLE_SHEET_ID=your_sheet_id_here
GOOGLE_CALENDAR_ID=your_calendar_id_or_primary
```

---

## Step 8: Test Connection

```bash
cd /opt/g9/scheduler

# Test Sheets
python3 exporters/sheets_exporter.py 2025 1

# Test Calendar
python3 exporters/calendar_exporter.py 2025 1
```

---

## Troubleshooting

### Permission Denied
- Make sure service account email is added to Sheet/Calendar with **Editor** permission
- Check JSON file path is correct

### API Not Enabled
- Verify Google Sheets API and Calendar API are enabled in Cloud Console

### JSON File Not Found
- Check file path in `.env` matches actual location
- Ensure JSON file was downloaded correctly

---

## Security Notes

- **Never commit** the JSON key file to git
- Keep JSON file permissions restricted: `chmod 600 google_service_account.json`
- Rotate keys periodically (create new key, delete old one)

---

## Done!

Your Google Services are now configured for G9 Schedule Manager.
