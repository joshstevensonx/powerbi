WITH prep AS (
    SELECT
        o.id AS order_id,
        o."date" AS order_date,
        o.userid AS client_id,
        pg.name AS product_group,
        p.name AS product,
        p.type AS product_type,
        ps.group_slug AS slug_group,
        ps.slug AS slug,
        sd.name AS service_name,
        (
            p.hidden
            AND pg.hidden
        ) AS is_hidden,
        h.id AS service_id,
        h.domain,
        h.amount,
        h.billingcycle,
        h.domainstatus AS service_status,
        o.status AS order_status
    FROM
        "Whmcs DB"."whmcsliv_live"."tblorders" o
        INNER JOIN "Whmcs DB"."whmcsliv_live"."tblhosting" h ON h.orderid = o.id
        INNER JOIN "Whmcs DB"."whmcsliv_live"."tblproducts" p ON p.id = h.packageid
        INNER JOIN "Whmcs DB"."whmcsliv_live".tblproductgroups pg ON p.gid = pg.id
        INNER JOIN "Whmcs DB"."whmcsliv_live"."tblproducts_slugs" ps ON ps.product_id = p.id
        INNER JOIN "Whmcs DB"."whmcsliv_live".tblservicedata sd ON sd.service_id = h.id
)
SELECT
    DISTINCT product_group,
    product,
    product_type,
    slug_group,
    slug,
    service_name,
    is_hidden
FROM
    prep
ORDER BY
    1