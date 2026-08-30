"""
データシーダー
============

既存のデータベースに追加のテストデータを投入するためのユーティリティモジュール。
ユーザーと勤怠記録を水増しして、アプリケーションのテストや開発を支援します。

マスターデータ（グループ、勤怠種別、社員種別）が存在しない場合は、
定義済みのリストに基づいて作成します。

実行方法:
プロジェクトルートディレクトリから以下のコマンドで実行してください。
`poetry run python -m scripts.seeding.data_seeder --users <数> --days-back <日数> --days-forward <日数>`
"""

import random
from typing import List, Dict, Optional, Set, Tuple, NamedTuple, Any
from datetime import date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.user import User
from app.models.attendance import Attendance
from app.models.location import Location
from app.models.group import Group
from app.models.user_type import UserType
from app.core.config import logger


# --- マスターデータ定義 ---
GROUP_NAMES = ["グループ１", "グループ２", "グループ３"]
LOCATION_NAMES = ["東京", "横浜", "大阪", "テレワーク", "夜勤"]
USER_TYPE_NAMES = ["マネージャー", "リーダー", "社員", "派遣"]


class UserInfo(NamedTuple):
    """データ生成に使用するユーザーの基本情報を格納する名前付きタプル。"""
    user_id: str
    full_name: str


