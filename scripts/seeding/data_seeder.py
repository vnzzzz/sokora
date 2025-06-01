"""
勤怠データシーダー
================

既存のユーザーと勤怠種別を利用して、勤怠記録のみを追加するためのユーティリティモジュール。
データベースに登録済みのユーザーと勤怠種別を取得し、指定された期間の勤怠記録を自動生成します。

実行方法:
プロジェクトルートディレクトリから以下のコマンドで実行してください。
`poetry run python -m scripts.seeding.data_seeder --days-back <日数> --days-forward <日数>`
"""

import random
from typing import List, Dict, Optional, Tuple
from datetime import date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.user import User
from app.models.attendance import Attendance
from app.models.location import Location
from app.core.config import logger


def create_location_preferences(
    locations: List[Location],
    primary_location: Optional[Location] = None,
    primary_weight: float = 0.7
) -> Dict[int, float]:
    """指定された勤怠種別リストに基づき、特定の場所を優先する確率分布を生成します。

    Args:
        locations: 勤怠種別のLocationオブジェクトのリスト。
        primary_location: 優先的に選択される勤怠種別のLocationオブジェクト。
        primary_weight: 優先勤怠種別が選択される確率の重み (デフォルト0.7)。

    Returns:
        Dict[int, float]: 各勤怠種別IDをキーとし、選択確率の重みを値とする辞書。
    """
    if not locations:
        logger.warning("勤怠種別リストが空です。")
        return {}

    # すべての勤怠種別に基本的な重みを設定
    prefs = {int(loc.id): random.uniform(0.1, 0.3) for loc in locations}
    
    # 優先勤怠種別が指定されている場合は重みを上げる
    if primary_location and primary_location.id in [loc.id for loc in locations]:
        prefs[int(primary_location.id)] = primary_weight
    
    return prefs


def seed_attendance(db: Session, days_back: int = 30, days_forward: int = 30) -> List[Attendance]:
    """
    データベース内の既存ユーザーと勤怠種別を利用して、ダミーの勤怠記録を生成します。

    Args:
        db: データベースセッション
        days_back: 過去何日分のデータを生成するか (デフォルト30日)。
        days_forward: 未来何日分のデータを生成するか (デフォルト30日)。

    Returns:
        List[Attendance]: データベースに追加されたAttendanceオブジェクトのリスト。
    """
    # 既存のユーザーを取得
    users = list(db.scalars(select(User)).all())
    if not users:
        logger.error("データベースにユーザーが存在しません。勤怠記録を生成できません。")
        return []
    
    logger.info(f"{len(users)} 人のユーザーが見つかりました。")

    # 既存の勤怠種別を取得
    locations = list(db.scalars(select(Location)).all())
    if not locations:
        logger.error("データベースに勤怠種別が存在しません。勤怠記録を生成できません。")
        return []
    
    logger.info(f"{len(locations)} 個の勤怠種別が見つかりました: {[loc.name for loc in locations]}")

    # 既存レコードを効率的にチェックするための準備
    existing_records: Dict[Tuple[str, date], Attendance] = {}
    for record in db.scalars(select(Attendance)).all():
        user_id = str(record.user_id)
        record_date = date.fromisoformat(str(record.date))
        key = (user_id, record_date)
        existing_records[key] = record

    today = date.today()
    start_date = today - timedelta(days=days_back)
    end_date = today + timedelta(days=days_forward)
    created_records = []

    # 勤怠種別を名前で分類
    office_locations = [loc for loc in locations if loc.name not in ["テレワーク", "夜勤"]]
    telework_location = next((loc for loc in locations if loc.name == "テレワーク"), None)

    for user in users:
        logger.info(f"ユーザー {user.username} ({user.id}) の勤怠記録を生成中...")
        
        # ユーザーごとの勤務傾向（オフィス派/テレワーク派、好みのオフィス）をランダムに設定
        is_office_worker = random.random() > 0.3

        # 優先勤怠種別を設定
        if is_office_worker and office_locations:
            preferred_location = random.choice(office_locations)
        elif telework_location:
            preferred_location = telework_location
        else:
            # どちらも該当しない場合は最初の勤怠種別を使用
            preferred_location = locations[0]

        # 曜日ごとの勤怠種別選択確率を格納する辞書を初期化
        weekday_patterns: Dict[int, Dict[int, float]] = {}

        # 平日 (月曜=0 〜 金曜=4) の勤務パターンを設定
        for weekday in range(5):
            if is_office_worker:
                location_prefs = create_location_preferences(locations, preferred_location)
            else:
                # テレワークを好むユーザー
                location_prefs = create_location_preferences(locations, telework_location)
            weekday_patterns[weekday] = location_prefs

        # 休日 (土曜=5, 日曜=6) の勤務パターンを設定 (出勤は稀)
        for weekday in range(5, 7):
            location_prefs = create_location_preferences(locations, preferred_location, 0.8)
            weekday_patterns[weekday] = location_prefs

        # 指定された日付範囲で勤怠記録を生成
        for day_offset in range((end_date - start_date).days + 1):
            day = start_date + timedelta(days=day_offset)

            # 既存レコードがある場合はスキップ
            if (str(user.id), day) in existing_records:
                continue

            # 勤務する確率 (平日は高く、休日は低い)
            attendance_probability = 0.9 if day.weekday() < 5 else 0.05

            if random.random() < attendance_probability:
                # その曜日の勤怠種別パターンを取得
                current_pattern = weekday_patterns.get(day.weekday(), {})
                if not current_pattern:
                    continue

                # パターンに基づいて勤怠種別を選択
                location_ids_in_pattern = list(current_pattern.keys())
                weights = list(current_pattern.values())
                
                if location_ids_in_pattern:
                    chosen_location_id = random.choices(location_ids_in_pattern, weights=weights, k=1)[0]

                    # 新しい勤怠記録オブジェクトを作成
                    attendance = Attendance(
                        user_id=str(user.id),
                        date=day,
                        location_id=chosen_location_id
                    )
                    db.add(attendance)
                    created_records.append(attendance)

    # まとめてコミット
    db.commit()
    logger.info(f"{len(created_records)} 件の勤怠記録をシードしました。")
    return created_records


