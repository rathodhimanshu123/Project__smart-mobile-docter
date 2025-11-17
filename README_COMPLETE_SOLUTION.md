# Smart Mobile Doctor - Complete Device Information Solution

## Your Requirement: Full Device Information After QR Scan

✅ **SOLUTION IMPLEMENTED**: After scanning QR code, the system now shows ALL possible internal device information.

## Two Ways to Get Device Information:

### 1. **Browser Method** (Works on any device, limited data)
- Scan QR → Opens in browser → Shows available browser data
- **Shows**: Model, Android version, estimated age, RAM (approx), storage estimate, battery level, CPU cores, screen resolution, network info
- **Limitations**: Cannot access IMEI, exact RAM/storage, carrier info, CPU model (browser security restrictions)

### 2. **Native Android App Method** (Full device details)
- Scan QR → Tap "Open App" link → Native app collects everything
- **Shows**: ALL information including IMEI, exact RAM/storage, carrier, CPU model, charging status, device ID, etc.

## HTTPS Setup with Cloudflare Tunnel (Recommended)

For full functionality, the app requires HTTPS to access browser APIs like Battery and Storage. Here's how to set up a Cloudflare Tunnel:

### Option A: Quick Tunnel (No Account Required)
```bash
# Install cloudflared if not already installed
# Windows: Download from https://github.com/cloudflare/cloudflared/releases
# Or use: winget install cloudflare.cloudflared

# Start quick tunnel (generates random URL)
cloudflared tunnel --url http://localhost:8080
```

This will output a URL like `https://random-name.trycloudflare.com` - use this URL to access your app.

### Option B: Named Tunnel (Persistent URL)
1. **Create a Cloudflare account** (free) at https://dash.cloudflare.com
2. **Create a tunnel:**
   ```bash
   cloudflared tunnel create smart-mobile-doctor
   ```
3. **Configure the tunnel** - Edit `cloudflared.yml` (provided in project root):
   - Replace `smart-mobile-doctor.your-domain.com` with your domain
   - Or use a trycloudflare.com subdomain
4. **Start the tunnel:**
   ```bash
   cloudflared tunnel --config cloudflared.yml run smart-mobile-doctor
   ```
5. **Verify HTTPS** - Open the tunnel URL and confirm it shows HTTPS in the browser

### Verification Steps:
1. ✅ Start Flask server: `python app.py` (or use WSGI server like gunicorn/waitress for production)
2. ✅ Verify local server is reachable: `curl -I http://127.0.0.1:8080`
3. ✅ Start cloudflared tunnel (Option A or B above)
4. ✅ Open the HTTPS URL in a browser
5. ✅ Generate QR code and scan with mobile device
6. ✅ Confirm `/api/collect` POST includes new fields:
   - `storageSandboxUsedMB`, `storageSandboxQuotaMB`, `storageSandboxUsagePercent`
   - `batteryLevel`, `batteryCharging`, `insecureContext`
7. ✅ Confirm battery changes reflect live in dashboard
8. ✅ Confirm storage updates every 12s in live monitor

### Production Deployment Notes:

**Using WSGI Server (Recommended):**
```bash
# Install gunicorn (Linux/Mac) or waitress (Windows)
pip install gunicorn  # or: pip install waitress

# Run with gunicorn (Linux/Mac)
gunicorn -w 4 -b 0.0.0.0:8080 --timeout 120 app:app

# Run with waitress (Windows)
waitress-serve --host=0.0.0.0 --port=8080 --threads=4 app:app
```

**Cloud Tunnel Setup:**
```bash
# Quick tunnel (no account needed)
.\cloudflared.exe tunnel --url http://127.0.0.1:8080

# Named tunnel (persistent URL)
cloudflared tunnel run <tunnel-name>
```

**Testing Share Links and PDF Downloads:**
```bash
# Test share link creation
curl -X POST http://localhost:8080/api/share-report/<session_id>

# Test PDF download (synchronous)
curl -I http://localhost:8080/api/download-health-report/<session_id>

# Test PDF download (with tunnel URL)
curl -L --output file.pdf https://<tunnel-url>/api/download-health-report/<session_id>

# Test async PDF status check
curl http://localhost:8080/api/report-status/<token>

# Test PDF file download
curl -L --output file.pdf http://localhost:8080/download-file/<token>
```

**Request Timeouts:**
- PDF generation timeout: 60 seconds (client-side)
- Server request timeout: 120 seconds (recommended for WSGI)
- Share token expiry: 24 hours
- PDF file TTL: 1 hour (auto-cleanup)

## 30-Day Mobile Health Prediction Feature

The app now includes AI-powered 30-day health predictions based on recent device trends.

### Testing the Prediction Feature:

