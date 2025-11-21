from db_helper import DBHelper
from collections import defaultdict

class AnimeRecommender:
    def __init__(self, db_helper):
        self.db = db_helper
        self.all_animes = self.db.get_all_animes()  # 缓存所有动画数据

    def recommend_based_on_genres(self, preferred_genres, min_score=0, top_n=5):
        """基于偏好类型和最低评分推荐"""
        # 1. 计算每个动画与偏好类型的匹配度
        anime_scores = []
        for anime in self.all_animes:
            # 跳过无类型数据的动画
            if not anime['genre']:
                continue

            # 评分筛选
            if anime['score'] < min_score:
                continue

            # 确保members是整数（双重保险）
            popularity = int(anime['members']) if str(anime['members']).isdigit() else 0

            # 计算类型匹配分数
            match_count = 0
            for genre in preferred_genres:
                if genre in anime['genre']:
                    match_count += 1

            # 分数计算（确保所有值都是数值类型）
            max_popularity = max([int(a['members']) if str(a['members']).isdigit() else 0 for a in
                                  self.all_animes]) if self.all_animes else 1
            normalized_popularity = popularity / max_popularity if max_popularity != 0 else 0
            score = match_count * 0.7 + normalized_popularity * 0.3
            anime_scores.append((anime, score))

        # 2. 按分数排序，取前N个
        anime_scores.sort(key=lambda x: x[1], reverse=True)
        return [anime for anime, score in anime_scores[:top_n]]

        # 2. 按分数排序，取前N个
        anime_scores.sort(key=lambda x: x[1], reverse=True)
        return [anime for anime, score in anime_scores[:top_n]]
    def explain_recommendation(self, anime, preferred_genres):
        """生成推荐理由"""
        reasons = []
        # 类型匹配理由
        matching_genres = [g for g in anime['genre'] if g in preferred_genres]
        if matching_genres:
            reasons.append(f"包含您喜欢的类型：{', '.join(matching_genres)}")
        # 流行度理由
        if anime['members'] and anime['members'] > 100000:
            reasons.append(f"热门动画（{anime['members']:,}人看过）")
        # 评分理由
        if anime['score'] and anime['score'] >= 8.0:
            reasons.append(f"高评分（{anime['score']}分）")
        return "；".join(reasons) if reasons else "符合您的观看偏好"