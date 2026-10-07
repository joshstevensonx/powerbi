"""Generate 'Daily sales (v2.0) - Redesign' PBIR report from the original live-connected pbix.

Usage: python3 build.py <orig_extract_dir> <out_dir>
Only report-side files change; the shared semantic model is untouched
(new measures live in Report/definition/reportExtensions.json).
"""
import json, os, shutil, sys, hashlib

SRC, OUT = sys.argv[1], sys.argv[2]
VC = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.13.0/schema.json"
PG = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json"
RO, CAL, EXT = "revenue_orders_tbl", "Calendar", "extension"

# ---------------------------------------------------------------- brand tokens
CYAN, GREY, GREEN, BLACK = "#00C1DE", "#55565A", "#00C18B", "#231F20"
DCYAN, DGREEN, LCYAN, LGREY, PALE = "#007E91", "#00845F", "#7FDFEE", "#A7A8AB", "#B3ECF5"
AMBER, RED, BORDER, PAGEBG, WHITE = "#F2A900", "#E5484D", "#E3E5E8", "#F4F6F8", "#FFFFFF"
FONT = "'Segoe UI', wf_segoe-ui_normal, helvetica, arial, sans-serif"
FONT_SB = "'Segoe UI Semibold', wf_segoe-ui_semibold, helvetica, arial, sans-serif"
FONT_B = "'Segoe UI Bold', wf_segoe-ui_bold, helvetica, arial, sans-serif"

CATEGORY_COLOURS = {
    "Domains": CYAN, "Application Hosting": DCYAN, "Infrastructure Hosting": GREY,
    "Web Services": GREEN, "Security & Backup": LCYAN, "Business Services": DGREEN,
    "Not in Combined Revenue": LGREY, "Other": "#C9CACC",
}
CUSTOMER_COLOURS = {"New Customer": GREEN, "Existing Customer": DCYAN, "Unknown Customer": LGREY}
STATUS_COLOURS = {"Paid": CYAN, "Unpaid": AMBER, "Payment Pending": "#F7CB66", "Collections": "#B37D00",
                  "Cancelled": RED, "Refunded": LGREY, "Draft": "#C9CACC"}
REGION_COLOURS = {"Local": CYAN, "International": GREY, "No Domain": LGREY}
CHANNEL_COLOURS = {"Online": CYAN, "Agent": GREY, "App Sale": GREEN}
SERVICE_COLOURS = {"Active": CYAN, "Pending": AMBER, "Suspended": GREY, "Cancelled": RED,
                   "Terminated": "#B23A3E", "Expired": LGREY, "Transferred Away": PALE, "Fraud": BLACK,
                   "Completed": GREEN}

_ids = {}
def uid(key):
    """Stable 20-hex id per logical key (re-runs give identical files)."""
    if key not in _ids:
        _ids[key] = hashlib.sha1(("1grid-redesign-s3/" + key).encode()).hexdigest()[:20]
    return _ids[key]

# ---------------------------------------------------------------- expression helpers
def L(v): return {"expr": {"Literal": {"Value": v}}}
def S(s): return L("'" + s.replace("'", "''") + "'")
def B(b): return L("true" if b else "false")
def D(n): return L(f"{n}D")
def I(n): return L(f"{n}L")
def C(hexv): return {"solid": {"color": S(hexv)}}
def col(prop, ent=RO): return {"Column": {"Expression": {"SourceRef": {"Entity": ent}}, "Property": prop}}
def m(prop, ent=RO): return {"Measure": {"Expression": {"SourceRef": {"Entity": ent}}, "Property": prop}}
def x(prop, ent=RO): return {"Measure": {"Expression": {"SourceRef": {"Schema": EXT, "Entity": ent}}, "Property": prop}}
def agg(prop, fn, ent=RO): return {"Aggregation": {"Expression": col(prop, ent), "Function": fn}}

def qref(field):
    if "Column" in field:
        c = field["Column"]; return f'{c["Expression"]["SourceRef"]["Entity"]}.{c["Property"]}'
    if "Measure" in field:
        c = field["Measure"]; return f'{c["Expression"]["SourceRef"]["Entity"]}.{c["Property"]}'
    if "Aggregation" in field:
        a = field["Aggregation"]; fn = {0: "Sum", 3: "Min", 4: "Max"}[a["Function"]]
        return f'{fn}({qref(a["Expression"])})'
    raise ValueError(field)

def native(field):
    if "Aggregation" in field:
        return "Min of " + native(field["Aggregation"]["Expression"])
    return (field.get("Column") or field.get("Measure"))["Property"]

def proj(field, name=None, active=None):
    p = {"field": field, "queryRef": qref(field), "nativeQueryRef": name or native(field)}
    if name: p["displayName"] = name
    if active is not None: p["active"] = active
    return p

def sort(field, desc=True):
    return {"sort": [{"field": field, "direction": "Descending" if desc else "Ascending"}], "isDefaultSort": True}

def scope_eq(field, value):
    return {"data": [{"scopeId": {"Comparison": {"ComparisonKind": 0, "Left": field, "Right": S(value)["expr"]}}}]}

def colour_points(field, mapping):
    return [{"properties": {"fill": C(hexv)}, "selector": scope_eq(field, k)} for k, hexv in mapping.items()]

# ---------------------------------------------------------------- filters
def f_in(prop, values, ent=RO, name=None):
    alias = ent[0].lower()
    return {"name": name or uid(f"flt/{ent}/{prop}/{values}"), "field": col(prop, ent), "type": "Categorical",
            "filter": {"Version": 2, "From": [{"Name": alias, "Entity": ent, "Type": 0}],
                       "Where": [{"Condition": {"In": {"Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": alias}}, "Property": prop}}],
                                                       "Values": [[S(v)["expr"]] for v in values]}}}]},
            "howCreated": "User"}

def f_not_blank(prop, ent=RO):
    alias = ent[0].lower()
    return {"name": uid(f"nb/{ent}/{prop}"), "field": col(prop, ent), "type": "Advanced",
            "filter": {"Version": 2, "From": [{"Name": alias, "Entity": ent, "Type": 0}],
                       "Where": [{"Condition": {"Not": {"Expression": {"Comparison": {"ComparisonKind": 0,
                           "Left": {"Column": {"Expression": {"SourceRef": {"Source": alias}}, "Property": prop}},
                           "Right": {"Literal": {"Value": "null"}}}}}}}]},
            "howCreated": "User"}

def f_topn(prop, by_measure, n, key, ent=RO):
    return {"name": uid(f"topn/{key}"), "field": col(prop, ent), "type": "TopN",
            "filter": {"Version": 2, "From": [
                {"Name": "subquery", "Expression": {"Subquery": {"Query": {"Version": 2,
                    "From": [{"Name": "r", "Entity": ent, "Type": 0}],
                    "Select": [{"Column": {"Expression": {"SourceRef": {"Source": "r"}}, "Property": prop}, "Name": "field"}],
                    "OrderBy": [{"Direction": 2, "Expression": by_measure(source="r")}], "Top": n}}}, "Type": 2},
                {"Name": "r", "Entity": ent, "Type": 0}],
                "Where": [{"Condition": {"In": {"Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "r"}}, "Property": prop}}],
                                                "Table": {"SourceRef": {"Source": "subquery"}}}}}]},
            "howCreated": "User"}

def m_src(prop, schema=None):
    def f(source):
        return {"Measure": {"Expression": {"SourceRef": {"Source": source}}, "Property": prop}}
    return f

def f_relative(prop, ent, amount, unit, name_key):
    """'In the last <amount> <unit>' incl. today. unit: 0 day, 1 week, 2 month, 3 year."""
    alias = ent[0].lower()
    return {"name": uid(f"rel/{name_key}"), "field": col(prop, ent), "type": "RelativeDate",
            "filter": {"Version": 2, "From": [{"Name": alias, "Entity": ent, "Type": 0}],
                       "Where": [{"Condition": {"Between": {
                           "Expression": {"Column": {"Expression": {"SourceRef": {"Source": alias}}, "Property": prop}},
                           "LowerBound": {"DateSpan": {"Expression": {"DateAdd": {"Expression": {"DateAdd": {"Expression": {"Now": {}}, "Amount": 1, "TimeUnit": 0}},
                                                                                  "Amount": -amount, "TimeUnit": unit}}, "TimeUnit": 0}},
                           "UpperBound": {"DateSpan": {"Expression": {"Now": {}}, "TimeUnit": 0}}}}}]},
            "howCreated": "User"}

