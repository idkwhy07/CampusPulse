CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('STUDENT', 'STAFF')),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS observations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    raw_text TEXT NOT NULL,
    category VARCHAR(50) NOT NULL DEFAULT 'OTHER',
    building VARCHAR(20) NOT NULL,
    floor VARCHAR(20),
    room VARCHAR(20),
    service_state VARCHAR(20) NOT NULL DEFAULT 'UNKNOWN',
    image_url TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE', 'DELETED')),
    occurred_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS incidents (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    category VARCHAR(50) NOT NULL,
    building VARCHAR(20) NOT NULL,
    floor VARCHAR(20),
    room VARCHAR(20),

    status VARCHAR(30) NOT NULL DEFAULT 'EMERGING'
        CHECK (
            status IN (
                'EMERGING',
                'CONFIRMED',
                'IN_PROGRESS',
                'RESOLVED'
            )
        ),

    severity VARCHAR(20) NOT NULL DEFAULT 'MEDIUM',

    confidence INTEGER NOT NULL DEFAULT 0
        CHECK (confidence BETWEEN 0 AND 100),

    assigned_team VARCHAR(100),

    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS incident_observations (
    incident_id INTEGER NOT NULL
        REFERENCES incidents(id),

    observation_id INTEGER NOT NULL
        REFERENCES observations(id),

    relation VARCHAR(20) NOT NULL DEFAULT 'SUPPORT'
        CHECK (
            relation IN (
                'SUPPORT',
                'CONTRADICT',
                'UNKNOWN'
            )
        ),

    match_score NUMERIC(5,4),

    created_at TIMESTAMP NOT NULL DEFAULT NOW(),

    PRIMARY KEY (
        incident_id,
        observation_id
    )
);

CREATE INDEX IF NOT EXISTS idx_observations_user_created
    ON observations(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_observations_active
    ON observations(status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_incidents_candidate
    ON incidents(
        category,
        building,
        room,
        status,
        created_at DESC
    );

CREATE INDEX IF NOT EXISTS idx_incident_observations_incident
    ON incident_observations(incident_id);

-- Compatibility with older CampusPulse databases.

ALTER TABLE observations
    ADD COLUMN IF NOT EXISTS service_state VARCHAR(20)
        NOT NULL DEFAULT 'UNKNOWN';

ALTER TABLE observations
    ADD COLUMN IF NOT EXISTS image_url TEXT;

ALTER TABLE observations
    ADD COLUMN IF NOT EXISTS occurred_at TIMESTAMP;

ALTER TABLE observations
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP
        NOT NULL DEFAULT NOW();


ALTER TABLE incidents
    ADD COLUMN IF NOT EXISTS severity VARCHAR(20)
        NOT NULL DEFAULT 'MEDIUM';

ALTER TABLE incidents
    ADD COLUMN IF NOT EXISTS confidence INTEGER
        NOT NULL DEFAULT 0;

ALTER TABLE incidents
    ADD COLUMN IF NOT EXISTS assigned_team VARCHAR(100);

ALTER TABLE incidents
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP
        NOT NULL DEFAULT NOW();

ALTER TABLE incidents
    ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMP;


ALTER TABLE incident_observations
    ADD COLUMN IF NOT EXISTS relation VARCHAR(20)
        NOT NULL DEFAULT 'SUPPORT';

ALTER TABLE incident_observations
    ADD COLUMN IF NOT EXISTS match_score NUMERIC(5,4);

ALTER TABLE incident_observations
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMP
        NOT NULL DEFAULT NOW();


-- Compatibility for databases created by older CampusPulse versions.

ALTER TABLE observations
    ADD COLUMN IF NOT EXISTS service_state VARCHAR(20)
        NOT NULL DEFAULT 'UNKNOWN';

ALTER TABLE observations
    ADD COLUMN IF NOT EXISTS image_url TEXT;

ALTER TABLE observations
    ADD COLUMN IF NOT EXISTS occurred_at TIMESTAMP;

ALTER TABLE observations
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP
        NOT NULL DEFAULT NOW();


ALTER TABLE incidents
    ADD COLUMN IF NOT EXISTS severity VARCHAR(20)
        NOT NULL DEFAULT 'MEDIUM';

ALTER TABLE incidents
    ADD COLUMN IF NOT EXISTS confidence INTEGER
        NOT NULL DEFAULT 0;

ALTER TABLE incidents
    ADD COLUMN IF NOT EXISTS assigned_team VARCHAR(100);

ALTER TABLE incidents
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP
        NOT NULL DEFAULT NOW();

ALTER TABLE incidents
    ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMP;


ALTER TABLE incident_observations
    ADD COLUMN IF NOT EXISTS relation VARCHAR(20)
        NOT NULL DEFAULT 'SUPPORT';

ALTER TABLE incident_observations
    ADD COLUMN IF NOT EXISTS match_score NUMERIC(5,4);

ALTER TABLE incident_observations
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMP
        NOT NULL DEFAULT NOW();
