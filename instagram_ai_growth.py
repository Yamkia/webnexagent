"""
Instagram AI Growth Assistant
Connects to your Instagram account and uses AI to analyze and grow it organically.
"""

import os
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json


class InstagramAIGrowthAssistant:
    """
    AI-powered Instagram growth assistant that analyzes your account
    and provides actionable recommendations.
    """
    
    def __init__(self, username: str = None):
        self.username = username
        self.account_data = {}
        self.analytics = {}
        self.recommendations = []
        
    def analyze_account(self, account_data: Dict) -> Dict:
        """
        Analyze Instagram account and provide AI-powered insights.
        
        Args:
            account_data: Dict containing account metrics
        
        Returns:
            Complete analysis with recommendations
        """
        self.account_data = account_data
        
        analysis = {
            'account_health': self._assess_account_health(),
            'content_performance': self._analyze_content_performance(),
            'audience_insights': self._analyze_audience(),
            'growth_opportunities': self._identify_growth_opportunities(),
            'ai_recommendations': self._generate_ai_recommendations(),
            'action_plan': self._create_action_plan(),
            'competitor_insights': self._analyze_competitors()
        }
        
        return analysis
    
    def _assess_account_health(self) -> Dict:
        """Assess overall account health"""
        followers = self.account_data.get('followers', 0)
        following = self.account_data.get('following', 0)
        posts = self.account_data.get('posts', 0)
        avg_engagement = self.account_data.get('avg_engagement_rate', 0)
        
        # Calculate health score
        health_score = 0
        issues = []
        strengths = []
        
        # Follower/Following ratio
        if followers > 0 and following > 0:
            ratio = followers / following
            if ratio > 1.5:
                health_score += 25
                strengths.append("Good follower/following ratio")
            elif ratio < 0.5:
                health_score += 10
                issues.append("Following too many accounts relative to followers")
            else:
                health_score += 20
        
        # Content consistency
        if posts > 50:
            health_score += 25
            strengths.append("Consistent posting history")
        elif posts > 20:
            health_score += 15
        else:
            issues.append("Need more content - aim for 50+ posts")
        
        # Engagement rate
        if avg_engagement > 3:
            health_score += 30
            strengths.append("Excellent engagement rate")
        elif avg_engagement > 1.5:
            health_score += 20
            strengths.append("Good engagement rate")
        elif avg_engagement > 0.5:
            health_score += 10
        else:
            issues.append("Low engagement - need to improve content quality")
        
        # Activity level
        last_post_days = self.account_data.get('days_since_last_post', 0)
        if last_post_days <= 1:
            health_score += 20
            strengths.append("Active account - posting regularly")
        elif last_post_days <= 3:
            health_score += 15
        elif last_post_days > 7:
            issues.append(f"Inactive for {last_post_days} days - post more frequently")
        
        return {
            'score': min(health_score, 100),
            'status': self._get_health_status(health_score),
            'strengths': strengths,
            'issues': issues
        }
    
    def _get_health_status(self, score: int) -> str:
        """Get health status based on score"""
        if score >= 80:
            return "Excellent"
        elif score >= 60:
            return "Good"
        elif score >= 40:
            return "Needs Improvement"
        else:
            return "Critical"
    
    def _analyze_content_performance(self) -> Dict:
        """Analyze which content performs best"""
        recent_posts = self.account_data.get('recent_posts', [])
        
        if not recent_posts:
            return {'message': 'No recent posts to analyze'}
        
        # Analyze post types
        best_format = self._find_best_format(recent_posts)
        best_times = self._find_best_posting_times(recent_posts)
        best_topics = self._find_best_topics(recent_posts)
        
        return {
            'best_format': best_format,
            'best_posting_times': best_times,
            'best_topics': best_topics,
            'avg_likes': sum(p.get('likes', 0) for p in recent_posts) / len(recent_posts),
            'avg_comments': sum(p.get('comments', 0) for p in recent_posts) / len(recent_posts),
            'top_performing_post': max(recent_posts, key=lambda x: x.get('engagement', 0)) if recent_posts else None
        }
    
    def _find_best_format(self, posts: List[Dict]) -> Dict:
        """Find which post format performs best"""
        formats = {}
        for post in posts:
            format_type = post.get('type', 'image')
            if format_type not in formats:
                formats[format_type] = {'count': 0, 'total_engagement': 0}
            formats[format_type]['count'] += 1
            formats[format_type]['total_engagement'] += post.get('engagement', 0)
        
        # Calculate average engagement per format
        for format_type in formats:
            formats[format_type]['avg_engagement'] = (
                formats[format_type]['total_engagement'] / formats[format_type]['count']
            )
        
        best = max(formats.items(), key=lambda x: x[1]['avg_engagement']) if formats else ('unknown', {})
        
        return {
            'type': best[0],
            'avg_engagement': best[1].get('avg_engagement', 0),
            'recommendation': f"Focus on {best[0]}s - they get the best engagement"
        }
    
    def _find_best_posting_times(self, posts: List[Dict]) -> List[str]:
        """Find optimal posting times"""
        # Simplified - would use actual post timestamps in real implementation
        return ['9:00 AM', '1:00 PM', '7:00 PM']
    
    def _find_best_topics(self, posts: List[Dict]) -> List[str]:
        """Find which topics resonate most"""
        # Simplified - would use NLP on captions in real implementation
        return ['Educational content', 'Behind-the-scenes', 'Tips & tricks']
    
    def _analyze_audience(self) -> Dict:
        """Analyze audience demographics and behavior"""
        followers = self.account_data.get('followers', 0)
        avg_engagement = self.account_data.get('avg_engagement_rate', 0)
        
        # Calculate audience quality
        if avg_engagement > 3:
            quality = "High Quality - Very engaged audience"
        elif avg_engagement > 1.5:
            quality = "Good Quality - Engaged audience"
        elif avg_engagement > 0.5:
            quality = "Average Quality - Some engagement"
        else:
            quality = "Low Quality - Need to improve engagement"
        
        return {
            'size': followers,
            'quality': quality,
            'engagement_rate': avg_engagement,
            'growth_rate': self.account_data.get('monthly_growth_rate', 0),
            'insights': [
                f"Your audience is {quality.lower()}",
                f"Engagement rate: {avg_engagement}%",
                "Focus on content that sparks conversations"
            ]
        }
    
    def _identify_growth_opportunities(self) -> List[Dict]:
        """Identify specific growth opportunities"""
        opportunities = []
        
        followers = self.account_data.get('followers', 0)
        posts = self.account_data.get('posts', 0)
        engagement = self.account_data.get('avg_engagement_rate', 0)
        
        # Opportunity 1: Reels
        if self.account_data.get('reels_count', 0) < 10:
            opportunities.append({
                'opportunity': 'Create More Reels',
                'impact': 'High',
                'effort': 'Medium',
                'description': 'Reels get 10x more reach than regular posts',
                'action': 'Post 3-5 Reels per week',
                'expected_result': '+15-30% follower growth'
            })
        
        # Opportunity 2: Posting frequency
        if self.account_data.get('posts_per_week', 0) < 5:
            opportunities.append({
                'opportunity': 'Increase Posting Frequency',
                'impact': 'High',
                'effort': 'Medium',
                'description': 'Consistency is key for algorithm visibility',
                'action': 'Post 1-2 times daily',
                'expected_result': '+20% reach improvement'
            })
        
        # Opportunity 3: Engagement rate
        if engagement < 2:
            opportunities.append({
                'opportunity': 'Boost Engagement',
                'impact': 'High',
                'effort': 'Low',
                'description': 'Higher engagement = Better algorithm ranking',
                'action': 'Add questions in captions, use polls in Stories',
                'expected_result': '+50-100% engagement rate'
            })
        
        # Opportunity 4: Hashtag optimization
        opportunities.append({
            'opportunity': 'Optimize Hashtag Strategy',
            'impact': 'Medium',
            'effort': 'Low',
            'description': 'Right hashtags = Better discoverability',
            'action': 'Mix of small (1k-10k), medium (10k-100k), and large (100k+) hashtags',
            'expected_result': '+25% discoverability'
        })
        
        # Opportunity 5: Collaborations
        if followers < 10000:
            opportunities.append({
                'opportunity': 'Collaborate with Similar Accounts',
                'impact': 'High',
                'effort': 'Medium',
                'description': 'Tap into other audiences',
                'action': 'Partner with 2-3 accounts per month (similar size)',
                'expected_result': '+100-500 followers per collaboration'
            })
        
        return opportunities
    
    def _generate_ai_recommendations(self) -> List[str]:
        """Generate AI-powered recommendations"""
        recommendations = []
        
        health = self._assess_account_health()
        
        # Based on health score
        if health['score'] < 40:
            recommendations.append("🚨 URGENT: Your account needs immediate attention. Start with posting consistency.")
        elif health['score'] < 60:
            recommendations.append("⚠️ Your account has potential but needs optimization. Focus on engagement.")
        else:
            recommendations.append("✅ Your account is healthy! Now focus on scaling what works.")
        
        # Content recommendations
        followers = self.account_data.get('followers', 0)
        if followers < 1000:
            recommendations.append("🎯 Focus on Reels to reach beyond your current audience")
        elif followers < 5000:
            recommendations.append("📈 Start collaborating with accounts your size (1k-5k)")
        elif followers < 10000:
            recommendations.append("🚀 Consider running Instagram ads to accelerate growth")
        
        # Engagement recommendations
        engagement = self.account_data.get('avg_engagement_rate', 0)
        if engagement < 1:
            recommendations.append("💬 Engagement is low. Ask questions, create polls, encourage comments")
        elif engagement < 2:
            recommendations.append("👍 Good engagement! Double down on content that gets most comments")
        else:
            recommendations.append("🔥 Excellent engagement! Your audience loves your content")
        
        return recommendations
    
    def _create_action_plan(self) -> Dict:
        """Create a weekly action plan"""
        return {
            'week_1': {
                'focus': 'Content Foundation',
                'goals': [
                    'Post 7 pieces of content (5 posts, 2 Reels)',
                    'Engage with 35 accounts daily (5 minutes)',
                    'Respond to all comments within 1 hour',
                    'Post 3-5 Stories daily'
                ],
                'expected_outcome': '+20-40 new followers'
            },
            'week_2': {
                'focus': 'Engagement Optimization',
                'goals': [
                    'Analyze which content performed best',
                    'Create more of what works',
                    'Start DM conversations with 10 potential connections',
                    'Test different posting times'
                ],
                'expected_outcome': '+30-50 new followers'
            },
            'week_3': {
                'focus': 'Collaboration & Reach',
                'goals': [
                    'Reach out to 5 accounts for collaboration',
                    'Post collaborative content',
                    'Optimize hashtag strategy',
                    'Increase Reel frequency (3-4 per week)'
                ],
                'expected_outcome': '+50-80 new followers'
            },
            'week_4': {
                'focus': 'Scaling & Automation',
                'goals': [
                    'Double down on what works',
                    'Batch create content for efficiency',
                    'Set up content calendar for next month',
                    'Review analytics and adjust strategy'
                ],
                'expected_outcome': '+60-100 new followers'
            }
        }
    
    def _analyze_competitors(self) -> Dict:
        """Analyze competitor strategies (placeholder)"""
        return {
            'recommendation': 'Find 5-10 accounts in your niche with 5k-50k followers',
            'what_to_analyze': [
                'What content formats they use most',
                'Their posting frequency',
                'How they engage with audience',
                'What hashtags they use',
                'Their bio and CTA'
            ],
            'action': 'Don\'t copy - learn and adapt their successful strategies to your style'
        }


def generate_growth_report(account_data: Dict) -> Dict:
    """Generate a complete growth report"""
    assistant = InstagramAIGrowthAssistant(account_data.get('username'))
    return assistant.analyze_account(account_data)
