CREATE TABLE sensor (
    uuid UUID PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT,
    sensor TEXT,
    apidetails TEXT,
    is_online BOOLEAN DEFAULT FALSE
);

