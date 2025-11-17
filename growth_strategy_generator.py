"""
Instagram Growth Strategy Generator
Creates personalized content strategies for organic Instagram growth
"""

from typing import Dict, List
from datetime import datetime, timedelta
import random


class InstagramGrowthStrategy:
    """
    Generates legitimate growth strategies based on industry best practices.
    Focus: Quality content, engagement, and authentic community building.
    """
    
    def __init__(self):
        self.content_pillars = {
            'web_design': {
                'topics': [
                    'Website design tips',
                    'UI/UX best practices',
                    'Before/after website transformations',
                    'Common design mistakes',
                    'Color psychology in web design',
                    'Mobile-first design',
                    'Website speed optimization',
                    'Conversion rate optimization'
                ],
                'hashtags': [
                    '#webdesign', '#uidesign', '#uxdesign', '#websitedesign',
                    '#webdevelopment', '#digitaldesign', '#webdesigner',
                    '#responsivedesign', '#userexperience', '#webdev'
                ]
            },
            'digital_marketing': {
                'topics': [
                    'Social media marketing tips',
                    'SEO strategies that work',
                    'Content marketing ideas',
                    'Email marketing best practices',
                    'Marketing analytics explained',
                    'Digital marketing trends',
                    'ROI optimization',
                    'Marketing automation'
                ],
                'hashtags': [
                    '#digitalmarketing', '#marketing', '#socialmediamarketing',
                    '#contentmarketing', '#marketingstrategy', '#seo',
                    '#digitalmarketingagency', '#marketingtips', '#onlinemarketing'
                ]
            },
            'business_tips': {
                'topics': [
                    'Small business growth tips',
                    'Entrepreneurship lessons',
                    'Client acquisition strategies',
                    'Pricing your services',
                    'Building your brand',
                    'Time management for entrepreneurs',
                    'Scaling your business',
                    'Customer retention strategies'
                ],
                'hashtags': [
                    '#smallbusiness', '#entrepreneur', '#businesstips',
                    '#businessgrowth', '#startuplife', '#entrepreneurship',
                    '#businessowner', '#businessstrategy', '#growyourbusiness'
                ]
            },
            'behind_the_scenes': {
                'topics': [
                    'Day in the life of an agency',
                    'Team collaboration moments',
                    'Client project walkthrough',
                    'Our workspace tour',
                    'Tools we use daily',
                    'Agency culture',
                    'Problem-solving process',
                    'Celebrating wins'
                ],
                'hashtags': [
                    '#behindthescenes', '#agencylife', '#teamwork',
                    '#companyculture', '#worklife', '#digitalagency',
                    '#agencyowner', '#creativeteam', '#workspacegoals'
                ]
            }
        }
        
        self.post_formats = {
            'carousel': 'Swipe-through educational posts (highest engagement)',
            'reel': 'Short-form video (highest reach)',
            'single_image': 'Quote or tip graphics',
            'story': 'Behind-the-scenes, polls, questions',
            'guide': 'Step-by-step tutorials'
        }
        
        self.optimal_posting_times = {
            'monday': ['9:00 AM', '1:00 PM', '7:00 PM'],
            'tuesday': ['9:00 AM', '12:00 PM', '6:00 PM'],
            'wednesday': ['9:00 AM', '1:00 PM', '7:00 PM'],
            'thursday': ['9:00 AM', '12:00 PM', '6:00 PM'],
            'friday': ['9:00 AM', '2:00 PM', '5:00 PM'],
            'saturday': ['11:00 AM', '2:00 PM', '7:00 PM'],
            'sunday': ['10:00 AM', '1:00 PM', '6:00 PM']
        }
    
    def generate_30_day_strategy(self, niche: str = 'web_design', 
                                 current_followers: int = 1000) -> Dict:
        """
        Generate a complete 30-day content strategy.
        
        Args:
            niche: Primary business focus
            current_followers: Current follower count
        
        Returns:
            Complete strategy with daily posts, hashtags, and tactics
        """
        strategy = {
            'overview': self._generate_overview(niche, current_followers),
            'content_calendar': self._generate_content_calendar(niche),
            'hashtag_strategy': self._generate_hashtag_strategy(niche),
            'engagement_tactics': self._generate_engagement_tactics(),
            'growth_predictions': self._predict_growth(current_followers),
            'success_metrics': self._define_success_metrics()
        }
        
        return strategy
    
    def _generate_overview(self, niche: str, current_followers: int) -> Dict:
        """Generate strategy overview"""
        return {
            'niche': niche,
            'current_followers': current_followers,
            'target_followers_30_days': current_followers + self._estimate_monthly_growth(current_followers),
            'posting_frequency': '1-2 posts/day + 3-5 stories/day',
            'focus_areas': [
                'Educational content (60%)',
                'Behind-the-scenes (20%)',
                'Client results/testimonials (10%)',
                'Engagement posts (10%)'
            ],
            'primary_goal': 'Build authentic community through value-driven content'
        }
    
    def _estimate_monthly_growth(self, current: int) -> int:
        """Estimate realistic monthly growth"""
        if current < 1000:
            return int(current * 0.3)  # 30% growth for small accounts
        elif current < 5000:
            return int(current * 0.2)  # 20% growth
        elif current < 10000:
            return int(current * 0.15)  # 15% growth
        else:
            return int(current * 0.1)  # 10% growth
    
    def _generate_content_calendar(self, niche: str) -> List[Dict]:
        """Generate 30 days of content ideas"""
        calendar = []
        topics = self.content_pillars.get(niche, self.content_pillars['web_design'])['topics']
        
        for day in range(1, 31):
            day_of_week = (datetime.now() + timedelta(days=day)).strftime('%A').lower()
            
            # Determine post type (Reels on high-engagement days)
            if day_of_week in ['wednesday', 'friday', 'sunday']:
                post_type = 'reel'
            elif day % 3 == 0:
                post_type = 'carousel'
            else:
                post_type = 'single_image'
            
            calendar.append({
                'day': day,
                'date': (datetime.now() + timedelta(days=day)).strftime('%Y-%m-%d'),
                'day_of_week': day_of_week.capitalize(),
                'post_type': post_type,
                'topic': topics[day % len(topics)],
                'posting_time': random.choice(self.optimal_posting_times[day_of_week]),
                'caption_hook': self._generate_caption_hook(topics[day % len(topics)]),
                'cta': self._generate_cta(day)
            })
        
        return calendar
    
    def _generate_caption_hook(self, topic: str) -> str:
        """Generate attention-grabbing caption hooks"""
        hooks = [
            f"🚨 Stop scrolling! {topic} tip you need to see",
            f"💡 {topic}: Here's what nobody tells you",
            f"🎯 Want better results with {topic}? Read this",
            f"⚡ Quick {topic} hack that actually works",
            f"🔥 The {topic} mistake costing you clients",
            f"✨ {topic}: The strategy we use for every client",
            f"📈 How {topic} can 10x your business",
            f"💰 {topic} = More revenue. Here's how"
        ]
        return random.choice(hooks)
    
    def _generate_cta(self, day: int) -> str:
        """Generate call-to-action for posts"""
        ctas = [
            "👉 Save this for later!",
            "💬 Drop a 🔥 if you found this helpful",
            "🤝 Tag someone who needs to see this",
            "📲 Follow for more daily tips",
            "💡 What topic should we cover next? Comment below!",
            "🎯 Need help with this? DM us 'READY'",
            "✅ Double tap if you agree",
            "📥 Check our bio for free resources"
        ]
        return ctas[day % len(ctas)]
    
    def _generate_hashtag_strategy(self, niche: str) -> Dict:
        """Generate hashtag strategy"""
        hashtags = self.content_pillars.get(niche, self.content_pillars['web_design'])['hashtags']
        
        return {
            'primary_hashtags': hashtags[:5],
            'secondary_hashtags': hashtags[5:],
            'usage_guide': {
                'per_post': '7-10 hashtags (optimal for reach)',
                'placement': 'In first comment (keeps caption clean)',
                'mix': '3 large (100k+), 4 medium (10k-100k), 3 small (<10k)'
            },
            'banned_hashtags_to_avoid': [
                '#follow4follow', '#like4like', '#followme',
                '#tagsforlikes', '#followback'
            ]
        }
    
    def _generate_engagement_tactics(self) -> List[Dict]:
        """Generate daily engagement tactics"""
        return [
            {
                'tactic': 'Morning Engagement Routine (15 mins)',
                'steps': [
                    'Comment on 5 posts from target audience accounts',
                    'Respond to all comments on your recent posts',
                    'Reply to 3 relevant Stories',
                    'Engage with accounts that recently followed you'
                ],
                'impact': 'Increases visibility and builds community'
            },
            {
                'tactic': 'Story Engagement (Daily)',
                'steps': [
                    'Post 3-5 Stories per day',
                    'Use polls and question stickers',
                    'Share behind-the-scenes content',
                    'Respond to all Story replies within 1 hour'
                ],
                'impact': 'Keeps you top-of-mind, boosts engagement'
            },
            {
                'tactic': 'DM Outreach (Quality over quantity)',
                'steps': [
                    'Send 5-10 genuine messages to potential connections',
                    'Comment before DM (warm approach)',
                    'Provide value, don\'t pitch immediately',
                    'Build relationships first'
                ],
                'impact': 'Converts followers to clients'
            },
            {
                'tactic': 'Collaboration Posts',
                'steps': [
                    'Partner with 1-2 accounts per week',
                    'Use Instagram\'s Collab feature',
                    'Create value for both audiences',
                    'Cross-promote in Stories'
                ],
                'impact': 'Exposes you to new audiences'
            }
        ]
    
    def _predict_growth(self, current_followers: int) -> Dict:
        """Predict growth based on consistent strategy"""
        weekly_growth = self._estimate_monthly_growth(current_followers) / 4
        
        return {
            'week_1': {
                'new_followers': int(weekly_growth * 0.8),
                'focus': 'Building consistency and testing content'
            },
            'week_2': {
                'new_followers': int(weekly_growth * 0.9),
                'focus': 'Analyzing what works, doubling down'
            },
            'week_3': {
                'new_followers': int(weekly_growth * 1.1),
                'focus': 'Momentum building, increased engagement'
            },
            'week_4': {
                'new_followers': int(weekly_growth * 1.2),
                'focus': 'Optimization and scaling what works'
            },
            'total_projected': int(weekly_growth * 4),
            'engagement_rate_goal': '2-4% (healthy for small accounts)'
        }
    
    def _define_success_metrics(self) -> Dict:
        """Define KPIs to track"""
        return {
            'daily_metrics': [
                'Follower count',
                'Engagement rate (likes + comments / followers)',
                'Story views',
                'Profile visits'
            ],
            'weekly_metrics': [
                'New followers',
                'Most engaging content type',
                'Best performing hashtags',
                'DM conversations started'
            ],
            'monthly_metrics': [
                'Overall follower growth %',
                'Average engagement rate',
                'Content that drove most followers',
                'Leads/clients acquired'
            ],
            'success_indicators': {
                'good': 'Steady growth + 2%+ engagement',
                'excellent': 'Accelerating growth + 3%+ engagement + client inquiries'
            }
        }
    
    def generate_reel_script(self, topic: str) -> Dict:
        """Generate script for Instagram Reel"""
        return {
            'topic': topic,
            'duration': '15-30 seconds',
            'hook': f"[0-3s] Text on screen: 'This {topic} mistake is costing you money'",
            'content': [
                f"[3-8s] Quick problem statement about {topic}",
                "[8-15s] Your solution/tip (3 quick points)",
                "[15-20s] Show example or before/after",
                "[20-25s] Call to action"
            ],
            'text_overlay': 'Use large, easy-to-read text (80% of Reels watched without sound)',
            'music': 'Trending audio (check Reels tab for what\'s popular)',
            'hashtags': '3-5 relevant hashtags in caption',
            'posting_tip': 'Post between 9AM-11AM or 7PM-9PM for maximum reach'
        }


