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