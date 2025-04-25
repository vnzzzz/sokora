"""
データシーダー
============

既存のデータベースに追加のテストデータを投入するためのユーティリティモジュール。
ユーザーと勤怠記録を水増しして、アプリケーションのテストや開発を支援します。
"""

import random
from typing import List, Dict, Any, Optional, Set, Tuple, NamedTuple, Union, cast
from datetime import date, timedelta
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.user import User
from app.models.attendance import Attendance
from app.models.location import Location
from app.models.group import Group
from app.models.user_type import UserType


class UserInfo(NamedTuple):
    """ユーザー情報を保持するクラス"""
    user_id: str
    full_name: str


# あらかじめ用意されたユーザー情報セット
# 実際のプロジェクトではより多くのデータを用意するべき
SAMPLE_USERS = [
    UserInfo("tanaka.taro", "田中太郎"),
    UserInfo("yamada.hanako", "山田花子"),
    UserInfo("suzuki.ichiro", "鈴木一郎"),
    UserInfo("sato.yumi", "佐藤由美"),
    UserInfo("takahashi.kenji", "高橋健二"),
    UserInfo("ito.megumi", "伊藤めぐみ"),
    UserInfo("watanabe.koji", "渡辺浩二"),
    UserInfo("nakamura.shiori", "中村詩織"),
    UserInfo("kobayashi.takashi", "小林隆"),
    UserInfo("kato.yoko", "加藤洋子"),
    UserInfo("yoshida.akira", "吉田明"),
    UserInfo("yamamoto.naoki", "山本直樹"),
    UserInfo("sasaki.miki", "佐々木美希"),
    UserInfo("yamaguchi.tomoki", "山口智樹"),
    UserInfo("matsumoto.aya", "松本彩"),
    UserInfo("inoue.ryota", "井上涼太"),
    UserInfo("kimura.kanako", "木村加奈子"),
    UserInfo("hayashi.daiki", "林大樹"),
    UserInfo("shimizu.miho", "清水美穂"),
    UserInfo("yamazaki.hiroshi", "山崎浩"),
    UserInfo("mori.sayaka", "森さやか"),
    UserInfo("ikeda.satoshi", "池田聡"),
    UserInfo("hashimoto.mai", "橋本麻衣"),
    UserInfo("abe.yoshihiro", "阿部義弘"),
    UserInfo("ishikawa.mika", "石川美香"),
    UserInfo("yamashita.kenta", "山下健太"),
    UserInfo("nakajima.reiko", "中島玲子"),
    UserInfo("maeda.tatsuya", "前田達也"),
    UserInfo("fujita.nana", "藤田菜々"),
    UserInfo("goto.shigeru", "後藤茂"),
    UserInfo("ogawa.yukiko", "小川由紀子"),
    UserInfo("okada.shohei", "岡田翔平"),
    UserInfo("hasegawa.rumi", "長谷川るみ"),
    UserInfo("murakami.kosuke", "村上康介"),
    UserInfo("kondo.mayu", "近藤真由"),
    UserInfo("ishii.tomoya", "石井智也"),
    UserInfo("sakamoto.ai", "坂本愛"),
    UserInfo("endo.takumi", "遠藤匠"),
    UserInfo("aoki.yuji", "青木裕二"),
    UserInfo("fujii.nanami", "藤井七海"),
    UserInfo("saito.kenta", "斉藤健太"),
    UserInfo("miura.ayumi", "三浦あゆみ"),
    UserInfo("fukuda.takeshi", "福田武"),
    UserInfo("ono.sachiko", "小野幸子"),
    UserInfo("murata.daisuke", "村田大輔"),
    UserInfo("hirano.kazuya", "平野和也"),
    UserInfo("takagi.rika", "高木里佳"),
    UserInfo("kaneko.masashi", "金子雅"),
    UserInfo("ishida.yuka", "石田由佳"),
    UserInfo("sugiyama.keisuke", "杉山圭介"),
    UserInfo("nomura.shinji", "野村真司"),
    UserInfo("kojima.hitomi", "小島ひとみ"),
    UserInfo("tamura.kazuo", "田村和夫"),
    UserInfo("matsuoka.yuki", "松岡由紀"),
    UserInfo("nosaka.akio", "野坂明生"),
    UserInfo("kawano.momoko", "河野桃子"),
    UserInfo("harada.junichi", "原田淳一"),
    UserInfo("akiyama.masako", "秋山正子"),
    UserInfo("hara.toshio", "原敏夫"),
    UserInfo("okamoto.misaki", "岡本美咲"),
    UserInfo("kubota.ryuichi", "久保田隆一"),
    UserInfo("ueda.naomi", "上田直美"),
    UserInfo("nishimura.shota", "西村翔太"),
    UserInfo("fujiwara.yui", "藤原結衣"),
    UserInfo("morita.keita", "森田啓太"),
    UserInfo("yasuda.sakura", "安田さくら"),
    UserInfo("tanabe.hiroyuki", "田辺浩之"),
    UserInfo("otsuka.haruka", "大塚春花"),
    UserInfo("koyama.shingo", "小山真吾"),
    UserInfo("tsuchiya.kaori", "土屋かおり"),
    UserInfo("sakai.minoru", "酒井実"),
    UserInfo("uehara.risa", "上原里沙"),
    UserInfo("miyazaki.takuya", "宮崎卓也"),
    UserInfo("kikuchi.yusuke", "菊池裕介"),
    UserInfo("miyata.asuka", "宮田明日香"),
    UserInfo("arai.toru", "新井徹"),
    UserInfo("ihara.mizuki", "井原瑞希"),
    UserInfo("kubo.naoto", "久保直人"),
    UserInfo("takeuchi.erika", "竹内絵里香"),
    UserInfo("nishida.yuichiro", "西田雄一郎"),
    UserInfo("matsubara.nanako", "松原奈々子"),
    UserInfo("ishizuka.haruto", "石塚陽翔"),
    UserInfo("mizuno.chiaki", "水野千秋"),
    UserInfo("koizumi.shuji", "小泉修二"),
    UserInfo("taguchi.akane", "田口あかね"),
    UserInfo("uchida.koichi", "内田浩一"),
    UserInfo("oishi.marina", "大石麻里奈"),
    UserInfo("yokoyama.takashi", "横山隆"),
    UserInfo("kuroda.aiko", "黒田愛子"),
    UserInfo("sano.kentaro", "佐野健太郎"),
    UserInfo("hamada.yumiko", "浜田由美子"),
    UserInfo("nakano.koji", "中野浩二"),
    UserInfo("kawasaki.ayaka", "川崎彩香"),
    UserInfo("sekiguchi.ryosuke", "関口亮介"),
    UserInfo("takeda.tomomi", "武田智美"),
    UserInfo("ohta.shin", "太田慎"),
    UserInfo("iida.miyuki", "飯田美幸"),
    UserInfo("narita.kotaro", "成田康太郎"),
    UserInfo("adachi.rie", "安達理恵"),
    UserInfo("sugiura.masao", "杉浦正雄")
]


