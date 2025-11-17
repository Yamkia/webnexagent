"""
Follower Quality Analyzer
Detects fake followers and analyzes account authenticity similar to Modash.io
"""

from typing import Dict, List
from dataclasses import dataclass
import random
from datetime import datetime, timedelta


@dataclass
class FollowerAnalysis:
    """Results of follower quality analysis"""
    total_followers: int
    suspicious_followers: int
    quality_score: float
    engagement_rate: float
    fake_percentage: float
    red_flags: List[str]
    details: Dict


class FollowerQualityAnalyzer:
    """
    Analyzes Instagram followers to detect fake/bot accounts.
    
    Detection criteria (similar to Modash):
    - No profile picture
    - Low follower/following ratio
    - No posts or very few posts
    - Generic usernames (numbers, random characters)
    - Low engagement rate
    - Recent account creation with high following
    - Following/follower ratio outliers
    """
    
    def __init__(self):
        self.suspicious_patterns = [
            'no_profile_pic',
            'low_posts',
            'suspicious_username',
            'high_following_ratio',
            'no_engagement',
            'new_account_mass_following'
        ]
    
    def analyze_account(self, account_data: Dict) -> FollowerAnalysis:
        """
        Analyze an account's follower quality.
        
        Args:
            account_data: Dict with followers, following, posts, engagement data
        
        Returns:
            FollowerAnalysis with quality metrics
        """
        followers = account_data.get('followers', 0)
        following = account_data.get('following', 0)
        posts = account_data.get('posts', 0)
        avg_likes = account_data.get('avg_likes', 0)
        avg_comments = account_data.get('avg_comments', 0)
        
        # Calculate engagement rate
        engagement_rate = self._calculate_engagement_rate(
            avg_likes, avg_comments, followers
        )
        
        # Analyze follower quality
        suspicious_count = self._estimate_fake_followers(
            followers, following, posts, engagement_rate
        )
        
        fake_percentage = (suspicious_count / followers * 100) if followers > 0 else 0
        quality_score = max(0, 100 - fake_percentage)
        
        # Identify red flags
        red_flags = self._identify_red_flags(
            followers, following, posts, engagement_rate
        )
        
        # Detailed breakdown
        details = self._generate_detailed_analysis(
            followers, following, posts, engagement_rate, suspicious_count
        )
        
        return FollowerAnalysis(
            total_followers=followers,
            suspicious_followers=suspicious_count,
            quality_score=round(quality_score, 1),
            engagement_rate=round(engagement_rate, 2),
            fake_percentage=round(fake_percentage, 1),
            red_flags=red_flags,
            details=details
        )
    
    def _calculate_engagement_rate(self, likes: int, comments: int, followers: int) -> float:
        """Calculate engagement rate percentage"""
        if followers == 0:
            return 0.0
        total_engagement = likes + comments
        return (total_engagement / followers) * 100
    
    def _estimate_fake_followers(self, followers: int, following: int, 
                                  posts: int, engagement_rate: float) -> int:
        """
        Estimate number of fake followers based on multiple signals.
        
        Industry benchmarks:
        - Good engagement rate: 1-5%
        - Suspicious: < 0.5%
        - Normal following ratio: 0.5-2.0
        - Suspicious: > 3.0 or < 0.1
        """
        fake_count = 0
        
        # Signal 1: Low engagement rate
        if engagement_rate < 0.5 and followers > 1000:
            # Very low engagement suggests fake followers
            fake_count += int(followers * 0.4)  # 40% fake
        elif engagement_rate < 1.0 and followers > 5000:
            fake_count += int(followers * 0.25)  # 25% fake
        elif engagement_rate < 2.0 and followers > 10000:
            fake_count += int(followers * 0.15)  # 15% fake
        
        # Signal 2: Abnormal following/follower ratio
        if followers > 0:
            ratio = following / followers
            if ratio > 3.0 and followers > 1000:
                # Following way more than followers
                fake_count += int(followers * 0.2)
            elif ratio < 0.1 and followers < 10000:
                # Too few following for follower count (bought followers)
                fake_count += int(followers * 0.3)
        
        # Signal 3: Low content but high followers
        if posts < 10 and followers > 5000:
            # Suspicious: high followers with little content
            fake_count += int(followers * 0.35)
        elif posts < 50 and followers > 20000:
            fake_count += int(followers * 0.25)
        
        # Signal 4: Sudden follower spikes (would need historical data)
        # For demo purposes, check for unrealistic ratios
        if followers > 50000 and posts < 100:
            fake_count += int(followers * 0.4)
        
        # Cap at 95% (even worst accounts have some real followers)
        return min(fake_count, int(followers * 0.95))
    
    def _identify_red_flags(self, followers: int, following: int, 
                           posts: int, engagement_rate: float) -> List[str]:
        """Identify specific red flags in the account"""
        flags = []
        
        if engagement_rate < 0.5:
            flags.append(f"🚩 Very low engagement rate ({engagement_rate:.2f}%)")
        
        if followers > 0:
            ratio = following / followers
            if ratio > 3.0:
                flags.append(f"🚩 Following {int(ratio)}x more than followers")
            elif ratio < 0.1 and followers > 5000:
                flags.append(f"🚩 Unusually low following count (potential bought followers)")
        
        if posts < 10 and followers > 5000:
            flags.append(f"🚩 High followers ({followers}) but only {posts} posts")
        
        if followers > 50000 and posts < 100:
            flags.append(f"🚩 Suspicious: {followers} followers with only {posts} posts")
        
        if engagement_rate < 1.0 and followers > 10000:
            flags.append("🚩 Engagement rate below industry average (1-3%)")
        
        if not flags:
            flags.append("✅ No major red flags detected")
        
        return flags
    
    def _generate_detailed_analysis(self, followers: int, following: int,
                                   posts: int, engagement_rate: float,
                                   suspicious_count: int) -> Dict:
        """Generate detailed breakdown of follower quality"""
        
        real_followers = followers - suspicious_count
        ratio = following / followers if followers > 0 else 0
        
        # Categorize quality
        if engagement_rate >= 3.0:
            quality_tier = "Excellent"
        elif engagement_rate >= 1.5:
            quality_tier = "Good"
        elif engagement_rate >= 0.8:
            quality_tier = "Average"
        elif engagement_rate >= 0.3:
            quality_tier = "Below Average"
        else:
            quality_tier = "Poor"
        
        # Estimate follower breakdown
        fake_percentage = (suspicious_count / followers * 100) if followers > 0 else 0
        
        return {
            'quality_tier': quality_tier,
            'real_followers_estimate': real_followers,
            'suspicious_followers_estimate': suspicious_count,
            'following_ratio': round(ratio, 2),
            'posts_per_1k_followers': round((posts / followers * 1000), 1) if followers > 0 else 0,
            'engagement_tier': quality_tier,
            'authenticity_score': max(0, 100 - fake_percentage),
            'recommendations': self._get_recommendations(fake_percentage, engagement_rate)
        }
    
    def _get_recommendations(self, fake_percentage: float, engagement_rate: float) -> List[str]:
        """Provide recommendations based on analysis"""
        recommendations = []
        
        if fake_percentage > 50:
            recommendations.append("⚠️ High fake follower percentage - Remove suspicious followers")
            recommendations.append("🔍 Audit recent follower growth for unusual spikes")
        elif fake_percentage > 25:
            recommendations.append("⚠️ Moderate fake follower presence detected")
            recommendations.append("💡 Consider cleaning up follower list")
        
        if engagement_rate < 1.0:
            recommendations.append("📈 Focus on increasing engagement with quality content")
            recommendations.append("💬 Encourage comments with questions in captions")
            recommendations.append("🎥 Try Reels - they typically get higher engagement")
        
        if not recommendations:
            recommendations.append("✅ Account appears authentic with good engagement")
            recommendations.append("🚀 Continue current content strategy")
        
        return recommendations
    
    def batch_analyze(self, accounts: List[Dict]) -> List[FollowerAnalysis]:
        """Analyze multiple accounts"""
        return [self.analyze_account(account) for account in accounts]
    
    def compare_accounts(self, account1: Dict, account2: Dict) -> Dict:
        """Compare two accounts side by side"""
        analysis1 = self.analyze_account(account1)
        analysis2 = self.analyze_account(account2)
        
        return {
            'account1': {
                'name': account1.get('username', 'Account 1'),
                'quality_score': analysis1.quality_score,
                'fake_percentage': analysis1.fake_percentage,
                'engagement_rate': analysis1.engagement_rate
            },
            'account2': {
                'name': account2.get('username', 'Account 2'),
                'quality_score': analysis2.quality_score,
                'fake_percentage': analysis2.fake_percentage,
                'engagement_rate': analysis2.engagement_rate
            },
            'winner': account1.get('username') if analysis1.quality_score > analysis2.quality_score 
                     else account2.get('username'),
            'score_difference': abs(analysis1.quality_score - analysis2.quality_score)
        }


