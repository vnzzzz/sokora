# API

JSON APIは`/api/v1`配下で提供します。request/response schemaはgenerated OpenAPIと`app/schemas/`に対応します。

- Swagger UI: `/docs`
- ReDoc: `/redoc`
- page / HTMX routeはOpenAPIへ含めません

## Endpoints

| Resource | Method / path | Purpose |
| --- | --- | --- |
| Attendance | `GET /api/v1/attendances` | 一覧 |
|  | `GET /api/v1/attendances/day/{day}` | 日別projection |
|  | `POST /api/v1/attendances` | 作成 |
|  | `PUT /api/v1/attendances/{id}` | 更新 |
|  | `DELETE /api/v1/attendances/{id}` | ID指定削除 |
|  | `DELETE /api/v1/attendances?user_id=...&date=...` | user/date指定削除 |
| Users | `GET /api/v1/users` | 一覧 |
|  | `GET /api/v1/users/{user_id}` | 1件取得 |
|  | `POST /api/v1/users` | 作成 |
|  | `PUT /api/v1/users/{user_id}` | 更新 |
|  | `DELETE /api/v1/users/{user_id}` | 削除 |
| Locations | `GET/POST /api/v1/locations` | 一覧 / 作成 |
|  | `PUT/DELETE /api/v1/locations/{location_id}` | 更新 / 削除 |
| Groups | `GET/POST /api/v1/groups` | 一覧 / 作成 |
|  | `PUT/DELETE /api/v1/groups/{group_id}` | 更新 / 削除 |
| User types | `GET/POST /api/v1/user_types` | 一覧 / 作成 |
|  | `PUT/DELETE /api/v1/user_types/{user_type_id}` | 更新 / 削除 |
| CSV | `GET /api/v1/csv/download` | 月次勤怠CSV |

custom holidayはJSON APIを持たず、page / HTMX routeからserviceを利用します。APIの対称性だけを理由に未使用endpointを追加しません。

## Adapter rules

JSON APIとpage / HTMX adapterはtransportを分離します。

- JSON API: JSON input/output
- page / HTMX: Form input、HTML fragment、`HX-*` response
- business rule / write transaction: shared service
- DB constraint: 最終的な整合性保証
- page adapterからJSON APIへの内部HTTP delegationは行わない

## Authentication

`SOKORA_AUTH_ENABLED=true`では、sessionのないAPI requestへ401を返します。authentication flow、OpenAPI、static asset、`/healthz`はpublicです。

認証方式とadmin routeは [Authentication](authentication.md) を参照してください。

## Errors

| Condition | Response |
| --- | --- |
| request schema / type error | FastAPI / Pydanticのvalidation response |
| invalid domain input / not found | 適切な4xx |
| concurrent write等のconstraint conflict | 409等のapplication error |
| verified DB unavailable / acquisition timeout | 503 |
| unexpected internal failure | 500 |

DB exception文字列、credential、filesystem path等の内部情報をpublic responseへ露出しません。

CSVはmonthとencoding（`utf-8` / `sjis`）を検証し、file生成が成功してからdownload responseを開始します。生成failureを200 responseのCSV本文へ埋め込みません。
