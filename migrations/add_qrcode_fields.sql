-- Adiciona campos para sistema de etiquetas com QR code
-- Data: 2026-02-01

ALTER TABLE movimentacoes_estoque 
ADD COLUMN IF NOT EXISTS qr_code_gerado VARCHAR(100) UNIQUE,
ADD COLUMN IF NOT EXISTS data_producao DATE,
ADD COLUMN IF NOT EXISTS data_validade DATE,
ADD COLUMN IF NOT EXISTS etiqueta_impressa BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS usado BOOLEAN DEFAULT FALSE;

-- Cria índice para busca rápida por QR code
CREATE INDEX IF NOT EXISTS idx_mov_qr_code ON movimentacoes_estoque(qr_code_gerado) WHERE qr_code_gerado IS NOT NULL;

-- Cria índice para buscar produtos não utilizados
CREATE INDEX IF NOT EXISTS idx_mov_usado ON movimentacoes_estoque(usado, tipo) WHERE tipo = 'entrada';

COMMENT ON COLUMN movimentacoes_estoque.qr_code_gerado IS 'UUID único gerado para etiqueta (apenas entradas)';
COMMENT ON COLUMN movimentacoes_estoque.data_producao IS 'Data de produção/embalagem do produto';
COMMENT ON COLUMN movimentacoes_estoque.data_validade IS 'Data de validade do produto';
COMMENT ON COLUMN movimentacoes_estoque.etiqueta_impressa IS 'Indica se a etiqueta já foi impressa';
COMMENT ON COLUMN movimentacoes_estoque.usado IS 'Indica se o QR code já foi escaneado e utilizado';