# データ生成用のサンプルユーザーリスト
SAMPLE_USERS = [
    UserInfo("tanaka_taro", "田中太郎"),
    UserInfo("yamada_hanako", "山田花子"),
    UserInfo("suzuki_ichiro", "鈴木一郎"),
    UserInfo("sato_yumi", "佐藤由美"),
    UserInfo("takahashi_kenji", "高橋健二"),
    UserInfo("ito_megumi", "伊藤めぐみ"),
    UserInfo("watanabe_koji", "渡辺浩二"),
    UserInfo("nakamura_shiori", "中村詩織"),
    UserInfo("kobayashi_takashi", "小林隆"),
    UserInfo("kato_yoko", "加藤洋子"),
    UserInfo("yoshida_akira", "吉田明"),
    UserInfo("yamamoto_naoki", "山本直樹"),
    UserInfo("sasaki_miki", "佐々木美希"),
    UserInfo("yamaguchi_tomoki", "山口智樹"),
    UserInfo("matsumoto_aya", "松本彩"),
    UserInfo("inoue_ryota", "井上涼太"),
    UserInfo("kimura_kanako", "木村加奈子"),
    UserInfo("hayashi_daiki", "林大樹"),
    UserInfo("shimizu_miho", "清水美穂"),
    UserInfo("yamazaki_hiroshi", "山崎浩"),
    UserInfo("mori_sayaka", "森さやか"),
    UserInfo("ikeda_satoshi", "池田聡"),
    UserInfo("hashimoto_mai", "橋本麻衣"),
    UserInfo("abe_yoshihiro", "阿部義弘"),
    UserInfo("ishikawa_mika", "石川美香"),
    UserInfo("yamashita_kenta", "山下健太"),
    UserInfo("nakajima_reiko", "中島玲子"),
    UserInfo("maeda_tatsuya", "前田達也"),
    UserInfo("fujita_nana", "藤田菜々"),
    UserInfo("goto_shigeru", "後藤茂"),
    UserInfo("ogawa_yukiko", "小川由紀子"),
    UserInfo("okada_shohei", "岡田翔平"),
    UserInfo("hasegawa_rumi", "長谷川るみ"),
    UserInfo("murakami_kosuke", "村上康介"),
    UserInfo("kondo_mayu", "近藤真由"),
    UserInfo("ishii_tomoya", "石井智也"),
    UserInfo("sakamoto_ai", "坂本愛"),
    UserInfo("endo_takumi", "遠藤匠"),
    UserInfo("aoki_yuji", "青木裕二"),
    UserInfo("fujii_nanami", "藤井七海"),
    UserInfo("saito_kenta", "斉藤健太"),
    UserInfo("miura_ayumi", "三浦あゆみ"),
    UserInfo("fukuda_takeshi", "福田武"),
    UserInfo("ono_sachiko", "小野幸子"),
    UserInfo("murata_daisuke", "村田大輔"),
    UserInfo("hirano_kazuya", "平野和也"),
    UserInfo("takagi_rika", "高木里佳"),
    UserInfo("kaneko_masashi", "金子雅"),
    UserInfo("ishida_yuka", "石田由佳"),
    UserInfo("sugiyama_keisuke", "杉山圭介"),
    UserInfo("nomura_shinji", "野村真司"),
    UserInfo("kojima_hitomi", "小島ひとみ"),
    UserInfo("tamura_kazuo", "田村和夫"),
    UserInfo("matsuoka_yuki", "松岡由紀"),
    UserInfo("nosaka_akio", "野坂明生"),
    UserInfo("kawano_momoko", "河野桃子"),
    UserInfo("harada_junichi", "原田淳一"),
    UserInfo("akiyama_masako", "秋山正子"),
    UserInfo("hara_toshio", "原敏夫"),
    UserInfo("okamoto_misaki", "岡本美咲"),
    UserInfo("kubota_ryuichi", "久保田隆一"),
    UserInfo("ueda_naomi", "上田直美"),
    UserInfo("nishimura_shota", "西村翔太"),
    UserInfo("fujiwara_yui", "藤原結衣"),
    UserInfo("morita_keita", "森田啓太"),
    UserInfo("yasuda_sakura", "安田さくら"),
    UserInfo("tanabe_hiroyuki", "田辺浩之"),
    UserInfo("otsuka_haruka", "大塚春花"),
    UserInfo("koyama_shingo", "小山真吾"),
    UserInfo("tsuchiya_kaori", "土屋かおり"),
    UserInfo("sakai_minoru", "酒井実"),
    UserInfo("uehara_risa", "上原里沙"),
    UserInfo("miyazaki_takuya", "宮崎卓也"),
    UserInfo("kikuchi_yusuke", "菊池裕介"),
    UserInfo("miyata_asuka", "宮田明日香"),
    UserInfo("arai_toru", "新井徹"),
    UserInfo("ihara_mizuki", "井原瑞希"),
    UserInfo("kubo_naoto", "久保直人"),
    UserInfo("takeuchi_erika", "竹内絵里香"),
    UserInfo("nishida_yuichiro", "西田雄一郎"),
    UserInfo("matsubara_nanako", "松原奈々子"),
    UserInfo("ishizuka_haruto", "石塚陽翔"),
    UserInfo("mizuno_chiaki", "水野千秋"),
    UserInfo("koizumi_shuji", "小泉修二"),
    UserInfo("taguchi_akane", "田口あかね"),
    UserInfo("uchida_koichi", "内田浩一"),
    UserInfo("oishi_marina", "大石麻里奈"),
    UserInfo("yokoyama_takashi", "横山隆"),
    UserInfo("kuroda_aiko", "黒田愛子"),
    UserInfo("sano_kentaro", "佐野健太郎"),
    UserInfo("hamada_yumiko", "浜田由美子"),
    UserInfo("nakano_koji", "中野浩二"),
    UserInfo("kawasaki_ayaka", "川崎彩香"),
    UserInfo("sekiguchi_ryosuke", "関口亮介"),
    UserInfo("takeda_tomomi", "武田智美"),
    UserInfo("ohta_shin", "太田慎"),
    UserInfo("iida_miyuki", "飯田美幸"),
    UserInfo("narita_kotaro", "成田康太郎"),
    UserInfo("adachi_rie", "安達理恵"),
    UserInfo("sugiura_masao", "杉浦正雄")
]


