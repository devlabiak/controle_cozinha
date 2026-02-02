-- Migration: Torna campo email opcional em clientes e tenants
-- Data: 2026-02-01

-- Alterar coluna email em clientes para permitir NULL
ALTER TABLE clientes ALTER COLUMN email DROP NOT NULL;

-- Alterar coluna email em tenants para permitir NULL
ALTER TABLE tenants ALTER COLUMN email DROP NOT NULL;

-- Nota: Os campos CNPJ já existem e são nullable por padrão
