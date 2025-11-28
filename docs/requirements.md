# 要件ドキュメント

sokora の API・DB・UI を横断的に把握するための要件集約ドキュメントです。詳細は分野別ドキュメントに委譲し、重複を避けます。

## ドキュメント一覧
- [API 要件](api/requirements.md)
- [DB 要件](db/requirements.md)
- [UI 要件](ui/requirements.md)
- [テンプレート構成](ui/templates.md)（UI のファイル配置の補足）

## 共通方針
- FastAPI（/api プレフィックス）と Jinja2 + HTMX/Alpine.js の SSR UI を整合させる。
- 勤怠・ユーザー・マスタ（勤怠種別/社員種別/グループ）の整合性は DB モデルを基準に、API と UI の期待値を合わせる。
- 振る舞いの詳細は分野別ドキュメントを参照し、記述が無い場合はテストや実装を一次情報として更新する。