# ---------------------------------------------------------------- container formatting
def card_frame(title=None, tooltip_page=None, show_title=True):
    o = {
        "background": [{"properties": {"show": B(True), "color": C(WHITE), "transparency": D(0)}}],
        "border": [{"properties": {"show": B(True), "color": C(BORDER), "radius": D(8), "width": D(1)}}],
        "dropShadow": [{"properties": {"show": B(False)}}],
        "padding": [{"properties": {"top": D(12), "bottom": D(8), "left": D(14), "right": D(14)}}],
        "visualHeader": [{"properties": {"show": B(True)}}],
    }
    if title is not None:
        o["title"] = [{"properties": {"show": B(show_title), "text": S(title), "fontFamily": S(FONT_SB),
                                      "fontSize": D(12), "fontColor": C(BLACK), "alignment": S("left")}}]
    if tooltip_page:
        o["visualTooltip"] = [{"properties": {"show": B(True), "type": S("Canvas"), "section": S(tooltip_page)}}]
    return o

def axis_objects(value_axis=False, labels=True, label_units=None, legend=False, cat_font=9):
    o = {
        "categoryAxis": [{"properties": {"showAxisTitle": B(False), "fontSize": D(cat_font), "labelColor": C(GREY),
                                         "gridlineShow": B(False)}}],
        "valueAxis": [{"properties": {"show": B(value_axis), "showAxisTitle": B(False), "gridlineShow": B(value_axis),
                                      "gridlineStyle": S("dotted"), "gridlineColor": C(BORDER), "labelColor": C(GREY),
                                      "fontSize": D(9)}}],
        "legend": [{"properties": {"show": B(legend), "position": S("Top"), "showTitle": B(False),
                                   "labelColor": C(GREY), "fontSize": D(9)}}],
    }
    if labels:
        lp = {"show": B(True), "color": C(GREY), "fontSize": D(9)}
        if label_units:
            lp["labelDisplayUnits"] = D(label_units); lp["labelPrecision"] = I(1)
        o["labels"] = [{"properties": lp}]
    return o

def container(page, key, x0, y0, w, h, visual, filters=None, z=None, parent=None, hidden=False):
    name = uid(f"{page}/{key}")
    c = {"$schema": VC, "name": name,
         "position": {"x": x0, "y": y0, "z": z if z is not None else 1000, "height": h, "width": w,
                      "tabOrder": z if z is not None else 1000},
         "visual": visual}
    if parent: c["parentGroupName"] = parent
    if filters: c["filterConfig"] = {"filters": filters}
    if hidden: c["isHidden"] = True
    return c

# ---------------------------------------------------------------- report-level measures (reportExtensions.json)
PR, PO = "[Paid Revenue (Products)]", "[Paid Orders (Products)]"
DATES_PP = """VAR _first = MIN ( 'Calendar'[Date (format)] )
VAR _last = MAX ( 'Calendar'[Date (format)] )
VAR _days = INT ( _last - _first ) + 1"""

def pp(expr):
    return f"""{DATES_PP}
RETURN
    CALCULATE (
        {expr},
        REMOVEFILTERS ( 'Calendar' ),
        FILTER (
            ALL ( 'Calendar'[Date (format)] ),
            'Calendar'[Date (format)] >= _first - _days
                && 'Calendar'[Date (format)] <= _first - 1
        )
    )"""

def delta_text(cur, prev, pts=False):
    if pts:
        return f"""VAR _c = {cur}
VAR _p = {prev}
VAR _d = ( _c - _p ) * 100
{DATES_PP}
RETURN
    IF (
        ISBLANK ( _p ) || ISBLANK ( _c ),
        "No prior-period data",
        IF ( _d >= 0, "▲ ", "▼ " ) & FORMAT ( ABS ( _d ), "0.0" ) & " pts vs prior " & _days & " days"
    )"""
    return f"""VAR _c = {cur}
VAR _p = {prev}
{DATES_PP}
RETURN
    IF (
        ISBLANK ( _p ) || _p = 0,
        "No prior-period data",
        VAR _d = DIVIDE ( _c - _p, _p )
        RETURN IF ( _d >= 0, "▲ ", "▼ " ) & FORMAT ( ABS ( _d ), "0.0%" ) & " vs prior " & _days & " days"
    )"""

def delta_colour(cur, prev):
    return f"""VAR _c = {cur}
VAR _p = {prev}
RETURN IF ( ISBLANK ( _p ) || _c >= _p, "{DGREEN}", "{RED}" )"""

RAND = '"R"\\ #,0;"R"\\ -#,0;"R"\\ #,0'
RAND2 = '"R"\\ #,0.00;"R"\\ -#,0.00;"R"\\ #,0.00'
PCT = "0.0%;-0.0%;0.0%"
PAID_DATE = """VAR _dates = VALUES ( 'Calendar'[Date (format)] )
RETURN"""

