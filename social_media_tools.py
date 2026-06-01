import random
import time
from typing import List, Optional, Dict
from langchain_core.tools import tool

PLATFORM_TEMPLATES = {
    'instagram': {
        'cta': 'Comment below or follow for updates!',
        'mention_token': '@',
        'hashtag_prefix': '#',
        'max_caption_chars': 2200,
    },
    'facebook': {
        'cta': 'Share this with your network.',
        'mention_token': '@',
        'hashtag_prefix': '#',
        'max_caption_chars': 63206,
    },
    'twitter': {
        'cta': 'Retweet if you found this helpful.',
        'mention_token': '@',
        'hashtag_prefix': '#',
        'max_caption_chars': 280,
    },
    'linkedin': {
        'cta': 'Share your thoughts in the comments.',
        'mention_token': '@',
        'hashtag_prefix': '#',
        'max_caption_chars': 1300,
    },
}

SOCIAL_ACCOUNT_LIBRARY = [
    {
        'platform': 'instagram',
        'handle': '@creative.cafe',
        'name': 'Creative Cafe',
        'niche': 'coffee shop',
        'location': 'New York',
        'followers': 7800,
        'engagement_rate': 4.5,
        'bio': 'Local coffee shop with daily creative brews.',
    },
    {
        'platform': 'instagram',
        'handle': '@urbanbookshop',
        'name': 'Urban Bookshop',
        'niche': 'bookstore',
        'location': 'London',
        'followers': 9200,
        'engagement_rate': 5.1,
        'bio': 'Community bookstore for readers and creators.',
    },
    {
        'platform': 'twitter',
        'handle': '@startupguide',
        'name': 'Startup Guide',
        'niche': 'entrepreneurship',
        'location': 'Remote',
        'followers': 34000,
        'engagement_rate': 2.8,
        'bio': 'Growth advice for founders and small teams.',
    },
    {
        'platform': 'linkedin',
        'handle': '@digitalgrowthco',
        'name': 'Digital Growth Co.',
        'niche': 'digital marketing',
        'location': 'Cape Town',
        'followers': 16000,
        'engagement_rate': 3.3,
        'bio': 'Marketing strategy for fast-growing brands.',
    },
]


def _normalize_platform(platform: str) -> str:
    return platform.strip().lower()


def _pick_hashtags(topic: str, platform: str, count: int = 8) -> List[str]:
    normalized_topic = topic.lower().replace(' ', '')
    base_tags = [normalized_topic, 'socialmedia', 'growth', 'marketing', 'content']
    extra = [
        'organic',
        'reach',
        'engagement',
        'business',
        'smallbusiness',
        'community',
        'creative',
    ]
    random.shuffle(extra)
    tags = base_tags + extra[:max(0, count - len(base_tags))]
    prefix = PLATFORM_TEMPLATES.get(platform, {}).get('hashtag_prefix', '#')
    return [f"{prefix}{tag}" for tag in tags[:count]]


def _build_outreach_subject(goal: str) -> str:
    lowered = goal.lower()
    if 'collab' in lowered or 'partnership' in lowered:
        return 'Partnership opportunity for your profile'
    if 'feature' in lowered or 'share' in lowered:
        return 'Feature request from a fellow creator'
    return 'Quick question about your content strategy'


def _build_message(platform: str, handle: str, goal: str, tone: str) -> str:
    normalized_platform = _normalize_platform(platform)
    cta = PLATFORM_TEMPLATES.get(normalized_platform, {}).get('cta', 'Let me know what you think!')
    greeting = f"Hi {handle.lstrip('@').replace('.', ' ').title()},"
    if tone == 'friendly':
        opener = 'I love the way you connect with your audience.'
    elif tone == 'professional':
        opener = 'I enjoyed reviewing your recent content and wanted to reach out.'
    else:
        opener = 'I have a quick idea that could help you grow.'
    return (
        f"{greeting}\n\n"
        f"{opener} I am building a campaign to reach more people in {goal}."
        f" I believe your profile would be a great fit for this collaboration.\n\n"
        f"{cta}\n\n"
        f"Thanks,\nYour growth team"
    )