def generate_webnexagency_strategy():
    """Generate custom strategy for @webnexagency"""
    generator = InstagramGrowthStrategy()
    
    strategy = generator.generate_30_day_strategy(
        niche='web_design',
        current_followers=1000
    )
    
    print("=" * 60)
    print("📈 30-DAY GROWTH STRATEGY FOR @WEBNEXAGENCY")
    print("=" * 60)
    print(f"\n🎯 OVERVIEW")
    print(f"Current Followers: {strategy['overview']['current_followers']}")
    print(f"Target (30 days): {strategy['overview']['target_followers_30_days']}")
    print(f"Posting Frequency: {strategy['overview']['posting_frequency']}")
    
    print(f"\n📅 WEEK 1 CONTENT PREVIEW:")
    for post in strategy['content_calendar'][:7]:
        print(f"\nDay {post['day']} ({post['day_of_week']})")
        print(f"  Type: {post['post_type']}")
        print(f"  Topic: {post['topic']}")
        print(f"  Time: {post['posting_time']}")
        print(f"  Hook: {post['caption_hook']}")
    
    print(f"\n💬 ENGAGEMENT TACTICS:")
    for tactic in strategy['engagement_tactics'][:2]:
        print(f"\n✅ {tactic['tactic']}")
        for step in tactic['steps']:
            print(f"   - {step}")
    
    print(f"\n📊 GROWTH PREDICTIONS:")
    print(f"Week 1: +{strategy['growth_predictions']['week_1']['new_followers']} followers")
    print(f"Week 2: +{strategy['growth_predictions']['week_2']['new_followers']} followers")
    print(f"Week 3: +{strategy['growth_predictions']['week_3']['new_followers']} followers")
    print(f"Week 4: +{strategy['growth_predictions']['week_4']['new_followers']} followers")
    print(f"Total: +{strategy['growth_predictions']['total_projected']} followers (1,{1000 + strategy['growth_predictions']['total_projected']} total)")
    
    return strategy


if __name__ == '__main__':
    generate_webnexagency_strategy()
