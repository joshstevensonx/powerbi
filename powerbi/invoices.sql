SELECT
    i.id AS invoice_id,
    i."date" AS invoice_date,
    i.total as invoice_total,
    i.status as invoice_status,
    i.duedate as invoice_due_date,
    i.datepaid as invoice_paid_date,
    i.paymentmethod as invoice_pay_method,
    i."userid" AS user_id
FROM
    "Whmcs DB"."whmcsliv_live".tblinvoices i
ORDER BY
    i."date" DESC;