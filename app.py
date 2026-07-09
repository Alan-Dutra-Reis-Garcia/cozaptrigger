import streamlit as st
import pandas as pd
import time
import random
import requests
from firebase_manager import FirebaseManager
from gerenciador_mensagens import GerenciadorMensagens

# 🌐 CONFIGURAÇÕES DA SUA API EVOLUTION NO RAILWAY
EVOLUTION_API_URL = "https://evolution-api-production-2e1d3.up.railway.app"
INSTANCE_NAME = "carole_refeitorio"
EVOLUTION_API_KEY = "d34725dc513a4029896e17d6091736e15c65c7fc7d1b878019f6bc43e6d26d3e"

# Configuração da página do Streamlit
st.set_page_config(page_title="CoZapTrigger - Disparos API", page_icon="🚀", layout="wide")

# Inicializa as conexões na sessão do Streamlit
if "firebase" not in st.session_state:
    try:
        st.session_state.firebase = FirebaseManager()
    except Exception as e:
        st.error(f"Erro ao conectar ao Firebase: {e}")

if "gerenciador_msg" not in st.session_state:
    st.session_state.gerenciador_msg = GerenciadorMensagens()

if "logado" not in st.session_state:
    st.session_state.logado = False
    st.session_state.usuario_nome = ""

if "wpp_status" not in st.session_state:
    st.session_state.wpp_status = "Verificando..."

# --- FUNÇÃO PARA CONVERSAR COM A EVOLUTION API ---
def checar_status_instancia():
    """Verifica na Evolution API se a instância está conectada ou precisa de QR Code"""
    url = f"{EVOLUTION_API_URL}/instance/connectionState/{INSTANCE_NAME}"
    headers = {"apikey": EVOLUTION_API_KEY}
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            dados = response.json()
            status = dados.get("instance", {}).get("state", "DESCONECTADO")
            if status in ["CONNECTED", "open", "PAIRED"]:
                return "Conectado"
            return "Aguardando QR Code"
        elif response.status_code == 404:
            return "Instância Não Criada"
        return "Desconectado"
    except:
        return "Erro de Conexão com API"

