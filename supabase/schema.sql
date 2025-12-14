-- Intelligent Zone Generator - Supabase Schema
-- Run this in Supabase SQL Editor to create tables

-- Enable PostGIS for geospatial operations
CREATE EXTENSION IF NOT EXISTS postgis;

-- ============================================
-- CUSTOMERS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id TEXT NOT NULL UNIQUE,
    customer_name TEXT NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    city TEXT,
    zone TEXT,
    agent_id TEXT,
    agent_name TEXT,
    status TEXT,
    area TEXT,
    region TEXT,
    raw_data JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_customers_city ON customers(city);
CREATE INDEX IF NOT EXISTS idx_customers_zone ON customers(zone);
CREATE INDEX IF NOT EXISTS idx_customers_agent ON customers(agent_id);
CREATE INDEX IF NOT EXISTS idx_customers_location ON customers USING GIST (
    ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
);

-- ============================================
-- ZONES TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS zones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    geometry GEOMETRY(POLYGON, 4326),
    geometry_wkt TEXT, -- Temporary column for WKT input (converted by trigger)
    depot_code TEXT,
    customer_count INTEGER DEFAULT 0,
    method TEXT, -- 'polar', 'isochrone', 'clustering', 'manual'
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_zones_geometry ON zones USING GIST(geometry);
CREATE INDEX IF NOT EXISTS idx_zones_depot ON zones(depot_code);

-- Trigger to convert WKT to geometry
CREATE OR REPLACE FUNCTION convert_wkt_to_geometry()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.geometry_wkt IS NOT NULL AND NEW.geometry IS NULL THEN
        NEW.geometry := ST_GeomFromText(NEW.geometry_wkt, 4326);
        NEW.geometry_wkt := NULL; -- Clear after conversion
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER zones_convert_wkt
    BEFORE INSERT OR UPDATE ON zones
    FOR EACH ROW
    EXECUTE FUNCTION convert_wkt_to_geometry();

-- ============================================
-- ROUTES TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS routes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    zone_id UUID REFERENCES zones(id) ON DELETE CASCADE,
    route_date DATE NOT NULL,
    stops JSONB NOT NULL DEFAULT '[]',
    total_distance_km DOUBLE PRECISION,
    total_duration_min DOUBLE PRECISION,
    vehicle_id TEXT,
    driver_id TEXT,
    status TEXT DEFAULT 'planned', -- planned, active, completed
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_routes_zone ON routes(zone_id);
CREATE INDEX IF NOT EXISTS idx_routes_date ON routes(route_date);

-- ============================================
-- DEPOTS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS depots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code TEXT NOT NULL UNIQUE,
    name TEXT,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    effective_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- REPORTS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    type TEXT NOT NULL, -- 'zone_summary', 'route_plan', 'customer_list'
    parameters JSONB DEFAULT '{}',
    file_path TEXT,
    file_format TEXT, -- 'csv', 'json', 'geojson'
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- UPDATED_AT TRIGGER
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER customers_updated_at
    BEFORE UPDATE ON customers
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- ============================================
-- USEFUL FUNCTIONS
-- ============================================

-- Get customers within radius (km) of a point
CREATE OR REPLACE FUNCTION get_customers_in_radius(
    lat DOUBLE PRECISION,
    lng DOUBLE PRECISION,
    radius_km DOUBLE PRECISION
)
RETURNS SETOF customers AS $$
BEGIN
    RETURN QUERY
    SELECT *
    FROM customers
    WHERE ST_DWithin(
        ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography,
        ST_SetSRID(ST_MakePoint(lng, lat), 4326)::geography,
        radius_km * 1000
    );
END;
$$ LANGUAGE plpgsql;

-- Get customers within a zone polygon
CREATE OR REPLACE FUNCTION get_customers_in_zone(zone_id_param UUID)
RETURNS SETOF customers AS $$
BEGIN
    RETURN QUERY
    SELECT c.*
    FROM customers c
    JOIN zones z ON ST_Contains(
        z.geometry,
        ST_SetSRID(ST_MakePoint(c.longitude, c.latitude), 4326)
    )
    WHERE z.id = zone_id_param;
END;
$$ LANGUAGE plpgsql;

-- Insert zone with WKT geometry conversion
CREATE OR REPLACE FUNCTION insert_zone_with_geometry(
    zone_name TEXT,
    geometry_wkt TEXT,
    depot_code TEXT DEFAULT NULL,
    customer_count INTEGER DEFAULT 0,
    method TEXT DEFAULT NULL,
    metadata JSONB DEFAULT '{}'::jsonb
)
RETURNS UUID AS $$
DECLARE
    zone_id UUID;
BEGIN
    INSERT INTO zones (name, geometry, depot_code, customer_count, method, metadata)
    VALUES (
        zone_name,
        ST_GeomFromText(geometry_wkt, 4326),
        depot_code,
        customer_count,
        method,
        metadata
    )
    RETURNING id INTO zone_id;
    
    RETURN zone_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- ROW LEVEL SECURITY (Optional)
-- ============================================
-- Uncomment if you want to enable RLS

-- ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE zones ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE routes ENABLE ROW LEVEL SECURITY;

-- Example policy: Allow authenticated users to read all
-- CREATE POLICY "Allow read for authenticated" ON customers
--     FOR SELECT TO authenticated USING (true);

-- ============================================
-- SAMPLE DATA (Optional - remove in production)
-- ============================================
-- INSERT INTO depots (code, name, latitude, longitude)
-- VALUES ('RYD01', 'Riyadh DC', 24.7136, 46.6753);
