--Query used in daily sales report, ppc report and other new revenue/ sales related reports.
-- Revenue calculation is based on first payment amaount or recurring amount depending on product.
-- High importance query in terms of report usage and expected availabilty.
-- this query will return new service revenue and new domains revenue. addon revenue is derived from the invoice detail table
SELECT
    order_id,
    client_id,
    create_date,
    order_datetime,
    service_group,
    service_type,
    domain,
    service_id,
    invoice_id,
    payment_type,
    recurring_amount,
    amount,
    service_status,
    billing_cycle,
    billing_period,
    signup_agent,
    setup_fee,
    smoothed,
    revenue,
    product_1,
    product_2,
    base_or_addon,
    order_month
FROM
    (
        SELECT
            service_revenue.order_id,
            service_revenue.client_id,
            service_revenue.create_date,
            service_revenue.order_datetime,
            service_revenue.service_group,
            service_revenue.service_type,
            service_revenue.domain,
            service_revenue.service_id,
            service_revenue.invoice_id,
            service_revenue.payment_type,
            service_revenue.recurring_amount,
            service_revenue.amount,
            service_revenue.service_status,
            service_revenue.billing_cycle,
            service_revenue.billing_period,
            service_revenue.signup_agent,
            service_revenue.setup_fee,
            service_revenue.smoothed,
            service_revenue.revenue,
            CASE
                WHEN service_revenue.product_1 IS NULL
                AND service_group = 'Virtual Private Servers' THEN 'Infrastructure Hosting'
                WHEN service_revenue.product_1 IS NULL
                AND service_group <> 'Virtual Private Servers' THEN 'Application Hosting'
                ELSE service_revenue.product_1
            END AS product_1,
            CASE
                WHEN service_revenue.product_2 IS NULL
                AND service_group = 'Virtual Private Servers' THEN 'Infrastructure Hosting'
                WHEN service_revenue.product_2 IS NULL
                AND service_group <> 'Virtual Private Servers' THEN 'Application Hosting'
                ELSE service_revenue.product_2
            END AS product_2,
            service_revenue.base_or_addon,
            service_revenue.order_month
        FROM
            (
                SELECT
                    orders.order_id,
                    orders.client_id,
                    orders.create_date,
                    orders.order_datetime,
                    orders.service_group,
                    orders.service_type,
                    orders.domain,
                    orders.service_id,
                    orders.payment_type,
                    orders.recurring_amount,
                    orders.invoice_id,
                    orders.amount,
                    orders.service_status,
                    orders.billing_cycle,
                    orders.billing_period,
                    orders.signup_agent,
                    orders.setup_fee,
                    CASE
                        WHEN orders.service_type IN (
                            'Domain',
                            'Domain Essentials (Including ID Privacy)',
                            'Cloud Linux',
                            'Dedicated IP',
                            'SSL Certificate - Secure your Domain Name'
                        ) THEN orders.recurring_amount
                        ELSE (orders.recurring_amount / orders.billing_period)
                    END AS smoothed,
                    CASE
                        WHEN orders.service_type IN (
                            'Domain',
                            'Domain Essentials (Including ID Privacy)',
                            'Cloud Linux',
                            'Dedicated IP',
                            'SSL Certificate - Secure your Domain Name'
                        ) THEN (orders.recurring_amount / 1.15)
                        ELSE (
                            (orders.recurring_amount / orders.billing_period) / 1.15
                        )
                    END AS revenue,
                    orders.product_1,
                    orders.product_2,
                    orders.base_or_addon,
                    orders.order_month
                FROM
                    (
                        SELECT
                            tblorders.id AS order_id,
                            tblorders.invoiceid AS invoice_id,
                            tblorders."date" AS order_datetime,
                            tblhosting.userid AS client_id,
                            tblhosting.regdate AS create_date,
                            TO_CHAR(tblhosting.regdate, 'yyyy-mm') AS order_month,
                            tblproductgroups.name AS service_group,
                            tblproducts.name AS service_type,
                            tblhosting.domain AS domain,
                            tblhosting.id AS service_id,
                            tblhosting.paymentmethod AS payment_type,
                            cast(
                                CASE
                                    WHEN tblproductgroups.name = 'Company Registration'
                                    AND tblhosting.domainstatus = 'Active' THEN tblhosting.firstpaymentamount
                                    ELSE tblhosting.amount
                                END AS float
                            ) AS recurring_amount,
                            tblhosting.amount AS amount,
                            tblhosting.domainstatus AS service_status,
                            tblhosting.billingcycle AS billing_cycle,
                            CASE
                                WHEN tblhosting.billingcycle = 'Monthly' THEN 1
                                WHEN tblhosting.billingcycle = 'Semi-Annually' THEN 6
                                WHEN tblhosting.billingcycle = 'Quarterly' THEN 3
                                WHEN tblhosting.billingcycle = 'onetime' THEN 1
                                WHEN tblhosting.billingcycle = 'One Time' THEN 1
                                WHEN tblhosting.billingcycle = 'Free Account' THEN 1
                                WHEN tblhosting.billingcycle = 'semiannually' THEN 6
                                WHEN tblhosting.billingcycle = 'Annually' THEN 12
                                WHEN tblhosting.billingcycle = 'Biennially' THEN 24
                                WHEN tblhosting.billingcycle = 'Triennially' THEN 36
                            END AS billing_period,
                            CASE
                                WHEN tblorders.ipaddress = '196.220.32.228' THEN 'Agent'
                                WHEN tblorders.admin_requestor_id = 203
                                OR tblorders.ipaddress = '41.185.120.117' THEN 'App Sale'
                                ELSE 'Online'
                            END AS signup_agent,
                            CAST(tblpricing.msetupfee AS DOUBLE) AS setup_fee,
                            mapping.product_1,
                            mapping.product_2,
                            mapping.base_or_addon
                        FROM
                            "Whmcs DB"."whmcsliv_live".tblhosting
                            LEFT JOIN "Whmcs DB"."whmcsliv_live".tblproducts ON tblhosting.packageid = tblproducts.id
                            LEFT JOIN "Whmcs DB"."whmcsliv_live".tblproductgroups ON tblproducts.gid = tblproductgroups.id
                            LEFT JOIN "Whmcs DB"."whmcsliv_live".tblorders ON tblhosting.orderid = tblorders.id
                            LEFT JOIN "Whmcs DB"."whmcsliv_live".tblpricing ON tblproducts.id = tblpricing.relid
                            LEFT JOIN "Power BI Files"."power-bi"."Bi Reports"."Mapping Tables"."Revenue Report Mapping.csv" AS mapping ON mapping.service_type = tblproducts.name
                        WHERE
                            tblhosting.regdate >= '2020-01-01'
                            AND tblpricing.currency = 1
                            AND tblpricing.type = 'product'
                    ) AS orders
                WHERE
                    orders.order_id NOT IN (226506, 229377, 231737) --and service_id <> 370837
            ) AS service_revenue
        WHERE
            create_date > '2020-12-31' -- date needs to be updated regulary to limit data to 18 months, alternatively use :date_sub(current_date(),450) 
        UNION
        SELECT
            domain_revenue.order_id,
            domain_revenue.client_id,
            domain_revenue.create_date,
            domain_revenue.order_datetime,
            domain_revenue.service_group,
            domain_revenue.service_type,
            domain_revenue.domain,
            domain_revenue.service_id,
            domain_revenue.invoice_id,
            domain_revenue.payment_type,
            domain_revenue.recurring_amount,
            domain_revenue.amount,
            domain_revenue.service_status,
            domain_revenue.billing_cycle,
            domain_revenue.billing_period,
            domain_revenue.signup_agent,
            domain_revenue.setup_fee,
            domain_revenue.smoothed,
            domain_revenue.revenue,
            CASE
                WHEN domain_revenue.product_1 IS NULL THEN 'Domain'
                ELSE domain_revenue.product_1
            END AS product_1,
            CASE
                WHEN domain_revenue.product_2 IS NULL THEN 'Domain'
                ELSE domain_revenue.product_2
            END AS product_2,
            domain_revenue.base_or_addon,
            domain_revenue.order_month
        FROM
            (
                SELECT
                    orders.order_id,
                    orders.client_id,
                    orders.create_date,
                    orders.order_datetime,
                    orders.service_group,
                    orders.service_type,
                    orders.domain,
                    orders.service_id,
                    orders.payment_type,
                    CASE
                        WHEN service_type IN (
                            'co.za',
                            'net.za',
                            'org.za',
                            'web.za',
                            'africa',
                            'online',
                            'joburg',
                            'capetown',
                            'durban',
                            'co',
                            'tech'
                        ) THEN orders.recurring_amount
                        ELSE orders.recurring_amount2
                    END AS recurring_amount,
                    orders.invoice_id,
                    orders.amount,
                    orders.service_status,
                    orders.billing_cycle,
                    orders.billing_period,
                    orders.signup_agent,
                    orders.setup_fee,
                    CASE
                        WHEN orders.service_type IN (
                            'Domain',
                            'Domain Essentials (Including ID Privacy)',
                            'Cloud Linux',
                            'Dedicated IP',
                            'SSL Certificate - Secure your Domain Name'
                        ) THEN orders.recurring_amount
                        ELSE (orders.recurring_amount / orders.billing_period)
                    END AS smoothed,
                    CASE
                        WHEN orders.service_type IN (
                            'Domain',
                            'Domain Essentials (Including ID Privacy)',
                            'Cloud Linux',
                            'Dedicated IP',
                            'SSL Certificate - Secure your Domain Name'
                        ) THEN (orders.recurring_amount / 1.15)
                        ELSE (
                            (orders.recurring_amount / orders.billing_period) / 1.15
                        )
                    END AS revenue,
                    orders.product_1,
                    orders.product_2,
                    orders.base_or_addon,
                    orders.order_month
                FROM
                    (
                        SELECT
                            tblorders.id AS order_id,
                            tblorders.invoiceid AS invoice_id,
                            tblorders."date" AS order_datetime,
                            tbldomains.userid AS client_id,
                            tbldomains.registrationdate AS create_date,
                            TO_CHAR(tbldomains.registrationdate, 'yyyy-mm') AS order_month,
                            'Domains' AS service_group,
                            extract_pattern(
                                tbldomains.domain,
                                '(.*?)\.(.*)',
                                1,
                                'CAPTURE_GROUP'
                            ) AS service_type,
                            tbldomains.domain AS domain,
                            tbldomains.id AS service_id,
                            tbldomains.paymentmethod AS payment_type,
                            cast(tbldomains.firstpaymentamount AS float) AS recurring_amount,
                            cast(tbldomains.recurringamount AS float) AS recurring_amount2,
                            tblorders.amount AS amount,
                            tbldomains.status AS service_status,
                            'Annually' AS billing_cycle,
                            12 AS billing_period,
                            CASE
                                WHEN tblorders.ipaddress = '196.220.32.228' THEN 'Agent'
                                WHEN tblorders.admin_requestor_id = 203
                                OR tblorders.ipaddress = '41.185.120.117' THEN 'App Sale'
                                ELSE 'Online'
                            END AS signup_agent,
                            CAST(0 AS DOUBLE) AS setup_fee,
                            mapping.product_1,
                            mapping.product_2,
                            mapping.base_or_addon
                        FROM
                            "Whmcs DB"."whmcsliv_live".tbldomains
                            LEFT JOIN "Whmcs DB"."whmcsliv_live".tblorders ON tbldomains.orderid = tblorders.id
                            LEFT JOIN "Power BI Files"."power-bi"."Bi Reports"."Mapping Tables"."Revenue Report Mapping.csv" AS mapping ON mapping.service_type = 'Domain'
                        WHERE
                            tbldomains.registrationdate >= '2020-10-01'
                    ) AS orders
            ) domain_revenue
        WHERE
            create_date > '2020-12-31' -- date needs to be updated regulary to limit data to 18 months, alternatively use :date_sub(current_date(),450) 
    ) nested_0
ORDER BY
    create_date DESC