# UI

browser UIはJinja2によるSSRを基本に、HTMXでpartial update、Alpine.jsで局所的なclient-side stateを扱います。page routeはOpenAPIへ含めません。

## Screens

| Route | Purpose |
| --- | --- |
| `/` | top / monthly calendar入口 |
| `/calendar` | monthly summary calendar |
| `/calendar/day/{day}` | 日別detail |
| `/attendance/weekly` | weekly attendance |
| `/attendance/monthly` | user別monthly attendance |
| `/users` | user master |
| `/groups` | group master |
| `/locations` | attendance/location master |
| `/user-types` | user type master |
| `/holidays` | custom holiday master |
| `/csv` | CSV download UI |
| `/analysis` | monthly / fiscal-year attendance coverage chart |
| `/analysis/day/{day}` | analysis filter適用済みの日別detail fragment |
| `/auth/*` | login / logout / OIDC protocol flow |
| `/admin/auth` | OIDC / authentication settings |
| `/admin/database` | SQLite backup / restore |

認証画面のbehaviorは [Authentication](authentication.md)、SQLite管理画面は [SQLite database management](sqlite-database-management.md) を参照してください。

## HTMX boundary

page / HTMX adapterがForm input、HTML fragment、`HX-*` headerを担当し、business ruleはserviceへ委譲します。

write成功時はcustom eventで必要なUIだけを更新します。validation / application errorは対象modalやfragmentへHTMLとして返し、success eventを送信しません。JSON API error responseをHTML targetへ流用しません。

refresh対象のmonth / weekは変更対象dateから導出し、`Referer`等から推測しません。

## Frontend responsibilities

| Area | Responsibility |
| --- | --- |
| Jinja2 | full page / partial / reusable componentのrender |
| HTMX | server request、partial replacement、custom event |
| Alpine.js | component-localな小さいstate |
| shared shell JS | theme / sidebar等、DBに依存しないpresentation state |
| page-specific JS | 対象pageだけのinteraction |

DB由来stateやHTMX lifecycleをAlpine global storeで共有状態として持ちません。server-sideで決定できるnavigation active stateはJinjaでrenderし、HTML標準機能で十分な操作にはclient JSを追加しません。

sidebarとthemeの保存stateは初回paint前に`html`へ反映し、layout geometryやvisual mappingはCSSが所有します。個別のscript/file責務は`app/static/js/`を参照してください。

## Analysis view contract

analysisは表示条件と単一coverage chartを中心に構成します。

- monthlyは日別、fiscal-yearは4月〜翌3月の月別bucket
- groupとuser typeは独立filterで、初期状態は全group / 全user type
- 初期seriesは全合計のみ。個別attendance typeは必要なものだけ追加できる
- 全合計はbucket内で何らかのattendance typeを持つunique user数。複数typeを持っても1人として数える
- 個別seriesもbucket内のunique user数を数え、選択seriesは1つのchartへ重ねる
- monthlyの日付labelから、現在のfilterを適用したday detailをchart直下へ読み込める。fiscal-yearにはday detail controlを出さない
- mode / periodはURL/historyへ残し、filter状態は残さない。mode / period変更時は初期filterへ戻す
- chartはserver-rendered SVGと同内容のaccessible text summaryを持ち、client-side chart state/libraryへ依存しない

coverage matrix、KPI群、社員別集計table等をprimary surfaceへ追加しません。集計modelの実装は`app/services/analysis_coverage_service.py`、page interactionは`app/static/js/analysis.js`を参照してください。

## Styling boundary

runtime dataからTailwind / daisyUI class名を組み立てません。

- Python/serviceはframework classをpresentation contractとして返さない
- Jinjaはsemantic stateを`data-*` attributeで表現する
- actual color / background / visual mappingは`builder/input.css`が所有する
- Tailwind safelistをruntime presentation contractとして使わない

attendance typeのtoneは永続`location_id`からstable palette slotへ写像し、templateへsemantic indexだけを渡します。名称変更や表示順変更ではtoneを変えません。週末/祝日も`data-day-kind`で状態を渡し、色指定をtemplateから分離します。

## Template layout

```text
app/templates/
├── layout/       # application shell
├── pages/        # full-page templates
└── components/   # partials / macros / domain components
```

`components/macros/`は責務別macroを必要なtemplateから直接importし、compatibility facadeは置きません。

## Assets

application JS sourceは`app/static/js/`、Tailwind/daisyUIとvendor JSのbuild sourceは`builder/`です。generated assetを直接編集せず、既存flowを利用します。

```bash
make assets
```

local build、production image、Dev Containerはいずれも`scripts/build_assets.sh`をasset build boundaryとして共有します。
