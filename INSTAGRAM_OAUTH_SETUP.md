# Instagram OAuth Setup Guide

This guide will help you set up Instagram OAuth authentication to allow users to login and automatically fetch their account data.

## Prerequisites

- An Instagram account
- A Facebook account (Instagram is owned by Facebook/Meta)
- Your application running on `http://127.0.0.1:5001`

## Step 1: Create a Facebook App

1. Go to [Facebook Developers](https://developers.facebook.com/)
2. Click "My Apps" → "Create App"
3. Select "Consumer" as the app type
4. Fill in the app details:
   - **App Name**: "Web-Nexus Social Suite" (or your preferred name)
   - **App Contact Email**: Your email
5. Click "Create App"

## Step 2: Add Instagram Basic Display Product

1. In your app dashboard, scroll down to "Add Products"
2. Find "Instagram Basic Display" and click "Set Up"
3. Click "Create New App" in the Basic Display section
4. Accept the terms and click "Create App"

## Step 3: Configure Instagram Basic Display Settings

1. Go to "Instagram Basic Display" → "Basic Display"
2. Scroll to "User Token Generator"
3. Configure the following settings:

### OAuth Redirect URIs
Add these URLs:
```
http://127.0.0.1:5001/auth/instagram/callback
https://127.0.0.1:5001/auth/instagram/callback
http://localhost:5001/auth/instagram/callback
```

### Deauthorize Callback URL
```
http://127.0.0.1:5001/auth/instagram/deauthorize
```

### Data Deletion Request URL
```
http://127.0.0.1:5001/auth/instagram/data-deletion
```

4. Click "Save Changes"

## Step 4: Add Instagram Test Users

1. In "Instagram Basic Display" → "Basic Display"
2. Scroll to "User Token Generator"
3. Click "Add or Remove Instagram Testers"
4. This opens Instagram Settings
5. Go to your Instagram app → Settings → Apps and Websites → Tester Invites
6. Accept the invite for your test account

## Step 5: Get Your App Credentials

1. Go to "Settings" → "Basic" in your Facebook App dashboard
2. Copy your **App ID** (Instagram App ID)
3. Click "Show" next to **App Secret** and copy it

## Step 6: Update Your .env File

Add these lines to your `.env` file:

```bash
# Instagram OAuth Credentials
INSTAGRAM_APP_ID=your_app_id_here
INSTAGRAM_APP_SECRET=your_app_secret_here
INSTAGRAM_REDIRECT_URI=http://127.0.0.1:5001/auth/instagram/callback
```

Replace `your_app_id_here` and `your_app_secret_here` with the actual values from Step 5.

## Step 7: Install Required Dependencies

Make sure you have the `requests` library installed:

```bash
pip install requests
```

## Step 8: Restart Your Flask Server

```bash
python app.py
```

## Step 9: Test Instagram Login

1. Open http://127.0.0.1:5001/apps/social_media
2. Click on "Instagram AI Growth" card
3. Click "📸 Login with Instagram" button
4. You should be redirected to Instagram's authorization page
5. Login and authorize the app
6. You'll be redirected back with your account data automatically loaded

## Important Notes

### Instagram Basic Display API Limitations

The Instagram Basic Display API has some limitations:

1. **No Follower/Following Count**: The API doesn't provide follower or following counts
2. **Personal Accounts Only**: Works with personal Instagram accounts
3. **Test Users Required**: In development mode, only test users can login

### Upgrading to Instagram Graph API (Recommended)

For production use and to get follower counts, you should upgrade to the Instagram Graph API:

1. Convert your Instagram account to a Business or Creator account
2. Link it to a Facebook Page
3. Use Facebook's Graph API instead of Basic Display API
4. This provides access to:
   - Follower/following counts
   - Insights and analytics
   - Publishing capabilities
   - Comments and mentions

### Instagram Business Account Setup

1. Go to Instagram Settings → Account
2. Switch to Professional Account
3. Choose Business or Creator
4. Connect to your Facebook Page
5. Update your app to use Graph API endpoints

## Troubleshooting

### "Invalid OAuth Redirect URI"
- Make sure the redirect URI in your app matches exactly what's in .env
- Check that you added all variants (http/https, 127.0.0.1/localhost)

### "User not authorized as test user"
- Go to your Instagram app settings
- Accept the tester invite from Instagram
- Wait a few minutes for it to propagate

### "Failed to exchange code for token"
- Verify your App ID and App Secret are correct
- Check that your app is not in development mode restrictions
- Make sure your Instagram account is a test user

### "Cannot fetch follower count"
- This is expected with Basic Display API
- Upgrade to Instagram Graph API (Business account required)
- Or ask users to manually enter follower counts

## Alternative: Manual Entry

If you don't want to set up OAuth, users can still:
1. Skip the Instagram login
2. Manually enter their account stats
3. Click "🚀 Analyze My Account"
4. Get AI-powered growth recommendations

## Security Best Practices

1. **Never commit credentials**: Keep your .env file out of version control
2. **Use HTTPS in production**: OAuth redirect URIs should use HTTPS
3. **Implement state parameter**: Already implemented for CSRF protection
4. **Store tokens securely**: Use database encryption in production
5. **Implement token refresh**: Long-lived tokens expire after 60 days

## Next Steps

Once Instagram OAuth is working:

1. Test the login flow with your Instagram account
2. Verify account data is fetched correctly
3. Test the AI analysis with real account data
4. Consider upgrading to Instagram Graph API for full features
5. Implement data deletion endpoint for GDPR compliance

## Support

If you encounter issues:
1. Check the Flask server logs for detailed error messages
2. Verify all redirect URIs are correctly configured
3. Ensure your Instagram account is added as a test user
4. Check Facebook Developer Console for any app restrictions