1. **Collect at least 3 snapshots:**
   - Generate QR code and scan with mobile device
   - Tap "Start Scan" on the collector page
   - Wait a few minutes, then scan again (repeat 2-3 times)
   - This builds history for predictions

2. **Verify prediction API:**
   ```bash
   # Get session ID from the result page URL or QR code
   curl http://localhost:8080/api/prediction/YOUR_SESSION_ID
   ```
   Expected JSON format:
   ```json
   {
     "success": true,
     "prediction": {
       "status": "success",
       "last_recompute": "2024-01-15T10:30:00",
       "days_projected": 30,
       "time_series": {
         "battery": [85, 84, 83, ...],  // 30 values
         "storage": [45, 46, 47, ...],  // 30 values
         "responsiveness": [75, 74, 73, ...]  // 30 values
       },
       "key_dates": {
         "battery_20": "2024-02-15T10:30:00",
         "storage_80": "2024-02-10T10:30:00"
       },
       "risk_scores": {
         "thermal_stress": 25.5,
         "battery_drain_rate": -2.3,
         "storage_growth_rate": 0.5
       },
       "health_score_30_day": 72.5,
       "recommendations": [
         "✅ Device health projections look stable. Continue regular maintenance."
       ],
       "current_values": {
         "battery": 85.0,
         "storage": 45.0,
         "responsiveness": 75.0
       }
     }
   }
   ```

3. **Test SSE prediction updates:**
   - Open result page with session ID
   - Open browser console (F12)
   - Trigger a new snapshot (scan QR again or wait for battery update)
   - Verify console shows: `[PREDICTION] SSE update received`
   - Verify charts update automatically

4. **Test chart rendering:**
   - Navigate to result page with session ID
   - Verify "Future Health Prediction (30 days)" card appears
   - Verify 3 charts render (Battery, Storage, Responsiveness)
   - Verify health score displays
   - Verify risk badges show correct colors
   - Verify recommendations list populates

5. **Test demo mode:**
   - Toggle "Demo Mode" checkbox in prediction card
   - Verify charts update with accelerated trends (2x speed)
   - Toggle off and verify charts return to normal

6. **Test insufficient data handling:**
   - Create a new session (generate new QR)
   - Scan once (only 1 data point)
   - Verify "Insufficient data" message appears
   - Verify prediction card is hidden

7. **Run unit tests:**
   ```bash
   python test_prediction.py
   ```
   Expected output: All 7 tests pass

### Prediction Features:
- ✅ Battery drain rate prediction (linear regression)
- ✅ Storage growth rate prediction
- ✅ Responsiveness projection (exponential smoothing)
- ✅ Thermal/stress risk score calculation
- ✅ Overall 30-day health score (weighted)

### Time Format Display:
All prediction times are displayed in 12-hour (AM/PM) format for better readability:
- **Example**: ISO timestamp `2024-01-01T14:30:00Z` displays as `2:30 PM`
- Chart tooltips show projected times in 12-hour format
- "Battery drops to X%" labels show times like "In ~120 min (2:30 PM)"
- Feature flag `window.USE_12H_FORMAT` can be set to `false` to disable 12-hour format
- ✅ Key dates (battery thresholds, storage thresholds)
- ✅ Actionable recommendations
- ✅ Real-time updates via SSE
- ✅ Chart.js visualizations
- ✅ Demo mode for presentations
- ✅ Graceful fallbacks for missing data

## Quick Setup Instructions:

### Step 1: Build and Install Android App
```bash
# Run this on Windows:
build_apk.bat

# Or manually:
cd app
gradlew assembleDebug
```

The APK will be created at: `app/build/outputs/apk/debug/app-debug.apk`

### Step 2: Install APK on Your Phone
1. Enable "Developer options" and "USB debugging" on your phone
2. Transfer the APK file to your phone
3. Install the APK (allow installation from unknown sources)
4. Grant permissions when prompted:
   - Phone state
   - Storage
   - Network access

### Step 3: Test the Complete Solution
1. Start the Flask server: `python app.py`
2. Go to `http://localhost:8080`
3. Upload a phone screenshot (optional)
4. Click "Generate QR Code"
5. Scan the QR with your phone
6. **Tap the "Open App" link** (not just the HTTP link)
7. The app will collect full device details and redirect to results

## What Information is Collected:

### Browser Method:
- 📱 Device Model (from User Agent)
- 🤖 Android Version
- 📅 Estimated Device Age
- 💾 RAM (approximate)
- 💿 Storage (quota estimate)
- 🔋 Battery Level & Status
- ⚡ CPU Cores
- 📱 Screen Resolution & Pixel Ratio
- 📶 Network Type & Speed
- 🌍 Language & Timezone