def seed_users(db: Session, count: int = 10) -> List[User]:
    """
    サンプルユーザーをデータベースに追加します

    Args:
        db: データベースセッション
        count: 追加するユーザー数（最大100）

    Returns:
        追加されたユーザーのリスト
    """
    # 既存のユーザーIDを取得して重複を避ける
    existing_user_ids: Set[str] = set(str(user.user_id) for user in db.query(User).all())
    
    # グループとユーザータイプを取得
    groups = db.query(Group).all()
    user_types = db.query(UserType).all()
    
    # 実際に追加する数を決定（利用可能なサンプルと要求カウントの小さい方）
    actual_count = min(count, len(SAMPLE_USERS))
    
    created_users = []
    
    # ランダムにサンプルユーザーを選択（重複なし）
    selected_samples = random.sample(SAMPLE_USERS, actual_count)
    
    for user_info in selected_samples:
        user_id = user_info.user_id
        
        # 重複を避けるための対策
        counter = 1
        temp_user_id = user_id
        while temp_user_id in existing_user_ids:
            temp_user_id = f"{user_id}{counter}"
            counter += 1
        user_id = temp_user_id
        
        # 新しいユーザーを作成
        user = User(
            user_id=user_id,
            username=user_info.full_name,
            group_id=random.choice(groups).group_id,
            user_type_id=random.choice(user_types).user_type_id
        )
        
        db.add(user)
        created_users.append(user)
        existing_user_ids.add(user_id)
    
    db.commit()
    return created_users


# 勤務場所の好みパターンを作成する関数
def create_location_preferences(
    location_ids: List[int],
    primary_location_id: int, 
    primary_weight: float = 0.7
) -> Dict[int, float]:
    """特定の勤務場所を優先した確率分布を作成"""
    prefs = {loc_id: random.uniform(0.1, 0.3) for loc_id in location_ids}
    prefs[primary_location_id] = primary_weight
    return prefs


