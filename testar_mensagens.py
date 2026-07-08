from gerenciador_mensagens import GerenciadorMensagens

gerenciador = GerenciadorMensagens()

print("--- TESTANDO SUA IDEIA COM METADADOS DOS BLOCOS (QUITADOS) ---")
for i in range(3):
    msg, blocos = gerenciador.gerar_mensagem_randomica(nome_cliente="Alan Garcia", fonte_cliente="Quitados")
    
    print(f"\n--- COMBINAÇÃO DE DISPARO {i+1} ---")
    print("[MENSAGEM FINAL]:")
    print(msg)
    print("\n[DADOS COMPLETO DOS BLOCOS PARA O FIRESTORE]:")
    print(f"-> Saudação: {blocos['saudacao_texto']}")
    print(f"-> Introdução: {blocos['introducao_texto']}")
    print(f"-> Oferta: {blocos['oferta_texto']}")
    print(f"-> CTA: {blocos['cta_texto']}")
    print(f"-> Conclusão: {blocos['conclusao_texto']}")
    print("-" * 60)