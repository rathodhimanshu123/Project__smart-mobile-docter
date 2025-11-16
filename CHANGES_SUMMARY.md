# Changes Summary

## 12-Hour Time Format Update

### Overview
Updated all time displays in the prediction system to use 12-hour (AM/PM) format for better user readability. All formatting is done client-side using a shared utility function.

### Example
- **Input (ISO)**: `2024-01-01T14:30:00Z`
- **Output (12h)**: `2:30 PM` (or `1:30 PM` depending on timezone)

### Files Changed
1. **`static/js/time-utils.js`** (NEW)
   - Shared utility for 12-hour time formatting
   - `formatTime12h(ts)` function handles ISO strings, Date objects, and timestamps
   - Feature flag `USE_12H_FORMAT` for easy toggling
   - Graceful fallback for invalid dates

2. **`static/js/prediction.js`**
   - Updated chart tooltips to use 12-hour format
   - Updated "Battery drops to X%" labels to show 12-hour times
   - Updated `updateKeyDates()` to format dates in 12-hour format
   - All time displays now use `formatTime12h()` helper

3. **`templates/result.html`**
   - Added `<script>` tag to load `time-utils.js`
   - All time formatting moved to client-side JavaScript

4. **`tests/prediction_format_test.js`** (NEW)
   - Unit tests for time formatting helper
   - Tests edge cases: 00:00 → 12:00 AM, 12:00 → 12:00 PM, 13:05 → 1:05 PM
   - Tests timezone independence with ISO strings

### Backend
- No changes to backend API
- Continues returning ISO timestamps in `predictedTimeTo` fields
- All presentation logic handled in frontend

### Feature Flag
Set `window.USE_12H_FORMAT = false` to disable 12-hour format and revert to ISO display.

---

# HTTPS-Friendly Updates Summary

## Files Changed

1. **`cloudflared.yml`** (NEW)
   - Cloudflare Tunnel configuration example
   - Supports named tunnels for persistent HTTPS URLs

2. **`README_COMPLETE_SOLUTION.md`**
   - Added HTTPS setup section with Cloudflare Tunnel instructions
   - Added verification steps for testing

3. **`app.py`**
   - Added `is_secure_request()` helper function
   - Updated `/api/collect` to accept and normalize new fields:
     - `batteryLevel`, `batteryCharging`, `insecureContext`
     - `storageSandboxUsedMB`, `storageSandboxQuotaMB`, `storageSandboxUsagePercent`, `storageSource`
   - Updated `compute_performance_score()` to prefer new sandbox MB format
   - Updated QR generation to use HTTPS detection
   - Updated SSE endpoint to ensure session exists
   - Added logging for new fields

4. **`templates/collector.html`**
   - Added `bytesToMB()` and `safeEstimateStorage()` helper functions
   - Updated to use `navigator.storage.estimate()` with MB conversion
   - Updated to use `navigator.getBattery()` with event listeners
   - Added `batteryLevel`, `batteryCharging`, `insecureContext` to snapshot
   - Updated storage collection to use new format
   - Updated UI labels to clearly indicate "Browser Sandbox" storage
   - Added last-updated timestamps
   - Enhanced console logging

5. **`templates/result.html`**
   - Updated live monitor to poll storage every 12 seconds
   - Updated responsiveness tests to run every 5 seconds
   - Updated storage gauge label to "Storage Usage (Browser Sandbox)"
   - Added tooltips: "Browser sandbox storage (not full device storage)"
   - Updated gauge timestamps to show "Last updated: HH:MM:SS"
   - Updated storage display to show "Browser Sandbox" labels
   - Enhanced storage polling with proper error handling

## Key Features

### HTTPS Support
- All URLs converted to relative paths (works behind tunnels)
- QR codes use HTTPS when available (via `X-Forwarded-Proto` header)
- Graceful fallback for insecure contexts

### Storage API
- Uses `navigator.storage.estimate()` with MB conversion
- Computes `storageSandboxUsedMB`, `storageSandboxQuotaMB`, `storageSandboxUsagePercent`
- Polls every 12 seconds in live monitor
- Shows "N/A" with tooltip when unavailable

### Battery API
- Uses `navigator.getBattery()` with event listeners
- Posts `batteryLevel`, `batteryCharging` to `/api/collect`
- Includes `insecureContext` flag when APIs are blocked
- Live updates via SSE

### Backward Compatibility
- Accepts both new (MB) and old (bytes) storage formats
- Computes missing fields automatically
- Falls back gracefully when fields are absent

## Test Log Example

### Successful Collector POST
```
[COLLECTOR] SessionId from query: abc123
[COLLECTOR] Storage collected: {usedMB: 45, quotaMB: 512, usagePercent: 8}
[COLLECTOR] Sending snapshot to /api/collect: {
  sessionId: "abc123",
  hasBattery: true,
  hasStorage: true,
  batteryLevel: 85,
  batteryCharging: false,
  insecureContext: false,
  storageSandboxUsedMB: 45,
  storageSandboxQuotaMB: 512,
  storageSandboxUsagePercent: 8
}
[COLLECTOR] POST successful: {success: true, message: "Snapshot received", sessionId: "abc123", timestamp: "2024-01-15T10:30:00"}
```

### Backend Processing
```
[COLLECTOR] POST received for sessionId: abc123
[COLLECTOR] Snapshot fields: batteryLevel=85, batteryCharging=false, insecureContext=false, storageSandboxUsedMB=45, storageSandboxQuotaMB=512, storageSandboxUsagePercent=8
```

### SSE Update
```
[SSE] Opening stream for sessionId: abc123
[SSE] Broadcast sent for session abc123: snapshot
[DASHBOARD] SSE message received: snapshot
[DASHBOARD] Snapshot loaded: {battery: {level: 85, charging: false}, storage: {storageSandboxUsedMB: 45, storageSandboxQuotaMB: 512, storageSandboxUsagePercent: 8, storageSource: "browser-sandbox"}}
```

### Live Monitor Updates
```
[MONITOR] Live monitor started
[MONITOR] Storage updated: {usedMB: 45, quotaMB: 512, usagePercent: 8, timestamp: "2024-01-15T10:30:12"}
[MONITOR] Responsiveness test: {duration: "45.23ms", index: 95}
```

## Verification Checklist

- [x] Cloudflared tunnel configuration created
- [x] README updated with tunnel setup steps
- [x] All hardcoded URLs converted to relative paths
- [x] Collector uses `navigator.storage.estimate()` with MB conversion
- [x] Collector uses `navigator.getBattery()` with event listeners
- [x] Live monitor polls storage every 12s
- [x] Responsiveness tests run every 5s
- [x] UI clearly labels sandbox vs device storage
- [x] Last-updated timestamps shown
- [x] Backend accepts and stores new fields
- [x] QR links use HTTPS detection
- [x] Performance score prefers sandbox MB format
- [x] SSE uses same sessionId as collector
- [x] Graceful fallbacks for missing fields
- [x] Console/log messages added
- [x] Backward compatibility maintained

