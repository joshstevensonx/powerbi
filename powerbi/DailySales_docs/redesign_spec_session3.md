# Daily Sales (v2.0) — Redesign build spec (Session 3, 7 Oct 2026)

**For:** Josh Stevenson (Nexora Web Agency) · client 1-grid
**Source of truth:** *Daily Sales (v2.0) — Semantic Model, Data & Report Documentation* (`DailySales_docs/Daily_Sales_v2_Documentation.md`, also in [Notion](https://app.notion.com/p/Daily-Sales-v2-0-Semantic-Model-Data-Report-Documentation-3f22b1d10782808e8b90f7366f409f28)).
**Deliverable built this session:** `powerbi/Daily sales (v2.0) – Redesign.pbix`, a thin report live-connected to *Daily sales (Model) v2.0*. It was generated from the report's PBIR definition and validated against Microsoft's published PBIR JSON schemas. **It has not been opened in Power BI yet**, because this session had no browser or Power BI Desktop (see §9). This spec is complete enough to rebuild every page by hand if the file won't open.

---

## 0. How to apply

**Option A: use the generated file (fastest)**
1. Open `Daily sales (v2.0) – Redesign.pbix` in Power BI Desktop (current version; PBIR preview format enabled). It connects live to *Daily sales (Model) v2.0* in **BigQuery Reports**.
2. Check each page against §4 and §7. Fix anything Desktop flags; the file's formatting properties are hand-written JSON.
3. **Publish** to *BigQuery Reports* under the name **Daily sales (v2.0) – Redesign**. The link to the live report's ID (`RemoteArtifacts` in `Connections`) was removed, so publishing creates a new report. The live *Daily sales (v2.0)* (7e523292-…) is never overwritten.
4. Run the verification checklist (§7).

**Option B: rebuild by hand in the service**
1. In the service, use File › Save a copy of *Daily sales (v2.0)* as **Daily sales (v2.0) – Redesign**.
2. Apply the theme changes (§3.6).
3. Add the report measures (§5). The service's "New measure" on a live-connected report creates a **report-level measure**, so the shared model is unchanged.
4. Build the frame once on a new page (§3), then duplicate it and add the visuals from §4.
5. Delete the old pages in the copy only.

**Never** edit the semantic model. Every new calculation in this spec is a report-level measure, stored in the report and not in the shared model.

### Why report-level measures, not visual calculations
The brief asked for visual calculations for ratios and period comparisons, so the shared model stays untouched. Report-level measures (thin-report measures) meet the same rule: they live in the report file and are invisible to the model and to other reports. They also:
- work in **cards and text lines**, where visual calculations are awkward or unavailable;
- can be **reused** on every page (one definition of AOV, not one per visual);
- keep working when the user changes slicers, because they are ordinary measures.

Visual-calculation equivalents are in §5.3 if you prefer them for specific charts.

---

## 1. What the business values (Excel + beta report evidence)

Evidence: `Sales_Report.xlsx` (summarised in `context/Sales_Report_summary.md`) and the *Daily sales (beta)* page list and descriptions. The Excel is **evidence of what matters, not a layout to copy**. v2.0 doesn't reproduce the 13-column daily product grid or the tracker sheets; it answers the same questions inside the v2.0 page structure.

### 1.1 What they rely on → where it is now

| # | Insight the team relies on (source) | Status in redesign | Where / how |
|---|---|---|---|
| 1 | Daily paid **new revenue, excl. VAT, on payment day** (Excel *Daily Actual Sales*, beta *Daily*) | ✅ | KPI *Paid revenue*; Overview daily combo; Daily Sales matrix. `[Paid Revenue (Products)]` already uses paid date and excl. VAT. |
| 2 | **No. of paid orders** per day (Excel) | ✅ | KPI *Paid orders*; Daily Sales matrix; Overview combo line. |
| 3 | Power BI (invoiced) vs Paid, **% paid** (Excel *Paid tracker*, daily variance %) | ✅ | Daily Sales matrix columns *Invoiced (all)* and *% paid*; Collections page; report measures `Invoiced Value`, `Paid Share of Invoiced`. |
| 4 | **Unpaid orders** (Excel col B) | ✅ improved | Unpaid (collectable) and Cancelled (lost) are now **separate** KPIs (amber / red). Collections page has a chase list. |
| 5 | **Product split** (13 Excel columns) | ✅ re-expressed | The Category › Sub Category › Product hierarchy replaces the Excel columns (mapping in §1.3). Products matrix, sub-category bar on Daily Sales, category bars. |
| 6 | **Local vs international domains**, revenue and **count added** (Excel) | ✅ | Products page domain block; Daily Sales matrix (R and #); *Domain region* slicer. Counts are registrations on **paid** orders. |
| 7 | **New-revenue %** (new-customer share) (Excel *New Revenue*) | ✅ | KPI *New-customer share* (Δ pts vs prior period); Overview donut; weekly share on Customers. |
| 8 | **App sales** (Excel) | ✅ | Daily Sales matrix *App sales*; Customers *channel* chart; Overview insight sentence; *Sales channel* slicer. |
| 9 | **Monthly sales with YoY %** (Excel *Monthly Actual Sales*, *2025 Sales*) | ⚠️ partial | Overview "Are we ahead of last year?": last 13 months with *same month last year*. Orders data starts ~Jul 2025, so the LY line fills in from Jul 2026 only. 2022–2025 history is not in the model (see §1.2). |
| 10 | **Period comparison** (Excel compares months and days) | ✅ | Every KPI shows Δ vs the prior period of equal length; Products matrix *vs prior period*. |
| 11 | Beta decomposition tree month › product type | ✅ re-expressed | Products matrix drill (Category › Sub Category › Product) with % of total and Δ. |
| 12 | Beta per-product pages (Domains, Web builder, Web design, Email hosting) | ✅ via filters | One Products page plus the Category/Sub category/Product slicers, synced across pages. No separate pages to maintain. |
| 13 | **Churn: services sold by status** (Excel *Churn*) | ⚠️ partial | Products "Are services sold this period still active?" shows the *current* `service_status` of services sold in the selected period. Year cohorts 2022–2025 aren't possible (§1.2). |
| 14 | Dec daily YoY (Excel *Dec Sales*) | ⚠️ from Dec 2026 | Use the Daily Sales page and set Period to December. LY comparison needs Dec 2025 data, which exists (from Jul 2025), so `[Paid Revenue LY]` works for Dec 2026 vs Dec 2025. |

### 1.2 What the model can't support, and the change each needs

| Insight | Why not | Data/model change needed (owner: BI team; changes the shared model) |
|---|---|---|
| **Total active domains**, **net domain movement** (local) | The model holds only new registrations, with no domain status history. | Add a **Domains** table from `tbldomains` (id, domain, TLD, registrationdate, expirydate, status, nextduedate) and a **daily snapshot** (date, active count, adds, expiries/transfers out) via a Dremio view or incremental refresh. Measures: Active Domains (as of date), Net Movement = adds − losses. |
| **Market share** (.co.za) | External ZACR data. | Monthly **Market Share** table (Month, 1-grid .co.za count, total .co.za, share) on SharePoint/Dremio, related to Calendar via a month key. |
| **YoY for 2022 – Jun 2025** | `tblorders` Dremio view (`Power BI Reports.Data analytics.Daily sales (beta).tblorders`) only returns ~Jul 2025 onwards. | Widen the view's date filter to 2022-01-01 (check refresh time), **or** import the Excel monthly totals as a **Historical Monthly Sales** table (Month, Paid new revenue excl. VAT) for a stitched trend. |
| **Churn by sales year (cohorts)** | `revenue_orders_tbl` lacks the service registration date for pre-Jul-2025 rows, and Calendar reaches it only through orders_invoices_tbl. | Add `create_date` (Combined Revenue) to revenue_orders_tbl, plus an inactive Calendar relationship or a `Sale Year` column. Measure: Services Sold (by create_date, any invoice). |
| **Midday view** (beta) / time of day | `order_time` exists in Combined Revenue but isn't carried into revenue_orders_tbl. | Add `order_hour` to revenue_orders_tbl. Then add a Midday KPI (paid revenue before 12:00) and a weekday × hour heatmap. |
| **Actual vs Budget** (beta nav) | Budget tables are FY21/FY22 and outdated. | A current **Budget** table (Date or Month, Category, budget R excl. VAT) and measures Budget, Variance, % of budget. |
| **Site traffic** (beta nav) | GA tables use the retired Universal Analytics connector. | GA4 connector or BigQuery export → Sessions table by date. |
| **Website Builder / DIFM** as separate lines | The model puts them in Sub Category *Website Design*; they're only separable at Product Name level. | Optional: split Sub Category into *Website Builder*, *DIFM*, *Website Design* in the `Sub Category` DAX (and Product Guide). |
| Excel counts **all** domain registrations; v2.0 counts paid ones | Free/unpaid registrations have no paid date. | Decide which definition the business wants. "All registrations by order date" would be a report measure on `order_date` without the Paid filter. |

### 1.3 Excel product columns → v2.0 hierarchy

| Excel column | v2.0 filter |
|---|---|
| Local Domains / International Domains | Sub Category = *Domains* × Domain Region = Local / International |
| SSL | Category *Security & Backup* (SSL products) |
| Shared Hosting | Sub Category *Web Hosting* |
| VPS | Sub Category *VPS & Cloud Servers* |
| Reseller Hosting | Sub Category *Reseller Hosting* |
| Dedicated Server | Sub Category *Dedicated Servers* |
| Company Registrations | Category *Business Services* |
| Website Design / Website Builder / DIFM | Sub Category *Website Design* (split at Product Name) |
| Email | Sub Category *Email* |
| Other | *Domain Add-ons*, *Domain Parking*, *Website Migration*, *SEO*, *Not in Combined Revenue* |

---

## 2. Pages (overview)

| # | Page | Business question | Audience |
|---|---|---|---|
| 1 | **Overview** | Are paid sales on track this period, and what is driving them? | Execs |
| 2 | **Daily Sales** | What sold each day? (replaces the Excel daily sheet) | Sales team, finance |
| 3 | **Products** | Which products earn the revenue, and is the mix changing? | Sales & marketing |
| 4 | **Customers & Channels** | Who is buying, how established are they, and through which channel? | Sales & marketing |
| 5 | **Collections** | How much invoiced value is still uncollected, and where? | Finance |
| – | Guide (hidden, drill-through) | What does each category include? | All (kept unchanged) |
| – | TT - Category, TT - Period, Revenue Tooltip (hidden tooltip pages) | Hover detail | — |
| – | _Frame template (hidden) | Duplicate to build new pages | BI team |

The old pages (TEMPLATE, Data_Exploration, PRODUCT SALES, SALES TRENDS, CUSTOMER INSIGHTS, PRODUCT MIX) aren't in the redesign copy; their content is absorbed above. They remain in the live report.

---

## 3. Design system

### 3.1 Colours (all from the *1-grid Brand* theme)

| Token | Hex | Use |
|---|---|---|
| Primary cyan | `#00C1DE` | Paid revenue (primary series), slicer accents, brand word "Daily Sales" in titles |
| Cool grey | `#55565A` | Secondary series (orders line), labels, subtitles |
| Green | `#00C18B` | New customers; positive Δ text uses dark green `#00845F` |
| Text black | `#231F20` | Titles, values |
| Tints | `#7FDFEE #A7A8AB #7FE0C5 #007E91 #00845F #B3ECF5` | Category palette, data bars (`#B3ECF5`) |
| Amber | `#F2A900` | Unpaid / pending, "same month last year" line |
| Red | `#E5484D` | Cancelled, negative Δ |
| Border | `#E3E5E8` | Card borders, gridlines |
| Page | `#F4F6F8` | Page background |

**Semantic colours (identical on every page):**

| Field value | Colour |
|---|---|
| Category: Domains / Application Hosting / Infrastructure Hosting / Web Services / Security & Backup / Business Services / Not in Combined Revenue / Other | `#00C1DE` / `#007E91` / `#55565A` / `#00C18B` / `#7FDFEE` / `#00845F` / `#A7A8AB` / `#C9CACC` |
| type_of_customer: New / Existing / Unknown | `#00C18B` / `#007E91` / `#A7A8AB` |
| invoice_status: Paid / Unpaid / Payment Pending / Collections / Cancelled / Refunded / Draft | `#00C1DE` / `#F2A900` / `#F7CB66` / `#B37D00` / `#E5484D` / `#A7A8AB` / `#C9CACC` |
| signup_agent: Online / Agent / App Sale | `#00C1DE` / `#55565A` / `#00C18B` |
| service_status: Active / Pending / Suspended / Cancelled / Terminated / Expired / Transferred Away / Fraud / Completed | `#00C1DE` / `#F2A900` / `#55565A` / `#E5484D` / `#B23A3E` / `#A7A8AB` / `#B3ECF5` / `#231F20` / `#00C18B` |

### 3.2 Type
Segoe UI stack throughout.
- Page title: Segoe UI Semibold 18 pt, "Daily Sales" in cyan + "· Page" in black.
- Subtitle: Segoe UI 10 pt grey.
- Visual titles: Segoe UI Semibold 12 pt black, left-aligned, **one line, phrased as a question**.
- KPI label: Semibold 10 pt grey. KPI value: Semibold 24 pt black. KPI caption: 10 pt, coloured by measure.
- Axis/data labels: 9 pt grey. Tables: 10 pt (headers 9 pt Semibold grey).

### 3.3 Spacing & grid (canvas 1500 × 900, Fit to page)

| Zone | x | y | w | h |
|---|---|---|---|---|
| Header band (white, bottom border) | 0 | 0 | 1500 | 64 |
| Title / subtitle | 24 | 8 / 38 | 760 | 28 / 20 |
| Period + "Data to …" text (right-aligned) | 800 | 10 | 540 | 44 |
| Logo | 1366 | 12 | 110 | 40 |
| Filter rail (card) | 16 | 80 | 224 | 804 |
| KPI row: 6 cards, 10 px gaps | 256 → 1484 | 80 | 196 each | 100 |
| Insight / note line | 256 | 188 | 1228 | 30 |
| Chart row 1 | 256 | 226 | — | 323 |
| Chart row 2 | 256 | 561 | — | 323 |

Column splits (12 px gutters): **808 + 408** (main + side) or **604 + 612** (halves), or thirds of row 2 (400 / 404 / 400).

### 3.4 Card spec (every chart, table and KPI)
White background (0 % transparency), **1 px border `#E3E5E8`, radius 8**, **no shadow**, padding 12 top / 8 bottom / 14 sides. Chart visuals: value axis **off** with **data labels on** (bars); axis titles off; gridlines dotted `#E3E5E8` (only where a value axis is shown: combo, weekly status); legend **top, no title**. KPI cards: no accent bar, labels hidden (the card title is the label).

### 3.5 Filter rail (same order on every page, all synced)

| # | Header | Field | Style | Sync group |
|---|---|---|---|---|
| 1 | Period | `Calendar[Date (format)]` | Relative date, default **Last 30 days (incl. today)** | Period |
| 2 | Category | `revenue_orders_tbl[Category]` | Dropdown, multi | Category |
| 3 | Sub category | `revenue_orders_tbl[Sub Category]` | Dropdown | Sub category |
| 4 | Product | `revenue_orders_tbl[Product Name]` | Dropdown | Product |
| 5 | Customer type | `revenue_orders_tbl[type_of_customer]` | Dropdown | Customer type |
| 6 | Account age | `revenue_orders_tbl[customer_tenure_group]` | Dropdown | Account age |
| 7 | Sales channel | `revenue_orders_tbl[Sales Channel]` | Dropdown | Sales channel |
| 8 | Domain region | `revenue_orders_tbl[Domain Region]` | Dropdown | Domain region |
| 9 | Province | `revenue_orders_tbl[client_state]` | Dropdown | Province |
| 10 | Billing cycle | `revenue_orders_tbl[billing_cycle]` | Dropdown | Billing cycle |
| 11 | Payment method | `revenue_orders_tbl[invoice_paymethod]` | Dropdown | Payment method |
| 12 | Heard about us | `revenue_orders_tbl[heard_about_us]` | Dropdown | Heard about us |

Slicer geometry: x 28, w 200; Period h 58, others h 52, 6 px apart starting y 124. *Clear all* button (ClearAllSlicers action) at x 136 y 88, 92 × 26. Footnote at the bottom of the rail: "Values excl. VAT. Paid revenue lands on the payment date; unpaid and cancelled on the order date."
Selection-pane names: each slicer's title text = its header (fixes the "all named Date" issue).
**Removed from the rail:** Client ID, Order ID, Invoice ID, Domain, IP Address, Company, Client Group, Country, Service Status. ID/IP fields are high-cardinality, not dropdown material. Look up a specific order with the Filters pane, or the Collections chase table. Country is ~all ZA (use Province). Client Group and Service Status can be added back as a 13th slicer if the team uses them.

### 3.6 Theme JSON changes (applied to `1-grid_Brand…json` in the copy)

Added to `visualStyles["*"]["*"]` and the page background:

```json
{
  "visualStyles": {
    "*": { "*": {
      "background":  [{ "show": true, "color": { "solid": { "color": "#FFFFFF" } }, "transparency": 0 }],
      "border":      [{ "show": true, "color": { "solid": { "color": "#E3E5E8" } }, "radius": 8, "width": 1 }],
      "dropShadow":  [{ "show": false }],
      "title":       [{ "show": true, "fontColor": { "solid": { "color": "#231F20" } }, "fontSize": 12,
                        "fontFamily": "'Segoe UI Semibold', wf_segoe-ui_semibold, helvetica, arial, sans-serif", "alignment": "left" }],
      "padding":     [{ "top": 12, "bottom": 8, "left": 14, "right": 14 }],
      "legend":      [{ "show": true, "position": "Top", "showTitle": false, "labelColor": { "solid": { "color": "#55565A" } }, "fontSize": 9 }],
      "categoryAxis":[{ "showAxisTitle": false, "gridlineShow": false }],
      "valueAxis":   [{ "showAxisTitle": false, "gridlineStyle": "dotted", "gridlineColor": { "solid": { "color": "#E3E5E8" } } }]
    } },
    "page": { "*": { "background": [{ "color": { "solid": { "color": "#F4F6F8" } }, "transparency": 0 }] } }
  }
}
```
(The existing visualHeader and visualTooltip entries and per-visual-type styles are kept.)

---

## 4. Page-by-page build

### 4.0 Common to every main page
- **Frame** as in §3.3 – §3.5.
- **KPI row** (6 new-card visuals, one measure + one caption each, title = label):

| # | Title | Value (format) | Caption (2nd data field) | Caption colour (fx → field value) | x |
|---|---|---|---|---|---|
| 1 | Paid revenue | `[Paid Revenue (Products)]`, display units K, 1 dp | `[KPI Revenue Δ]` | `[KPI Revenue Δ Colour]` | 256 |
| 2 | Paid orders | `[Paid Orders (Products)]` | `[KPI Orders Δ]` | `[KPI Orders Δ Colour]` | 462 |
| 3 | Average order value | `[Average Order Value]` | `[KPI AOV Δ]` | `[KPI AOV Δ Colour]` | 668 |
| 4 | New-customer share | `[New Customer Share]` | `[KPI New Share Δ]` | `[KPI New Share Δ Colour]` | 875 |
| 5 | Unpaid (collectable) | `[Open Unpaid Revenue]`, K | `[KPI Unpaid Caption]` | grey | 1081 |
| 6 | Cancelled (lost) | `[Cancelled Revenue]`, K | `[KPI Cancelled Caption]` | grey | 1287 |

  y 80, w 196, h 100. **No visual-level filters on the cards.** The old Paid card's `invoice_status = Paid` filters on both tables were redundant: the measures already filter Paid. The orders_invoices_tbl filter was the likely cause of the "category bars R532K vs card R518.6K" gap (§11).
- **Header right text:** a new card (no frame, 2 columns, right-aligned, 10 pt grey) with `[Period Label]` and `[Data As Of]`.
- **No page-level filters.** Removed: duplicate `invoice_total > 0` (both tables) and the empty `Status_Group` filter. The measures already exclude R0 orders and non-paid rows, so totals are unchanged and category charts now reconcile to the cards.
- **Report-level filters kept:** Calendar[Year] (all) and Calendar[Date (format)] in the last 4 years.
- Drill-through bindings on the main pages removed (they made every page a drill-through target). The Guide drill-through is kept.

### 4.1 Positions, fields and filters per visual
Tables generated from the built report. Titles are exactly as set.


#### Overview — 1500×900

| Visual | Type | x | y | w | h | Fields | Visual filters | Tooltip |
|---|---|---|---|---|---|---|---|---|
| Insight | cardVisual | 256 | 188 | 1228 | 30 | Data: [Overview Insight] (report measure) as "Insight" | — | — |
| How did paid revenue move day by day? Paid revenue (bars) and paid orders (line) | lineClusteredColumnComboChart | 256 | 226 | 808 | 323 | Category: Calendar[Date (format)]<br>Y: [Paid Revenue (Products)] as "Paid revenue"<br>Y2: [Paid Orders (Products)] as "Paid orders" | — | TT - Period |
| Which categories earn the revenue? | clusteredBarChart | 1076 | 226 | 408 | 323 | Category: revenue_orders_tbl[Category]<br>Y: [Paid Revenue (Products)] as "Paid revenue" | — | TT - Category |
| Are we ahead of last year? Monthly paid revenue, last 13 months | lineClusteredColumnComboChart | 256 | 561 | 604 | 323 | Category: Calendar[MonthYear]<br>Y: [Paid Revenue (Products)] as "Paid revenue"<br>Y2: [Paid Revenue LY] (report measure) as "Same month last year" | Date (format): relative (see notes) | — |
| Which 5 products earn the most? | clusteredBarChart | 872 | 561 | 300 | 323 | Category: revenue_orders_tbl[Product Name]<br>Y: [Paid Revenue (Products)] as "Paid revenue" | Top 5 Product Name | TT - Category |
| How much comes from new customers? | donutChart | 1184 | 561 | 300 | 323 | Category: revenue_orders_tbl[type_of_customer]<br>Y: [Paid Revenue (Products)] as "Paid revenue" | — | TT - Category |

#### Daily Sales — 1500×900

| Visual | Type | x | y | w | h | Fields | Visual filters | Tooltip |
|---|---|---|---|---|---|---|---|---|
| What sold each day? Paid sales, domains and collection by day | pivotTable | 256 | 226 | 796 | 658 | Rows: Calendar[Date (format)]<br>Values: [Paid Revenue (Products)] as "Paid revenue", [Paid Orders (Products)] as "Paid orders", [Average Order Value] (report measure) as "AOV", [New Customer Share] (report measure) as "New-customer %", [App Sales Revenue] (report measure) as "App sales", [Local Domain Revenue] (report measure) as "Local domains R", [International Domain Revenue] (report measure) as "Int. domains R", [Local Domains Added] (report measure) as "Local domains #", [International Domains Added] (report measure) as "Int. domains #", [Invoiced Value] (report measure) as "Invoiced (all)", [Paid Share of Invoiced] (report measure) as "% paid" | — | TT - Period |
| What sold on the selected days? Paid revenue by sub category | clusteredBarChart | 1064 | 226 | 420 | 323 | Category: revenue_orders_tbl[Sub Category]<br>Y: [Paid Revenue (Products)] as "Paid revenue" | — | TT - Category |
| Which weekdays sell best? | clusteredColumnChart | 1064 | 561 | 420 | 323 | Category: Calendar[Weekday]<br>Y: [Paid Revenue (Products)] as "Paid revenue" | — | TT - Period |

#### Products — 1500×900

| Visual | Type | x | y | w | h | Fields | Visual filters | Tooltip |
|---|---|---|---|---|---|---|---|---|
| Which products earn the revenue? Category › sub category › product | pivotTable | 256 | 226 | 808 | 658 | Rows: revenue_orders_tbl[Category], revenue_orders_tbl[Sub Category], revenue_orders_tbl[Product Name]<br>Values: [Paid Revenue (Products)] as "Paid revenue", [Revenue % of Total] (report measure) as "% of total", [Paid Orders (Products)] as "Paid orders", [Average Order Value] (report measure) as "AOV", [Paid Revenue Δ%] (report measure) as "vs prior period" | — | Revenue Tooltip |
| Are local domains holding up? Paid domain registrations | cardVisual | 1076 | 226 | 408 | 150 | Data: [Local Domain Revenue] (report measure) as "Local domains (R)", [International Domain Revenue] (report measure) as "International (R)", [Local Domains Added] (report measure) as "Local domains added", [International Domains Added] (report measure) as "Int. domains added" | — | — |
| Which extensions sell? Top 8 TLDs by paid revenue | clusteredBarChart | 1076 | 388 | 408 | 161 | Category: revenue_orders_tbl[TLD]<br>Y: [Paid Revenue (Products)] as "Paid revenue" | Top 8 TLD; Sub Category in 'Domains' | TT - Category |
| Are services sold this period still active? Status today | hundredPercentStackedBarChart | 1076 | 561 | 408 | 323 | Category: revenue_orders_tbl[Category]<br>Y: [Services Sold] (report measure) as "Services sold"<br>Series: revenue_orders_tbl[service_status] | — | TT - Category |

#### Customers & Channels — 1500×900

| Visual | Type | x | y | w | h | Fields | Visual filters | Tooltip |
|---|---|---|---|---|---|---|---|---|
| Is the new-customer share growing? Weekly paid revenue by customer type | hundredPercentStackedColumnChart | 256 | 226 | 604 | 323 | Category: Calendar[WeekDate]<br>Y: [Paid Revenue (Products)] as "Paid revenue"<br>Series: revenue_orders_tbl[type_of_customer] | — | TT - Period |
| What do new and existing customers buy? | clusteredBarChart | 872 | 226 | 612 | 323 | Category: revenue_orders_tbl[Category]<br>Y: [Paid Revenue (Products)] as "Paid revenue"<br>Series: revenue_orders_tbl[type_of_customer] | — | TT - Category |
| How long have buyers been with us? Paid revenue by account age | clusteredBarChart | 256 | 561 | 400 | 323 | Category: revenue_orders_tbl[customer_tenure_group]<br>Y: [Paid Revenue (Products)] as "Paid revenue"<br>Tooltips: Min(customer_tenure_sort) as "Sort" | — | TT - Category |
| How much comes through the app or an agent? | clusteredBarChart | 668 | 561 | 404 | 323 | Category: revenue_orders_tbl[signup_agent]<br>Y: [Paid Revenue (Products)] as "Paid revenue" | — | TT - Category |
| Which marketing sources bring revenue? Top 8 | clusteredBarChart | 1084 | 561 | 400 | 323 | Category: revenue_orders_tbl[heard_about_us]<br>Y: [Paid Revenue (Products)] as "Paid revenue" | Top 8 heard_about_us | TT - Category |

#### Collections — 1500×900

| Visual | Type | x | y | w | h | Fields | Visual filters | Tooltip |
|---|---|---|---|---|---|---|---|---|
| Is invoiced value being collected? Weekly invoice value by status | columnChart | 256 | 226 | 808 | 323 | Category: Calendar[WeekDate]<br>Y: [RO Invoice Total] as "Invoice value"<br>Series: revenue_orders_tbl[invoice_status] | — | TT - Period |
| Which payment methods collect best? % of invoiced value paid | clusteredBarChart | 1076 | 226 | 408 | 323 | Category: revenue_orders_tbl[invoice_paymethod]<br>Y: [Paid Share of Invoiced] (report measure) as "% paid"<br>Tooltips: [Invoiced Value] (report measure) as "Invoiced", [Open Unpaid Revenue] (report measure) as "Unpaid" | — | TT - Category |
| Where is value stuck? Unpaid and cancelled by category | clusteredBarChart | 256 | 561 | 604 | 323 | Category: revenue_orders_tbl[Category]<br>Y: [Open Unpaid Revenue] (report measure) as "Unpaid (collectable)", [Cancelled Revenue] (report measure) as "Cancelled (lost)" | — | TT - Category |
| Which invoices should we chase? Top 50 open invoices | tableEx | 872 | 561 | 612 | 323 | Values: revenue_orders_tbl[order_id] as "Order", revenue_orders_tbl[invoice_id] as "Invoice", revenue_orders_tbl[invoice_date] as "Invoiced", revenue_orders_tbl[invoice_duedate] as "Due", revenue_orders_tbl[invoice_paymethod] as "Method", revenue_orders_tbl[invoice_status] as "Status", [Open Unpaid Revenue] (report measure) as "Unpaid (R)" | Top 50 order_id; Status_Filter in 'Unpaid', 'Payment Pending', 'Collections', 'Draft' | — |

#### TT - Category — 480×300 (hidden tooltip page)

| Visual | Type | x | y | w | h | Fields | Visual filters | Tooltip |
|---|---|---|---|---|---|---|---|---|
| Top products here | clusteredBarChart | 8 | 92 | 464 | 200 | Category: revenue_orders_tbl[Product Name]<br>Y: [Paid Revenue (Products)] as "Paid revenue" | Top 5 Product Name | — |

#### TT - Period — 480×330 (hidden tooltip page)

| Visual | Type | x | y | w | h | Fields | Visual filters | Tooltip |
|---|---|---|---|---|---|---|---|---|
| Paid revenue by category | clusteredBarChart | 8 | 92 | 464 | 230 | Category: revenue_orders_tbl[Category]<br>Y: [Paid Revenue (Products)] as "Paid revenue" | — | — |

#### Revenue Tooltip — 480×320 (hidden tooltip page)

| Visual | Type | x | y | w | h | Fields | Visual filters | Tooltip |
|---|---|---|---|---|---|---|---|---|
| Products in this selection | pivotTable | 8 | 8 | 464 | 304 | Rows: revenue_orders_tbl[Sub Category], revenue_orders_tbl[Product Name]<br>Values: [Paid Revenue (Products)] as "Paid revenue", [Paid Orders (Products)] as "Paid orders", [Revenue % of Total] (report measure) as "% of total" | — | — |

#### _Frame template — 1500×900 (hidden)

| Visual | Type | x | y | w | h | Fields | Visual filters | Tooltip |
|---|---|---|---|---|---|---|---|---|


### 4.2 Per-page formatting and behaviour notes

**Overview**
- Insight line: new card, `[Overview Insight]`, 11 pt black, left-aligned, no frame. It follows the pattern *"Paid revenue R ‹x› from ‹n› orders (▲/▼ ‹y›% vs prior period). ‹Top category› brought ‹z›% of it; new customers ‹w›%; app sales ‹v›%."*
- Daily combo: columns cyan (paid revenue), line grey with small markers (paid orders), secondary axis on, value axis on with dotted gridlines, display units K, legend top.
- Category bar: sorted by revenue desc, category colours, data labels in K, value axis off.
- Monthly combo: x = `Calendar[MonthYear]` (sorts chronologically by CurMonthOffset). Columns = paid revenue (cyan), line = `[Paid Revenue LY]` (amber). Visual filter `Calendar[Date (format)]` *is in the last 13 months* (relative, incl. today). **Edit interactions: Period slicer → this visual = None**, so the trend always shows 13 months. Category and the other slicers still apply.
- Top 5 products: Top N 5 by `[Paid Revenue (Products)]`, cyan, labels.
- New vs existing donut: inner radius 62 %, labels = % of total, customer colours.

**Daily Sales**
- Matrix rows `Calendar[Date (format)]`, **sorted by date descending** (latest day on top). 11 value columns as listed, headers word-wrapped, grid horizontal lines only, data bars (`#B3ECF5`) on Paid revenue, total row shaded `#E6F8FB`.
  Formats: R columns `R #,0`; AOV `R #,0`; % columns `0.0%`; counts `#,0`.
- Selecting a day (or several with Ctrl) cross-filters the two side charts.
- Sub-category bar: sorted desc. Weekday column chart: sorted Sun → Sat (Weekday sorts by WeekdayNum), labels in K.

**Products**
- Matrix rows Category › Sub Category › Product Name (stepped layout, +/- buttons, subtotals on). Values: Paid revenue (data bars), % of total, Paid orders, AOV, vs prior period (`0.0%`). Optional: conditional font colour on *vs prior period* (rules: < 0 red `#E5484D`, ≥ 0 dark green `#00845F`). Tooltip: Revenue Tooltip.
- Domain block: new card, 2 × 2 grid: Local domains (R) [cyan], International (R) [grey], Local domains added, Int. domains added.
- TLD bar: visual filters Sub Category = Domains and Top 8 TLD by paid revenue.
- Service-status bar: 100 % stacked, Category × `service_status` using `[Services Sold]`; data labels off; legend top; service-status colours.

**Customers & Channels**
- Weekly 100 % stacked columns: WeekDate × type_of_customer, customer colours, labels off.
- Category × customer type clustered bar: customer colours, labels in K.
- Account age bar: **sort ascending by Min(customer_tenure_sort)**. Put `customer_tenure_sort` in Tooltips as *Minimum*, then Sort axis › Min of customer_tenure_sort › Ascending. The model has no sort-by-column on `customer_tenure_group`.
- Channel bar: `signup_agent` (Online / Agent / App Sale) with channel colours.
- Heard-about-us: Top 8 by paid revenue.

**Collections**
- Weekly status: stacked columns `[RO Invoice Total]` by WeekDate × invoice_status, status colours, value axis on (K), labels off. This view is by **order week**: the value invoiced that week and its status today.
- Payment method: `[Paid Share of Invoiced]` (0.0 %), sorted desc; tooltips add Invoiced and Unpaid.
- Unpaid vs cancelled by category: two measures, amber and red, labels in K.
- Chase table: columns Order, Invoice, Invoiced, Due, Method, Status, Unpaid (R). Visual filters: `Status_Filter` in {Unpaid, Payment Pending, Collections, Draft}, and Top 50 order_id by `[Unpaid Revenue (Products)]`. Sorted by Unpaid desc, totals on.

### 4.3 Tooltip mapping

| Visual kind | Tooltip page |
|---|---|
| Category, product, TLD, customer, channel, source, status-by-category, payment-method charts | **TT - Category** (480 × 300): new card with Paid revenue (K), Paid orders, AOV, Unpaid (amber, K) + Top 5 products bar |
| Time-axis charts (daily combo, weekday, weekly share, weekly status) and the Daily Sales matrix | **TT - Period** (renamed from TT - Week, 480 × 330): the same 4 KPIs + paid revenue by category (category colours) |
| Products matrix | **Revenue Tooltip** (480 × 320): matrix Sub Category › Product with `[Paid Revenue (Products)]`, `[Paid Orders (Products)]`, `[Revenue % of Total]`. **Fixed:** it used `Sum(invoice_total)` and `Count(order_id)` (implicit, incl. VAT, repeated per row) and pointed its own tooltip at Guide. |
| Overview monthly trend, KPI cards, text lines, chase table | Default tooltip |

All tooltip pages: Page type Tooltip, white background, hidden in view mode. Visuals use "Report page" tooltip type with "Show tooltip fields only" off.

### 4.4 Interactions
- Default cross-filtering everywhere.
- Overview: Period slicer → *Monthly paid revenue* = **None**.
- KPI cards receive cross-filters (selecting a category bar updates the cards). That is intended, because every KPI uses revenue_orders_tbl measures.

---

## 5. Report-level measures (table: revenue_orders_tbl, stored in the report)

Created as report measures on `revenue_orders_tbl` (PBIR: `Report/definition/reportExtensions.json`). They don't change the shared model. Display folders: Headline, Time, KPI text, Customers, Collections, Channels, Domains, Products, Labels.

### 5.1 Key definitions and choices
- **Unpaid vs cancelled split** filters `Status_Filter`, not `invoice_status`. `[Unpaid Revenue (Products)]` already applies `invoice_status <> "Paid"` inside CALCULATE, which *overrides* any outer filter on `invoice_status`. A visual filter on invoice_status = Cancelled would be silently ignored. `Status_Filter` is a different column with the same values (blank → "Unpaid"), so KEEPFILTERS on it works.
- **Prior period** = the same number of days immediately before the selected range: Last 30 days → the 30 days before.
- **Paid share of invoiced** is cohort-based: of the value invoiced for orders placed in the period, how much is paid now. This matches the Excel *Paid tracker*. Paid revenue (cards) is on paid date, so the two answer different questions; both are labelled.
- **Domains added** counts distinct `service_id` in Sub Category *Domains* on **paid** orders, by paid date.

### 5.2 DAX

**Average Order Value** · folder *Headline* · Double · format `"R"\ #,0;"R"\ -#,0;"R"\ #,0`  
Paid revenue excl. VAT ÷ paid orders (paid date).

```dax
Average Order Value =
DIVIDE ( [Paid Revenue (Products)], [Paid Orders (Products)] )
```

**Paid Revenue PP** · folder *Time* · Double · format `"R"\ #,0;"R"\ -#,0;"R"\ #,0`  
Paid revenue for the prior period of equal length immediately before the selected dates.

```dax
Paid Revenue PP =
VAR _first = MIN ( 'Calendar'[Date (format)] )
VAR _last = MAX ( 'Calendar'[Date (format)] )
VAR _days = INT ( _last - _first ) + 1
RETURN
    CALCULATE (
        [Paid Revenue (Products)],
        REMOVEFILTERS ( 'Calendar' ),
        FILTER (
            ALL ( 'Calendar'[Date (format)] ),
            'Calendar'[Date (format)] >= _first - _days
                && 'Calendar'[Date (format)] <= _first - 1
        )
    )
```

**Paid Orders PP** · folder *Time* · Double · format `0`  
Paid orders, prior period of equal length.

```dax
Paid Orders PP =
VAR _first = MIN ( 'Calendar'[Date (format)] )
VAR _last = MAX ( 'Calendar'[Date (format)] )
VAR _days = INT ( _last - _first ) + 1
RETURN
    CALCULATE (
        [Paid Orders (Products)],
        REMOVEFILTERS ( 'Calendar' ),
        FILTER (
            ALL ( 'Calendar'[Date (format)] ),
            'Calendar'[Date (format)] >= _first - _days
                && 'Calendar'[Date (format)] <= _first - 1
        )
    )
```

**Average Order Value PP** · folder *Time* · Double · format `"R"\ #,0;"R"\ -#,0;"R"\ #,0`  
AOV for the prior period of equal length.

```dax
Average Order Value PP =
DIVIDE ( [Paid Revenue PP], [Paid Orders PP] )
```

**Paid Revenue Δ%** · folder *Time* · Double · format `0.0%;-0.0%;0.0%`  
Change in paid revenue vs the prior period of equal length.

```dax
Paid Revenue Δ% =
VAR _p = [Paid Revenue PP] RETURN IF ( NOT ISBLANK ( _p ), DIVIDE ( [Paid Revenue (Products)] - _p, _p ) )
```

**Paid Revenue LY** · folder *Time* · Double · format `"R"\ #,0;"R"\ -#,0;"R"\ #,0`  
Paid revenue for the same dates one year earlier. Blank before Jul 2026 (orders data starts Jul 2025).

```dax
Paid Revenue LY =
VAR _first = MIN ( 'Calendar'[Date (format)] )
VAR _last = MAX ( 'Calendar'[Date (format)] )
VAR _days = INT ( _last - _first ) + 1
RETURN
    CALCULATE (
        [Paid Revenue (Products)],
        REMOVEFILTERS ( 'Calendar' ),
        FILTER (
            ALL ( 'Calendar'[Date (format)] ),
            'Calendar'[Date (format)] >= EDATE ( _first, -12 )
                && 'Calendar'[Date (format)] <= EDATE ( _last, -12 )
        )
    )
```

**KPI Revenue Δ** · folder *KPI text* · Text  
Card caption.

```dax
KPI Revenue Δ =
VAR _c = [Paid Revenue (Products)]
VAR _p = [Paid Revenue PP]
VAR _first = MIN ( 'Calendar'[Date (format)] )
VAR _last = MAX ( 'Calendar'[Date (format)] )
VAR _days = INT ( _last - _first ) + 1
RETURN
    IF (
        ISBLANK ( _p ) || _p = 0,
        "No prior-period data",
        VAR _d = DIVIDE ( _c - _p, _p )
        RETURN IF ( _d >= 0, "▲ ", "▼ " ) & FORMAT ( ABS ( _d ), "0.0%" ) & " vs prior " & _days & " days"
    )
```

**KPI Orders Δ** · folder *KPI text* · Text  
Card caption.

```dax
KPI Orders Δ =
VAR _c = [Paid Orders (Products)]
VAR _p = [Paid Orders PP]
VAR _first = MIN ( 'Calendar'[Date (format)] )
VAR _last = MAX ( 'Calendar'[Date (format)] )
VAR _days = INT ( _last - _first ) + 1
RETURN
    IF (
        ISBLANK ( _p ) || _p = 0,
        "No prior-period data",
        VAR _d = DIVIDE ( _c - _p, _p )
        RETURN IF ( _d >= 0, "▲ ", "▼ " ) & FORMAT ( ABS ( _d ), "0.0%" ) & " vs prior " & _days & " days"
    )
```

**KPI AOV Δ** · folder *KPI text* · Text  
Card caption.

```dax
KPI AOV Δ =
VAR _c = [Average Order Value]
VAR _p = [Average Order Value PP]
VAR _first = MIN ( 'Calendar'[Date (format)] )
VAR _last = MAX ( 'Calendar'[Date (format)] )
VAR _days = INT ( _last - _first ) + 1
RETURN
    IF (
        ISBLANK ( _p ) || _p = 0,
        "No prior-period data",
        VAR _d = DIVIDE ( _c - _p, _p )
        RETURN IF ( _d >= 0, "▲ ", "▼ " ) & FORMAT ( ABS ( _d ), "0.0%" ) & " vs prior " & _days & " days"
    )
```

**KPI Revenue Δ Colour** · folder *KPI text* · Text  
Green up / red down.

```dax
KPI Revenue Δ Colour =
VAR _c = [Paid Revenue (Products)]
VAR _p = [Paid Revenue PP]
RETURN IF ( ISBLANK ( _p ) || _c >= _p, "#00845F", "#E5484D" )
```

**KPI Orders Δ Colour** · folder *KPI text* · Text  
Green up / red down.

```dax
KPI Orders Δ Colour =
VAR _c = [Paid Orders (Products)]
VAR _p = [Paid Orders PP]
RETURN IF ( ISBLANK ( _p ) || _c >= _p, "#00845F", "#E5484D" )
```

**KPI AOV Δ Colour** · folder *KPI text* · Text  
Green up / red down.

```dax
KPI AOV Δ Colour =
VAR _c = [Average Order Value]
VAR _p = [Average Order Value PP]
RETURN IF ( ISBLANK ( _p ) || _c >= _p, "#00845F", "#E5484D" )
```

**New Customer Revenue** · folder *Customers* · Double · format `"R"\ #,0;"R"\ -#,0;"R"\ #,0`  
Paid revenue from clients who signed up on the order day.

```dax
New Customer Revenue =
CALCULATE ( [Paid Revenue (Products)], KEEPFILTERS ( revenue_orders_tbl[type_of_customer] = "New Customer" ) )
```

**New Customer Share** · folder *Customers* · Double · format `0.0%;-0.0%;0.0%`  
Share of paid revenue from new customers (Excel: New Revenue %).

```dax
New Customer Share =
DIVIDE ( [New Customer Revenue], [Paid Revenue (Products)] )
```

**New Customer Share PP** · folder *Customers* · Double · format `0.0%;-0.0%;0.0%`  
New-customer share, prior period of equal length.

```dax
New Customer Share PP =
VAR _first = MIN ( 'Calendar'[Date (format)] )
VAR _last = MAX ( 'Calendar'[Date (format)] )
VAR _days = INT ( _last - _first ) + 1
RETURN
    CALCULATE (
        DIVIDE ( [New Customer Revenue], [Paid Revenue (Products)] ),
        REMOVEFILTERS ( 'Calendar' ),
        FILTER (
            ALL ( 'Calendar'[Date (format)] ),
            'Calendar'[Date (format)] >= _first - _days
                && 'Calendar'[Date (format)] <= _first - 1
        )
    )
```

**KPI New Share Δ** · folder *KPI text* · Text  
Card caption.

```dax
KPI New Share Δ =
VAR _c = [New Customer Share]
VAR _p = [New Customer Share PP]
VAR _d = ( _c - _p ) * 100
VAR _first = MIN ( 'Calendar'[Date (format)] )
VAR _last = MAX ( 'Calendar'[Date (format)] )
VAR _days = INT ( _last - _first ) + 1
RETURN
    IF (
        ISBLANK ( _p ) || ISBLANK ( _c ),
        "No prior-period data",
        IF ( _d >= 0, "▲ ", "▼ " ) & FORMAT ( ABS ( _d ), "0.0" ) & " pts vs prior " & _days & " days"
    )
```

**KPI New Share Δ Colour** · folder *KPI text* · Text  
Green up / red down.

```dax
KPI New Share Δ Colour =
VAR _c = [New Customer Share]
VAR _p = [New Customer Share PP]
RETURN IF ( ISBLANK ( _p ) || _c >= _p, "#00845F", "#E5484D" )
```

**Open Unpaid Revenue** · folder *Collections* · Double · format `"R"\ #,0;"R"\ -#,0;"R"\ #,0`  
Invoice value excl. VAT still collectable (Unpaid, Payment Pending, Collections, Draft), by order date. Filters Status_Filter because the base measure overrides invoice_status.

```dax
Open Unpaid Revenue =
CALCULATE ( [Unpaid Revenue (Products)], KEEPFILTERS ( revenue_orders_tbl[Status_Filter] IN { "Unpaid", "Payment Pending", "Collections", "Draft" } ) )
```

**Open Unpaid Orders** · folder *Collections* · Double · format `0`  
Orders whose invoice is still collectable.

```dax
Open Unpaid Orders =
CALCULATE ( [Unpaid Orders (Products)], KEEPFILTERS ( revenue_orders_tbl[Status_Filter] IN { "Unpaid", "Payment Pending", "Collections", "Draft" } ) )
```

**Cancelled Revenue** · folder *Collections* · Double · format `"R"\ #,0;"R"\ -#,0;"R"\ #,0`  
Invoice value excl. VAT on cancelled invoices (lost), by order date.

```dax
Cancelled Revenue =
CALCULATE ( [Unpaid Revenue (Products)], KEEPFILTERS ( revenue_orders_tbl[Status_Filter] = "Cancelled" ) )
```

**Cancelled Orders** · folder *Collections* · Double · format `0`  
Orders whose invoice was cancelled.

```dax
Cancelled Orders =
CALCULATE ( [Unpaid Orders (Products)], KEEPFILTERS ( revenue_orders_tbl[Status_Filter] = "Cancelled" ) )
```

**KPI Unpaid Caption** · folder *KPI text* · Text  
Card caption.

```dax
KPI Unpaid Caption =
VAR _n = [Open Unpaid Orders] RETURN IF ( ISBLANK ( _n ), "No open invoices", FORMAT ( _n, "#,0" ) & " orders awaiting payment" )
```

**KPI Cancelled Caption** · folder *KPI text* · Text  
Card caption.

```dax
KPI Cancelled Caption =
VAR _n = [Cancelled Orders] RETURN IF ( ISBLANK ( _n ), "No cancelled invoices", FORMAT ( _n, "#,0" ) & " orders cancelled" )
```

**Invoiced Value** · folder *Collections* · Double · format `"R"\ #,0;"R"\ -#,0;"R"\ #,0`  
All invoices excl. VAT, each once, by order date (Excel: 'Power BI new revenue').

```dax
Invoiced Value =
[RO Invoice Total]
```

**Paid Share of Invoiced** · folder *Collections* · Double · format `0.0%;-0.0%;0.0%`  
Share of invoiced value (orders placed in the period) that is paid. Excel: Paid tracker '% Paid'.

```dax
Paid Share of Invoiced =
DIVIDE ( CALCULATE ( [RO Invoice Total], revenue_orders_tbl[invoice_status] = "Paid" ), [RO Invoice Total] )
```

**App Sales Revenue** · folder *Channels* · Double · format `"R"\ #,0;"R"\ -#,0;"R"\ #,0`  
Paid revenue from app sales (signup_agent = App Sale).

```dax
App Sales Revenue =
CALCULATE ( [Paid Revenue (Products)], KEEPFILTERS ( revenue_orders_tbl[Sales Channel] = "App" ) )
```

**App Sales Share** · folder *Channels* · Double · format `0.0%;-0.0%;0.0%`  
Share of paid revenue from app sales.

```dax
App Sales Share =
DIVIDE ( [App Sales Revenue], [Paid Revenue (Products)] )
```

**Local Domain Revenue** · folder *Domains* · Double · format `"R"\ #,0;"R"\ -#,0;"R"\ #,0`  
Paid domain-registration revenue for local TLDs (.co.za, .africa …).

```dax
Local Domain Revenue =
CALCULATE ( [Paid Revenue (Products)], KEEPFILTERS ( revenue_orders_tbl[Sub Category] = "Domains" ), KEEPFILTERS ( revenue_orders_tbl[Domain Region] = "Local" ) )
```

**International Domain Revenue** · folder *Domains* · Double · format `"R"\ #,0;"R"\ -#,0;"R"\ #,0`  
Paid domain-registration revenue for international TLDs.

```dax
International Domain Revenue =
CALCULATE ( [Paid Revenue (Products)], KEEPFILTERS ( revenue_orders_tbl[Sub Category] = "Domains" ), KEEPFILTERS ( revenue_orders_tbl[Domain Region] = "International" ) )
```

**Domains Added** · folder *Domains* · Double · format `#,0`  
Domain registrations/transfers on paid orders, by paid date.

```dax
Domains Added =
VAR _dates = VALUES ( 'Calendar'[Date (format)] )
RETURN
    CALCULATE (
        DISTINCTCOUNT ( revenue_orders_tbl[service_id] ),
        revenue_orders_tbl[invoice_status] = "Paid",
        KEEPFILTERS ( revenue_orders_tbl[Sub Category] = "Domains" ),
        REMOVEFILTERS ( 'Calendar' ),
        TREATAS ( _dates, revenue_orders_tbl[Revenue Date] )
    )
```

**Local Domains Added** · folder *Domains* · Double · format `#,0`  
Excel: No. of Local Domains Added (paid orders only).

```dax
Local Domains Added =
CALCULATE ( [Domains Added], KEEPFILTERS ( revenue_orders_tbl[Domain Region] = "Local" ) )
```

**International Domains Added** · folder *Domains* · Double · format `#,0`  
Excel: No. of Int. Domains Added (paid orders only).

```dax
International Domains Added =
CALCULATE ( [Domains Added], KEEPFILTERS ( revenue_orders_tbl[Domain Region] = "International" ) )
```

**Services Sold** · folder *Products* · Double · format `#,0`  
Services/domains on paid orders, by paid date. Split by service_status to see how many are still active.

```dax
Services Sold =
VAR _dates = VALUES ( 'Calendar'[Date (format)] )
RETURN
    CALCULATE (
        DISTINCTCOUNT ( revenue_orders_tbl[service_id] ),
        revenue_orders_tbl[invoice_status] = "Paid",
        REMOVEFILTERS ( 'Calendar' ),
        TREATAS ( _dates, revenue_orders_tbl[Revenue Date] )
    )
```

**Revenue % of Total** · folder *Products* · Double · format `0.0%;-0.0%;0.0%`  
Share of the selected total, for the product matrix.

```dax
Revenue % of Total =
DIVIDE (
    [Paid Revenue (Products)],
    CALCULATE (
        [Paid Revenue (Products)],
        ALLSELECTED ( revenue_orders_tbl[Category], revenue_orders_tbl[Sub Category], revenue_orders_tbl[Product Name] )
    )
)
```

**Period Label** · folder *Labels* · Text  
Selected period.

```dax
Period Label =
VAR _first = MIN ( 'Calendar'[Date (format)] )
VAR _last = MAX ( 'Calendar'[Date (format)] )
RETURN FORMAT ( _first, "d mmm yyyy" ) & " – " & FORMAT ( _last, "d mmm yyyy" )
```

**Data As Of** · folder *Labels* · Text  
Latest order date in the model.

```dax
Data As Of =
VAR _d = CALCULATE ( MAX ( orders_invoices_tbl[order_date] ), REMOVEFILTERS () )
RETURN "Data to " & FORMAT ( _d, "d mmm yyyy" ) & " · excl. VAT · revenue on paid date"
```

**Overview Insight** · folder *Labels* · Text  
One-sentence summary for the Overview page.

```dax
Overview Insight =
VAR _rev = [Paid Revenue (Products)]
VAR _ord = [Paid Orders (Products)]
VAR _d = [Paid Revenue Δ%]
VAR _top =
    TOPN ( 1, ADDCOLUMNS ( VALUES ( revenue_orders_tbl[Category] ), "@r", [Paid Revenue (Products)] ), [@r], DESC )
VAR _topName = MAXX ( _top, revenue_orders_tbl[Category] )
VAR _topShare = DIVIDE ( MAXX ( _top, [@r] ), _rev )
VAR _new = [New Customer Share]
RETURN
    IF (
        ISBLANK ( _rev ),
        "No paid sales in the selected period.",
        "Paid revenue R " & FORMAT ( _rev, "#,0" ) & " from " & FORMAT ( _ord, "#,0" ) & " orders"
            & IF ( ISBLANK ( _d ), "", " (" & IF ( _d >= 0, "▲ ", "▼ " ) & FORMAT ( ABS ( _d ), "0.0%" ) & " vs prior period)" )
            & ". " & _topName & " brought " & FORMAT ( _topShare, "0%" ) & " of it; new customers "
            & FORMAT ( _new, "0%" ) & "; app sales " & FORMAT ( [App Sales Share], "0%" ) & "."
    )
```

### 5.3 Visual-calculation alternatives
Use these if you'd rather not add report measures to a given chart. They work in charts and matrices, but not in the KPI cards. Field names refer to the visual's own fields.

| Purpose | Visual calculation |
|---|---|
| AOV in a matrix / table | `AOV = DIVIDE([Paid Revenue (Products)], [Paid Orders (Products)])` |
| % of total in a matrix | `% of total = DIVIDE([Paid Revenue (Products)], COLLAPSEALL([Paid Revenue (Products)], ROWS))` |
| Change vs previous row (day, week, month) | `vs previous = DIVIDE([Paid Revenue (Products)] - PREVIOUS([Paid Revenue (Products)]), PREVIOUS([Paid Revenue (Products)]))` |
| Month-to-date running total on a daily axis | `MTD = RUNNINGSUM([Paid Revenue (Products)], ROWS, HIGHESTPARENT)` with Month › Day on the axis |
| 7-day moving average on the daily combo | `7-day avg = MOVINGAVERAGE([Paid Revenue (Products)], 7)` |
| Paid share of invoiced | `% paid = DIVIDE([Paid revenue], [Invoiced])`, with both measures placed in the visual |

---

## 6. Known report issues (documentation §11): fixes

| Issue | Fix in the redesign copy |
|---|---|
| Revenue Tooltip matrix uses implicit `Sum(invoice_total)` / `Count(order_id)` (incl. VAT, repeated per service row) | Rebuilt with `[Paid Revenue (Products)]`, `[Paid Orders (Products)]`, `[Revenue % of Total]`; its self-tooltip to Guide removed |
| Relative date slicer header text "Product Category" | One Period slicer, header "Period" |
| "Billling Cycle" typo, duplicate Billing / Client Group / Sales Channel slicers | One slicer per field, fixed order (§3.5) |
| All slicers named "Date" in the Selection pane | Each slicer's title = its header |
| Duplicate page filter `invoice_total > 0` (both tables) + empty `Status_Group` filter | Removed. The measures already exclude R0 and unpaid rows. |
| Empty Data_Exploration matrix | Page not carried into the redesign; the Daily Sales matrix replaces it |
| Date slicers not synced; all default *Last 1 Days* | Every rail slicer is in a sync group; Period defaults to *Last 30 days* |
| Inconsistent tooltip pages | Mapping in §4.3; TT - Week renamed TT - Period (used for days, weeks and months) |
| Invoice-status colours drift after theme changes | Colours pinned per value on each visual (§3.1) |
| Unpaid & Cancelled shown as one number | Split into Unpaid (collectable, amber) and Cancelled (lost, red) |
| "Existing" / "New" cards identical to Paid | Replaced by New-customer share (KPI) and the new-vs-existing donut/bars |
| Unused custom visuals (Enlighten Slicer, Simple Waterfall, WordCloud ref) | Removed from the copy |
| Category bars ≠ Paid card (R532K vs R518.6K) | Cards no longer carry the extra orders_invoices_tbl filters, so both use the same measure and filter context and reconcile by construction |

---

## 7. Verification & reconciliation

### 7.1 Reconciliation (re-derived this session from the uploaded WHMCS extracts)
The design brief's test, **1–29 Sep 2026: 588 paid orders, R143,924.45**, was checked against `paid_orders_(01:09)-(29:09).csv` (Dremio `paid_orders.sql`): **588 orders, R143,924.45 exactly**. That figure is **incl. VAT, by order date** (orders placed 1–29 Sep that are now Paid, invoice > R0).

The current measures are **excl. VAT** and dated on **paid date**, so the comparable targets are:

| Basis | Paid orders | Paid revenue | How to check in Power BI |
|---|---|---|---|
| Brief (incl. VAT, order date) | 588 | R143,924.45 | — (not what the report shows any more) |
| Excl. VAT, order date | 588 | ≈ **R125,152** (143,924.45 ÷ 1.15; exact value uses invoice subtotal, so credit-paid invoices move it slightly) | `[Paid Invoice Revenue]` (orders_invoices_tbl) with Calendar 1–29 Sep. Must equal the subtotal sum of these 588 invoices. |
| Excl. VAT, **paid date** (what the cards show) | ≠ 588 | ≠ R125k | Period 1–29 Sep on any page. Includes August orders paid in September, excludes September orders paid in October. From `september_orders.csv`: of the 1–29 Sep paid-date set, 573 orders / R141,397.52 incl. VAT (≈ R122,954 excl.) are September orders. August orders paid in September are not in the extract. |

**Re-run in Power BI** (DAX query view on the model, read-only):
```dax
EVALUATE
CALCULATETABLE (
    ROW (
        "Paid Orders (order date)", [Paid Orders],
        "Paid Invoice Revenue excl VAT (order date)", [Paid Invoice Revenue],
        "Paid Revenue (Products) (paid date)", [Paid Revenue (Products)],
        "Paid Orders (Products) (paid date)", [Paid Orders (Products)]
    ),
    DATESBETWEEN ( 'Calendar'[Date (format)], DATE ( 2026, 9, 1 ), DATE ( 2026, 9, 29 ) )
)
```
Expect 588 and ≈ R125.15k for the first two. The other two are the report's paid-date numbers to record as the new baseline.

### 7.2 Click-through checklist (to run in the service / Desktop)
For each main page:
1. Change Period (Last 7 / 30 / 90 days, This month): KPI cards and all charts change, and no visual shows an error. For the 1–29 Sep 2026 check, temporarily switch the Period slicer to *Between* in edit mode.
2. **Category bars sum = Paid revenue card** (Overview, Customers "What do new and existing customers buy?" summed over both series, TT - Period). Products matrix total = card.
3. New donut New + Existing + Unknown = card.
4. Select *Domains* in Category: all cards, charts and the Daily matrix respond on all pages (sync).
5. Unpaid card + Cancelled card + Refunded (via the Collections status chart) ≈ `[Unpaid Revenue (Products)]`.
6. Daily Sales matrix: sum of daily Paid revenue = card; *% paid* between 0 and 100 %.
7. Overview monthly chart keeps 13 months when Period changes, and responds to Category.
8. Hover: category charts → TT - Category; time charts → TT - Period; product matrix → Revenue Tooltip.
9. Account-age bar order: New → Under 1 year → 1–3 → 3–5 → 5–10 → 10+ → Unknown.
10. Clear all resets every slicer, and Period returns to its default.
11. Performance analyzer: every visual < 1 s (the Daily matrix with 11 measures is the heaviest).

Record mismatches in the handoff doc.

---

## 8. Open decisions for Josh

1. **Period default**: *Last 30 days* (chosen) vs *This month* (MTD, matches the Excel monthly view but is short early in the month). A Between slicer can't default to a moving window.
2. **Domain counts**: paid registrations (now) vs all registrations by order date (closer to Excel's "added").
3. **Old pages**: the copy drops TEMPLATE, Data_Exploration, PRODUCT SALES, SALES TRENDS, CUSTOMER INSIGHTS, PRODUCT MIX. Once the redesign is signed off, retire them in the live report, or swap the redesign in as the live report.
4. **Removed slicers** (IDs, IP, Company, Domain, Client Group, Country, Service Status): confirm no one relies on them, or add them to a collapsible "More filters" panel (bookmark toggle).
5. **Model backlog** (§1.2): domains snapshot, market share, history before Jul 2025, order hour, budget. Each changes the shared model and needs BI-team sign-off.
6. Whether to keep the Excel running in parallel until the redesign's numbers have been reconciled for a full month.

---

## 9. What was and wasn't done this session
- **Done:** value analysis; full design; the redesigned report generated as PBIR and packaged as `Daily sales (v2.0) – Redesign.pbix`, schema-validated (one pre-existing bookmark warning from a newer property); wireframes (`DailySales_docs/redesign_session3/wireframes/`); this spec; the handoff doc update.
- **Not done, needs a browser / Desktop:** opening the file in Power BI, publishing it to *BigQuery Reports*, "Save a copy" in the service, click-through verification, and the DAX reconciliation query. This cloud session had no Claude in Chrome connection and no Power BI Desktop. Run those steps from a session on Josh's Mac (Claude Desktop app or `claude remote-control`, with Claude in Chrome connected), or by hand.
- **Not checked:** whether every hand-written formatting property is honoured by Desktop. The PBIR schema validates structure and queries, but not formatting property names. Anything unrecognised falls back to the theme defaults, which carry the same card spec.

## 10. Files
| Path | What |
|---|---|
| `powerbi/Daily sales (v2.0) – Redesign.pbix` | Redesigned thin report (live connection to Daily sales (Model) v2.0) |
| `powerbi/DailySales_docs/redesign_session3/pbir/` | The PBIR definition inside the .pbix, readable and diffable |
| `powerbi/DailySales_docs/redesign_session3/tools/build.py` | Generator: every position, colour, field and measure is defined here. Re-run with `python3 build.py <extracted original pbix> <out>` |
| `powerbi/DailySales_docs/redesign_session3/tools/validate.py`, `pack.py`, `wireframe.py` | Schema validation, packaging, wireframes |
| `powerbi/DailySales_docs/redesign_session3/wireframes/*.png` | Page wireframes |
