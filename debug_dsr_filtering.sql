-- Debug DSR filtering for AXLE ENERGY
-- Check LocationGroup data for DSR + AXLE ENERGY

-- 1. Find all LocationGroups with DSR technology and AXLE ENERGY company
SELECT 
    location,
    is_active,
    auction_years,
    technologies,
    companies,
    component_count
FROM checker_locationgroup 
WHERE technologies::text ILIKE '%DSR%' 
  AND companies::text ILIKE '%AXLE ENERGY%'
ORDER BY location;

-- 2. Check individual components for AXLE ENERGY + DSR
SELECT 
    location,
    company_name,
    technology,
    auction_name,
    delivery_year,
    cmu_id
FROM checker_component 
WHERE company_name ILIKE '%AXLE ENERGY%' 
  AND technology ILIKE '%DSR%'
ORDER BY location, auction_name;

-- 3. Check if there are components without corresponding LocationGroups
SELECT 
    c.location,
    COUNT(*) as component_count,
    STRING_AGG(DISTINCT c.auction_name, ', ') as auction_years,
    CASE WHEN lg.location IS NULL THEN 'Missing LocationGroup' ELSE 'Has LocationGroup' END as status
FROM checker_component c
LEFT JOIN checker_locationgroup lg ON c.location = lg.location
WHERE c.company_name ILIKE '%AXLE ENERGY%' 
  AND c.technology ILIKE '%DSR%'
GROUP BY c.location, lg.location
ORDER BY c.location;