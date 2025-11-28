# API 要件

 FastAPI v1 ルーター（`app/routers/api/v1/__init__.py`）配下で `/api/v1` プレフィックスを使用します。データモデルは [DB 要件](../db/requirements.md) を基準とし、UI 側の HTMX フローは [UI 要件](../ui/requirements.md) を参照してください。

## 共通仕様
- 応答は原則 JSON。勤怠作成/更新/削除はフォーム送信を受け、204 + `HX-Trigger` で UI 更新を指示。
- 外部連携や認可は未実装。バリデーションはサービス/CRUD層で外部キー整合性や重複を確認。
- OpenAPI は `/docs` `/redoc` で公開される。

## エンドポイント一覧（v1）
- `GET /api/v1/attendances`：全勤怠リスト（`{"records": [...]}`）。  
- `GET /api/v1/attendances/day/{day}`：日付別の勤怠詳細をロケーション軸で返却。  
- `POST /api/v1/attendances`：`user_id`・`date`（YYYY-MM-DD）・`location_id`・`note?` をフォームで受付。ユーザー + 日付の重複を禁止。成功時はモーダル閉鎖と当月再読み込みを `HX-Trigger` で通知。  
- `PUT /api/v1/attendances/{attendance_id}`：勤怠種別や備考を更新。`HX-Trigger` で対象ユーザー/月の再描画を要求。  
- `DELETE /api/v1/attendances/{attendance_id}`：ID指定削除。  
- `DELETE /api/v1/attendances?user_id=...&date=...`：ユーザー + 日付指定削除。  
- `GET /api/v1/users` / `GET /api/v1/users/{user_id}`：社員一覧・単体取得。`{"users": [...]}` 形式。  
- `POST /api/v1/users`：社員作成（JSON）。グループ・社員種別の存在確認と重複チェックをサービス層で実施。  
- `PUT /api/v1/users/{user_id}`：社員更新。  
- `DELETE /api/v1/users/{user_id}`：関連勤怠を先に削除してからユーザーを削除（204）。  
- `GET /api/v1/locations`：勤怠種別一覧を名前順で返す。  
- `POST /api/v1/locations` / `PUT /api/v1/locations/{location_id}`：勤怠種別の作成・更新。サービス層で重複/参照チェック。  
- `DELETE /api/v1/locations/{location_id}`：勤怠種別削除。CRUD側で利用中データの検証を実施。  
- `GET /api/v1/groups`：グループ一覧（order → name の順でソート）。  
- `POST /api/v1/groups` / `PUT /api/v1/groups/{group_id}` / `DELETE /api/v1/groups/{group_id}`：グループ CRUD。  
- `GET /api/v1/user_types`：社員種別一覧（order → name でソート）。  
- `POST /api/v1/user_types` / `PUT /api/v1/user_types/{user_type_id}` / `DELETE /api/v1/user_types/{user_type_id}`：社員種別 CRUD。  
- `GET /api/v1/csv/download?month=YYYY-MM&encoding=utf-8|sjis`：勤怠データをストリーミング出力。エンコーディング検証と月フォーマット検証を実施。Content-Disposition でファイル名を付与。

## UI 連携の留意点
- 勤怠 CRUD は HTMX モーダルから呼び出され、`HX-Trigger` (`closeModal` / `refreshUserAttendance` / `refreshAttendance`) を返す前提。UI の具体的なトリガー名は [UI 要件](../ui/requirements.md#カレンダーと勤怠登録) を参照。
- `/api/v1/csv/download` は `pages/csv.html` からクエリストリングを組み立ててダウンロードする。
- API が前提とするフィールド名や型は [DB 要件](../db/requirements.md) のモデル構成に従う。