def seed_attendance(db: Session, users: Optional[List[User]] = None, 
                   days_back: int = 30, days_forward: int = 30) -> List[Attendance]:
    """
    指定されたユーザーに対して勤怠記録を生成します

    Args:
        db: データベースセッション
        users: 勤怠記録を追加するユーザー（Noneの場合は全ユーザー）
        days_back: 過去何日分のデータを生成するか
        days_forward: 未来何日分のデータを生成するか

    Returns:
        追加された勤怠記録のリスト
    """
    if users is None:
        users = db.query(User).all()
    
    # 勤務場所を取得
    locations = db.query(Location).all()
    location_ids = [int(loc.location_id) for loc in locations]
    
    # 既存の勤怠記録を取得して重複を避ける
    existing_records: Dict[Tuple[str, date], Attendance] = {}
    for record in db.query(Attendance).all():
        # SQLAlchemyのColumnオブジェクトから実際の値を取得
        user_id = str(record.user_id)
        record_date = date.fromisoformat(str(record.date))  # SQLAlchemyのColumn型をdate型に変換
        key = (user_id, record_date)
        existing_records[key] = record
    
    # 日付範囲を設定
    today = date.today()
    start_date = today - timedelta(days=days_back)
    end_date = today + timedelta(days=days_forward)
    
    created_records = []
    
    for user in users:
        # このユーザーの特性を決定
        is_office_worker = random.random() > 0.3  # 70%はオフィス勤務派
        preferred_office = 1 if random.random() > 0.5 else 2  # 東京か横浜か
        
        # 曜日ごとの出勤パターン
        weekday_patterns = {}
        
        # 平日のパターン
        for weekday in range(5):  # 月曜〜金曜
            if is_office_worker:
                # オフィス勤務派
                location_prefs = create_location_preferences(location_ids, preferred_office)
            else:
                # テレワーク派
                location_prefs = create_location_preferences(location_ids, 5)  # テレワークのID=5
            
            weekday_patterns[weekday] = {
                "probability": 0.95,  # 95%の確率で出勤
                "preferences": location_prefs
            }
        
        # 土日のパターン
        for weekday in range(5, 7):  # 土曜、日曜
            # 休日出勤の場合はテレワーク確率が高い
            location_prefs = create_location_preferences(location_ids, 5, 0.8)
            
            weekday_patterns[weekday] = {
                "probability": 0.2,  # 20%の確率で出勤
                "preferences": location_prefs
            }
        
        # 日付範囲でループ
        current_date = start_date
        while current_date <= end_date:
            # すでに記録が存在するかチェック
            key = (str(user.user_id), current_date)
            if key in existing_records:
                current_date += timedelta(days=1)
                continue
            
            # 曜日を取得
            weekday = current_date.weekday()
            pattern = weekday_patterns[weekday]
            
            # 出勤確率と比較
            probability_value = pattern.get("probability", 0.0)
            if isinstance(probability_value, (int, float)) and random.random() < probability_value:
                # 出勤する場合、勤務場所を確率分布に従って選択
                loc_preferences = cast(Dict[int, float], pattern.get("preferences", {}))
                
                location_id = random.choices(
                    population=list(loc_preferences.keys()),
                    weights=list(loc_preferences.values()),
                    k=1
                )[0]
                
                # 勤怠記録を追加
                attendance = Attendance(
                    user_id=user.user_id,
                    date=current_date,
                    location_id=location_id
                )
                
                db.add(attendance)
                created_records.append(attendance)
            
            current_date += timedelta(days=1)
    
    db.commit()
    return created_records


def run_seeder(user_count: int = 20, days_back: int = 60, days_forward: int = 30) -> Dict[str, int]:
    """
    シードデータを生成して実行します

    Args:
        user_count: 追加するユーザー数
        days_back: 過去何日分のデータを生成するか
        days_forward: 未来何日分のデータを生成するか

    Returns:
        各エンティティの追加数を含む辞書
    """
    db = SessionLocal()
    try:
        # ユーザーを追加
        users = seed_users(db, count=user_count)
        
        # 勤怠記録を追加
        attendances = seed_attendance(db, users=users, days_back=days_back, days_forward=days_forward)
        
        return {
            "users": len(users),
            "attendances": len(attendances)
        }
    finally:
        db.close()


if __name__ == "__main__":
    # このスクリプトが直接実行された場合、シーダーを実行
    import argparse
    
    parser = argparse.ArgumentParser(description="データベースにテストデータを追加します")
    parser.add_argument("--users", type=int, default=20, help="追加するユーザー数")
    parser.add_argument("--days-back", type=int, default=60, help="過去何日分のデータを生成するか")
    parser.add_argument("--days-forward", type=int, default=30, help="未来何日分のデータを生成するか")
    
    args = parser.parse_args()
    
    print(f"データシーダーを実行中...")
    result = run_seeder(user_count=args.users, days_back=args.days_back, days_forward=args.days_forward)
    print(f"完了しました！")
    print(f"追加されたデータ:")
    print(f"- ユーザー: {result['users']}")
    print(f"- 勤怠記録: {result['attendances']}") 