# API requirements

この文書は、FastAPI JSON APIのpublic HTTP contractと、JSON API / page-HTMX adapterの責務境界をSSoTとする。data modelは [Database requirements](database.md)、UI behaviorは [UI requirements](ui.md) を参照する。

## Adapter boundary

- JSON APIは`app/routers/api/v1/`配下、prefixは`/api/v1`。
- `/api/v1/*`はJSON request/responseを担当し、HTML fragment、Form adapter、`HX-*` response headerを持たない。
- page/HTMX endpointは`app/routers/pages/`配下に置き、OpenAPIへ含めない。Form inputをapplication inputへ変換し、service/use caseを直接利用する。JSON APIへの内部HTTP委譲は行わない。
- write use caseのtransaction ownerはservice層。CRUD層はuse case単位のcommit/rollbackを所有しない。
- application-side validationに加え、UNIQUE/FK等のDB constraintを最終的な整合性保証とする。
- DB integrity race等はapplication errorへ変換し、DB例外文字列を外部へ直接公開しない。
- OpenAPI UIは`/docs`、`/redoc`で公開する。

## Authentication guard

`SOKORA_AUTH_ENABLED=true`の場合、UIと`/api`にsigned session guardを適用する。

- unauthenticated UI request: `/auth/login`へredirect。
- unauthenticated API request: HTTP 401 JSONを返す。
- authentication flow、static asset、OpenAPI等のpublic入口はguard対象外。
- admin-only pageは共通authorization dependencyで`role=admin`を要求する。
- `GET /healthz`はplatform probe用で認証を要求しない。

認証方式、cookie、OIDC discovery、local admin fallbackのarchitectureは [ADR 0002](adr/0002-authentication-runtime.md)、runtime設定contractは [Production runtime](runtime.md) を参照する。この文書ではOIDC library内部処理やcookie implementationを重複して保守しない。

## Error contract

- request schema/format errorはFastAPI/Pydantic contractに従う。
- domain/application側で事前判定できる入力不備、not found、重複等は適切な4xxへ変換する。
- concurrent write等でDB constraintへ競合した場合は409等のapplication errorへ変換する。
- internal DB exception text、credential、filesystem path等をpublic API errorへ露出しない。
- page/HTMX adapterのvalidation/application errorはJSON responseを再利用せず、UIが扱えるHTML fragmentとして返す。

## v1 endpoints

### Attendance

- `GET /api/v1/attendances`: 勤怠一覧。
- `GET /api/v1/attendances/day/{day}`: 日付別勤怠detail。
- `POST /api/v1/attendances`: `AttendanceCreate` JSONから作成し201を返す。`user_id + date`は一意。
- `PUT /api/v1/attendances/{attendance_id}`: `AttendanceUpdate` JSONから更新。
- `DELETE /api/v1/attendances/{attendance_id}`: ID指定削除、204。
- `DELETE /api/v1/attendances?user_id=...&date=...`: user/date指定削除、204。

### Users

- `GET /api/v1/users`
- `GET /api/v1/users/{user_id}`
- `POST /api/v1/users`
- `PUT /api/v1/users/{user_id}`
- `DELETE /api/v1/users/{user_id}`

user create/updateではgroup/user typeの参照整合性を検証する。user deleteは関連attendance削除と同一transactionで処理し、途中失敗時に一部だけを確定しない。

### Locations

- `GET /api/v1/locations`
- `POST /api/v1/locations`
- `PUT /api/v1/locations/{location_id}`
- `DELETE /api/v1/locations/{location_id}`

利用中locationの削除はapplication checkとDB FKで拒否する。

### Groups

- `GET /api/v1/groups`
- `POST /api/v1/groups`
- `PUT /api/v1/groups/{group_id}`
- `DELETE /api/v1/groups/{group_id}`

### User types

- `GET /api/v1/user_types`
- `POST /api/v1/user_types`
- `PUT /api/v1/user_types/{user_type_id}`
- `DELETE /api/v1/user_types/{user_type_id}`

### CSV

- `GET /api/v1/csv/download?month=YYYY-MM&encoding=utf-8|sjis`: 月次勤怠CSVをstreaming responseで返す。month/encodingを検証し、download filenameを`Content-Disposition`で指定する。

custom holidayのCRUDは現時点でJSON APIを持たず、page/HTMX adapter + serviceで提供する。APIの対称性だけを理由に未使用endpointを追加しない。

## UI integration boundary

- attendance modal writeは`/attendance/entries`等のpage/HTMX adapterを利用し、成功時の`HX-Trigger`をUI eventとして返す。
- refresh対象month/weekは変更対象dateから導出し、`Referer`等を表示stateのSSoTにしない。
- CSV pageはdownload時だけJSON API側のCSV endpointをbrowser navigationとして利用する。
- APIが扱うfield/type/constraintは [Database requirements](database.md) に従う。

endpointの詳細schemaはOpenAPIと`app/schemas/`を一次情報とし、private field一覧をこの文書へ複製しない。
