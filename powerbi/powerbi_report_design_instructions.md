# Instructions: Designing Power BI Report Pages for the 1-grid Daily Sales Model

You are a Power BI report designer and analyst working on the **Daily sales (Model) v2.0** semantic model for 1-grid (South African web hosting provider; WHMCS billing data served through Dremio). Your job is to design and build report pages that give the business **accurate numbers, clear insights and fast decisions**.

Read this whole document before building anything. Section 2 describes the model; Section 3 lists rules that keep numbers correct; Section 4 audits the current report; Sections 5–7 specify pages, measures and design standards; Section 8 is the build and validation workflow.

---

## 1. Objective and audience

| Audience | What they need | Where they look |
|---|---|---|
| Executives / management | Is revenue on track? What changed and why? | Overview page, one screen, no scrolling |
| Sales & marketing | Which products, customers and channels drive revenue? | Product, Customer, Channel pages |
| Finance / collections | How much is unpaid, cancelled or pending debit order? | Collections page |
| Data / BI team | Do the numbers reconcile to WHMCS? | Data Quality page (hidden from general users) |

Every page must answer **one main business question**, stated in the page title or subtitle. A visual that doesn't help answer that question does not go on the page.

---

## 2. The data model (what exists today)

### 2.1 Source and refresh

- Source: Dremio 21.2 (`dl-coordinator01.1-grid.com:31010`), WHMCS MySQL behind it, via the on-premises gateway **BI Gateway Office** (server 1G-WPDN-POWERBI).
- Import mode, refreshed on a schedule. Numbers are as of the last refresh; any `TODAY()` logic in calculated columns is evaluated at refresh.

### 2.2 Core tables

| Table | Grain (one row per…) | Use it for |
|---|---|---|
| **orders_invoices_tbl** | Order (unique `order_id`), with its invoice fields | **Headline totals and counts**: paid revenue, paid orders, unpaid/cancelled, trends over time |
| **revenue_orders_tbl** (calculated) | Service on an order (from Combined Revenue) **plus** one row per order missing from Combined Revenue (`service_group` = "Not in Combined Revenue") | **Product, category, customer and location breakdowns** |
| **Combined Revenue** | Service line (legacy fact, 2021→) | Legacy pages only; source for revenue_orders_tbl |
| **Calendar** | Date | All date slicers and time axes |
| **Clients** | Client | Client attributes (already looked up into revenue_orders_tbl) |
| **tblorders**, **tblinvoices** | Raw WHMCS order / invoice (Dremio view) | Source for orders_invoices_tbl; avoid in visuals |

### 2.3 Key columns in revenue_orders_tbl

