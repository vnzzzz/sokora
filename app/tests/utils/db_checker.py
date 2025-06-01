#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, '/app')

from app.db.session import SessionLocal, Base, engine
from app.models import Group, UserType, Location, User, Attendance

def check_database() -> int:
    """データベースの状態を確認し、テスト関連データの残存をチェックする"""
    # テーブル作成
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        print("=== データベース状態確認 ===")
        print(f"Groups: {db.query(Group).count()}")
        print(f"User Types: {db.query(UserType).count()}")
        print(f"Locations: {db.query(Location).count()}")
        print(f"Users: {db.query(User).count()}")
        print(f"Attendances: {db.query(Attendance).count()}")
        
        print("\n=== テスト関連データ ===")
        
        # テスト関連のグループ
        test_groups = db.query(Group).filter(
            (Group.name.like('%テスト%')) |
            (Group.name.like('%編集%')) |
            (Group.name.like('%削除%'))
        ).all()
        print(f"Test Groups ({len(test_groups)}):")
        for g in test_groups:
            print(f"  - {g.id}: {g.name}")
        
        # テスト関連のユーザータイプ
        test_user_types = db.query(UserType).filter(
            (UserType.name.like('%テスト%')) |
            (UserType.name.like('%編集%')) |
            (UserType.name.like('%削除%'))
        ).all()
        print(f"Test User Types ({len(test_user_types)}):")
        for ut in test_user_types:
            print(f"  - {ut.id}: {ut.name}")
        
        # テスト関連のロケーション
        test_locations = db.query(Location).filter(
            (Location.name.like('%テスト%')) |
            (Location.name.like('%編集%')) |
            (Location.name.like('%削除%'))
        ).all()
        print(f"Test Locations ({len(test_locations)}):")
        for l in test_locations:
            print(f"  - {l.id}: {l.name}")
        
        # テスト関連のユーザー
        test_users = db.query(User).filter(
            (User.username.like('%テスト%')) |
            (User.username.like('%編集%')) |
            (User.username.like('%削除%'))
        ).all()
        print(f"Test Users ({len(test_users)}):")
        for u in test_users:
            print(f"  - {u.id}: {u.username}")
            
        # テスト関連データの総数を返す
        total_test_data = len(test_groups) + len(test_user_types) + len(test_locations) + len(test_users)
        return total_test_data
            
    finally:
        db.close()

def has_test_data() -> bool:
    """テスト関連データが存在するかどうかを確認する"""
    db = SessionLocal()
    try:
        # テスト関連データの存在チェック
        test_groups_count = db.query(Group).filter(
            (Group.name.like('%テスト%')) |
            (Group.name.like('%編集%')) |
            (Group.name.like('%削除%'))
        ).count()
        
        test_user_types_count = db.query(UserType).filter(
            (UserType.name.like('%テスト%')) |
            (UserType.name.like('%編集%')) |
            (UserType.name.like('%削除%'))
        ).count()
        
        test_locations_count = db.query(Location).filter(
            (Location.name.like('%テスト%')) |
            (Location.name.like('%編集%')) |
            (Location.name.like('%削除%'))
        ).count()
        
        test_users_count = db.query(User).filter(
            (User.username.like('%テスト%')) |
            (User.username.like('%編集%')) |
            (User.username.like('%削除%'))
        ).count()
        
        return (test_groups_count + test_user_types_count + test_locations_count + test_users_count) > 0
        
    finally:
        db.close()

if __name__ == "__main__":
    check_database() 