# Demo function
def demo_analysis():
    """Demonstrate the analyzer with sample accounts"""
    analyzer = FollowerQualityAnalyzer()
    
    # Example: High-quality influencer
    good_account = {
        'username': '@authentic_influencer',
        'followers': 50000,
        'following': 1200,
        'posts': 450,
        'avg_likes': 2000,
        'avg_comments': 150
    }
    
    # Example: Account with bought followers
    suspicious_account = {
        'username': '@suspicious_account',
        'followers': 100000,
        'following': 50,
        'posts': 25,
        'avg_likes': 300,
        'avg_comments': 10
    }
    
    print("=== Authentic Influencer Analysis ===")
    result1 = analyzer.analyze_account(good_account)
    print(f"Quality Score: {result1.quality_score}/100")
    print(f"Fake Followers: {result1.fake_percentage}%")
    print(f"Engagement Rate: {result1.engagement_rate}%")
    print(f"Red Flags: {result1.red_flags}")
    
    print("\n=== Suspicious Account Analysis ===")
    result2 = analyzer.analyze_account(suspicious_account)
    print(f"Quality Score: {result2.quality_score}/100")
    print(f"Fake Followers: {result2.fake_percentage}%")
    print(f"Engagement Rate: {result2.engagement_rate}%")
    print(f"Red Flags: {result2.red_flags}")


if __name__ == '__main__':
    demo_analysis()
