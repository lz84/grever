-- Migration 011: Create scenarios and scenario_steps tables
-- Author: Kouzi
-- Date: 2026-04-16

-- UP Migration
CREATE TABLE IF NOT EXISTS scenarios (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    version TEXT DEFAULT 'v1.0',
    description TEXT,
    scenario_desc TEXT DEFAULT '',
    triggers TEXT,  -- JSON array as text
    total_executions INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,
    success_rate REAL DEFAULT 0.0,
    avg_duration_ms REAL DEFAULT 0.0,
    min_duration_ms REAL DEFAULT 0.0,
    max_duration_ms REAL DEFAULT 0.0,
    avg_conflicts REAL DEFAULT 0.0,
    avg_step_completion REAL DEFAULT 0.0,
    usage_count INTEGER DEFAULT 0,
    versions TEXT,  -- JSON array as text
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_scenarios_category ON scenarios(category);
CREATE INDEX IF NOT EXISTS idx_scenarios_status ON scenarios(status);
CREATE INDEX IF NOT EXISTS idx_scenarios_created_at ON scenarios(created_at);

CREATE TABLE IF NOT EXISTS scenario_steps (
    id TEXT PRIMARY KEY,
    scenario_id TEXT NOT NULL,
    "order" INTEGER NOT NULL,
    name TEXT NOT NULL,
    agent_type TEXT,
    required_capabilities TEXT,  -- JSON array as text
    FOREIGN KEY (scenario_id) REFERENCES scenarios(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_scenario_steps_scenario_id ON scenario_steps(scenario_id);
CREATE INDEX IF NOT EXISTS idx_scenario_steps_order ON scenario_steps("order");

-- Insert initial test scenarios
INSERT INTO scenarios (id, name, category, status, version, description, scenario_desc, triggers, total_executions, success_count, failed_count, success_rate, avg_duration_ms, usage_count, versions) VALUES 
('scenario-eqrescue001', '地震救援', 'earthquake', 'active', 'v1.0', '地震发生后的紧急救援场景', '该场景适用于地震灾害后的搜救工作，包括人员搜救、医疗救护、物资配送等环节', '["seismic_event", "magnitude_6_or_above", "emergency_alert"]', 15, 12, 3, 80.0, 125000.0, 25, '["v1.0"]'),
('scenario-chemleak001', '危化品泄漏', 'chemical', 'active', 'v1.0', '危险化学品泄漏应急处置场景', '该场景适用于化工厂或运输过程中发生的危险化学品泄漏事故的应急处置', '["chemical_leak", "hazardous_material", "emergency_response"]', 8, 6, 2, 75.0, 95000.0, 15, '["v1.0"]'),
('scenario-firefight001', '火灾应急响应', 'fire', 'active', 'v1.0', '城市建筑火灾应急响应场景', '该场景适用于城市建筑火灾的应急响应，包括火场侦查、人员疏散、灭火救援等环节', '["fire_alarm", "structure_fire", "emergency_dispatch"]', 22, 20, 2, 90.9, 75000.0, 32, '["v1.0"]');

-- Insert scenario steps for earthquake rescue
INSERT INTO scenario_steps (id, scenario_id, "order", name, agent_type, required_capabilities) VALUES 
('step-eqrescue001', 'scenario-eqrescue001', 1, '灾情评估', 'monitoring', '["seismic_monitoring", "damage_assessment", "drone_surveillance"]'),
('step-eqrescue002', 'scenario-eqrescue001', 2, '搜救队伍部署', 'coordination', '["resource_coordination", "team_management", "logistics_support"]'),
('step-eqrescue003', 'scenario-eqrescue001', 3, '医疗救护', 'medical', '["medical_emergency", "patient_triage", "emergency_treatment"]'),
('step-eqrescue004', 'scenario-eqrescue001', 4, '后勤保障', 'logistics', '["supply_distribution", "transportation", "infrastructure"]');

-- Insert scenario steps for chemical leak
INSERT INTO scenario_steps (id, scenario_id, "order", name, agent_type, required_capabilities) VALUES 
('step-chemleak001', 'scenario-chemleak001', 1, '现场隔离与警戒', 'safety', '["hazard_identification", "area_securement", "risk_assessment"]'),
('step-chemleak002', 'scenario-chemleak001', 2, '泄漏源控制', 'technical', '["containment", "plugging", "neutralization"]'),
('step-chemleak003', 'scenario-chemleak001', 3, '人员疏散', 'coordination', '["evacuation_planning", "crowd_control", "public_notification"]'),
('step-chemleak004', 'scenario-chemleak001', 4, '环境监测', 'monitoring', '["air_quality", "water_contamination", "soil_testing"]');

-- Insert scenario steps for fire emergency
INSERT INTO scenario_steps (id, scenario_id, "order", name, agent_type, required_capabilities) VALUES 
('step-firefight001', 'scenario-firefight001', 1, '火场侦察', 'reconnaissance', '["thermal_imaging", "structural_assessment", "smoke_analysis"]'),
('step-firefight002', 'scenario-firefight001', 2, '人员疏散', 'rescue', '["evacuation_assistance", "disability_accommodation", "emergency_exit"]'),
('step-firefight003', 'scenario-firefight001', 3, '灭火行动', 'extinguishment', '["water_supply", "foam_application", "ventilation"]'),
('step-firefight004', 'scenario-firefight001', 4, '现场清理', 'cleanup', '["debris_removal", "safety_inspection", "investigation"]');
