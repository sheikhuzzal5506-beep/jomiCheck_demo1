-- LandGuard BD MySQL starter schema overview. Runtime SQLAlchemy models are the source used by the app.
CREATE DATABASE IF NOT EXISTS landguard_bd CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE landguard_bd;
-- Tables are created automatically by backend/app/main.py at startup.
-- Core tables: users, registry_offices, persons, land_parcels, deeds,
-- mutation_records, document_hash_references, verification_jobs, audit_logs.
-- Synthetic/demo records only. Never insert real personal data into the hackathon demo.
