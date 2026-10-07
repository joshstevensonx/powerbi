-- "Power BI Reports"."Data analytics"."Orders through App"."App Orders"
select
    clients.client_id,
    clients.firstname,
    clients.lastname,
    clients.email,
    clients.groupname,
    events.id as event_id,
    events.event as event_name,
    events.device as device_name,
    events.os as device_os,
    events.created_at as event_created_at,
    orders.order_id,
    orders.order_date,
    orders.order_amount,
    orders.order_paymentmethod,
    orders.invoiceid,
    orders.order_status,
    addons.addon_id,
    addons.service_id as addon_service_id,
    addons.addonid as addon_product_id,
    addons.name as addon_name,
    addons.firstpaymentamount as addon_first_payment_amount,
    addons.amount as addon_recurring_amount,
    addons.domainstatus as addon_status,
    services.service_id,
    services.plan_id as service_plan_id,
    services.plan_name as service_plan_name,
    services.domain as service_name,
    services.firstpaymentamount as service_first_payment_amount,
    services.amount as service_recurring_amount,
    services.domainstatus as service_status,
    domains.domain_id,
    domains.type as domain_reg_type,
    domains.domain as domain_name,
    domains.firstpaymentamount as domain_first_payment_amount,
    domains.recurringamount as domain_recurring_amount,
    domains.status as domain_status
from "Whmcs DB".whmcsliv_live.tblmobileevents events
join Helpers.Whmcs."Tables"."Clients (tblclients)" clients on clients.client_id = events.userid 
join Helpers.Whmcs."Tables"."Orders (tblorders)" orders on orders.client_id = events.userid 
left join Helpers.Whmcs."Tables"."Service Addons (tblhostingaddons)" addons on addons.order_id = orders.order_id 
left join Helpers.Whmcs."Tables"."Services (tblhosting)" services on services.order_id = orders.order_id 
left join Helpers.Whmcs."Tables"."Domains (tbldomains)" domains on domains.order_id = orders.order_id 
where
    events.event in ('OrderNewService','OrderSuccess')
and
    orders.order_ipaddress = '41.185.120.117'