MEASURES = [
    # name, expression, dataType, format, folder, description
    ("Average Order Value", f"DIVIDE ( {PR}, {PO} )", "Double", RAND, "Headline",
     "Paid revenue excl. VAT ÷ paid orders (paid date)."),
    ("Paid Revenue PP", pp(PR), "Double", RAND, "Time",
     "Paid revenue for the prior period of equal length immediately before the selected dates."),
    ("Paid Orders PP", pp(PO), "Double", "0", "Time", "Paid orders, prior period of equal length."),
    ("Average Order Value PP", "DIVIDE ( [Paid Revenue PP], [Paid Orders PP] )", "Double", RAND, "Time",
     "AOV for the prior period of equal length."),
    ("Paid Revenue Δ%", f"VAR _p = [Paid Revenue PP] RETURN IF ( NOT ISBLANK ( _p ), DIVIDE ( {PR} - _p, _p ) )",
     "Double", PCT, "Time", "Change in paid revenue vs the prior period of equal length."),
    ("Paid Revenue LY", f"""{DATES_PP}
RETURN
    CALCULATE (
        {PR},
        REMOVEFILTERS ( 'Calendar' ),
        FILTER (
            ALL ( 'Calendar'[Date (format)] ),
            'Calendar'[Date (format)] >= EDATE ( _first, -12 )
                && 'Calendar'[Date (format)] <= EDATE ( _last, -12 )
        )
    )""", "Double", RAND, "Time",
     "Paid revenue for the same dates one year earlier. Blank before Jul 2026 (orders data starts Jul 2025)."),
    ("KPI Revenue Δ", delta_text(PR, "[Paid Revenue PP]"), "Text", None, "KPI text", "Card caption."),
    ("KPI Orders Δ", delta_text(PO, "[Paid Orders PP]"), "Text", None, "KPI text", "Card caption."),
    ("KPI AOV Δ", delta_text("[Average Order Value]", "[Average Order Value PP]"), "Text", None, "KPI text", "Card caption."),
    ("KPI Revenue Δ Colour", delta_colour(PR, "[Paid Revenue PP]"), "Text", None, "KPI text", "Green up / red down."),
    ("KPI Orders Δ Colour", delta_colour(PO, "[Paid Orders PP]"), "Text", None, "KPI text", "Green up / red down."),
    ("KPI AOV Δ Colour", delta_colour("[Average Order Value]", "[Average Order Value PP]"), "Text", None, "KPI text", "Green up / red down."),
    ("New Customer Revenue", f'CALCULATE ( {PR}, KEEPFILTERS ( revenue_orders_tbl[type_of_customer] = "New Customer" ) )',
     "Double", RAND, "Customers", "Paid revenue from clients who signed up on the order day."),
    ("New Customer Share", f"DIVIDE ( [New Customer Revenue], {PR} )", "Double", PCT, "Customers",
     "Share of paid revenue from new customers (Excel: New Revenue %)."),
    ("New Customer Share PP", pp("DIVIDE ( [New Customer Revenue], " + PR + " )"), "Double", PCT, "Customers",
     "New-customer share, prior period of equal length."),
    ("KPI New Share Δ", delta_text("[New Customer Share]", "[New Customer Share PP]", pts=True), "Text", None, "KPI text", "Card caption."),
    ("KPI New Share Δ Colour", delta_colour("[New Customer Share]", "[New Customer Share PP]"), "Text", None, "KPI text", "Green up / red down."),
    ("Open Unpaid Revenue", 'CALCULATE ( [Unpaid Revenue (Products)], KEEPFILTERS ( revenue_orders_tbl[Status_Filter] IN { "Unpaid", "Payment Pending", "Collections", "Draft" } ) )',
     "Double", RAND, "Collections",
     "Invoice value excl. VAT still collectable (Unpaid, Payment Pending, Collections, Draft), by order date. Filters Status_Filter because the base measure overrides invoice_status."),
    ("Open Unpaid Orders", 'CALCULATE ( [Unpaid Orders (Products)], KEEPFILTERS ( revenue_orders_tbl[Status_Filter] IN { "Unpaid", "Payment Pending", "Collections", "Draft" } ) )',
     "Double", "0", "Collections", "Orders whose invoice is still collectable."),
    ("Cancelled Revenue", 'CALCULATE ( [Unpaid Revenue (Products)], KEEPFILTERS ( revenue_orders_tbl[Status_Filter] = "Cancelled" ) )',
     "Double", RAND, "Collections", "Invoice value excl. VAT on cancelled invoices (lost), by order date."),
    ("Cancelled Orders", 'CALCULATE ( [Unpaid Orders (Products)], KEEPFILTERS ( revenue_orders_tbl[Status_Filter] = "Cancelled" ) )',
     "Double", "0", "Collections", "Orders whose invoice was cancelled."),
    ("KPI Unpaid Caption", 'VAR _n = [Open Unpaid Orders] RETURN IF ( ISBLANK ( _n ), "No open invoices", FORMAT ( _n, "#,0" ) & " orders awaiting payment" )',
     "Text", None, "KPI text", "Card caption."),
    ("KPI Cancelled Caption", 'VAR _n = [Cancelled Orders] RETURN IF ( ISBLANK ( _n ), "No cancelled invoices", FORMAT ( _n, "#,0" ) & " orders cancelled" )',
     "Text", None, "KPI text", "Card caption."),
    ("Invoiced Value", "[RO Invoice Total]", "Double", RAND, "Collections",
     "All invoices excl. VAT, each once, by order date (Excel: 'Power BI new revenue')."),
    ("Paid Share of Invoiced", 'DIVIDE ( CALCULATE ( [RO Invoice Total], revenue_orders_tbl[invoice_status] = "Paid" ), [RO Invoice Total] )',
     "Double", PCT, "Collections",
     "Share of invoiced value (orders placed in the period) that is paid. Excel: Paid tracker '% Paid'."),
    ("App Sales Revenue", f'CALCULATE ( {PR}, KEEPFILTERS ( revenue_orders_tbl[Sales Channel] = "App" ) )',
     "Double", RAND, "Channels", "Paid revenue from app sales (signup_agent = App Sale)."),
    ("App Sales Share", f"DIVIDE ( [App Sales Revenue], {PR} )", "Double", PCT, "Channels", "Share of paid revenue from app sales."),
    ("Local Domain Revenue", f'CALCULATE ( {PR}, KEEPFILTERS ( revenue_orders_tbl[Sub Category] = "Domains" ), KEEPFILTERS ( revenue_orders_tbl[Domain Region] = "Local" ) )',
     "Double", RAND, "Domains", "Paid domain-registration revenue for local TLDs (.co.za, .africa …)."),
    ("International Domain Revenue", f'CALCULATE ( {PR}, KEEPFILTERS ( revenue_orders_tbl[Sub Category] = "Domains" ), KEEPFILTERS ( revenue_orders_tbl[Domain Region] = "International" ) )',
     "Double", RAND, "Domains", "Paid domain-registration revenue for international TLDs."),
    ("Domains Added", f"""{PAID_DATE}
    CALCULATE (
        DISTINCTCOUNT ( revenue_orders_tbl[service_id] ),
        revenue_orders_tbl[invoice_status] = "Paid",
        KEEPFILTERS ( revenue_orders_tbl[Sub Category] = "Domains" ),
        REMOVEFILTERS ( 'Calendar' ),
        TREATAS ( _dates, revenue_orders_tbl[Revenue Date] )
    )""", "Double", "#,0", "Domains", "Domain registrations/transfers on paid orders, by paid date."),
    ("Local Domains Added", 'CALCULATE ( [Domains Added], KEEPFILTERS ( revenue_orders_tbl[Domain Region] = "Local" ) )',
     "Double", "#,0", "Domains", "Excel: No. of Local Domains Added (paid orders only)."),
    ("International Domains Added", 'CALCULATE ( [Domains Added], KEEPFILTERS ( revenue_orders_tbl[Domain Region] = "International" ) )',
     "Double", "#,0", "Domains", "Excel: No. of Int. Domains Added (paid orders only)."),
    ("Services Sold", f"""{PAID_DATE}
    CALCULATE (
        DISTINCTCOUNT ( revenue_orders_tbl[service_id] ),
        revenue_orders_tbl[invoice_status] = "Paid",
        REMOVEFILTERS ( 'Calendar' ),
        TREATAS ( _dates, revenue_orders_tbl[Revenue Date] )
    )""", "Double", "#,0", "Products", "Services/domains on paid orders, by paid date. Split by service_status to see how many are still active."),
    ("Revenue % of Total", f"""DIVIDE (
    {PR},
    CALCULATE (
        {PR},
        ALLSELECTED ( revenue_orders_tbl[Category], revenue_orders_tbl[Sub Category], revenue_orders_tbl[Product Name] )
    )
)""", "Double", PCT, "Products", "Share of the selected total, for the product matrix."),
    ("Period Label", """VAR _first = MIN ( 'Calendar'[Date (format)] )
VAR _last = MAX ( 'Calendar'[Date (format)] )
RETURN FORMAT ( _first, "d mmm yyyy" ) & " – " & FORMAT ( _last, "d mmm yyyy" )""",
     "Text", None, "Labels", "Selected period."),
    ("Data As Of", """VAR _d = CALCULATE ( MAX ( orders_invoices_tbl[order_date] ), REMOVEFILTERS () )
RETURN "Data to " & FORMAT ( _d, "d mmm yyyy" ) & " · excl. VAT · revenue on paid date\"""",
     "Text", None, "Labels", "Latest order date in the model."),
    ("Overview Insight", f"""VAR _rev = {PR}
VAR _ord = {PO}
VAR _d = [Paid Revenue Δ%]
VAR _top =
    TOPN ( 1, ADDCOLUMNS ( VALUES ( revenue_orders_tbl[Category] ), "@r", {PR} ), [@r], DESC )
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
    )""", "Text", None, "Labels", "One-sentence summary for the Overview page."),
]

def report_extensions():
    out = []
    for name, expr, dt, fmt, folder, desc in MEASURES:
        mm = {"name": name, "dataType": dt, "expression": expr, "displayFolder": folder, "description": desc}
        if fmt: mm["formatString"] = fmt
        out.append(mm)
    return {"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/reportExtension/1.0.0/schema.json",
            "name": "extension", "entities": [{"name": RO, "measures": out}]}

# ---------------------------------------------------------------- frame (header, rail, KPI row)
W, H = 1500, 900
RAIL_X, RAIL_W = 16, 224
CX, CW = 256, 1228          # content area x / width
KPI_Y, KPI_H = 80, 100
NOTE_Y, NOTE_H = 188, 30
GRID_Y = 226
ROW_H = 323
GAP = 12

SLICERS = [  # (key, header, field, kind)
    ("period", "Period", col("Date (format)", CAL), "relative"),
    ("category", "Category", col("Category"), "dropdown"),
    ("subcat", "Sub category", col("Sub Category"), "dropdown"),
    ("product", "Product", col("Product Name"), "dropdown"),
    ("custtype", "Customer type", col("type_of_customer"), "dropdown"),
    ("tenure", "Account age", col("customer_tenure_group"), "dropdown"),
    ("channel", "Sales channel", col("Sales Channel"), "dropdown"),
    ("region", "Domain region", col("Domain Region"), "dropdown"),
    ("province", "Province", col("client_state"), "dropdown"),
    ("billing", "Billing cycle", col("billing_cycle"), "dropdown"),
    ("paymethod", "Payment method", col("invoice_paymethod"), "dropdown"),
    ("source", "Heard about us", col("heard_about_us"), "dropdown"),
]

