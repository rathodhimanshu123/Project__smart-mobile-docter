# QR Code Troubleshooting Guide

## Issue: Page stops loading after scanning QR code

If the QR code scans successfully but the mobile page stops loading after a few seconds, follow these troubleshooting steps:

### 1. Check Server Status

First, ensure the server is running properly:

```bash
python app.py
```

The server should start on `http://localhost:8080` or `http://0.0.0.0:8080`

### 2. Test Basic Connectivity

Run the test script to verify all components are working:

```bash
python test_qr_functionality.py
```

This will test:
- Server health
- QR code generation
- Mobile endpoint
- Data submission

### 3. Common Issues and Solutions

#### Issue A: Network Connectivity Problems

**Symptoms:**
- Page loads but stops after a few seconds
- No error messages visible
- Console shows network errors

**Solutions:**
1. **Check if phone and computer are on the same network**
   - Both devices must be connected to the same WiFi network
   - Try using mobile hotspot from your phone

2. **Verify server IP address**
   - The QR code should point to your computer's local IP (e.g., 192.168.1.100:8080)
   - Not localhost or 127.0.0.1 (these only work on the same device)

3. **Check firewall settings**
   - Windows Firewall might block port 8080
   - Allow Python/Flask through firewall

#### Issue B: JavaScript Errors

**Symptoms:**
- Page loads but JavaScript stops working
- Console shows error messages
- Data collection fails

**Solutions:**
1. **Check browser console**
   - Open Developer Tools (F12) on your phone
   - Look for JavaScript errors in the Console tab

2. **Try different browser**
   - Some browsers have different API support
   - Try Chrome, Firefox, or Safari

3. **Check browser permissions**
   - Ensure the site has permission to access device information
   - Some APIs require HTTPS (not an issue on localhost)

#### Issue C: Server-Side Errors

**Symptoms:**
- Data collection works but submission fails
- Server logs show errors
- 500 error responses

**Solutions:**
1. **Check server logs**
   - Look at the terminal where you ran `python app.py`
   - Look for error messages

2. **Verify file permissions**
   - Ensure the `static/phone_data` directory is writable
   - Check disk space

3. **Test data submission manually**
   ```bash
   curl -X POST http://localhost:8080/api/submit_phone_data \
     -H "Content-Type: application/json" \
     -d '{"session_id":"test","phone_data":{"test":true}}'
   ```

### 4. Debug Steps

#### Step 1: Check QR Code URL
1. Generate a QR code
2. Use a QR code reader that shows the URL
3. Verify the URL points to your computer's IP address, not localhost

#### Step 2: Test Mobile Page Directly
1. Copy the URL from the QR code
2. Open it directly in your phone's browser
3. Check if the page loads completely

#### Step 3: Monitor Network Traffic
1. Open Developer Tools on your phone
2. Go to Network tab
3. Scan the QR code and watch for failed requests

#### Step 4: Check Server Logs
1. Watch the terminal where the server is running
2. Look for error messages when you scan the QR code
3. Check for any exceptions or failed requests

### 5. Manual Workaround

If the automatic data collection fails, you can still view results:

1. **Manual redirect button**: The page should show a "View Diagnosis Results" button
2. **Direct URL access**: Use the session ID to access results directly
3. **Debug page**: Visit `/debug` to test individual components

### 6. Prevention

To avoid future issues:

1. **Use consistent network setup**
2. **Keep server running on same IP**
3. **Test QR codes before sharing**
4. **Monitor server logs regularly**

### 7. Getting Help

If the issue persists:

1. **Collect debug information**:
   - Server logs
   - Browser console errors
   - Network request failures
   - QR code URL

2. **Test with different devices**:
   - Try different phones
   - Try different browsers
   - Try different networks

3. **Check recent changes**:
   - Any recent code modifications
   - Network configuration changes
   - System updates

## Quick Fix Checklist

- [ ] Server is running (`python app.py`)
- [ ] Phone and computer on same network
- [ ] Firewall allows port 8080
- [ ] QR code URL uses computer's IP (not localhost)
- [ ] Browser has necessary permissions
- [ ] No JavaScript errors in console
- [ ] Server logs show no errors
- [ ] Test script passes all checks

If all items are checked and the issue persists, the problem might be:
- Network infrastructure issues
- Browser compatibility problems
- Device-specific limitations
- Server resource constraints
