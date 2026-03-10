import requests
import json
import time

BASE_URL = "https://www.dnd5eapi.co"

def extrair_dados(endpoint, nome_arquivo):
    print(f"\n--- Iniciando extração de {endpoint} ---")
    
    # 1. Pega a lista com todos os itens do endpoint
    resposta_lista = requests.get(f"{BASE_URL}/api/{endpoint}").json()
    itens = resposta_lista.get('results', [])
    
    dados_completos = []
    
    # 2. Entra em cada item para pegar os dados profundos
    # (Remova o [:3] se quiser baixar todos. Deixei [:3] apenas para você testar rápido a primeira vez)
    for item in itens: 
        print(f"Baixando: {item['name']}")
        resposta_detalhe = requests.get(BASE_URL + item['url']).json()
        dados_completos.append(resposta_detalhe)
        
        time.sleep(0.2) # Pausa amigável de 200ms para não tomar ban
        
    # 3. Salva os dados estruturados em formato JSON
    with open(nome_arquivo, 'w', encoding='utf-8') as f:
        json.dump(dados_completos, f, ensure_ascii=False, indent=4)
        
    print(f"✅ {nome_arquivo} salvo com {len(dados_completos)} registros!")

if __name__ == "__main__":
    print("Iniciando o download do Banco de Dados para o Criador de Fichas...")
    
    # Extrai as 9 Raças do SRD (Elfo, Humano, Anão, etc)
    extrair_dados("races", "DND5e_Racas.json")
    
    # Extrai as 12 Classes do SRD (Bárbaro, Mago, Ladino, etc)
    extrair_dados("classes", "DND5e_Classes.json")
    
    # Extrai ~230 Equipamentos (Armas, armaduras, ferramentas e itens iniciais)
    extrair_dados("equipment", "DND5e_Equipamentos.json")
    
    print("\n🎉 Extração finalizada! Verifique os arquivos JSON na sua pasta.")
