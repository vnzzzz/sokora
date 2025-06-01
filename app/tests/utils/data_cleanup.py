#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, '/app')

from app.db.session import SessionLocal
from app.models import Group, UserType, Location, User, Attendance

def cleanup_test_data() -> bool:
    """テストで作成されたデータをクリーンアップする"""
    db = SessionLocal()
    try:
        print("=== テストデータのクリーンアップ開始 ===")
        
        cleanup_count = 0
        
        # 1. テスト関連のattendanceレコードを最初に削除（外部キー制約のため）
        # テスト関連のユーザーを取得
        test_users = db.query(User).filter(
            (User.username.like('%テスト%')) |
            (User.username.like('%編集%')) |
            (User.username.like('%削除%'))
        ).all()
        test_user_ids = [user.id for user in test_users]
        
        # テスト関連のロケーションを取得
        test_locations = db.query(Location).filter(
            (Location.name.like('%テスト%')) |
            (Location.name.like('%編集%')) |
            (Location.name.like('%削除%'))
        ).all()
        test_location_ids = [location.id for location in test_locations]
        
        # テストユーザーまたはテストロケーションに関連するattendanceを削除
        if test_user_ids or test_location_ids:
            test_attendances = db.query(Attendance).filter(
                (Attendance.user_id.in_(test_user_ids)) |
                (Attendance.location_id.in_(test_location_ids))
            ).all()
            for attendance in test_attendances:
                print(f"Deleting attendance: {attendance.id} (user: {attendance.user_id}, location: {attendance.location_id}, date: {attendance.date})")
                db.delete(attendance)
                cleanup_count += 1
        
        # 2. テスト関連のユーザーを削除
        for user in test_users:
            print(f"Deleting user: {user.id} - {user.username}")
            db.delete(user)
            cleanup_count += 1
        
        # 3. テスト関連のロケーションを削除
        for location in test_locations:
            print(f"Deleting location: {location.id} - {location.name}")
            db.delete(location)
            cleanup_count += 1
        
        # 4. テスト関連のグループを削除
        test_groups = db.query(Group).filter(
            (Group.name.like('%テスト%')) |
            (Group.name.like('%編集%')) |
            (Group.name.like('%削除%'))
        ).all()
        for group in test_groups:
            print(f"Deleting group: {group.id} - {group.name}")
            db.delete(group)
            cleanup_count += 1
        
        # 5. テスト関連のユーザータイプを削除
        test_user_types = db.query(UserType).filter(
            (UserType.name.like('%テスト%')) |
            (UserType.name.like('%編集%')) |
            (UserType.name.like('%削除%'))
        ).all()
        for user_type in test_user_types:
            print(f"Deleting user type: {user_type.id} - {user_type.name}")
            db.delete(user_type)
            cleanup_count += 1
        
        # 変更をコミット
        db.commit()
        print(f"=== テストデータのクリーンアップ完了 ({cleanup_count}件削除) ===")
        return True
        
    except Exception as e:
        print(f"Error during cleanup: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = cleanup_test_data()
    if success:
        print("クリーンアップが正常に完了しました。")
    else:
        print("クリーンアップでエラーが発生しました。")
        sys.exit(1) 