def criar_ou_conectar_instancia():
    """Cria a instância na nuvem caso ela não exista"""
    url = f"{EVOLUTION_API_URL}/instance/create"
    headers = {"Content-Type": "application/json", "apikey": EVOLUTION_API_KEY}
    payload = {
        "instanceName": INSTANCE_NAME,
        "token": "CoZapTokenSecret2026",
        "qrcode": True
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def obter_qrcode_base64():
    """Busca a imagem do QR Code para exibir no Streamlit"""
    url = f"{EVOLUTION_API_URL}/instance/connect/{INSTANCE_NAME}"
    headers = {"apikey": EVOLUTION_API_KEY}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json().get("base64")
    except:
        return None


# --- 🔐 TELA DE LOGIN RESTAURADA ---
if not st.session_state.logado:
    st.markdown("<h1 style='text-align: center; color: #004B87;'>CoZapTrigger</h1>", unsafe_allow_html=True)
    with st.form(key="form_login"):
        email = st.text_input("E-mail", placeholder="nome.sobrenome@crefaz.com.br").strip()
        senha = st.text_input("Senha", type="password", placeholder="******")
        botao_entrar = st.form_submit_button(label="Entrar no Sistema")
        
        if botao_entrar:
            with st.spinner("Autenticando..."):
                resultado = st.session_state.firebase.verificar_login(email, senha)
                if resultado["sucesso"]:
                    st.session_state.logado = True
                    st.session_state.usuario_nome = resultado["nome"]
                    st.rerun()
                else:
                    st.error(f"Falha no login: {resultado['erro']}")

# --- 🚀 TELA INTERNA DO SISTEMA ---
else:
    st.sidebar.markdown(f"👤 **Vendedor:**\n{st.session_state.usuario_nome}")
    st.sidebar.markdown("---")
    
    st.sidebar.subheader("🔌 Conexão WhatsApp (API)")
    st.sidebar.session_state.wpp_status = checar_status_instancia()
    
    if st.session_state.wpp_status == "Instância Não Criada":
        if st.sidebar.button("⚙️ Inicializar Instância na Nuvem"):
            criar_ou_conectar_instancia()
            st.rerun()
            
    if st.session_state.wpp_status == "Conectado":
        st.sidebar.success("🟢 Status Atual: Conectado")
    else:
        st.sidebar.info(f"🔵 Status: {st.session_state.wpp_status}")
        if st.sidebar.button("🔄 Verificar Status"):
            st.rerun()
            
        if st.session_state.wpp_status == "Aguardando QR Code":
            qr_base64 = obter_qrcode_base64()
            if qr_base64:
                st.sidebar.image(qr_base64, caption="Escaneie para conectar seu chip")

    st.sidebar.markdown("---")
    if st.sidebar.button("Sair do Sistema"):
        st.session_state.logado = False
        st.rerun()

    # Cabeçalho principal
    st.title("🚀 Painel de Disparos - CoZapTrigger")
    st.markdown("---")

    aba_upload, aba_colar = st.tabs(["📁 Subir Planilha (CSV/Excel)", "✍️ Copiar e Colar (Ctrl+V)"])
    lista_leads_brutos = []

    # --- ABA 1: SUBIR PLANILHA (CSV/EXCEL) ---
    with aba_upload:
        st.subheader("Carregar arquivo de dados")
        st.markdown("A planilha deve conter obrigatoriamente as colunas: **cpf**, **nome**, **fonte**, **criado**, **telefone**.")
        arquivo_carregado = st.file_uploader("Selecione o arquivo (.csv, .xlsx, .xls)", type=["csv", "xlsx", "xls"])
        
        if arquivo_carregado is not None:
            try:
                if arquivo_carregado.name.endswith('.csv'):
                    df_upload = pd.read_csv(arquivo_carregado, sep=None, engine='python', dtype=str)
                else:
                    df_upload = pd.read_excel(arquivo_carregado, dtype=str)
                
                # Normaliza o nome das colunas para evitar problemas de maiúsculas/minúsculas
                df_upload.columns = [c.strip().lower() for c in df_upload.columns]
                colunas_obrigatorias = ['cpf', 'nome', 'fonte', 'criado', 'telefone']
                
                if all(col in df_upload.columns for col in colunas_obrigatorias):
                    for _, row in df_upload.iterrows():
                        if pd.notna(row['telefone']) and str(row['telefone']).strip() != "":
                            lista_leads_brutos.append({
                                "cpf": str(row['cpf']).strip() if pd.notna(row['cpf']) else "",
                                "nome": str(row['nome']).strip() if pd.notna(row['nome']) else "Cliente",
                                "fonte": str(row['fonte']).strip() if pd.notna(row['fonte']) else "Não Informada",
                                "criado": str(row['criado']).strip() if pd.notna(row['criado']) else "",
                                "telefone": str(row['telefone']).strip()
                            })
                    st.success(f"📊 {len(lista_leads_brutos)} contatos importados com sucesso da planilha!")
                else:
                    st.error(f"❌ Erro na estrutura: O arquivo precisa conter as colunas: {', '.join(colunas_obrigatorias)}")
            except Exception as e:
                st.error(f"❌ Erro ao processar o arquivo: {e}")

    # --- ABA 2: COPIAR E COLAR (CTRL+V) ---
    with aba_colar:
        st.subheader("Colar dados dos clientes")
        texto_colado = st.text_area("Cole as linhas aqui (CPF;Nome;Fonte;Criado;Telefone):", height=150)
        if texto_colado.strip():
            linhas_texto = texto_colado.strip().split('\n')
            for linha in linhas_texto:
                partes = linha.split(';')
                if len(partes) == 5:
                    lista_leads_brutos.append({
                        "cpf": partes[0].strip(), "nome": partes[1].strip(),
                        "fonte": partes[2].strip(), "criado": partes[3].strip(), "telefone": partes[4].strip()
                    })

    # --- PROCESSAMENTO E REVISÃO DOS LEADS ---
    if lista_leads_brutos:
        st.markdown("---")
        st.subheader("📋 Revisão dos Disparos Dinâmicos")
        
        # 🎯 BULLETS DE INFORMAÇÕES DE CARREGAMENTO
        st.markdown(f"""
        * 🔢 **Total de registros identificados:** {len(lista_leads_brutos)} contatos prontos para processamento.
        * 🛡️ **Estratégia Antiban:** Gerando blocos randômicos e textos dinâmicos para cada envio individual.
        """)
        
        dados_revisao = []
        for lead in lista_leads_brutos:
            msg_final, blocos = st.session_state.gerenciador_msg.gerar_mensagem_randomica(
                nome_cliente=lead['nome'], fonte_cliente=lead['fonte']
            )
            dados_revisao.append({
                "CPF": lead['cpf'], "Nome": lead['nome'], "Fonte": lead['fonte'],
                "Telefone": lead['telefone'], "Mensagem que será Enviada": msg_final,
                "_blocos": blocos, "_original": lead
            })
        
        df_revisao = pd.DataFrame(dados_revisao)
        st.dataframe(df_revisao[["CPF", "Nome", "Fonte", "Telefone", "Mensagem que será Enviada"]], use_container_width=True)

        st.markdown("### ⚡ Execução")
        if st.session_state.wpp_status != "Conectado":
            st.error("⚠️ A API do WhatsApp precisa estar CONECTADA na barra lateral.")
        else:
            if st.button("Iniciar Fila de Disparos Seguro (Via API)", type="primary"):
                horario_inicio = time.strftime("%H:%M:%S")
                timestamp_inicio_total = time.time()
                
                # 📊 CARD MACRO ATUALIZADO (Agora com 4 Colunas)
                card_metricas = st.columns(4)
                barra_progresso = st.progress(0)
                status_disparo = st.empty()
                
                # 📋 PAINEL DO HISTÓRICO LINHA A LINHA
                st.markdown("### 📋 Acompanhamento Detalhado (Linha a Linha)")
                placeholder_tabela_viva = st.empty()
                historico_envios_locais = []
                
                total_leads = len(dados_revisao)
                enviados_sucesso = 0
                
                with card_metricas[0]:
                    metrica_inicio = st.metric("Início dos Disparos", horario_inicio)
                with card_metricas[1]:
                    metrica_progresso = st.metric("Progresso de Envio", f"0 de {total_leads}")
                with card_metricas[2]:
                    metrica_sucesso = st.metric("Enviados com Sucesso", "0")
                with card_metricas[3]:
                    metrica_tempo_medio = st.metric("Tempo Médio / Disparo", "0.0s")

                for index, item in enumerate(dados_revisao):
                    lead_orig = item["_original"]
                    blocos_msg = item["_blocos"]
                    msg_texto = item["Mensagem que será Enviada"]
                    
                    telefone = "".join(filter(str.isdigit, str(item["Telefone"])))
                    if not telefone.startswith("55") and len(telefone) >= 10:
                        telefone = f"55{telefone}"
                        
                    status_disparo.info(f"⏳ Enviando via API para {item['Nome']}...")
                    
                    url_envio = f"{EVOLUTION_API_URL}/message/sendText/{INSTANCE_NAME}"
                    headers_envio = {"Content-Type": "application/json", "apikey": EVOLUTION_API_KEY}
                    payload_envio = {
                        "number": telefone,
                        "text": msg_texto,
                        "delay": 1200,
                        "linkPreview": False
                    }
                    
                    status_atual_linha = "Erro"
                    try:
                        response_api = requests.post(url_envio, json=payload_envio, headers=headers_envio, timeout=15)
                        
                        if response_api.status_code in [200, 201, 202]:
                            enviados_sucesso += 1
                            status_atual_linha = "Sucesso"
                            
                            try:
                                dados_resposta = response_api.json()
                                wpp_message_id = dados_resposta.get("key", {}).get("id") or dados_resposta.get("response", {}).get("key", {}).get("id", f"msg_{int(time.time())}")
                            except Exception:
                                wpp_message_id = f"msg_{int(time.time())}_{item['CPF']}"
                            
                            dados_para_salvar = {
                                "cpf": item["CPF"],
                                "nome": item["Nome"],
                                "fonte": lead_orig.get("fonte", "Não informada"),
                                "criado_em_origem": lead_orig.get("criado", ""),
                                "telefone": telefone,
                                "mensagem_enviada": msg_texto,
                                "wpp_message_id": wpp_message_id,
                                "horario_disparo": time.strftime("%Y-%m-%d %H:%M:%S"),
                                "timestamp_disparo": time.time(),
                                "template_blocos": blocos_msg, 
                                "status_envio": "ENTREGUE"
                            }
                            
                            st.session_state.firebase.salvar_lead_disparado(dados_para_salvar, blocos_msg)
                            st.toast(f"✅ Enviado para {item['Nome']}!")
                        else:
                            st.error(f"❌ Erro na API ao enviar para {item['Nome']}: Code {response_api.status_code}")
                            
                    except Exception as err:
                        st.error(f"❌ Falha de rede ao contatar a API para {item['Nome']}: {err}")
                    
                    # 🕒 Captura hora do disparo atual e alimenta a tabela viva abaixo do macro
                    hora_disparo_atual = time.strftime("%H:%M:%S")
                    historico_envios_locais.append({
                        "Nome": item["Nome"],
                        "Telefone": item["Telefone"],
                        "Mensagem": msg_texto,
                        "Hora do Disparo": hora_disparo_atual,
                        "Status": status_atual_linha
                    })
                    # Atualiza o componente visual de tabela com os novos dados estruturados
                    placeholder_tabela_viva.dataframe(pd.DataFrame(historico_envios_locais), use_container_width=True)
                    
                    # ⏱️ CÁLCULO DE TEMPO MÉDIO REAL DE DISPARO
                    tempo_decorrido_total = time.time() - timestamp_inicio_total
                    tempo_medio_atual = tempo_decorrido_total / (index + 1)
                    
                    # Atualiza as métricas macros superiores
                    progresso_atual = (index + 1) / total_leads
                    barra_progresso.progress(progresso_atual)
                    metrica_progresso.metric("Progresso de Envio", f"{index + 1} de {total_leads}")
                    metrica_sucesso.metric("Enviados com Sucesso", str(enviados_sucesso))
                    metrica_tempo_medio.metric("Tempo Médio / Disparo", f"{tempo_medio_atual:.1f}s")
                    
                    if index < total_leads - 1:
                        tempo_espera = random.randint(5, 50)
                        for segundo in range(tempo_espera, 0, -1):
                            status_disparo.warning(f"🛡️ Antiban: Aguardando {segundo} segundos para o próximo disparo...")
                            time.sleep(1)
                            
                status_disparo.success(f"🎉 Fila concluída via API! Total enviados com sucesso: {enviados_sucesso}")