- Keys: `order_id`, `client_id`, `service_id`, `invoice_id`
- Product: `service_group`, `service_type`, **`Category`**, **`Sub Category`**, **`Product Name`** (calculated; hierarchy **Product Hierarchy** = Category › Sub Category › Product Name), `billing_cycle`, `billing_period`, `service_status`
- Amounts: `recurring_amount`, `setup_fee`, `total_rev` (legacy, see 3.4), `invoice_total` (repeated per row, see 3.1), **`invoice_total_alloc`** (invoice total split across the order's products; sums correctly)
- Customer: `type_of_customer` ("New Customer" / "Existing Customer" / "Unknown Customer"), `customer_age_group` (person's age band), **`customer_tenure_group`** (account age at order date; sorted by `customer_tenure_sort`), `location`, `client_city`, `client_state`, `client_country`, `client_datecreated`, `signup_agent` (Online / Agent), `heard_about_us`
- Order / invoice: `order_date`, `order_status`, `order_paymethod`, `invoice_status`, `invoice_paymethod`, `invoice_date`, `invoice_duedate`, `invoice_datepaid`

### 2.4 Product hierarchy (6 categories, 13 sub categories)

| Category | Sub Categories |
|---|---|
| Domains | Domains, Domain Parking, Domain Add-ons |
| Application Hosting | Web Hosting, Reseller Hosting, Email |
| Infrastructure Hosting | VPS & Cloud Servers, Dedicated Servers |
| Web Services | Website Design, Website Migration, SEO |
| Security & Backup | Security & Backup |
| Business Services | Business Services |
| *(gap)* | Not in Combined Revenue |

### 2.5 Relationships that matter

- `revenue_orders_tbl[order_id]` → `orders_invoices_tbl[order_id]` (many-to-one, active, single direction).
- `Combined Revenue[order_id]` → `orders_invoices_tbl[order_id]` (active).
- `revenue_orders_tbl[client_id]` → `Clients[client_id]` (active).
- `orders_invoices_tbl[order_date]` → `Calendar[Date]`: **may be inactive** because Calendar already reaches Combined Revenue via Invoice detail (bidirectional many-to-many). If inactive, every date-sensitive measure on these tables must include `USERELATIONSHIP ( 'Calendar'[Date], orders_invoices_tbl[order_date] )`. **Check this first** (Manage relationships).
- Filters flow orders_invoices_tbl → revenue_orders_tbl, **not** the reverse. Product slicers do not filter orders_invoices_tbl measures.

### 2.6 Existing measures (use these; do not re-create)

On **orders_invoices_tbl** (headline):
- `Paid Invoice Total`: paid invoices, each invoice counted once.
- `Paid Orders`: distinct paid orders with invoice > R0 (matches WHMCS/database).

On **revenue_orders_tbl** (breakdowns):
- `Paid Revenue (Products)`, `Paid Revenue excl VAT (Products)`, `Paid Orders (Products)`
- `Unpaid Revenue (Products)`, `Unpaid Revenue excl VAT (Products)`, `Unpaid Orders (Products)`
- `RO Invoice Total` (each invoice once; not product-split)
- `Revenue (%)`, `Orders (%)` (share of parent level in a Category › Product matrix)
- `Tooltip Text` (sentence tooltip for the product matrix)

### 2.7 Reconciliation targets (use to validate)

For **1–29 Sep 2026, Paid**: `Paid Orders` = **588**, `Paid Invoice Total` = **R143,924.45**. `Paid Revenue (Products)` total must also equal **R143,924.45**, of which "Not in Combined Revenue" ≈ **R18,659.71** (57 orders).

---

## 3. Rules that keep the numbers correct

1. **Never `SUM(invoice_total)` on revenue_orders_tbl.** It repeats per service row (inflated R206k vs R144k in Sep). Use `invoice_total_alloc`-based measures or `RO Invoice Total`.
2. **Headline cards and time trends come from orders_invoices_tbl measures**; product/customer splits come from revenue_orders_tbl measures. Both reconcile to the same total.
3. **Paid orders exclude R0 invoices** (free domains bundled with hosting, credit-paid). If a page shows R0 orders, label them separately ("Free / R0 orders").
4. **`total_rev` is not invoice revenue.** It is list price excl. VAT, Infrastructure Hosting spread monthly, missing 57 orders. Use only when explicitly showing "list-price MRR-style revenue", and label it so.
5. **VAT:** invoice measures include 15% VAT. State "incl. VAT" or use the `excl VAT` measure; never mix in one visual.
6. **Orders by product double-count by design** (one order, several products). Category rows can sum to more than the total; percentages of orders can exceed 100%. Explain this in a tooltip or footnote; never stack order counts by product into a "total".
7. **Date coverage:** orders_invoices_tbl / revenue_orders_tbl order and invoice fields start ~**Jul 2025** (Dremio view limit). Don't build year-on-year comparisons before Jul 2026 without flagging the gap; set Calendar slicer defaults to ≥ Jul 2025.
8. **Blank invoice status** = no invoice; exclude from "unpaid" logic (`NOT ISBLANK`).
9. **Use Calendar[Date]** for every date slicer and axis, never a fact table's own date column.
10. **High-cardinality IDs** (Order ID, Invoice ID, Client ID) are for search/drill-through, not dropdown slicers on summary pages.

---

## 4. Audit of the current report (do this before designing)

### 4.1 How to audit any existing page

For each page and visual, record: business question answered · measures/columns used · table each comes from · whether it violates a rule in Section 3 · whether filters behave correctly (change the date range and a product slicer; note what does/doesn't respond) · duplicated information · interaction usefulness. Use **Performance analyzer** to capture slow visuals (> 1 s).

Ask: Who opens this page, what decision do they make, and does the first screen give them the answer?

### 4.2 Findings on the current "DAILY SALES | Overview" page

| Element | Current state | Issue | Recommendation |
|---|---|---|---|
| Date slicer (between) | 01/09/2026 – 29/09/2026 | Fine | Keep; add relative presets (This month, Last 30 days) via a separate page-level setting or bookmarks |
| 8 dropdown slicers (Category, Sub-category, Product, Invoice ID, Order ID, Client ID, Location, Payment Method) | One row across the page | Takes ~15% of canvas; ID slicers are near-useless as dropdowns; Product slicers don't filter the orders_invoices_tbl cards (rule 2.5) so users see unchanged cards and lose trust | Keep Date + Category + Payment Method on the page; move the rest to a collapsible **filter panel** (bookmark toggle) or the Filters pane; replace ID slicers with a **search** on the Order Detail page |
| "Paid" cards | R143.92K / 588 | Correct (reconciles) | Keep; add vs prior period delta and AOV |
| "Unpaid & Cancelled" cards | R175.34K / 154 orders | Larger than paid revenue and grouped together; unpaid (collectable) and cancelled (lost) mean different things | Split into **Unpaid (collectable)** and **Cancelled (lost)**; move detail to a Collections page; show **collection rate** |
| "Existing" and "New" cards | Both show R143.92K / 588, identical to Paid | Bug: no customer-type filter is applied (or applied to a table that doesn't filter orders_invoices_tbl) | Rebuild with revenue_orders_tbl measures filtered on `type_of_customer`; show as **New vs Existing split** (two values that add to Paid) |
| Month matrix (daily rows) | Paid revenue + orders per day | Readable but slow to scan; daily trend is a shape, not a list | Replace with a **line/column combo chart** (revenue bars, orders line) by day; keep a matrix only on a detail page |
| Category matrix | Uses `total_rev` (R106,779.65) | Doesn't reconcile with Paid card (rule 4) | Use `Paid Revenue (Products)` + `Revenue (%)` + `Paid Orders (Products)`; add Product Hierarchy drill |
| Formatting | Mixed (R 143.92K vs 106,779.65 with no currency) | Inconsistent units | Standardise formats (Section 7.4) |

### 4.3 Data value not yet used

These fields exist and carry decision value but appear on no page today: `invoice_status` detail (Refunded, Collections), `Invoice Status Group` / pending debit orders (`mygateDebit` + future due date), `invoice_paymethod` vs `order_paymethod`, `billing_cycle` (monthly vs annual mix), `service_status` (churned/terminated services from recent orders), `signup_agent` (Online vs Agent), `heard_about_us` (marketing attribution), `customer_tenure_group`, `client_city/state/country`, `customer_age_group`, `base_or_addon` (attach rate), time of day (`order_datetime` in Combined Revenue), `invoice_datepaid − invoice_date` (days to pay).

---

## 5. Pages to build

Build in this order. Each page: 16:9, 1280 × 720, no vertical scroll on summary pages.

### Page 1 — Overview (rebuild of current page)
**Question:** How are sales tracking this period, and what is driving the change?

- **Header band:** title, last refresh time (`MAX` of a refresh timestamp or `orders_invoices_tbl[today]`), date slicer, Category slicer, filter-panel toggle.
- **KPI row (5 cards, each with delta vs prior period and a small sparkline):** Paid Revenue (incl. VAT) · Paid Orders · Average Order Value · New Customer Share of revenue · Collection Rate.
- **Trend (left, 60% width):** daily Paid Revenue (columns) + Paid Orders (line), with prior-period revenue as a faint line.
- **Mix (right, 40% width):** Paid Revenue by Category (horizontal bar, sorted desc, data labels with R and %).
- **Bottom strip:** New vs Existing revenue (100% bar) · Top 5 products (bar) · Unpaid (collectable) R and count with a link button to Collections.
- **Insight text:** one smart narrative or a DAX-driven sentence: "Paid revenue R143.9k, ▲x% vs previous 29 days; Domains contributed y%."

### Page 2 — Product Performance
**Question:** Which products and categories earn the revenue, and where is growth or decline?

- Matrix with **Product Hierarchy** rows; values: Paid Revenue, Revenue (%), Paid Orders, Orders (%), AOV, Δ vs prior period (conditional formatting: green/red icons). Tooltip page or `Tooltip Text`.
- Treemap or bar of Sub Category revenue (≤ 13 items).
- Billing cycle mix by Category (stacked 100% bar: Monthly / Annually / other).
- Attach rate: share of orders with an add-on (`base_or_addon`).
- Callout card: revenue in "Not in Combined Revenue" (data gap, links to Data Quality page).

### Page 3 — Collections & Payment Status
**Question:** How much invoiced revenue is uncollected, why, and what needs action?

- Cards: Unpaid (collectable) R / count · Cancelled R / count · Refunded R · Pending debit orders (mygateDebit, due in future) R / count · Collection rate.
- Status funnel or bar: Invoiced → Paid → Unpaid → Cancelled.
- Unpaid by age bucket (days past due: not due, 0–7, 8–30, 30+), from `invoice_duedate` vs today.
- Payment method performance: paid rate and cancellation rate by `invoice_paymethod`.
- Days-to-pay distribution (column chart).
- Table (top 50 unpaid by value): order, client, product, invoice date, due date, amount, method. Drill-through to Order Detail.

### Page 4 — Customers
**Question:** Who is buying — new or existing customers, how established, and from where?

- New vs Existing: revenue, orders, AOV (clustered bar).
- `customer_tenure_group` bar (sorted by `customer_tenure_sort`): revenue and orders.
- Map or bar by `client_state` / `client_city` (South Africa first; country split card for non-ZA).
- `customer_age_group` bar (exclude/label "Unknown").
- Repeat buyers in period: clients with > 1 paid order.
- Matrix: Category × New/Existing (what new customers buy first).

### Page 5 — Channels & Acquisition
**Question:** Which sales channels and marketing sources bring revenue?

- `signup_agent` (Online vs Agent): revenue, orders, AOV.
- `heard_about_us`: revenue and new-customer orders (bar, sorted; "Did not say how" shown last and greyed).
- Order payment method mix (`order_paymethod`).
- Order hour-of-day heatmap (day of week × hour), if `order_datetime` is brought into revenue_orders_tbl.

### Page 6 — Order Detail (drill-through target)
**Question:** What exactly is in this order / for this client?

- Drill-through fields: `order_id`, `client_id`, `Product Name`, `Category`.
- Cards: order total, invoice status, paid date, client tenure, location.
- Table of service lines: product, billing cycle, recurring amount, setup fee, allocated invoice amount, service status.
- Search box (text filter or slicer with search) for Order ID / Invoice ID / Client ID — this replaces the ID dropdowns removed from Overview.

### Page 7 — Data Quality & Reconciliation (hidden; BI team only)
**Question:** Can we trust the numbers?

- Cards: Paid Invoice Total vs Paid Revenue (Products) (must be equal) · orders "Not in Combined Revenue" (count, R) · R0 paid orders · rows with blank invoice status · Combined Revenue rows with blank `order_id` · Combined Revenue dates outside 2009–today (a `create_date` of 3001-09-01 exists).
- Table of "Not in Combined Revenue" orders for investigation.
- Last refresh status and row counts per table.

### Supporting pages
- **Guide** page: Category › Sub Category › Product mapping (matrix on the hierarchy), metric definitions (Section 6 glossary), how to use filters.
- **Tooltip pages** (hidden): TT – Category (cards + top 5 products), TT – Day (revenue, orders, top category that day).

---

## 6. Measures to add

Create in a dedicated `_Measures` table (display folders: Headline, Products, Collections, Customers, Time). Format every measure on creation. If the Calendar → orders_invoices_tbl link is inactive, add `USERELATIONSHIP ( 'Calendar'[Date], orders_invoices_tbl[order_date] )` inside each `CALCULATE` that reads orders_invoices_tbl or revenue_orders_tbl by date.

```DAX
-- ---------- Headline ----------
Average Order Value =
DIVIDE ( [Paid Invoice Total], [Paid Orders] )

Unpaid Invoice Total =
CALCULATE (
    SUMX ( VALUES ( orders_invoices_tbl[order_invoiceid] ),
           CALCULATE ( MAX ( orders_invoices_tbl[invoice_total] ) ) ),
    orders_invoices_tbl[invoice_status] = "Unpaid"
)

Cancelled Invoice Total =
CALCULATE (
    SUMX ( VALUES ( orders_invoices_tbl[order_invoiceid] ),
           CALCULATE ( MAX ( orders_invoices_tbl[invoice_total] ) ) ),
    orders_invoices_tbl[invoice_status] = "Cancelled"
)

Collection Rate =
-- Share of invoiced value (paid + unpaid + cancelled) that was paid
DIVIDE (
    [Paid Invoice Total],
    [Paid Invoice Total] + [Unpaid Invoice Total] + [Cancelled Invoice Total]
)

Pending Debit Orders (R) =
CALCULATE (
    SUMX ( VALUES ( orders_invoices_tbl[order_invoiceid] ),
           CALCULATE ( MAX ( orders_invoices_tbl[invoice_total] ) ) ),
    orders_invoices_tbl[invoice_status] = "Unpaid",
    orders_invoices_tbl[invoice_paymethod] = "mygateDebit",
    orders_invoices_tbl[invoice_duedate] > TODAY ()
)

-- ---------- Time comparison (prior period of equal length) ----------
Paid Invoice Total PP =
VAR firstDay = MIN ( 'Calendar'[Date] )
VAR lastDay  = MAX ( 'Calendar'[Date] )
VAR days     = lastDay - firstDay + 1
RETURN
    CALCULATE (
        [Paid Invoice Total],
        DATESBETWEEN ( 'Calendar'[Date], firstDay - days, firstDay - 1 )
    )

Paid Invoice Total Δ% =
DIVIDE ( [Paid Invoice Total] - [Paid Invoice Total PP], [Paid Invoice Total PP] )

-- ---------- Customers ----------
New Customer Revenue =
CALCULATE ( [Paid Revenue (Products)], revenue_orders_tbl[type_of_customer] = "New Customer" )

Existing Customer Revenue =
CALCULATE ( [Paid Revenue (Products)], revenue_orders_tbl[type_of_customer] = "Existing Customer" )

New Customer Share =
DIVIDE ( [New Customer Revenue], [Paid Revenue (Products)] )

New Customers =
CALCULATE (
    DISTINCTCOUNT ( revenue_orders_tbl[client_id] ),
    revenue_orders_tbl[type_of_customer] = "New Customer",
    revenue_orders_tbl[invoice_status] = "Paid",
    revenue_orders_tbl[invoice_total] > 0
)

-- ---------- Products ----------
AOV (Products) =
DIVIDE ( [Paid Revenue (Products)], [Paid Orders (Products)] )

Days to Pay (avg) =
AVERAGEX (
    FILTER ( orders_invoices_tbl,
             orders_invoices_tbl[invoice_status] = "Paid"
                 && NOT ISBLANK ( orders_invoices_tbl[invoice_datepaid] ) ),
    orders_invoices_tbl[invoice_datepaid] - orders_invoices_tbl[invoice_date]
)
```

Validate every new measure against Section 2.7 before using it on a page. Mark **Calendar** as a date table (Table tools › Mark as date table) for time intelligence.

### Glossary (put on the Guide page)

| Term | Definition |
|---|---|
| Paid revenue | Sum of paid invoice totals, incl. 15% VAT, each invoice once, invoices > R0 |
| Paid orders | Distinct orders whose invoice is Paid and > R0 |
| AOV | Paid revenue ÷ paid orders |
| Collection rate | Paid ÷ (Paid + Unpaid + Cancelled) invoice value |
| New customer | Client account created on the order date |
| Tenure | Account age at the order date |
| Not in Combined Revenue | Paid orders whose products aren't in the product feed yet; counted in totals, not in product categories |

---

## 7. Design standards

### 7.1 Layout
- Canvas 1280 × 720; 8 px grid; 16 px outer margin; 12 px gutters.
- Reading order **top-left → bottom-right**: context (filters, date) → KPIs → main trend → breakdowns → detail.
- Maximum **6–8 visuals** per summary page. Group related visuals on a shared light background panel.
- KPIs in one row, equal size, same order on every page.

### 7.2 Visual choice
| Data shape | Use | Avoid |
|---|---|---|
| Change over time | Line, or columns + line combo | Pie, table of days |
| Compare categories (≤ 15) | Horizontal bar, sorted desc | Pie/donut with > 4 slices, 3D |
| Part of whole (≤ 5 parts) | 100% stacked bar, donut only if ≤ 4 parts | Stacked bars for overlapping counts (orders by product) |
| Hierarchy | Matrix with drill, decomposition tree for exploration | Deeply nested tables on summary pages |
| Single number | Card / new card with reference label (Δ vs prior) | Gauges without a target |
| Two measures across items | Scatter (e.g., AOV vs orders by product) | Dual axis with unrelated units |

### 7.3 Colour
- Brand: 1-grid cyan (title colour; sample the exact hex from the logo) for the primary series; dark grey (logo text) for text.
- Greys for context; one accent colour for what the title is about.
- Semantic colours only for meaning: green = paid / up, red = cancelled / down, amber = unpaid / pending. Use the same colour for the same Category on every page (define in the theme JSON).
- Check contrast ≥ 4.5:1 for text; don't rely on colour alone (add icons or labels).

### 7.4 Text and numbers
- Titles state the insight or the question ("Domains drove 39% of paid revenue"), not the field list ("Sum of revenue by category").
- Currency: `R #,##0` on cards (with K/M display units where space is tight, e.g., R143.9K), `R #,##0.00` in tables. Percentages 1 decimal. Counts no decimals.
- Label units and VAT basis in subtitles ("incl. VAT").
- Font: Segoe UI (or theme font); titles 14–16 pt, labels 10–12 pt, card values 24–32 pt.

### 7.5 Interaction
- Cross-highlighting on by default; turn off interactions that produce misleading results (e.g., product visuals filtering orders_invoices_tbl cards have no effect — set to "None" and explain).
- Drill-through to Order Detail from any table/matrix with order, client or product.
- Tooltip pages on main charts; `Tooltip Text` measure on the product matrix with "Tooltip fields only" on.
- Sync the Date slicer across all pages; keep page-specific slicers local.
- Bookmarks for a collapsible filter panel and "Reset filters".

### 7.6 Performance
- Prefer measures to calculated columns for anything aggregated.
- Avoid visuals that render > 1,000 rows on summary pages; use Top N filters.
- Check Performance analyzer; target < 1 s per visual.

---

## 8. Workflow for the AI

1. **Inspect the model.** In DAX query view, run `EVALUATE INFO.VIEW.TABLES()`, `INFO.VIEW.MEASURES()` and `INFO.VIEW.RELATIONSHIPS()` (or the Model view) to confirm tables, measure names and whether the Calendar → orders_invoices_tbl link is active. Note any name differences from this document and use the model's actual names.
2. **Validate baselines.** Run:
   ```DAX
   EVALUATE
   CALCULATETABLE (
       ROW ( "Paid Orders", [Paid Orders],
             "Paid Invoice Total", [Paid Invoice Total],
             "Paid Revenue (Products)", [Paid Revenue (Products)] ),
       DATESBETWEEN ( 'Calendar'[Date], DATE ( 2026, 9, 1 ), DATE ( 2026, 9, 29 ) )
   )
   ```
   Expect 588 / 143,924.45 / 143,924.45. Stop and report if they differ.
3. **Audit current pages** (Section 4.1) and list what to keep, fix or remove.
4. **Explore before designing.** For each page, query the data for the period: top categories, biggest changes vs prior period, unpaid share, new vs existing split. Write the 2–3 insights each page should surface; design visuals that make those insights obvious.
5. **Create missing measures** (Section 6), formatted, in display folders, then re-validate.
6. **Build pages** in the order of Section 5 using the standards in Section 7. Apply a theme JSON for colours and fonts first.
7. **Test** each page: change date range, select a Category, drill through, hover tooltips. Confirm totals still reconcile and no visual shows a blank/error state.
8. **Report back** with: pages built, measures added, insights found (with numbers), open issues (data gaps, rules you couldn't follow), and screenshots.

### Do not
- Use `SUM` on `invoice_total` in revenue_orders_tbl, or `total_rev` as "revenue".
- Mix incl./excl. VAT in one visual.
- Add a visual whose question you can't state in one sentence.
- Modify or delete existing relationships, tables or measures without listing the change and its impact first.
- Present orders-by-product totals as a sum of categories.