def run_seeder(days_back: int = 60, days_forward: int = 30) -> Dict[str, int]:
    """
    既存のユーザーと勤怠種別を利用して勤怠記録を生成します。

    Args:
        days_back: 過去何日分のデータを生成するか
        days_forward: 未来何日分のデータを生成するか

    Returns:
        生成された勤怠記録数を含む辞書
    """
    db = SessionLocal()
    try:
        # 既存データの確認
        user_count = len(list(db.scalars(select(User)).all()))
        location_count = len(list(db.scalars(select(Location)).all()))
        
        logger.info(f"データベース内の既存データ:")
        logger.info(f"- ユーザー: {user_count} 人")
        logger.info(f"- 勤怠種別: {location_count} 個")
        
        if user_count == 0:
            logger.error("ユーザーが存在しません。先にユーザーを登録してください。")
            return {"attendances": 0}
        
        if location_count == 0:
            logger.error("勤怠種別が存在しません。先に勤怠種別を登録してください。")
            return {"attendances": 0}

        # 勤怠記録を生成
        logger.info("勤怠データの生成を開始します...")
        attendances = seed_attendance(db, days_back=days_back, days_forward=days_forward)
        logger.info("勤怠データの生成が完了しました。")

        return {"attendances": len(attendances)}
        
    except Exception as e:
        logger.error(f"シーダー実行中にエラーが発生しました: {e}", exc_info=True)
        db.rollback()
        return {"attendances": 0}
    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="既存のユーザーと勤怠種別を利用して勤怠記録を追加します")
    parser.add_argument("--days-back", type=int, default=60, help="過去何日分のデータを生成するか")
    parser.add_argument("--days-forward", type=int, default=30, help="未来何日分のデータを生成するか")

    args = parser.parse_args()

    print(f"勤怠データシーダーを実行中...")
    result = run_seeder(days_back=args.days_back, days_forward=args.days_forward)
    print(f"完了しました！")
    print(f"生成された勤怠記録: {result['attendances']} 件") 