### Native Android App Method (FULL DETAILS):
- 📱 **Device Model** (exact)
- 🏭 **Manufacturer** (exact)
- 🤖 **Android Version** (exact)
- 📅 **Device Age** (estimated from Android version)
- 💾 **RAM Total** (exact in GB)
- 💾 **RAM Available** (exact in GB)
- 💿 **Storage Total** (exact in GB)
- 💿 **Storage Available** (exact in GB)
- 🔋 **Battery Level** (exact percentage)
- 🔌 **Charging Status** (Charging/Discharging/Full)
- 🔌 **Plugged Type** (AC/USB/Wireless)
- ⚡ **CPU Cores** (exact count)
- 🏗️ **CPU Model** (exact model name)
- ⚡ **CPU Max Frequency** (in MHz)
- 📱 **Screen Resolution** (exact)
- 📏 **Screen Size** (in inches)
- 📶 **Network Type** (4G/5G/WiFi)
- 🏢 **Carrier Name** (if available)
- 📱 **SIM State** (if available)
- 🔑 **Device ID** (IMEI or Android ID)
- 🌍 **Language & Timezone**

## Health Score System

The application displays **two distinct health scores** to provide comprehensive device health assessment:

### (A) Live Performance Score
- **Source**: Real-time browser-exposed live metrics
- **Computation**: Based on RAM (30%), Storage (30%), Battery (20%), and OS recency (20%)
- **Updates**: Automatically updates as live data changes via SSE
- **Use Case**: Quick real-time assessment based on current browser-accessible metrics
- **Limitations**: Uses browser sandbox storage (not full device storage) and approximate RAM values

### (B) Verified Health Score
- **Source**: Trusted score computed from parsed "About device" screenshot + live samples
- **Computation**: 
  - **Battery Health (30%)**: If battery capacity (mAh) is present, estimates wear and maps to 0-100. Otherwise, uses battery percent × 0.85 (penalizes unknown health)
  - **Storage (30%)**: Free percentage = (storageTotal - storageUsed)/storageTotal × 100, clamped to 0-100
  - **RAM+Responsiveness (20%)**: RAM normalized to 8GB baseline, combined 50/50 with live responsiveness index
  - **OS/Updates (20%)**: Recent OS versions (Android 12+, iOS 15+) score 100, older versions score 50-100
- **Updates**: Recomputes on (a) successful About-parsing uploads and (b) every new non-charging battery SSE update
- **Use Case**: Accurate health assessment based on verified device specifications
- **Features**: 
  - Shows breakdown panel with component scores and raw parsed fields
  - Displays warning tooltip when fallback logic is used (missing device info)
  - Color-coded score display (green/yellow/red bands)

### Difference Between Scores:
- **Live Performance Score**: Real-time, based on browser-exposed metrics (approximate, limited by browser security)
- **Verified Health Score**: Computed from verified device profile (accurate, based on About device screenshot + live samples)

### API Endpoints:
- `GET /api/session/<session_id>/verified-score` - Get verified health score breakdown
- Verified score updates are broadcast over SSE as `verified_score` events

## Technical Implementation:

### Files Modified:
1. **`app.py`** - Enhanced QR generation with LAN IP, deep link support, verified score computation
2. **`templates/mobile.html`** - Auto-attempts to open native app
3. **`static/js/mobile.js`** - Maximum browser data collection
4. **`templates/result.html`** - Shows both app deep link and HTTP link, displays two score cards
5. **`utils/ocr_processor.py`** - Enhanced OCR parsing with confidence scores
6. **Android App Files** - Native device information collection

### Key Features:
- **Dual Mode**: Browser fallback + Native app enhancement
- **LAN Support**: QR codes work on same WiFi network
- **Deep Linking**: `smd://collect?session_id=...&base_url=...`
- **Permission Handling**: Runtime permissions for sensitive data
- **Error Handling**: Graceful fallbacks and user guidance
- **Rich Data**: 20+ device parameters collected

## Troubleshooting:

### If browser shows "Not available":
- ✅ This is normal for browser-only access
- ✅ Install the Android app for full details
- ✅ Tap the "Open App" link in the QR debug section

### If app doesn't open from QR:
- Check if app is installed
- Grant all permissions in app settings
- Try tapping the "Open App" link manually

### If server connection fails:
- Ensure phone and PC are on same WiFi
- Check Windows Firewall allows port 8080
- Test: `http://<PC_IP>:8080/test` from phone

## Result:
✅ **Your requirement is now FULLY MET**: After scanning QR code, the system displays ALL possible internal device information through the native Android app, with browser fallback for maximum compatibility.

The solution works in "every situation" - browser users get available data, app users get complete device details. 