def seed_master_data(db: Session) -> Dict[str, Dict[str, Any]]:
    """
    グループ、勤怠種別、社員種別のマスターデータを作成します。
    既に同名のデータが存在する場合は作成しません。

    Args:
        db: データベースセッション

    Returns:
        Dict[str, Dict[str, Any]]: 作成または取得したマスターデータオブジェクト
                                     (名前をキーとする辞書) を含む辞書。
                                     例: {'groups': {'グループ１': <Group obj>}, ...}
    """
    created_data: Dict[str, Dict[str, Any]] = {
        "groups": {},
        "locations": {},
        "user_types": {}
    }
    commit_needed = False

    # グループ作成 (キーを str() でキャスト)
    existing_groups = {str(g.name): g for g in db.scalars(select(Group)).all()}
    for name in GROUP_NAMES:
        if name not in existing_groups:
            group = Group(name=name)
            db.add(group)
            created_data["groups"][name] = group
            logger.info(f"マスターデータ作成 (Group): {name}")
            commit_needed = True
        else:
            created_data["groups"][name] = existing_groups[name]

    # 勤怠種別作成 (キーを str() でキャスト)
    existing_locations = {str(loc.name): loc for loc in db.scalars(select(Location)).all()}
    for name in LOCATION_NAMES:
        if name not in existing_locations:
            location = Location(name=name)
            db.add(location)
            created_data["locations"][name] = location
            logger.info(f"マスターデータ作成 (Location): {name}")
            commit_needed = True
        else:
            created_data["locations"][name] = existing_locations[name]

    # 社員種別作成 (キーを str() でキャスト)
    existing_user_types = {str(ut.name): ut for ut in db.scalars(select(UserType)).all()}
    for name in USER_TYPE_NAMES:
        if name not in existing_user_types:
            user_type = UserType(name=name)
            db.add(user_type)
            created_data["user_types"][name] = user_type
            logger.info(f"マスターデータ作成 (UserType): {name}")
            commit_needed = True
        else:
            created_data["user_types"][name] = existing_user_types[name]

    if commit_needed:
        db.commit()
        # 再取得部分 (キーを str() でキャスト)
        created_data["groups"] = {str(g.name): g for g in db.scalars(select(Group)).all()}
        created_data["locations"] = {str(loc.name): loc for loc in db.scalars(select(Location)).all()}
        created_data["user_types"] = {str(ut.name): ut for ut in db.scalars(select(UserType)).all()}

    return created_data


def seed_users(db: Session, master_data: Dict[str, Dict[str, Any]], count: int = 10) -> List[User]:
    """
    サンプルユーザーデータをデータベースに追加します。
    グループと社員種別は、提供されたマスターデータからランダムに割り当てます。

    Args:
        db: データベースセッション
        master_data: seed_master_data から返されたマスターデータオブジェクト辞書
        count: 追加するユーザー数 (最大100まで)

    Returns:
        List[User]: データベースに追加されたUserオブジェクトのリスト。
    """
    existing_user_ids: Set[str] = set(str(user.id) for user in db.scalars(select(User)).all())

    # マスターデータからグループと社員種別のリストを取得
    groups = list(master_data.get("groups", {}).values())
    user_types = list(master_data.get("user_types", {}).values())

    # グループや社員種別が存在しない場合は処理を中断
    if not groups:
        logger.error("マスターデータにグループが存在しません。ユーザーシードをスキップします。")
        return []
    if not user_types:
        logger.error("マスターデータに社員種別が存在しません。ユーザーシードをスキップします。")
        return []

    actual_count = min(count, len(SAMPLE_USERS))
    created_users = []
    selected_samples = random.sample(SAMPLE_USERS, actual_count)

    for user_info in selected_samples:
        user_id = user_info.user_id
        counter = 1
        temp_user_id = user_id
        while temp_user_id in existing_user_ids:
            temp_user_id = f"{user_id}{counter}"
            counter += 1
        user_id = temp_user_id

        user = User(
            id=user_id,
            username=user_info.full_name,
            # マスターデータのリストからランダムに選択
            group_id=random.choice(groups).id,
            user_type_id=random.choice(user_types).id
        )
        db.add(user)
        created_users.append(user)
        existing_user_ids.add(user_id) # 新規追加したIDもセットに追加

    db.commit()
    logger.info(f"{len(created_users)} 件のユーザーをシードしました。")
    return created_users


