# src/tutor_app/core/srs_logic.py
import datetime
from src.tutor_app.db.models import UserQuestionStats

def update_srs_stats(stats: UserQuestionStats, quality: int) -> UserQuestionStats:
    """
    根据SM-2算法更新一个题目的记忆统计数据。
    quality: 用户对题目掌握程度的评分，范围0-5。
             >= 3 表示回答正确。
    """
    if quality >= 3: # 回答正确
        if stats.repetitions == 0:
            stats.interval = 1
        elif stats.repetitions == 1:
            stats.interval = 6
        else:
            stats.interval = round(stats.interval * stats.ease_factor)

        stats.repetitions += 1
    else: # 回答错误
        stats.repetitions = 0
        stats.interval = 1

    # 更新简易度因子 E-Factor
    stats.ease_factor += (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    if stats.ease_factor < 1.3:
        stats.ease_factor = 1.3 # E-Factor最低为1.3

    # 计算下一次复习日期
    stats.next_review_date = datetime.date.today() + datetime.timedelta(days=stats.interval)

    return stats