# Instagram API Setup Guide

## Prerequisites
Before you can connect to the real Instagram API, you need to complete these steps:

## Step 1: Create a Meta (Facebook) Developer Account
1. Go to https://developers.facebook.com/
2. Click "Get Started" or "My Apps"
3. Log in with your Facebook account
4. Complete the developer registration process

## Step 2: Create a New App
1. In Meta Developer Dashboard, click "Create App"
2. Select "Business" as the app type
3. Fill in your app details:
   - App Name: "WebNex Social Manager" (or your preferred name)
   - App Contact Email: your email
   - Business Account: Select your business (or create one)

## Step 3: Add Instagram Graph API
1. In your app dashboard, scroll to "Add Products"
2. Find "Instagram" and click "Set Up"
3. This adds Instagram Graph API to your app

## Step 4: Configure Instagram Business Account
**Important**: You need an Instagram Business or Creator account (not personal)

1. Convert your Instagram account to Business:
   - Open Instagram app
   - Go to Settings → Account
   - Switch to Professional Account
   - Choose "Business"

2. Connect to Facebook Page:
   - Your Instagram Business account must be connected to a Facebook Page
   - Go to Instagram Settings → Account → Linked Accounts → Facebook
   - Link to your Facebook Page

## Step 5: Get Access Tokens
1. In Meta Developer Dashboard, go to Tools → Graph API Explorer
2. Select your app
3. Add permissions:
   - `instagram_basic`
   - `instagram_manage_insights`
   - `pages_read_engagement`
   - `pages_show_list`
4. Click "Generate Access Token"
5. Copy the token (this is temporary)

## Step 6: Get Long-Lived Access Token
Use this endpoint to convert short-lived token to long-lived (60 days):
```
https://graph.facebook.com/v18.0/oauth/access_token?
  grant_type=fb_exchange_token&
  client_id={app-id}&
  client_secret={app-secret}&
  fb_exchange_token={short-lived-token}
```

## Step 7: Get Instagram Business Account ID
```
https://graph.facebook.com/v18.0/me/accounts?access_token={access-token}
```
This returns your Facebook Pages. Find the page connected to your Instagram account.

Then get Instagram Business Account ID:
```
https://graph.facebook.com/v18.0/{page-id}?fields=instagram_business_account&access_token={access-token}
```

## Step 8: Configure Environment Variables
Create a `.env` file with:
```
INSTAGRAM_APP_ID=your_app_id
INSTAGRAM_APP_SECRET=your_app_secret
INSTAGRAM_ACCESS_TOKEN=your_long_lived_token
INSTAGRAM_BUSINESS_ACCOUNT_ID=your_ig_business_account_id
```

## Step 9: App Review (For Production)
For production use, you need to submit your app for review:
1. Go to App Review in Developer Dashboard
2. Request permissions:
   - `instagram_basic`
   - `instagram_manage_insights`
3. Provide privacy policy URL
4. Explain your use case
5. Submit for review (can take 1-2 weeks)

## Rate Limits
- 200 calls per hour per user
- Use webhooks for real-time updates instead of polling

## Current API Capabilities
With Instagram Graph API, you can:
- ✅ Get follower count
- ✅ Get media insights (likes, comments, engagement)
- ✅ Get account insights (reach, impressions)
- ✅ Publish posts and stories
- ❌ Cannot directly add followers (against Instagram policies)
- ❌ Cannot automate likes/comments (against policies)

## Important Notes
⚠️ **You CANNOT buy or add fake followers via the API**
- Instagram's terms prohibit artificial engagement
- Focus on organic growth strategies
- Use insights to optimize your content

## Next Steps
Once you have your credentials, I'll help you:
1. Integrate the real API into this app
2. Display real follower counts and insights
3. Schedule posts
4. Track engagement analytics
5. Monitor growth trends

---

**Need Help?**
- Meta Developer Docs: https://developers.facebook.com/docs/instagram-api
- Instagram Graph API: https://developers.facebook.com/docs/instagram-api/overview