def slicer_visual(header, field, kind):
    objs = {
        "header": [{"properties": {"show": B(True), "text": S(header), "fontColor": C(GREY), "bold": B(False),
                                   "fontFamily": S(FONT_SB), "textSize": D(9)}}],
        "items": [{"properties": {"fontColor": C(BLACK), "fontFamily": S(FONT), "textSize": D(10),
                                  "background": C(WHITE), "outlineStyle": D(0)}}],
        "general": [{"properties": {"outlineColor": C(BORDER), "outlineWeight": D(1)}}],
    }
    if kind == "relative":
        objs["data"] = [{"properties": {"mode": S("Relative"), "relativeRange": S("Last"),
                                        "relativeDuration": D(30), "relativePeriod": S("Days")}}]
        objs["dateRange"] = [{"properties": {"includeToday": B(True)}}]
        objs["date"] = [{"properties": {"textSize": D(10), "fontColor": C(BLACK), "fontFamily": S(FONT)}}]
        objs["numericInputStyle"] = [{"properties": {"textSize": D(10), "fontColor": C(BLACK), "background": C(WHITE)}}]
        rel = f_relative("Date (format)", CAL, 30, 0, "period-default")["filter"]
        objs["general"][0]["properties"]["filter"] = {"filter": rel}
        sort_def = {"sort": [{"field": field, "direction": "Ascending"}], "isDefaultSort": True}
    else:
        objs["data"] = [{"properties": {"mode": S("Dropdown")}}]
        objs["selection"] = [{"properties": {"selectAllCheckboxEnabled": B(True), "singleSelect": B(False)}}]
        sort_def = {"isDefaultSort": True}
    return {"visualType": "slicer",
            "query": {"queryState": {"Values": {"projections": [proj(field, active=True)]}}, "sortDefinition": sort_def},
            "objects": objs,
            "visualContainerObjects": {
                "title": [{"properties": {"show": B(False), "text": S(header)}}],
                "background": [{"properties": {"show": B(False)}}],
                "border": [{"properties": {"show": B(False)}}],
                "padding": [{"properties": {"top": D(0), "bottom": D(0), "left": D(0), "right": D(0)}}],
                "visualHeader": [{"properties": {"show": B(False)}}],
            },
            "syncGroup": {"groupName": header, "fieldChanges": True, "filterChanges": True},
            "drillFilterOtherVisuals": True}

def shape(fill, border=None, radius=0):
    o = {"shape": [{"properties": {"tileShape": S("rectangle"), "roundEdge": D(radius)}}],
         "fill": [{"properties": {"show": B(True), "fillColor": C(fill), "transparency": D(0)}, "selector": {"id": "default"}}],
         "outline": [{"properties": {"show": B(border is not None), "lineColor": C(border or fill), "weight": D(1)},
                      "selector": {"id": "default"}}]}
    return {"visualType": "shape", "objects": o,
            "visualContainerObjects": {"visualHeader": [{"properties": {"show": B(False)}}]},
            "drillFilterOtherVisuals": True}

def textbox(runs_paragraphs, alt):
    paras = [{"textRuns": [{"value": t, "textStyle": st} for t, st in p]} for p in runs_paragraphs]
    return {"visualType": "textbox", "objects": {"general": [{"properties": {"paragraphs": paras}}]},
            "visualContainerObjects": {"title": [{"properties": {"show": B(False), "text": S(alt)}}],
                                       "background": [{"properties": {"show": B(False)}}],
                                       "padding": [{"properties": {"top": D(0), "bottom": D(0), "left": D(0), "right": D(0)}}],
                                       "visualHeader": [{"properties": {"show": B(False)}}]},
            "drillFilterOtherVisuals": True}

def text_card(measures, align="right", size=10, colour=GREY, alt="Text"):
    """cardVisual used as a text line (no frame)."""
    v = {"visualType": "cardVisual",
         "query": {"queryState": {"Data": {"projections": [proj(f, n) for f, n in measures]}}},
         "objects": {
             "layout": [{"properties": {"columnCount": I(len(measures)), "alignment": S("middle")}},
                        {"properties": {"paddingUniform": I(0), "backgroundShow": B(False)}, "selector": {"id": "default"}}],
             "label": [{"properties": {"show": B(False)}, "selector": {"id": "default"}}],
             "outline": [{"properties": {"show": B(False)}, "selector": {"id": "default"}}],
             "divider": [{"properties": {"show": B(False)}, "selector": {"id": "default"}}],
             "accentBar": [{"properties": {"show": B(False)}, "selector": {"id": "default"}}],
             "value": [{"properties": {"fontSize": D(size), "fontFamily": S(FONT), "fontColor": C(colour),
                                       "horizontalAlignment": S(align)}, "selector": {"id": "default"}}],
         },
         "visualContainerObjects": {"title": [{"properties": {"show": B(False), "text": S(alt)}}],
                                    "background": [{"properties": {"show": B(False)}}],
                                    "border": [{"properties": {"show": B(False)}}],
                                    "padding": [{"properties": {"top": D(0), "bottom": D(0), "left": D(0), "right": D(0)}}],
                                    "visualHeader": [{"properties": {"show": B(False)}}]},
         "drillFilterOtherVisuals": True}
    return v

KPIS = [  # title, main field, main fmt (units), caption field, caption colour field, accent
    ("Paid revenue", m("Paid Revenue (Products)"), 1000, x("KPI Revenue Δ"), x("KPI Revenue Δ Colour"), CYAN),
    ("Paid orders", m("Paid Orders (Products)"), None, x("KPI Orders Δ"), x("KPI Orders Δ Colour"), CYAN),
    ("Average order value", x("Average Order Value"), None, x("KPI AOV Δ"), x("KPI AOV Δ Colour"), CYAN),
    ("New-customer share", x("New Customer Share"), None, x("KPI New Share Δ"), x("KPI New Share Δ Colour"), GREEN),
    ("Unpaid (collectable)", x("Open Unpaid Revenue"), 1000, x("KPI Unpaid Caption"), None, AMBER),
    ("Cancelled (lost)", x("Cancelled Revenue"), 1000, x("KPI Cancelled Caption"), None, RED),
]

def kpi_card(title, main, units, caption, caption_colour, accent):
    mq, cq = qref(main), qref(caption)
    value_objs = [
        {"properties": {"fontSize": D(24), "fontFamily": S(FONT_SB), "fontColor": C(BLACK),
                        "horizontalAlignment": S("left"), "showBlankAs": S("–")}, "selector": {"id": "default"}},
        {"properties": {"fontSize": D(10), "fontFamily": S(FONT), "fontColor": C(GREY)}, "selector": {"metadata": cq}},
    ]
    if units:
        value_objs.append({"properties": {"labelDisplayUnits": D(units), "labelPrecision": I(1)}, "selector": {"metadata": mq}})
    if caption_colour:
        value_objs.append({"properties": {"fontColor": {"solid": {"color": {"expr": caption_colour}}}},
                           "selector": {"metadata": cq}})
    return {"visualType": "cardVisual",
            "query": {"queryState": {"Data": {"projections": [proj(main, title), proj(caption, "Change")]}}},
            "objects": {
                "layout": [{"properties": {"columnCount": I(1), "alignment": S("top"), "cellPadding": I(0)}},
                           {"properties": {"paddingUniform": I(0), "backgroundShow": B(False)}, "selector": {"id": "default"}}],
                "label": [{"properties": {"show": B(False)}, "selector": {"id": "default"}}],
                "divider": [{"properties": {"show": B(False)}, "selector": {"id": "default"}}],
                "outline": [{"properties": {"show": B(False)}, "selector": {"id": "default"}}],
                "spacing": [{"properties": {"verticalSpacing": I(2)}, "selector": {"id": "default"}}],
                "accentBar": [{"properties": {"show": B(False)}, "selector": {"id": "default"}}],
                "value": value_objs,
            },
            "visualContainerObjects": {
                **card_frame(title),
                "title": [{"properties": {"show": B(True), "text": S(title), "fontFamily": S(FONT_SB), "fontSize": D(10),
                                          "fontColor": C(GREY), "alignment": S("left")}}],
                "border": [{"properties": {"show": B(True), "color": C(BORDER), "radius": D(8), "width": D(1)}}],
                "padding": [{"properties": {"top": D(10), "bottom": D(6), "left": D(14), "right": D(10)}}],
                "visualHeader": [{"properties": {"show": B(False)}}],
            },
            "drillFilterOtherVisuals": True}

