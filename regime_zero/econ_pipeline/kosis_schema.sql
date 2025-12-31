-- KOSIS Master Table (Metadata)
CREATE TABLE IF NOT EXISTS econ_kosis_master (
    org_id TEXT NOT NULL,
    tbl_id TEXT NOT NULL,
    tbl_nm TEXT,
    meta_raw JSONB,
    last_crawled_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (org_id, tbl_id)
);

-- KOSIS Data Table (Values)
CREATE TABLE IF NOT EXISTS econ_kosis_data (
    org_id TEXT NOT NULL,
    tbl_id TEXT NOT NULL,
    date DATE NOT NULL,
    itm_id TEXT NOT NULL,
    obj_l1 TEXT DEFAULT '',
    obj_l2 TEXT DEFAULT '',
    value NUMERIC,
    unit TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (org_id, tbl_id, date, itm_id, obj_l1, obj_l2)
);

-- Index for faster queries
CREATE INDEX IF NOT EXISTS idx_kosis_data_date ON econ_kosis_data(date);
CREATE INDEX IF NOT EXISTS idx_kosis_data_tbl ON econ_kosis_data(tbl_id);
