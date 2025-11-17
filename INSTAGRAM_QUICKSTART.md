# Instagram Real API - Quick Start Guide

## What You Need to Know

🔴 **IMPORTANT**: You **CANNOT** add followers via Instagram's API. This is against Instagram's Terms of Service and not supported by their Graph API.

## What the Real API CAN Do

✅ **Get Real Follower Counts** - See your actual current follower count
✅ **Track Analytics** - Get insights on reach, impressions, engagement
✅ **View Posts** - See your recent posts with like/comment counts
✅ **Publish Content** - Post photos and stories programmatically
✅ **Monitor Growth** - Track your follower count over time

❌ **What It CANNOT Do** - Add fake followers, automate likes, spam

## Quick Setup Steps

### 1. Check if You Have Required Account Types
- ✅ Instagram Business or Creator Account (not personal)
- ✅ Facebook Page connected to your Instagram account
- ✅ Meta Developer Account

### 2. Get Your Credentials (5-10 minutes)

**Step 2a:** Go to https://developers.facebook.com/
- Create an account if you don't have one
- Create a new app (select "Business" type)

**Step 2b:** Add Instagram Product
- In your app dashboard, click "Add Product"
- Select "Instagram" and set it up

**Step 2c:** Get Access Token
1. Go to Tools → Graph API Explorer
2. Select your app from dropdown
3. Add permissions: `instagram_basic`, `instagram_manage_insights`, `pages_read_engagement`
4. Click "Generate Access Token"
5. Copy the token

**Step 2d:** Get Your Instagram Business Account ID
Run this in your browser (replace YOUR_TOKEN):
```
https://graph.facebook.com/v18.0/me/accounts?access_token=YOUR_TOKEN
```
Find your page ID, then get IG account:
```
https://graph.facebook.com/v18.0/PAGE_ID?fields=instagram_business_account&access_token=YOUR_TOKEN
```

### 3. Configure Your App

Edit your `.env` file (copy from `.env.example` if needed):

```bash
INSTAGRAM_APP_ID="your_app_id"
INSTAGRAM_APP_SECRET="your_app_secret"
INSTAGRAM_ACCESS_TOKEN="your_access_token"
INSTAGRAM_BUSINESS_ACCOUNT_ID="your_ig_account_id"
```

### 4. Test the Connection

Restart your Flask app and visit:
```
http://127.0.0.1:5001/social/instagram/account_info?real_api=true
```

You should see your real account data!

### 5. Use in Your App

The app now supports both modes:
- **Demo Mode** (default): Simulated data for testing
- **Real API Mode**: Add `?real_api=true` parameter to endpoints

## API Endpoints

### Get Real Account Info
```
GET /social/instagram/account_info?real_api=true
```

### Get Real Analytics/Insights
```
GET /social/instagram/insights?period=day
```

### Get Recent Posts
```
GET /social/instagram/media?limit=10
```

### Get Follower Growth
```
GET /social/instagram/real_follower_growth?days=30
```

## Token Management

⚠️ **Access tokens expire after 60 days!**

To refresh your token:
1. Use the token exchange endpoint to convert short-lived to long-lived
2. Set up a cron job to refresh automatically before expiration
3. Use webhooks for real-time updates instead of polling

## Rate Limits

- 200 API calls per hour per user
- Use caching to minimize API calls
- Webhooks are better than polling for real-time updates

## For Production Use

To go beyond testing (200 calls/hour), you need:
1. Submit your app for App Review
2. Request permissions: `instagram_basic`, `instagram_manage_insights`
3. Provide privacy policy URL
4. Wait 1-2 weeks for approval

## Growing Your Real Instagram

Since you can't buy followers via API, focus on:

### Organic Growth Strategies:
1. **Post Consistently** - 1-2 posts per day
2. **Use Hashtags** - 5-10 relevant hashtags per post
3. **Engage with Others** - Like and comment on target audience posts
4. **Post at Peak Times** - Use insights to find when your audience is active
5. **Use Stories** - Post 3-5 stories daily
6. **Reels** - Create short-form video content (highest reach)
7. **Collaborate** - Partner with other accounts in your niche

### Use This App To:
- ✅ Schedule posts for optimal times
- ✅ Track what content performs best
- ✅ Monitor follower growth trends
- ✅ Analyze engagement rates
- ✅ Get insights on audience demographics

## Need Help?

- **Setup Issues**: Check `INSTAGRAM_API_SETUP.md`
- **API Errors**: Check the Flask console for detailed error messages
- **Meta Docs**: https://developers.facebook.com/docs/instagram-api
- **Graph API Explorer**: https://developers.facebook.com/tools/explorer/

---

**Remember**: Real Instagram growth takes time and quality content. There are no shortcuts! 🚀