def frame(page, title, subtitle, note_measure=None, note_text=None, with_kpis=True):
    vs = []
    # header band
    vs.append(container(page, "hdr-bg", 0, 0, W, 64, shape(WHITE, BORDER), z=0))
    vs.append(container(page, "hdr-title", 24, 8, 760, 28, textbox(
        [[("Daily Sales  ", {"fontFamily": FONT_SB, "fontSize": "18pt", "color": CYAN}),
          ("· " + title, {"fontFamily": FONT_SB, "fontSize": "18pt", "color": BLACK})]], "Title"), z=100))
    vs.append(container(page, "hdr-sub", 24, 38, 760, 20, textbox(
        [[(subtitle, {"fontFamily": FONT, "fontSize": "10pt", "color": GREY})]], "Subtitle"), z=110))
    vs.append(container(page, "hdr-dates", 800, 10, 540, 44, text_card(
        [(x("Period Label"), "Period"), (x("Data As Of"), "Data as of")], align="right", size=10, alt="Data updated"), z=120))
    # logo
    vs.append(container(page, "hdr-logo", 1366, 12, 110, 40, {
        "visualType": "image",
        "objects": {"image": [{"properties": {"sourceFile": {"image": {
            "name": S("1-grid_logo_resized.png"),
            "url": {"expr": {"ResourcePackageItem": {"PackageName": "RegisteredResources", "PackageType": 1,
                                                       "ItemName": "1-grid_logo_resized4072192553301752.png"}}},
            "scaling": S("Fit")}}}}]},
        "visualContainerObjects": {"title": [{"properties": {"show": B(False), "text": S("1-grid logo")}}],
                                   "visualHeader": [{"properties": {"show": B(False)}}]},
        "drillFilterOtherVisuals": True}, z=130))
    # filter rail
    vs.append(container(page, "rail-bg", RAIL_X, KPI_Y, RAIL_W, H - KPI_Y - 16, shape(WHITE, BORDER, 8), z=200))
    vs.append(container(page, "rail-title", RAIL_X + 14, KPI_Y + 10, 120, 22, textbox(
        [[("Filters", {"fontFamily": FONT_SB, "fontSize": "11pt", "color": BLACK})]], "Filters heading"), z=210))
    vs.append(container(page, "rail-clear", RAIL_X + 120, KPI_Y + 8, 92, 26, {
        "visualType": "actionButton",
        "objects": {
            "icon": [{"properties": {"show": B(False)}, "selector": {"id": "default"}}],
            "text": [{"properties": {"show": B(True), "text": S("Clear all"), "fontColor": C(DCYAN), "fontSize": D(9),
                                     "fontFamily": S(FONT_SB)}, "selector": {"id": "default"}}],
            "fill": [{"properties": {"show": B(True), "fillColor": C(WHITE)}, "selector": {"id": "default"}}],
            "outline": [{"properties": {"show": B(True), "lineColor": C(BORDER), "weight": D(1), "roundEdge": D(6)},
                         "selector": {"id": "default"}}]},
        "visualContainerObjects": {"visualLink": [{"properties": {"show": B(True), "type": S("ClearAllSlicers")}}],
                                   "title": [{"properties": {"show": B(False), "text": S("Clear all slicers")}}],
                                   "visualHeader": [{"properties": {"show": B(False)}}]},
        "drillFilterOtherVisuals": True}, z=215))
    y = KPI_Y + 44
    for i, (key, header, field, kind) in enumerate(SLICERS):
        h = 58 if kind == "relative" else 52
        vs.append(container(page, f"slicer-{key}", RAIL_X + 12, y, RAIL_W - 24, h,
                            slicer_visual(header, field, kind), z=300 + i))
        y += h + 6
    vs.append(container(page, "rail-foot", RAIL_X + 12, H - 16 - 58, RAIL_W - 24, 48, textbox(
        [[("Values excl. VAT. Paid revenue lands on the payment date; unpaid and cancelled on the order date.",
           {"fontFamily": FONT, "fontSize": "8pt", "color": GREY})]], "Footnote"), z=290))
    # KPI row
    if with_kpis:
        kw = (CW - 5 * 10) / 6
        for i, k in enumerate(KPIS):
            vs.append(container(page, f"kpi-{i}", round(CX + i * (kw + 10)), KPI_Y, round(kw), KPI_H, kpi_card(*k), z=400 + i))
    # insight / note line
    if note_measure is not None:
        vs.append(container(page, "note", CX, NOTE_Y, CW, NOTE_H, text_card([(note_measure, "Insight")], align="left",
                                                                            size=11, colour=BLACK, alt="Insight"), z=450))
    elif note_text:
        vs.append(container(page, "note", CX, NOTE_Y, CW, NOTE_H, textbox(
            [[(note_text, {"fontFamily": FONT, "fontSize": "10pt", "color": GREY})]], "Page note"), z=450))
    return vs

def slicer_names(page):
    return [uid(f"{page}/slicer-{k}") for k, *_ in SLICERS]

# ---------------------------------------------------------------- chart builders
TT_CAT, TT_WEEK, TT_REV = "58b168948b0de81ee9b7", "a8101c02ae3408a789b9", "055cb1e468097899a1d0"

def bar(cat, values, title, *, kind="clusteredBarChart", series=None, colours=None, colour_field=None,
        single_colour=CYAN, tooltip=TT_CAT, sort_by=None, sort_desc=True, label_units=None, legend=False,
        value_axis=False, extra_tooltips=None):
    qs = {"Category": {"projections": [proj(cat, active=True)]},
          "Y": {"projections": [proj(f, n) for f, n in values]}}
    if series is not None:
        qs["Series"] = {"projections": [proj(series)]}
    if extra_tooltips:
        qs["Tooltips"] = {"projections": [proj(f, n) for f, n in extra_tooltips]}
    objs = axis_objects(value_axis=value_axis, label_units=label_units, legend=legend)
    if colours:
        objs["dataPoint"] = colour_points(colour_field if colour_field is not None else (series or cat), colours)
    elif series is None and len(values) == 1:
        objs["dataPoint"] = [{"properties": {"fill": C(single_colour)}}]
    if series is not None or len(values) > 1:
        objs["legend"][0]["properties"]["show"] = B(True)
    return {"visualType": kind,
            "query": {"queryState": qs, "sortDefinition": sort(sort_by or values[0][0], sort_desc)},
            "objects": objs,
            "visualContainerObjects": card_frame(title, tooltip),
            "drillFilterOtherVisuals": True}

def combo(cat, col_val, line_val, title, tooltip=TT_WEEK, col_colour=CYAN, line_colour=GREY, label_units=1000):
    objs = axis_objects(value_axis=True, labels=False, legend=True)
    objs["valueAxis"][0]["properties"].update({"secShow": B(True), "secShowAxisTitle": B(False), "labelDisplayUnits": D(1000)})
    objs["dataPoint"] = [
        {"properties": {"fill": C(col_colour)}, "selector": {"metadata": qref(col_val[0])}},
        {"properties": {"fill": C(line_colour)}, "selector": {"metadata": qref(line_val[0])}}]
    objs["lineStyles"] = [{"properties": {"strokeWidth": D(2), "showMarker": B(True), "markerSize": D(3)}}]
    return {"visualType": "lineClusteredColumnComboChart",
            "query": {"queryState": {"Category": {"projections": [proj(cat, active=True)]},
                                     "Y": {"projections": [proj(*col_val)]},
                                     "Y2": {"projections": [proj(*line_val)]}},
                      "sortDefinition": sort(cat, False)},
            "objects": objs,
            "visualContainerObjects": card_frame(title, tooltip),
            "drillFilterOtherVisuals": True}

