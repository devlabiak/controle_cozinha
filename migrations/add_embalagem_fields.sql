-- Migration: Adiciona campos de embalagem à tabela alimentos
-- Data: 2026-02-01

ALTER TABLE alimentos 
ADD COLUMN IF NOT EXISTS tipo_embalagem VARCHAR(50),
ADD COLUMN IF NOT EXISTS unidades_por_embalagem INTEGER;

-- Comentários para documentação
COMMENT ON COLUMN alimentos.tipo_embalagem IS 'Tipo de embalagem: pacote, bandeja, caixa, fardo, pote, etc';
COMMENT ON COLUMN alimentos.unidades_por_embalagem IS 'Quantidade de unidades por embalagem (ex: 10 espetinhos por pacote)';
