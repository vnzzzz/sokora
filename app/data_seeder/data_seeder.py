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
    """データ生成に使用するユーザーの基本情報を格納する名前付きタプル。"""
    user_id: str
    full_name: str


# データ生成用のサンプルユーザーリスト
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
    サンプルユーザーデータをデータベースに追加します。

    既存のユーザーIDとの重複を避け、指定された数のユーザーを生成します。
    グループIDと社員種別IDはランダムに割り当てられます。

    Args:
        db: データベースセッション
        count: 追加するユーザー数 (最大100まで。サンプル数を超える場合はサンプル数に制限されます)

    Returns:
        List[User]: データベースに追加されたUserオブジェクトのリスト。
    """
    # 既存ユーザーIDをセットとして保持し、重複チェックを効率化します。
    existing_user_ids: Set[str] = set(str(user.user_id) for user in db.query(User).all())

    # データベースから利用可能なグループとユーザータイプを取得します。
    groups = db.query(Group).all()
    user_types = db.query(UserType).all()

    # 生成するユーザー数を決定します (指定数とサンプル数の小さい方)。
    actual_count = min(count, len(SAMPLE_USERS))

    created_users = []

    # 重複しないようにサンプルユーザーをランダムに選択します。
    selected_samples = random.sample(SAMPLE_USERS, actual_count)

    for user_info in selected_samples:
        user_id = user_info.user_id

        # ユーザーIDが既に存在する場合、末尾に連番を追加して重複を回避します。
        counter = 1
        temp_user_id = user_id
        while temp_user_id in existing_user_ids:
            temp_user_id = f"{user_id}{counter}"
            counter += 1
        user_id = temp_user_id

        # 新しいユーザーオブジェクトを作成します。
        user = User(
            user_id=user_id,
            username=user_info.full_name,
            group_id=random.choice(groups).group_id,
            user_type_id=random.choice(user_types).user_type_id
        )

        db.add(user)
        created_users.append(user)
        existing_user_ids.add(user_id) # 新規追加したIDもセットに追加

    db.commit()
    return created_users


# 勤務場所の選択確率を生成するヘルパー関数
def create_location_preferences(
    location_ids: List[int],
    primary_location_id: int,
    primary_weight: float = 0.7
) -> Dict[int, float]:
    """指定された勤務場所IDリストに基づき、特定の場所を優先する確率分布を生成します。

    Args:
        location_ids: 利用可能な勤務場所IDのリスト。
        primary_location_id: 優先的に選択される勤務場所のID。
        primary_weight: 優先勤務場所が選択される確率の重み (デフォルト0.7)。

    Returns:
        Dict[int, float]: 各勤務場所IDをキーとし、選択確率の重みを値とする辞書。
    """
    prefs = {loc_id: random.uniform(0.1, 0.3) for loc_id in location_ids}
    prefs[primary_location_id] = primary_weight
    return prefs


def seed_attendance(db: Session, users: Optional[List[User]] = None,
                   days_back: int = 30, days_forward: int = 30) -> List[Attendance]:
    """
    指定されたユーザーリストまたは全ユーザーに対して、ダミーの勤怠記録を生成します。

    ユーザーごとにランダムな出勤パターン（オフィス派/テレワーク派、優先オフィス）と
    曜日ごとの勤務場所選択確率を決定し、指定された期間の勤怠データを生成します。
    既存のレコードがある場合はスキップします。

    Args:
        db: データベースセッション
        users: 勤怠記録を追加するユーザーオブジェクトのリスト (Noneの場合は全ユーザーが対象)。
        days_back: 過去何日分のデータを生成するか (デフォルト30日)。
        days_forward: 未来何日分のデータを生成するか (デフォルト30日)。

    Returns:
        List[Attendance]: データベースに追加されたAttendanceオブジェクトのリスト。
    """
    if users is None:
        users = db.query(User).all()

    # 利用可能な勤務場所IDを取得します。
    locations = db.query(Location).all()
    location_ids = [int(loc.location_id) for loc in locations]
    if not location_ids:
        print("Error: No locations found in the database. Cannot seed attendance.")
        return []

    # 既存の勤怠記録を (user_id, date) をキーとする辞書に格納し、重複チェックを効率化します。
    existing_records: Dict[Tuple[str, date], Attendance] = {}
    for record in db.query(Attendance).all():
        user_id = str(record.user_id)
        record_date = date.fromisoformat(str(record.date))
        key = (user_id, record_date)
        existing_records[key] = record

    # データ生成対象の日付範囲を決定します。
    today = date.today()
    start_date = today - timedelta(days=days_back)
    end_date = today + timedelta(days=days_forward)

    created_records = []

    for user in users:
        # ユーザーごとの勤務傾向（オフィス派/テレワーク派、好みのオフィス）をランダムに設定します。
        is_office_worker = random.random() > 0.3
        # テレワーク(ID=3) 以外の場所を優先的に選択します。
        possible_offices = [loc_id for loc_id in location_ids if loc_id != 3]
        preferred_office = random.choice(possible_offices) if possible_offices else location_ids[0]

        # 曜日ごとの勤務場所選択確率を格納する辞書を初期化します。
        weekday_patterns: Dict[int, Dict[int, float]] = {}

        # 平日 (月曜=0 〜 金曜=4) の勤務パターンを設定します。
        for weekday in range(5):
            if is_office_worker:
                # オフィス勤務を好むユーザーの確率分布を設定します。
                location_prefs = create_location_preferences(location_ids, preferred_office)
            else:
                # テレワークを好むユーザーの確率分布を設定します (location_id=3 がテレワーク)。
                location_prefs = create_location_preferences(location_ids, 3)

            weekday_patterns[weekday] = {
                loc_id: weight for loc_id, weight in location_prefs.items()
            }

        # 休日 (土曜=5, 日曜=6) の勤務パターンを設定します (出勤は稀)。
        for weekday in range(5, 7):
            # 休日出勤の場合はテレワーク確率が高い
            location_prefs = create_location_preferences(location_ids, 3, 0.8)

            weekday_patterns[weekday] = {
                loc_id: weight for loc_id, weight in location_prefs.items()
            }

        # 指定された日付範囲で勤怠記録を生成します。
        for day_offset in range((end_date - start_date).days + 1):
            day = start_date + timedelta(days=day_offset)

            # 既存レコードがある場合はスキップします。
            if (str(user.user_id), day) in existing_records:
                continue

            # 勤務する確率 (平日は高く、休日は低い)
            attendance_probability = 0.9 if day.weekday() < 5 else 0.05

            if random.random() < attendance_probability:
                # その曜日の勤務場所パターンを取得します。
                current_pattern = weekday_patterns.get(day.weekday(), {}) # weekdayは整数なのでstr()は不要
                if not current_pattern: # パターンがない場合はスキップ（念のため）
                    continue

                # パターンに基づいて勤務場所を選択します。
                location_ids_in_pattern = list(current_pattern.keys())
                weights = list(current_pattern.values())
                chosen_location_id = random.choices(location_ids_in_pattern, weights=weights, k=1)[0]

                # 新しい勤怠記録オブジェクトを作成します。
                attendance = Attendance(
                    user_id=str(user.user_id),
                    date=day,
                    location_id=chosen_location_id
                )
                db.add(attendance)
                created_records.append(attendance)

    # まとめてコミットします。
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