def create_location_preferences(
    locations: Dict[str, Location],
    primary_location_name: str,
    primary_weight: float = 0.7
) -> Dict[int, float]:
    """指定された勤怠種別辞書に基づき、特定の場所を優先する確率分布を生成します。

    Args:
        locations: 勤怠種別の名前をキー、Locationオブジェクトを値とする辞書。
        primary_location_name: 優先的に選択される勤怠種別の名前。
        primary_weight: 優先勤怠種別が選択される確率の重み (デフォルト0.7)。

    Returns:
        Dict[int, float]: 各勤怠種別IDをキーとし、選択確率の重みを値とする辞書。
                          存在しないprimary_location_nameが指定された場合は空辞書。
    """
    if primary_location_name not in locations:
        logger.warning(f"優先勤怠種別 '{primary_location_name}' が見つかりません。")
        return {}

    # キーを int() でキャスト
    primary_location_id = int(locations[primary_location_name].id)
    prefs = {int(loc.id): random.uniform(0.1, 0.3) for loc in locations.values()}
    prefs[primary_location_id] = primary_weight
    return prefs


def seed_attendance(db: Session, master_data: Dict[str, Dict[str, Any]],
                   users: Optional[List[User]] = None,
                   days_back: int = 30, days_forward: int = 30) -> List[Attendance]:
    """
    指定されたユーザーリストまたは全ユーザーに対して、ダミーの勤怠記録を生成します。
    勤怠種別は提供されたマスターデータから選択されます。

    Args:
        db: データベースセッション
        master_data: seed_master_data から返されたマスターデータオブジェクト辞書
        users: 勤怠記録を追加するユーザーオブジェクトのリスト (Noneの場合は全ユーザーが対象)。
        days_back: 過去何日分のデータを生成するか (デフォルト30日)。
        days_forward: 未来何日分のデータを生成するか (デフォルト30日)。

    Returns:
        List[Attendance]: データベースに追加されたAttendanceオブジェクトのリスト。
    """
    if users is None:
        users_to_process: List[User] = list(db.scalars(select(User)).all())
    else:
        users_to_process = users

    # マスターデータから勤怠種別の辞書を取得
    locations_dict = master_data.get("locations", {})
    if not locations_dict:
        logger.error("マスターデータに勤怠種別が存在しません。勤怠シードをスキップします。")
        return []

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

    for user in users_to_process:
        # ユーザーごとの勤務傾向（オフィス派/テレワーク派、好みのオフィス）をランダムに設定します。
        is_office_worker = random.random() > 0.3

        # 優先オフィス候補から「テレワーク」「夜勤」を除外
        possible_offices = {
            name: loc for name, loc in locations_dict.items()
            if name not in ["テレワーク", "夜勤"]
        }
        if not possible_offices:
             logger.warning("優先オフィス候補 (テレワーク/夜勤以外) が見つかりません。")
             # 代替として最初の場所を使うか、処理を中断するかなど検討
             if locations_dict:
                 preferred_office_name = list(locations_dict.keys())[0]
             else:
                 continue # ユーザーの処理をスキップ
        else:
            preferred_office_name = random.choice(list(possible_offices.keys()))

        # 曜日ごとの勤怠種別選択確率を格納する辞書を初期化します。
        weekday_patterns: Dict[int, Dict[int, float]] = {}

        # 平日 (月曜=0 〜 金曜=4) の勤務パターンを設定します。
        for weekday in range(5):
            if is_office_worker:
                location_prefs = create_location_preferences(locations_dict, preferred_office_name)
            else:
                # テレワークを好むユーザー (テレワークのIDを渡す)
                location_prefs = create_location_preferences(locations_dict, "テレワーク")
            weekday_patterns[weekday] = location_prefs

        # 休日 (土曜=5, 日曜=6) の勤務パターンを設定します (出勤は稀)。
        for weekday in range(5, 7):
            location_prefs = create_location_preferences(locations_dict, preferred_office_name, 0.8)
            weekday_patterns[weekday] = location_prefs

        # 指定された日付範囲で勤怠記録を生成します。
        for day_offset in range((end_date - start_date).days + 1):
            day = start_date + timedelta(days=day_offset)

            # 既存レコードがある場合はスキップします。
            if (str(user.id), day) in existing_records:
                continue

            # 勤務する確率 (平日は高く、休日は低い)
            attendance_probability = 0.9 if day.weekday() < 5 else 0.05

            if random.random() < attendance_probability:
                # その曜日の勤怠種別パターンを取得します。
                current_pattern = weekday_patterns.get(day.weekday(), {}) # weekdayは整数なのでstr()は不要
                if not current_pattern: # パターンがない場合はスキップ（念のため）
                    continue

                # パターンに基づいて勤怠種別を選択します。
                location_ids_in_pattern = list(current_pattern.keys())
                weights = list(current_pattern.values())
                # locations_dict から ID を取得するようにする
                if location_ids_in_pattern: # パターンにIDがあれば
                    chosen_location_id = random.choices(location_ids_in_pattern, weights=weights, k=1)[0]

                    # 新しい勤怠記録オブジェクトを作成します。
                    attendance = Attendance(
                        user_id=str(user.id),
                        date=day,
                        location_id=chosen_location_id
                    )
                    db.add(attendance)
                    created_records.append(attendance)

    # まとめてコミットします。
    db.commit()
    logger.info(f"{len(created_records)} 件の勤怠記録をシードしました。")
    return created_records