def matrix(rows, values, title, *, tooltip=TT_REV, sort_field=None, sort_desc=True, row_cols=None, expand=False):
    qs = {"Rows": {"projections": [proj(f) for f in rows]},
          "Values": {"projections": [proj(f, n) for f, n in values]}}
    v = {"visualType": "pivotTable",
         "query": {"queryState": qs, "sortDefinition": sort(sort_field or values[0][0], sort_desc)},
         "objects": {
             "grid": [{"properties": {"gridVertical": B(False), "gridHorizontal": B(True), "gridHorizontalColor": C(BORDER),
                                      "rowPadding": D(4), "textSize": D(10)}}],
             "columnHeaders": [{"properties": {"fontColor": C(GREY), "backColor": C(WHITE), "fontFamily": S(FONT_SB),
                                               "fontSize": D(9), "alignment": S("Right"), "wordWrap": B(True),
                                               "columnAdjustment": S("growToFit")}}],
             "rowHeaders": [{"properties": {"fontColor": C(BLACK), "fontSize": D(10), "steppedLayoutIndentation": D(14),
                                            "showExpandCollapseButtons": B(True)}}],
             "values": [{"properties": {"fontColorPrimary": C(BLACK), "backColorPrimary": C(WHITE),
                                        "backColorSecondary": C(WHITE), "fontSize": D(10)}}],
             "total": [{"properties": {"fontFamily": S(FONT_SB), "backColor": C("#E6F8FB"), "fontColor": C(BLACK)}}],
             "subTotals": [{"properties": {"rowSubtotals": B(True)}}],
         },
         "visualContainerObjects": card_frame(title, tooltip),
         "drillFilterOtherVisuals": True}
    # data bars on the first value column (paid revenue)
    v["objects"]["columnFormatting"] = [{"properties": {"dataBars": {
        "positiveColor": C(PALE), "negativeColor": C("#FBD5D6"), "axisColor": C(BORDER),
        "reverseDirection": B(False), "hideText": B(False)}}, "selector": {"metadata": qref(values[0][0])}}]
    return v

def table(columns, title, tooltip=None):
    return {"visualType": "tableEx",
            "query": {"queryState": {"Values": {"projections": [proj(f, n) for f, n in columns]}},
                      "sortDefinition": sort(columns[-1][0], True)},
            "objects": {
                "grid": [{"properties": {"gridVertical": B(False), "gridHorizontalColor": C(BORDER), "rowPadding": D(3), "textSize": D(9)}}],
                "columnHeaders": [{"properties": {"fontColor": C(GREY), "backColor": C(WHITE), "fontFamily": S(FONT_SB), "fontSize": D(9)}}],
                "values": [{"properties": {"fontColorPrimary": C(BLACK), "backColorPrimary": C(WHITE), "backColorSecondary": C("#FAFBFC")}}],
                "total": [{"properties": {"totals": B(True), "fontFamily": S(FONT_SB)}}]},
            "visualContainerObjects": card_frame(title, tooltip),
            "drillFilterOtherVisuals": True}

def donut(cat, val, title, colours, tooltip=TT_CAT):
    return {"visualType": "donutChart",
            "query": {"queryState": {"Category": {"projections": [proj(cat, active=True)]},
                                     "Y": {"projections": [proj(*val)]}},
                      "sortDefinition": sort(val[0], True)},
            "objects": {"legend": [{"properties": {"show": B(True), "position": S("Top"), "showTitle": B(False), "fontSize": D(9), "labelColor": C(GREY)}}],
                        "labels": [{"properties": {"show": B(True), "labelStyle": S("Percent of total"), "fontSize": D(10), "color": C(BLACK)}}],
                        "slices": [{"properties": {"innerRadiusRatio": D(62)}}],
                        "dataPoint": colour_points(cat, colours)},
            "visualContainerObjects": card_frame(title, tooltip),
            "drillFilterOtherVisuals": True}