@tool
def find_business_leads(business_type: str, location: str) -> List[Dict[str, str]]:
    """Find likely business leads for a given business type and location."""
    print(f"INFO: Finding business leads for '{business_type}' in '{location}'...")
    leads: List[Dict[str, str]] = []
    normalized_type = business_type.lower()
    normalized_location = location.lower()

    if 'cafe' in normalized_type and 'new york' in normalized_location:
        leads.extend([
            {
                'name': 'The Cozy Corner Cafe',
                'contact_email': 'contact@cozycorner.com',
                'platform': 'instagram',
                'recommended_handle': '@cozycornernyc',
                'notes': 'High potential for local café visual posts and reels.',
            },
            {
                'name': 'Metropolis Coffee',
                'contact_email': 'hello@metropoliscoffee.com',
                'platform': 'instagram',
                'recommended_handle': '@metropoliscoffee',
                'notes': 'Engage with morning routine and local lifestyle audiences.',
            },
        ])
    elif 'bookstore' in normalized_type:
        leads.append(
            {
                'name': 'Pages & Co.',
                'contact_email': 'info@pagesandco.com',
                'platform': 'facebook',
                'recommended_handle': '@pagesandco',
                'notes': 'Great fit for community events and author collaborations.',
            }
        )
    else:
        for account in SOCIAL_ACCOUNT_LIBRARY:
            if normalized_type in account['niche'] or normalized_type in account['name'].lower():
                leads.append({
                    'name': account['name'],
                    'contact_email': f'hello+{account["handle"].lstrip("@")}@example.com',
                    'platform': account['platform'],
                    'recommended_handle': account['handle'],
                    'notes': f"Strong match for {account['niche']} audiences on {account['platform']}.",
                })
    if not leads:
        leads.append(
            {
                'name': f'{business_type.title()} Collective',
                'contact_email': f'contact@{business_type.replace(" ","")}.com',
                'platform': 'linkedin',
                'recommended_handle': f'@{business_type.replace(" ","")}',
                'notes': 'Broad business lead suitable for an outreach campaign.',
            }
        )
    return leads

@tool
def discover_target_accounts(platform: str, niche: str, location: Optional[str] = None) -> List[Dict[str, object]]:
    """Discover target social media accounts for a given platform, niche, and optional location."""
    normalized_platform = _normalize_platform(platform)
    location = (location or '').lower()
    print(f"INFO: Discovering target accounts on {normalized_platform} for niche '{niche}' in '{location}'...")
    matches: List[Dict[str, object]] = []
    for account in SOCIAL_ACCOUNT_LIBRARY:
        if account['platform'] != normalized_platform:
            continue
        if niche.lower() in account['niche'] or niche.lower() in account['bio'].lower():
            if not location or location in account['location'].lower():
                matches.append({
                    'handle': account['handle'],
                    'name': account['name'],
                    'followers': account['followers'],
                    'engagement_rate': account['engagement_rate'],
                    'bio': account['bio'],
                    'reason': f"Strong {niche} relevance and good engagement on {platform.title()}.",
                })
    return matches

@tool
def generate_outreach_message(platform: str, account_handle: str, goal: str, tone: Optional[str] = 'friendly') -> Dict[str, str]:
    """Generate a short outreach message for a target account on a social platform."""
    print(f"INFO: Generating outreach message for {account_handle} on {platform} with goal '{goal}'...")
    return {
        'subject': _build_outreach_subject(goal),
        'message': _build_message(platform, account_handle, goal, tone),
        'recommended_followup': 'Follow up in 3-5 days if there is no response.',
    }

@tool
def suggest_hashtags(platform: str, topic: str, count: int = 10) -> List[str]:
    """Suggest a list of hashtags for a topic on a specific social platform."""
    normalized_platform = _normalize_platform(platform)
    print(f"INFO: Suggesting {count} hashtags for topic '{topic}' on {normalized_platform}...")
    return _pick_hashtags(topic, normalized_platform, count)

@tool
def create_social_media_post(topic: str, platform: str, style: Optional[str] = 'informative') -> Dict[str, object]:
    """Create a suggested social media post caption and metadata for a given topic and platform."""
    normalized_platform = _normalize_platform(platform)
    print(f"INFO: Creating social media post for platform={normalized_platform}, topic='{topic}', style='{style}'...")
    cta = PLATFORM_TEMPLATES.get(normalized_platform, {}).get('cta', 'Engage with this post!')
    caption = (
        f"{topic.capitalize()} can help your audience take action today. "
        f"Use this post to educate, inspire, and invite people to connect. {cta}"
    )
    hashtags = _pick_hashtags(topic, normalized_platform, 8)
    max_chars = PLATFORM_TEMPLATES.get(normalized_platform, {}).get('max_caption_chars', 2200)
    if len(caption) > max_chars:
        caption = caption[:max_chars - 3] + '...'
    return {
        'platform': platform,
        'topic': topic,
        'style': style,
        'caption': caption,
        'hashtags': hashtags,
        'recommended_post_type': 'image' if normalized_platform in ['instagram', 'facebook'] else 'text',
        'cta': cta,
    }