def run_seeder(user_count: int = 20, days_back: int = 60, days_forward: int = 30) -> Dict[str, int]:
    """
    マスターデータとシードデータを生成して実行します

    Args:
        user_count: 追加するユーザー数
        days_back: 過去何日分のデータを生成するか
        days_forward: 未来何日分のデータを生成するか

    Returns:
        各エンティティの追加数を含む辞書
    """
    db = SessionLocal()
    try:
        # 1. マスターデータを作成/取得
        logger.info("マスターデータのシードを開始します...")
        master_data = seed_master_data(db)
        logger.info("マスターデータのシードが完了しました。")

        # 2. ユーザーを追加 (マスターデータを渡す)
        logger.info("ユーザーデータのシードを開始します...")
        # master_data が空でないことを確認
        if not master_data.get("groups") or not master_data.get("user_types"):
             logger.error("マスターデータ(グループまたは社員種別)の準備に失敗したため、ユーザーをシードできません。")
             users_created_count = 0
        else:
            users = seed_users(db, master_data, count=user_count)
            users_created_count = len(users)
        logger.info("ユーザーデータのシードが完了しました。")

        # 3. 勤怠記録を追加 (マスターデータを渡す)
        logger.info("勤怠データのシードを開始します...")
        # users リストが None でないことを確認 (seed_usersが空リストを返す場合があるため)
        users_to_seed = users if 'users' in locals() and users else None
        if not master_data.get("locations"):
             logger.error("マスターデータ(勤怠種別)の準備に失敗したため、勤怠をシードできません。")
             attendances_created_count = 0
        elif users_to_seed is None and user_count > 0:
             logger.warning("勤怠をシードする対象ユーザーが存在しません。")
             attendances_created_count = 0
        else:
            # users_to_seed が None の場合は seed_attendance が全ユーザーを対象にする
            attendances = seed_attendance(db, master_data, users=users_to_seed,
                                          days_back=days_back, days_forward=days_forward)
            attendances_created_count = len(attendances)
        logger.info("勤怠データのシードが完了しました。")

        return {
            "users": users_created_count,
            "attendances": attendances_created_count
        }
    except Exception as e:
        logger.error(f"シーダー実行中にエラーが発生しました: {e}", exc_info=True)
        # エラー発生時は空の結果を返すか、例外を再raiseするか検討
        return {"users": 0, "attendances": 0}
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    # ロガー設定 (必要であれば)
    # from app.core.logging_config import setup_logging
    # setup_logging()

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