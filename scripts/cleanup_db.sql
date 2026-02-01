-- Script para limpar banco de dados completamente
-- Executa em ordem para respeitar foreign keys

BEGIN TRANSACTION;
SET CONSTRAINTS ALL DEFERRED;

-- 1. Limpar tabelas de dependências
DELETE FROM user_tenants_association CASCADE;
DELETE FROM movimentacao_estoque CASCADE;
DELETE FROM alimentos CASCADE;
DELETE FROM tenants CASCADE;

-- 2. Limpar users (exceto admin principal id=1)
DELETE FROM users WHERE id != 1;

-- 3. Limpar clientes
DELETE FROM clientes CASCADE;

COMMIT;

-- Verificar estado final
SELECT 'Users:' as table_name, COUNT(*) as total FROM users
UNION ALL
SELECT 'Clientes:' as table_name, COUNT(*) as total FROM clientes
UNION ALL
SELECT 'Tenants:' as table_name, COUNT(*) as total FROM tenants
UNION ALL
SELECT 'Alimentos:' as table_name, COUNT(*) as total FROM alimentos
UNION ALL
SELECT 'user_tenants_association:' as table_name, COUNT(*) as total FROM user_tenants_association;

-- Mostrar usuários restantes
SELECT 'Admin User:' as info, id, email, is_admin FROM users;