@tool
def generate_short_form_video_script(topic: str, target_audience: str, platform: Optional[str] = 'instagram') -> Dict[str, object]:
    """Generate a short-form video script structure for a topic, audience, and platform."""
    normalized_platform = _normalize_platform(platform)
    print(f"INFO: Generating short-form video script for {normalized_platform} on topic '{topic}'...")
    hook = f"Stop scrolling if you're a {target_audience} who wants better {topic}."
    point1 = f"Why most {target_audience} miss this simple {topic} strategy."
    point2 = f"What to change today to improve reach and engagement."
    point3 = f"How to make this work in your next post or story."
    cta = PLATFORM_TEMPLATES.get(normalized_platform, {}).get('cta', 'Follow for more updates!')
    return {
        'platform': platform,
        'topic': topic,
        'target_audience': target_audience,
        'script': {
            'hook': hook,
            'points': [point1, point2, point3],
            'cta': cta,
            'visual_notes': [
                'Use quick cuts and text overlays.',
                'Show a real example or before/after.',
                'End with a strong prompt to engage.',
            ],
        },
    }

@tool
def estimate_social_media_reach(platform: str, audience_size: int, content_type: str, frequency_per_week: int) -> Dict[str, object]:
    """Estimate potential social media reach for a given audience size, platform, and posting cadence."""
    normalized_platform = _normalize_platform(platform)
    print(f"INFO: Estimating reach for {normalized_platform} with audience {audience_size}...")
    base_rate = 0.02
    if normalized_platform == 'instagram':
        base_rate = 0.035
    elif normalized_platform == 'linkedin':
        base_rate = 0.015
    elif normalized_platform == 'twitter':
        base_rate = 0.025
    estimated_reach = int(audience_size * base_rate * min(1.0, frequency_per_week / 5))
    estimated_engagement = int(estimated_reach * 0.1)
    score = min(100, int((frequency_per_week / 7) * 100))
    return {
        'platform': platform,
        'audience_size': audience_size,
        'content_type': content_type,
        'frequency_per_week': frequency_per_week,
        'estimated_reach': estimated_reach,
        'estimated_engagement': estimated_engagement,
        'recommendation': 'Increase content quality and consistency to maximize reach.',
        'score': score,
    }

@tool
def create_social_media_campaign(platform: str, objective: str, audience: str, duration_days: int = 30) -> Dict[str, object]:
    """Create a social media campaign plan for a platform, objective, and audience."""
    normalized_platform = _normalize_platform(platform)
    print(f"INFO: Creating {duration_days}-day campaign for {normalized_platform} targeting {audience}...")
    cadence = '3 posts per week' if duration_days <= 30 else '2-4 posts per week'
    campaign = {
        'platform': platform,
        'objective': objective,
        'audience': audience,
        'duration_days': duration_days,
        'cadence': cadence,
        'components': [
            'High-quality educational post',
            'Authentic short-form video',
            'Audience interaction and comment reply',
            'Targeted outreach to similar accounts',
        ],
        'weekly_focus': [
            'Week 1: Research audience and publish awareness content.',
            'Week 2: Share social proof and engage with target accounts.',
            'Week 3: Promote a collaboration or user-generated story.',
            'Week 4: Analyze performance and optimize topic clusters.',
        ],
    }
    if normalized_platform == 'instagram':
        campaign['recommended_formats'] = ['Reels', 'Carousels', 'Stories']
    elif normalized_platform == 'linkedin':
        campaign['recommended_formats'] = ['Articles', 'Carousel posts', 'Polls']
    else:
        campaign['recommended_formats'] = ['Text posts', 'Images', 'Video clips']
    return campaign

INSTAGRAM_ACCOUNTS = {
    'business_main': {
        'username': '@yourbusiness',
        'account_type': 'Business',
        'followers': 2500,
        'following': 450,
        'posts': 127,
        'bio': 'Your Business • Official Account 🚀',
        'verified': False,
        'follower_growth': [],
    },
    'webnexagency': {
        'username': '@webnexagency',
        'account_type': 'Business',
        'followers': 0,
        'following': 120,
        'posts': 45,
        'bio': 'WebNex Agency • Digital Marketing & Growth 🚀',
        'verified': False,
        'follower_growth': [],
    },
}

@tool
def get_instagram_account_info(account_id: str = 'business_main') -> dict:
    """Return stored Instagram account information for a demo account."""
    print(f"INFO: Fetching Instagram account info for '{account_id}'...")
    account = INSTAGRAM_ACCOUNTS.get(account_id)
    if not account:
        return {'error': f"Account '{account_id}' not found"}
    return account