def value_grid(cells, title):
    """cardVisual grid of several values with labels below (e.g. the domain block)."""
    return {"visualType": "cardVisual",
            "query": {"queryState": {"Data": {"projections": [proj(f, n) for f, n, _ in cells]}}},
            "objects": {
                "layout": [{"properties": {"columnCount": I(len(cells) // 2 if len(cells) > 3 else len(cells)), "alignment": S("top"), "cellPadding": I(4)}},
                           {"properties": {"paddingUniform": I(4), "backgroundShow": B(False)}, "selector": {"id": "default"}}],
                "label": [{"properties": {"show": B(True), "position": S("belowValue"), "fontSize": D(9), "fontColor": C(GREY),
                                          "fontFamily": S(FONT)}, "selector": {"id": "default"}}],
                "divider": [{"properties": {"show": B(False)}, "selector": {"id": "default"}}],
                "outline": [{"properties": {"show": B(False)}, "selector": {"id": "default"}}],
                "accentBar": [{"properties": {"show": B(False)}, "selector": {"id": "default"}}],
                "value": [{"properties": {"fontSize": D(18), "fontFamily": S(FONT_SB), "fontColor": C(BLACK),
                                          "horizontalAlignment": S("left"), "showBlankAs": S("0")}, "selector": {"id": "default"}}]
                         + [{"properties": {"fontColor": C(colr)}, "selector": {"metadata": qref(f)}} for f, _, colr in cells if colr],
            },
            "visualContainerObjects": card_frame(title),
            "drillFilterOtherVisuals": True}

def no_date_interactions(page, targets):
    return [{"source": uid(f"{page}/slicer-period"), "target": uid(f"{page}/{t}"), "type": "NoFilter"} for t in targets]

# ---------------------------------------------------------------- pages
pages = {}

def add_page(pid, display, visuals, interactions=None, hidden=False, filters=None, ptype=None, width=W, height=H, bg=PAGEBG):
    p = {"$schema": PG, "name": pid, "displayName": display, "displayOption": "FitToPage", "height": height, "width": width,
         "objects": {"background": [{"properties": {"color": C(bg), "transparency": D(0)}}],
                     "outspace": [{"properties": {"color": C(bg)}}]}}
    if hidden: p["visibility"] = "HiddenInViewMode"
    if ptype: p["type"] = ptype; p["displayOption"] = "ActualSize"
    if filters: p["filterConfig"] = {"filters": filters}
    if interactions: p["visualInteractions"] = interactions
    pages[pid] = (p, visuals)

C1W, C2W = 808, CW - 808 - GAP          # 808 / 408 split
H1W, H2W = 604, CW - 604 - GAP          # 604 / 612 split
R1, R2 = GRID_Y, GRID_Y + ROW_H + GAP
PRm, POm = m("Paid Revenue (Products)"), m("Paid Orders (Products)")
DATE = col("Date (format)", CAL)

# ---- Overview
pid = uid("page/overview")
v = frame(pid, "Overview", "Are paid sales on track this period, and what is driving them?", note_measure=x("Overview Insight"))
v.append(container(pid, "daily", CX, R1, C1W, ROW_H, combo(DATE, (PRm, "Paid revenue"), (POm, "Paid orders"),
    "How did paid revenue move day by day? Paid revenue (bars) and paid orders (line)"), z=1000))
v.append(container(pid, "bycat", CX + C1W + GAP, R1, C2W, ROW_H, bar(col("Category"), [(PRm, "Paid revenue")],
    "Which categories earn the revenue?", colours=CATEGORY_COLOURS, label_units=1000), z=1010))
monthly = combo(col("MonthYear", CAL), (PRm, "Paid revenue"), (x("Paid Revenue LY"), "Same month last year"),
                "Are we ahead of last year? Monthly paid revenue, last 13 months", tooltip=None, line_colour=AMBER)
monthly["query"]["sortDefinition"] = sort(col("MonthYear", CAL), False)
v.append(container(pid, "monthly", CX, R2, H1W, ROW_H, monthly,
                   filters=[f_relative("Date (format)", CAL, 13, 2, "overview-13m")], z=1020))
top5 = bar(col("Product Name"), [(PRm, "Paid revenue")], "Which 5 products earn the most?", label_units=1000)
v.append(container(pid, "top5", CX + H1W + GAP, R2, 300, ROW_H, top5,
                   filters=[f_topn("Product Name", m_src("Paid Revenue (Products)"), 5, "overview-top5")], z=1030))
v.append(container(pid, "newexist", CX + H1W + GAP + 300 + GAP, R2, H2W - 300 - GAP, ROW_H, donut(
    col("type_of_customer"), (PRm, "Paid revenue"), "How much comes from new customers?", CUSTOMER_COLOURS), z=1040))
add_page(pid, "Overview", v, interactions=no_date_interactions(pid, ["monthly"]))

# ---- Daily Sales
pid = uid("page/daily")
v = frame(pid, "Daily", "What sold each day? The day-by-day log the team used to keep in Excel.",
          note_text="Select a day in the table to see what sold that day on the right. % paid compares paid value with everything invoiced for orders placed that day.")
daily_vals = [(PRm, "Paid revenue"), (POm, "Paid orders"), (x("Average Order Value"), "AOV"),
              (x("New Customer Share"), "New-customer %"), (x("App Sales Revenue"), "App sales"),
              (x("Local Domain Revenue"), "Local domains R"), (x("International Domain Revenue"), "Int. domains R"),
              (x("Local Domains Added"), "Local domains #"), (x("International Domains Added"), "Int. domains #"),
              (x("Invoiced Value"), "Invoiced (all)"), (x("Paid Share of Invoiced"), "% paid")]
dm = matrix([DATE], daily_vals, "What sold each day? Paid sales, domains and collection by day", tooltip=TT_WEEK,
            sort_field=DATE, sort_desc=True)
v.append(container(pid, "daylog", CX, R1, C1W + GAP + C2W - 420 - GAP, ROW_H * 2 + GAP, dm, z=1000))
rx = CX + CW - 420
v.append(container(pid, "daycat", rx, R1, 420, ROW_H, bar(col("Sub Category"), [(PRm, "Paid revenue")],
    "What sold on the selected days? Paid revenue by sub category", label_units=None), z=1010))
v.append(container(pid, "weekday", rx, R2, 420, ROW_H, bar(col("Weekday", CAL), [(PRm, "Paid revenue")],
    "Which weekdays sell best?", kind="clusteredColumnChart", sort_by=col("Weekday", CAL), sort_desc=False,
    label_units=1000, tooltip=TT_WEEK), z=1020))
add_page(pid, "Daily Sales", v)

# ---- Products
pid = uid("page/products")
v = frame(pid, "Products", "Which products earn the revenue, and is the mix changing?",
          note_text="Order counts are per product: an order with a domain and hosting counts once in each, so product rows add up to more than the Paid orders card.")
pm = matrix([col("Category"), col("Sub Category"), col("Product Name")],
            [(PRm, "Paid revenue"), (x("Revenue % of Total"), "% of total"), (POm, "Paid orders"),
             (x("Average Order Value"), "AOV"), (x("Paid Revenue Δ%"), "vs prior period")],
            "Which products earn the revenue? Category › sub category › product")
v.append(container(pid, "matrix", CX, R1, C1W, ROW_H * 2 + GAP, pm, z=1000))
dom = value_grid([(x("Local Domain Revenue"), "Local domains (R)", CYAN), (x("International Domain Revenue"), "International (R)", GREY),
                  (x("Local Domains Added"), "Local domains added", None), (x("International Domains Added"), "Int. domains added", None)],
                 "Are local domains holding up? Paid domain registrations")
v.append(container(pid, "domains", CX + C1W + GAP, R1, C2W, 150, dom, z=1010))
tld = bar(col("TLD"), [(PRm, "Paid revenue")], "Which extensions sell? Top 8 TLDs by paid revenue", label_units=None)
v.append(container(pid, "tld", CX + C1W + GAP, R1 + 150 + GAP, C2W, ROW_H - 150 - GAP, tld,
                   filters=[f_topn("TLD", m_src("Paid Revenue (Products)"), 8, "products-tld"),
                            f_in("Sub Category", ["Domains"], name=uid("products/tld/subcat"))], z=1020))
svc = bar(col("Category"), [(x("Services Sold"), "Services sold")],
          "Are services sold this period still active? Status today",
          kind="hundredPercentStackedBarChart", series=col("service_status"), colours=SERVICE_COLOURS, legend=True,
          sort_by=x("Services Sold"))
svc["objects"]["labels"][0]["properties"]["show"] = B(False)
v.append(container(pid, "svcstatus", CX + C1W + GAP, R2, C2W, ROW_H, svc, z=1030))
add_page(pid, "Products", v)

# ---- Customers & Channels
pid = uid("page/customers")
v = frame(pid, "Customers & Channels", "Who is buying, how established are they, and through which channel?")
wk = bar(col("WeekDate", CAL), [(PRm, "Paid revenue")], "Is the new-customer share growing? Weekly paid revenue by customer type",
         kind="hundredPercentStackedColumnChart", series=col("type_of_customer"), colours=CUSTOMER_COLOURS,
         sort_by=col("WeekDate", CAL), sort_desc=False, tooltip=TT_WEEK, legend=True)
wk["objects"]["labels"][0]["properties"]["show"] = B(False)
v.append(container(pid, "newshare", CX, R1, H1W, ROW_H, wk, z=1000))
v.append(container(pid, "whatbuy", CX + H1W + GAP, R1, H2W, ROW_H, bar(col("Category"), [(PRm, "Paid revenue")],
    "What do new and existing customers buy?", series=col("type_of_customer"), colours=CUSTOMER_COLOURS, legend=True,
    label_units=1000), z=1010))
tw = 400
ten = bar(col("customer_tenure_group"), [(PRm, "Paid revenue")], "How long have buyers been with us? Paid revenue by account age",
          label_units=1000, sort_by=agg("customer_tenure_sort", 3), sort_desc=False,
          extra_tooltips=[(agg("customer_tenure_sort", 3), "Sort")])
v.append(container(pid, "tenure", CX, R2, tw, ROW_H, ten, z=1020))
v.append(container(pid, "channel", CX + tw + GAP, R2, 404, ROW_H, bar(col("signup_agent"), [(PRm, "Paid revenue")],
    "How much comes through the app or an agent?", colours=CHANNEL_COLOURS, label_units=1000), z=1030))
src = bar(col("heard_about_us"), [(PRm, "Paid revenue")], "Which marketing sources bring revenue? Top 8", label_units=1000)
v.append(container(pid, "source", CX + tw + GAP + 404 + GAP, R2, CW - tw - 404 - 2 * GAP, ROW_H, src,
                   filters=[f_topn("heard_about_us", m_src("Paid Revenue (Products)"), 8, "cust-source")], z=1040))
add_page(pid, "Customers & Channels", v)

# ---- Collections
pid = uid("page/collections")
v = frame(pid, "Collections", "How much invoiced value is still uncollected, and where?",
          note_text="Invoice value by the week the order was placed and its status today. Unpaid (amber) can still be collected; cancelled (red) is lost.")
st = bar(col("WeekDate", CAL), [(m("RO Invoice Total"), "Invoice value")], "Is invoiced value being collected? Weekly invoice value by status",
         kind="columnChart", series=col("invoice_status"), colours=STATUS_COLOURS, sort_by=col("WeekDate", CAL),
         sort_desc=False, tooltip=TT_WEEK, legend=True, value_axis=True)
st["objects"]["labels"][0]["properties"]["show"] = B(False)
v.append(container(pid, "status", CX, R1, C1W, ROW_H, st, z=1000))
v.append(container(pid, "paymethod", CX + C1W + GAP, R1, C2W, ROW_H, bar(col("invoice_paymethod"), [(x("Paid Share of Invoiced"), "% paid")],
    "Which payment methods collect best? % of invoiced value paid", single_colour=CYAN,
    extra_tooltips=[(x("Invoiced Value"), "Invoiced"), (x("Open Unpaid Revenue"), "Unpaid")]), z=1010))
uc = bar(col("Category"), [(x("Open Unpaid Revenue"), "Unpaid (collectable)"), (x("Cancelled Revenue"), "Cancelled (lost)")],
         "Where is value stuck? Unpaid and cancelled by category", label_units=1000, legend=True)
uc["objects"]["dataPoint"] = [{"properties": {"fill": C(AMBER)}, "selector": {"metadata": qref(x("Open Unpaid Revenue"))}},
                              {"properties": {"fill": C(RED)}, "selector": {"metadata": qref(x("Cancelled Revenue"))}}]
v.append(container(pid, "stuck", CX, R2, H1W, ROW_H, uc, z=1020))
tb = table([(col("order_id"), "Order"), (col("invoice_id"), "Invoice"), (col("invoice_date"), "Invoiced"),
            (col("invoice_duedate"), "Due"), (col("invoice_paymethod"), "Method"), (col("invoice_status"), "Status"),
            (x("Open Unpaid Revenue"), "Unpaid (R)")], "Which invoices should we chase? Top 50 open invoices")
v.append(container(pid, "chase", CX + H1W + GAP, R2, H2W, ROW_H, tb,
                   filters=[f_topn("order_id", m_src("Unpaid Revenue (Products)"), 50, "coll-top50"),
                            f_in("Status_Filter", ["Unpaid", "Payment Pending", "Collections", "Draft"], name=uid("coll/chase/status"))], z=1030))
add_page(pid, "Collections", v)

# ---- Frame template (hidden): duplicate this page to build new pages
pid = uid("page/template")
v = frame(pid, "Page title", "One-line business question this page answers.",
          note_text="Template: duplicate this page, keep the header, rail and KPI row, and place charts on the 808/408 or 604/612 grid below (y 226 and 561, height 323).")
add_page(pid, "_Frame template", v, hidden=True)

# ---------------------------------------------------------------- tooltip pages (restyled, same ids)
def tt_cards(pid, w, measures):
    return container(pid, "tt-cards", 8, 8, w - 16, 76, {
        "visualType": "cardVisual",
        "query": {"queryState": {"Data": {"projections": [proj(f, n) for f, n in measures]}}},
        "objects": {
            "layout": [{"properties": {"columnCount": I(len(measures)), "alignment": S("top"), "cellPadding": I(4)}},
                       {"properties": {"paddingUniform": I(4), "backgroundShow": B(False)}, "selector": {"id": "default"}}],
            "label": [{"properties": {"show": B(True), "position": S("belowValue"), "fontSize": D(9), "fontColor": C(GREY)}, "selector": {"id": "default"}}],
            "divider": [{"properties": {"show": B(False)}, "selector": {"id": "default"}}],
            "outline": [{"properties": {"show": B(False)}, "selector": {"id": "default"}}],
            "accentBar": [{"properties": {"show": B(False)}, "selector": {"id": "default"}}],
            "value": [{"properties": {"fontSize": D(16), "fontFamily": S(FONT_SB), "fontColor": C(BLACK), "showBlankAs": S("0")},
                       "selector": {"id": "default"}},
                      {"properties": {"labelDisplayUnits": D(1000), "labelPrecision": I(1)}, "selector": {"metadata": qref(PRm)}},
                      {"properties": {"fontColor": C(AMBER), "labelDisplayUnits": D(1000), "labelPrecision": I(1)},
                       "selector": {"metadata": qref(x("Open Unpaid Revenue"))}}]},
        "visualContainerObjects": {"title": [{"properties": {"show": B(False), "text": S("Tooltip KPIs")}}],
                                   "background": [{"properties": {"show": B(False)}}],
                                   "visualHeader": [{"properties": {"show": B(False)}}]},
        "drillFilterOtherVisuals": True}, z=100)

TT_MEASURES = [(PRm, "Paid revenue"), (POm, "Paid orders"), (x("Average Order Value"), "AOV"), (x("Open Unpaid Revenue"), "Unpaid")]

v = [tt_cards(TT_CAT, 480, TT_MEASURES)]
tb5 = bar(col("Product Name"), [(PRm, "Paid revenue")], "Top products here", tooltip=None, label_units=None)
tb5["visualContainerObjects"]["border"] = [{"properties": {"show": B(False)}}]
v.append(container(TT_CAT, "tt-top", 8, 92, 464, 200, tb5, filters=[f_topn("Product Name", m_src("Paid Revenue (Products)"), 5, "tt-cat-top5")], z=200))
add_page(TT_CAT, "TT - Category", v, hidden=True, ptype="Tooltip", width=480, height=300, bg=WHITE)

v = [tt_cards(TT_WEEK, 480, TT_MEASURES)]
tbw = bar(col("Category"), [(PRm, "Paid revenue")], "Paid revenue by category", tooltip=None, colours=CATEGORY_COLOURS, label_units=None)
tbw["visualContainerObjects"]["border"] = [{"properties": {"show": B(False)}}]
v.append(container(TT_WEEK, "tt-cat", 8, 92, 464, 230, tbw, z=200))
add_page(TT_WEEK, "TT - Period", v, hidden=True, ptype="Tooltip", width=480, height=330, bg=WHITE)

# Revenue Tooltip: fixed matrix (measures instead of Sum(invoice_total) / Count(order_id))
v = [container(TT_REV, "tt-matrix", 8, 8, 464, 304, matrix(
    [col("Sub Category"), col("Product Name")],
    [(PRm, "Paid revenue"), (POm, "Paid orders"), (x("Revenue % of Total"), "% of total")],
    "Products in this selection", tooltip=None), z=100)]
v[0]["visual"]["visualContainerObjects"]["border"] = [{"properties": {"show": B(False)}}]
v[0]["visual"]["visualContainerObjects"].pop("visualTooltip", None)
add_page(TT_REV, "Revenue Tooltip", v, hidden=True, ptype="Tooltip", width=480, height=320, bg=WHITE)

# ---------------------------------------------------------------- write out
if os.path.exists(OUT): shutil.rmtree(OUT)
shutil.copytree(SRC, OUT)
defn = os.path.join(OUT, "Report", "definition")
GUIDE = "d2a0f5b7b85490eb0eb3"
for d in os.listdir(os.path.join(defn, "pages")):
    if d != GUIDE and os.path.isdir(os.path.join(defn, "pages", d)):
        shutil.rmtree(os.path.join(defn, "pages", d))

def dump(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2)

for pid, (p, visuals) in pages.items():
    dump(os.path.join(defn, "pages", pid, "page.json"), p)
    names = set()
    for vc in visuals:
        assert vc["name"] not in names, vc["name"]; names.add(vc["name"])
        dump(os.path.join(defn, "pages", pid, "visuals", vc["name"], "visual.json"), vc)

order = [uid("page/overview"), uid("page/daily"), uid("page/products"), uid("page/customers"), uid("page/collections"),
         GUIDE, TT_CAT, TT_WEEK, TT_REV, uid("page/template")]
dump(os.path.join(defn, "pages", "pages.json"),
     {"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json",
      "pageOrder": order, "activePageName": order[0]})
dump(os.path.join(defn, "reportExtensions.json"), report_extensions())

# report.json: keep report-level filters & theme; drop unused custom visuals
rp = os.path.join(defn, "report.json")
r = json.load(open(rp))
r["publicCustomVisuals"] = [c for c in r.get("publicCustomVisuals", []) if c not in ("SimpleWaterfall", "WordCloud1447959067750")]
r["resourcePackages"] = [p for p in r["resourcePackages"] if p["name"] not in ("SimpleWaterfall", "enlightenSlicerB18DC0CE4A1F4BA79CE49FBE40F3965F")]
if not r["publicCustomVisuals"]: r.pop("publicCustomVisuals")
dump(rp, r)
shutil.rmtree(os.path.join(OUT, "Report", "CustomVisuals"), ignore_errors=True)
# bookmark pointed at the Guide page and one of its visuals; keep as-is.

# theme: global card spec (white, 1px #E3E5E8, radius 8, no shadow), dotted gridlines, legends top
tp = os.path.join(OUT, "Report", "StaticResources", "RegisteredResources", "1-grid_Brand1095741689915648.json")
t = json.load(open(tp))
star = t["visualStyles"].setdefault("*", {}).setdefault("*", {})
star.update({
    "background": [{"show": True, "color": {"solid": {"color": WHITE}}, "transparency": 0}],
    "border": [{"show": True, "color": {"solid": {"color": BORDER}}, "radius": 8, "width": 1}],
    "dropShadow": [{"show": False}],
    "title": [{"show": True, "fontColor": {"solid": {"color": BLACK}}, "fontSize": 12, "fontFamily": FONT_SB, "alignment": "left"}],
    "padding": [{"top": 12, "bottom": 8, "left": 14, "right": 14}],
    "legend": [{"show": True, "position": "Top", "showTitle": False, "labelColor": {"solid": {"color": GREY}}, "fontSize": 9}],
    "categoryAxis": [{"showAxisTitle": False, "gridlineShow": False}],
    "valueAxis": [{"showAxisTitle": False, "gridlineStyle": "dotted", "gridlineColor": {"solid": {"color": BORDER}}}],
})
t.setdefault("visualStyles", {}).setdefault("page", {}).setdefault("*", {})["background"] = [{"color": {"solid": {"color": PAGEBG}}, "transparency": 0}]
t["name"] = "1-grid Brand"
dump(tp, t)

# Connections: keep the live connection to the shared model, drop the link to the live report id
cp = os.path.join(OUT, "Connections")
cn = json.load(open(cp, encoding="utf-8-sig"))
cn.pop("RemoteArtifacts", None)
with open(cp, "w", encoding="utf-8") as fh: json.dump(cn, fh, separators=(",", ":"))

json.dump({"measures": [m_[0] for m_ in MEASURES],
           "pages": {p[0]["displayName"]: [(vc["name"], vc["visual"]["visualType"], vc["position"]) for vc in p[1]] for p in pages.values()}},
          open(os.path.join(os.path.dirname(OUT), "build_manifest.json"), "w"), indent=1, ensure_ascii=False)
print("pages", len(pages), "visuals", sum(len(p[1]) for p in pages.values()), "measures", len(MEASURES))
