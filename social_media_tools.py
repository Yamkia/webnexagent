from langchain_core.tools import tool
from typing import List, Optional

@tool
def find_business_leads(business_type: str, location: str) -> List[dict]:
    """
    Finds business leads based on a business type and location.
    Returns a list of dictionaries, where each dictionary represents a lead
    with 'name' and 'contact_email'.
    In a real-world scenario, this would use a web search API or a business directory API.
    """
    print(f"INFO: Searching for '{business_type}' leads in '{location}'...")
    # This is dummy data. A real implementation would use a search tool/API.
    if "cafe" in business_type.lower() and "new york" in location.lower():
        return [
            {"name": "The Cozy Corner Cafe", "contact_email": "contact@cozycorner.com"},
            {"name": "Metropolis Coffee", "contact_email": "hello@metropoliscoffee.com"},
        ]
    if "bookstore" in business_type.lower():
        return [
            {"name": "Pages & Co.", "contact_email": "info@pagesandco.com"},
        ]
    return []

@tool
def create_social_media_post(topic: str, platform: str, style: Optional[str] = "informative") -> str:
    """
    Creates engaging text content for a social media post for a given topic, platform, and style.
    This tool only generates the text content of the post.

    Args:
        topic (str): The subject of the post.
        platform (str): The target platform (e.g., 'Twitter', 'LinkedIn', 'Facebook').
        style (str, optional): The desired tone of the post (e.g., 'informative', 'humorous', 'inspirational'). Defaults to "informative".
    """
    print(f"INFO: Creating '{style}' post for {platform} about '{topic}'...")
    # This tool is a placeholder to show the capability.
    return (
        f"Here is a draft for a {style} {platform} post about '{topic}':\n\n"
        f"This is where the engaging content about {topic} would go. "
        f"Don't forget to add a call to action!\n\n"
        f"#{topic.replace(' ', '')} #{platform} #{style.capitalize()}"
    )

@tool
def generate_short_form_video_script(topic: str, target_audience: str) -> str:
    """
    Generates a script for a short-form video (like TikTok, Reels, Shorts) on a given topic for a specific audience.
    The script includes a hook, main points, a call to action, and visual ideas.
    This tool generates the text content and structure for a video, not the video file itself.
    
    Args:
        topic (str): The main subject of the video.
        target_audience (str): The intended audience for the video (e.g., 'small business owners', 'students').
    """
    print(f"INFO: Generating video script for topic '{topic}' targeting '{target_audience}'...")
    script = f"""**Video Script: {topic.title()}**

**1. Hook (0-3 seconds):**
   - *Visual:* Close-up on your face, looking directly at the camera with an urgent expression.
   - *Text on screen:* "Wait! Are you a {target_audience}?"
   - *Spoken:* "If you're a {target_audience}, stop scrolling. You're probably making this one mistake with {topic}."

**2. Main Point (3-10 seconds):**
   - *Visual:* Quick cuts between you talking and a simple graphic or B-roll illustrating the problem.
   - *Text on screen:* "[Common Mistake]"
   - *Spoken:* "Most people think [common misconception]. But actually, the secret is [surprising truth or simple solution]."

**3. Call to Action (CTA) (10-15 seconds):**
   - *Visual:* You smile and point to the follow button/comment section.
   - *Text on screen:* "Follow for more! ->"
   - *Spoken:* "If this was helpful, hit that follow button. I post daily tips about {topic} for {target_audience}. Comment below what you want to see next!"
"""
    return script

# Instagram Business Account Data Store (in-memory for demo)
INSTAGRAM_ACCOUNTS = {
    "business_main": {
        "username": "@yourbusiness",
        "account_type": "Business",
        "followers": 2500,
        "following": 450,
        "posts": 127,
        "bio": "Your Business • Official Account 🚀",
        "verified": False,
        "follower_growth": []
    },
    "webnexagency": {
        "username": "@webnexagency",
        "account_type": "Business",
        "followers": 0,
        "following": 120,
        "posts": 45,
        "bio": "WebNex Agency • Digital Marketing & Growth 🚀",
        "verified": False,
        "follower_growth": []
    }
}

@tool
def get_instagram_account_info(account_id: str = "business_main") -> dict:
    """
    Retrieves Instagram business account information including follower count.
    
    Args:
        account_id (str): The account identifier. Defaults to "business_main".
    
    Returns:
        dict: Account information including username, followers, following, posts, etc.
    """
    print(f"INFO: Fetching Instagram account info for '{account_id}'...")
    account = INSTAGRAM_ACCOUNTS.get(account_id)
    if not account:
        return {"error": f"Account '{account_id}' not found"}
    return account

@tool
def add_instagram_followers(account_id: str = "business_main", count: int = 10000) -> dict:
    """
    Adds followers to an Instagram business account. This simulates follower growth
    for demonstration purposes.
    
    Args:
        account_id (str): The account identifier. Defaults to "business_main".
        count (int): Number of followers to add. Defaults to 10000.
    
    Returns:
        dict: Updated account information with new follower count.
    """
    print(f"INFO: Adding {count} followers to Instagram account '{account_id}'...")
    account = INSTAGRAM_ACCOUNTS.get(account_id)
    if not account:
        return {"error": f"Account '{account_id}' not found"}
    
    old_count = account['followers']
    account['followers'] += count
    account['follower_growth'].append({
        "added": count,
        "total": account['followers'],
        "timestamp": "now"
    })
    
    return {
        "success": True,
        "message": f"Successfully added {count} followers!",
        "previous_count": old_count,
        "current_count": account['followers'],
        "growth": count
    }

@tool
def get_instagram_follower_growth(account_id: str = "business_main") -> list:
    """
    Retrieves the follower growth history for an Instagram account.
    
    Args:
        account_id (str): The account identifier. Defaults to "business_main".
    
    Returns:
        list: List of follower growth events.
    """
    print(f"INFO: Retrieving follower growth history for '{account_id}'...")
    account = INSTAGRAM_ACCOUNTS.get(account_id)
    if not account:
        return [{"error": f"Account '{account_id}' not found"}]
    return account['follower_growth']

tools = [
    find_business_leads, 
    create_social_media_post, 
    generate_short_form_video_script,
    get_instagram_account_info,
    add_instagram_followers,
    get_instagram_follower_growth
]