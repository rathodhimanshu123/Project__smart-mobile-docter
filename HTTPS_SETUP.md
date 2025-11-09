# HTTPS Setup Guide for Smart Mobile Doctor

The Smart Mobile Doctor app requires HTTPS to access modern browser APIs like Battery, Storage, and approximate RAM. This guide covers several options for running the app over HTTPS.

## Why HTTPS is Required

Modern browser APIs require a secure context (HTTPS) for security and privacy reasons:
- **Battery API** (`navigator.getBattery()`) - Requires HTTPS
- **Storage API** (`navigator.storage.estimate()`) - Requires HTTPS  
- **Device Memory API** (`navigator.deviceMemory`) - Requires HTTPS

Without HTTPS, these APIs will return `null` and show "Insecure context (enable HTTPS)" messages.

## Option 1: Cloudflare Tunnel (Recommended for Testing)

Cloudflare Tunnel provides a free HTTPS URL that tunnels to your local server.

### Setup:
1. Install Cloudflare Tunnel:
   ```bash
   # Windows (using Chocolatey)
   choco install cloudflared
   
   # macOS
   brew install cloudflared
   
   # Linux
   wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
   chmod +x cloudflared-linux-amd64
   sudo mv cloudflared-linux-amd64 /usr/local/bin/cloudflared
   ```

2. Start your Flask server:
   ```bash
   python app.py
   ```

3. In a new terminal, start Cloudflare Tunnel:
   ```bash
   cloudflared tunnel --url http://localhost:8080
   ```

4. Cloudflare will provide a URL like `https://random-subdomain.trycloudflare.com`
   - Use this URL to access your app
   - Share this URL with your mobile device to scan the QR code

### Pros:
- Free
- No configuration needed
- Works immediately
- Public URL (can share with others)

### Cons:
- URL changes each time (unless you set up a custom domain)
- Requires internet connection

## Option 2: ngrok

ngrok provides secure tunnels to localhost.

### Setup:
1. Sign up at https://ngrok.com (free tier available)
2. Install ngrok and authenticate:
   ```bash
   # Download from https://ngrok.com/download
   ngrok config add-authtoken YOUR_AUTH_TOKEN
   ```

3. Start your Flask server:
   ```bash
   python app.py
   ```

4. In a new terminal, start ngrok:
   ```bash
   ngrok http 8080
   ```

5. Use the HTTPS URL provided (e.g., `https://abc123.ngrok.io`)

### Pros:
- Free tier available
- Can use custom domains (paid)
- Stable URLs with paid plans

### Cons:
- Requires account setup
- Free tier has session limits

## Option 3: mkcert (Localhost Only)

mkcert creates locally-trusted development certificates for localhost.

### Setup:
1. Install mkcert:
   ```bash
   # Windows (using Chocolatey)
   choco install mkcert
   
   # macOS
   brew install mkcert
   
   # Linux
   sudo apt install libnss3-tools
   wget https://github.com/FiloSottile/mkcert/releases/latest/download/mkcert-v1.4.4-linux-amd64
   chmod +x mkcert-v1.4.4-linux-amd64
   sudo mv mkcert-v1.4.4-linux-amd64 /usr/local/bin/mkcert
   ```

2. Install local CA:
   ```bash
   mkcert -install
   ```

3. Create certificate for localhost:
   ```bash
   mkcert localhost 127.0.0.1 ::1
   ```
   This creates `localhost+2.pem` and `localhost+2-key.pem`

4. Update `app.py` to use SSL:
   ```python
   if __name__ == '__main__':
       app.run(host='0.0.0.0', port=8080, debug=True, ssl_context=('localhost+2.pem', 'localhost+2-key.pem'))
   ```

5. Access via `https://localhost:8080`

### Pros:
- Works offline
- No external services
- Fast and reliable

### Cons:
- Only works on localhost
- Mobile devices need to be on same network and trust the certificate
- More complex setup

## Option 4: Deploy to Vercel/Render/Heroku

Deploy the app to a platform that provides HTTPS automatically.

### Vercel:
1. Install Vercel CLI: `npm i -g vercel`
2. Run `vercel` in project directory
3. Follow prompts

### Render:
1. Create account at https://render.com
2. Create new Web Service
3. Connect your Git repository
4. Render automatically provides HTTPS

### Pros:
- Production-ready
- Automatic HTTPS
- Persistent URLs
- No local setup needed

### Cons:
- Requires deployment
- May have costs for production use

## Testing HTTPS Setup

After setting up HTTPS:

1. Open the collector page in your browser
2. Check that the HTTPS banner is NOT shown (or is dismissible)
3. Tap "Start Scan"
4. Verify that Battery, Storage, and RAM data are collected (not showing "Insecure context")
5. On Android Chrome, verify User-Agent Client Hints are working (Model/Manufacturer should be more accurate)

## Troubleshooting

### "Insecure context" still showing:
- Verify the URL starts with `https://`
- Check browser console for mixed content warnings
- Ensure all resources (CSS, JS) are loaded over HTTPS

### Battery API not working:
- Must be HTTPS
- Not available on iOS/Safari
- Some browsers may require user gesture (Start Scan button handles this)

### Storage API not working:
- Must be HTTPS
- Some browsers may require user gesture

### Mobile device can't access:
- For localhost: Ensure device is on same network
- For mkcert: Install certificate on mobile device
- For Cloudflare/ngrok: Use the provided public URL

## Security Note

These HTTPS setups are for development/testing. For production:
- Use proper SSL certificates (Let's Encrypt, etc.)
- Configure security headers
- Use environment variables for secrets
- Enable HTTPS redirects