@tool
def add_instagram_followers(account_id: str = 'business_main', count: int = 10000) -> dict:
    """Simulate adding Instagram followers to a demo account."""
    print(f"INFO: Simulating follower growth for '{account_id}' with {count} followers...")
    account = INSTAGRAM_ACCOUNTS.get(account_id)
    if not account:
        return {'error': f"Account '{account_id}' not found"}
    if count <= 0:
        return {'error': 'Count must be greater than zero.'}
    old_count = account['followers']
    account['followers'] += count
    account['follower_growth'].append({
        'type': 'simulated_growth',
        'added': count,
        'total': account['followers'],
        'timestamp': int(time.time()),
    })
    return {
        'success': True,
        'message': 'Simulated follower growth for demo purposes only.',
        'previous_count': old_count,
        'current_count': account['followers'],
        'growth': count,
    }

@tool
def get_instagram_follower_growth(account_id: str = 'business_main') -> list:
    """Retrieve simulated follower growth history for a demo Instagram account."""
    print(f"INFO: Retrieving follower growth history for '{account_id}'...")
    account = INSTAGRAM_ACCOUNTS.get(account_id)
    if not account:
        return [{'error': f"Account '{account_id}' not found"}]
    return account['follower_growth']

@tool
def follow_instagram_accounts(account_id: str = 'business_main', target_accounts: Optional[List[str]] = None, count: int = 10) -> dict:
    """Simulate following a set of Instagram accounts from a demo account."""
    print(f"INFO: Simulating follow actions for '{account_id}'...")
    account = INSTAGRAM_ACCOUNTS.get(account_id)
    if not account:
        return {'error': f"Account '{account_id}' not found"}
    target_accounts = target_accounts or [f'@suggested_{i+1}' for i in range(count)]
    action_count = min(count, len(target_accounts))
    if action_count <= 0:
        return {'error': 'Count must be greater than zero.'}
    account['following'] += action_count
    account.setdefault('engagement_actions', []).append({
        'type': 'follow',
        'target_accounts': target_accounts[:action_count],
        'count': action_count,
        'timestamp': int(time.time()),
    })
    return {
        'success': True,
        'message': 'Simulated following target accounts to improve discoverability.',
        'target_accounts': target_accounts[:action_count],
        'new_following': account['following'],
    }

@tool
def like_instagram_posts(account_id: str = 'business_main', posts: Optional[List[str]] = None, total_likes: int = 50) -> dict:
    """Simulate liking Instagram posts on behalf of a demo account."""
    print(f"INFO: Simulating likes for '{account_id}'...")
    account = INSTAGRAM_ACCOUNTS.get(account_id)
    if not account:
        return {'error': f"Account '{account_id}' not found"}
    if total_likes <= 0:
        return {'error': 'total_likes must be greater than zero.'}
    posts = posts or [f'post_{i+1}' for i in range(total_likes)]
    liked_count = min(total_likes, len(posts))
    account.setdefault('engagement_actions', []).append({
        'type': 'like',
        'posts': posts[:liked_count],
        'count': liked_count,
        'timestamp': int(time.time()),
    })
    return {
        'success': True,
        'message': 'Simulated liking posts to increase engagement signals.',
        'post_ids': posts[:liked_count],
        'total_liked': liked_count,
    }

@tool
def publish_instagram_post(account_id: str = 'business_main', post_text: str = '', hashtags: Optional[List[str]] = None) -> dict:
    """Simulate publishing an Instagram post from a demo account."""
    print(f"INFO: Publishing simulated post for '{account_id}'...")
    account = INSTAGRAM_ACCOUNTS.get(account_id)
    if not account:
        return {'error': f"Account '{account_id}' not found"}
    if not post_text.strip():
        return {'error': 'Post text cannot be empty.'}
    tags = hashtags or []
    account.setdefault('published_posts', []).append({
        'text': post_text,
        'hashtags': tags,
        'timestamp': int(time.time()),
        'likes': 0,
        'comments': 0,
    })
    new_likes = min(120, max(5, int(len(post_text) * 0.5)))
    new_comments = min(25, max(2, int(len(tags) * 0.8)))
    account['follower_growth'].append({
        'type': 'published_post',
        'likes': new_likes,
        'comments': new_comments,
        'timestamp': int(time.time()),
    })
    return {
        'success': True,
        'message': 'Post created and content promotion suggested.',
        'initial_engagement': {
            'likes': new_likes,
            'comments': new_comments,
        },
        'post_text': post_text,
        'hashtags': tags,
    }

TOOLS = [
    find_business_leads,
    discover_target_accounts,
    generate_outreach_message,
    suggest_hashtags,
    create_social_media_post,
    generate_short_form_video_script,
    estimate_social_media_reach,
    create_social_media_campaign,
    get_instagram_account_info,
    add_instagram_followers,
    get_instagram_follower_growth,
    follow_instagram_accounts,
    like_instagram_posts,
    publish_instagram_post,
]

tools = TOOLS
