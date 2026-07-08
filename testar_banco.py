from firebase_manager import FirebaseManager

print("Testando conexão com o CoZapTrigger...")
try:
    # Inicializa o gerenciador
    manager = FirebaseManager()
    
    # Cria um lead de teste para forçar uma gravação no Firestore
    lead_teste = {
        "cpf": "00000000000",
        "nome": "Cliente Teste Inicial",
        "fonte": "Pré-Aprovados",
        "criado": "2026-07-07",
        "telefone": "5544999999999",
        "mensagem_enviada": "Mensagem de teste de infraestrutura",
        "mensagem_id": "TESTE_ID_123"
    }
    
    print("Tentando salvar lead de teste no Firebase...")
    resultado = manager.salvar_lead_disparado(lead_teste)
    
    if resultado["sucesso"]:
        print("🎉 SUCESSO ABSOLUTO! O Python conectou e gravou os dados no Firebase.")
    else:
        print(f"❌ Erro ao gravar dados: {resultado['erro']}")

except Exception as e:
    print(f"❌ Falha crítica no teste: {e}")