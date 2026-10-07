WITH cte_orders AS (
    SELECT
        o.id AS order_id,
        TO_DATE(o."date") AS order_date,
        o.userid AS user_id,
        o.invoiceid AS invoice_id,
        o.status AS order_status,
        o."amount" AS order_total,
        o.promovalue AS order_promo_amount
    FROM
        "Whmcs DB"."whmcsliv_live".tblorders o
),
cte_invoices AS (
    SELECT
        i.id AS invoice_id,
        i."date" AS invoice_date,
        i.total AS invoice_total,
        i.subtotal AS invoice_subtotal,
        i.credit AS invoice_credit,
        i.tax AS invoice_tax,
        i.status AS invoice_status,
        i.duedate AS invoice_due_date,
        TO_DATE(i.datepaid) AS invoice_paid_date,
        i.paymentmethod AS invoice_pay_method,
        i.userid AS user_id
    FROM
        "Whmcs DB"."whmcsliv_live".tblinvoices i
),
cte_prep AS (
    SELECT
        DISTINCT co.order_id,
        ci.invoice_id,
        co.order_date,
        ci.invoice_date,
        co.user_id,
        co.order_status,
        ci.invoice_status,
        ci.invoice_total,
        co.order_total,
        co.order_promo_amount,
        ci.invoice_subtotal,
        ci.invoice_credit,
        ci.invoice_tax,
        ci.invoice_pay_method,
        ci.invoice_due_date,
        ci.invoice_paid_date
    FROM
        cte_orders co
        INNER JOIN cte_invoices ci ON co.invoice_id = ci.invoice_id
    WHERE
        co.order_date >= DATE '2026-09-01'
        AND invoice_total > 0
)
SELECT
    order_id,
    invoice_id,
    user_id,
    order_date,
    invoice_date,
    order_status,
    invoice_status,
    CASE
        WHEN invoice_status = 'Paid' THEN 'Paid Invoice'
        WHEN invoice_status = 'Unpaid'
        AND invoice_pay_method = 'mygateDebit'
        AND invoice_due_date >= CURRENT_DATE THEN 'Pending Debit Order'
        ELSE invoice_status
    END AS invoice_status_group,
    invoice_total,
    order_total,
    order_promo_amount,
    invoice_subtotal,
    invoice_credit,
    invoice_tax,
    invoice_pay_method,
    invoice_due_date,
    invoice_paid_date
FROM
    cte_prep
ORDER BY
    order_date DESC