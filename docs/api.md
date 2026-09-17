# API

JSON APIは`/api/v1`配下で提供します。exact method / path / request / response schemaはgenerated OpenAPIを参照してください。

- Swagger UI: `/docs`
- ReDoc: `/redoc`
- page / HTMX routeはOpenAPIへ含めません

主なresourceはattendance、users、locations、groups、user types、CSVです。custom holidayはJSON APIを持たず、page / HTMX routeからserviceを利用します。APIの対称性だけを理由に未使用endpointを追加しません。

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
