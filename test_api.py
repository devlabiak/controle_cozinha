"""Script para testar o endpoint de clientes"""
import requests

# Testar endpoint
url = "http://localhost:8000/api/admin/clientes"
print(f"Testando: {url}")

try:
    response = requests.get(url)
    print(f"Status: {response.status_code}")
    print(f"Headers: {response.headers.get('content-type')}")
    print(f"Response: {response.text[:500]}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✓ Sucesso! {len(data)} clientes encontrados")
        for cliente in data:
            print(f"  - {cliente.get('nome_empresa')} (ID: {cliente.get('id')})")
    else:
        print(f"\n✗ Erro: {response.status_code}")
        
except Exception as e:
    print(f"✗ Erro na requisição: {e}")
