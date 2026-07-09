import streamlit as st
import pandas as pd
import time
import random
import requests
import datetime
from firebase_manager import FirebaseManager
from gerenciador_mensagens import GerenciadorMensagens

# 🌐 CONFIGURAÇÕES DA SUA API EVOLUTION NO RAILWAY
EVOLUTION_API_URL = "https://evolution-api-production-2e1d3.up.railway.app"
INSTANCE_NAME = "carole_refeitorio"
EVOLUTION_API_KEY = "d34725dc513a4029896e17d6091736e15c65c7fc7d1b878019f6bc43e6d26d3e"

# Configuração da página do Streamlit
st.set_page_config(page_title="CoZapTrigger - Sistema Integrado", page_icon="🚀", layout="wide")

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

# --- FUNÇÕES AUXILIARES DA API ---
def checar_status_instancia():
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
    url = f"{EVOLUTION_API_URL}/instance/create"
    headers = {"Content-Type": "application/json", "apikey": EVOLUTION_API_KEY}
    payload = {"instanceName": INSTANCE_NAME, "token": "CoZapTokenSecret2026", "qrcode": True}
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def obter_qrcode_base64():
    url = f"{EVOLUTION_API_URL}/instance/connect/{INSTANCE_NAME}"
    headers = {"apikey": EVOLUTION_API_KEY}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json().get("base64")
    except:
        return None

def calcular_metricas_completas(df_alvo):
    """Calcula a tabela comparativa de métricas baseada em qualquer agrupamento de DataFrame"""
    if df_alvo.empty:
        return pd.DataFrame()
        
    resumos = []
    for grupo, sub_df in df_alvo:
        disp = len(sub_df)
        entregues = len(sub_df[sub_df['status_envio'].isin(['ENTREGUE', 'LIDO'])])
        lidos = len(sub_df[sub_df['status_envio'] == 'LIDO'])
        respondidos = len(sub_df[sub_df['houve_retorno'] == True])
        
        p_entregue = (entregues / disp * 100) if disp > 0 else 0
        p_lido_vs_ent = (lidos / entregues * 100) if entregues > 0 else 0
        p_resp_vs_lido = (respondidos / lidos * 100) if lidos > 0 else 0
        p_resp_vs_disp = (respondidos / disp * 100) if disp > 0 else 0
        
        df_retornos = sub_df[(sub_df['houve_retorno'] == True) & (sub_df['tempo_ate_resposta_segundos'].notna())]
        t_medio = df_retornos['tempo_ate_resposta_segundos'].mean() if not df_retornos.empty else 0
        
        resumos.append({
            "Item/Grupo": grupo,
            "Disparos": disp,
            "Entregues": entregues,
            "% Entregue": f"{p_entregue:.1f}%",
            "Lidos": lidos,
            "% Lido/Ent": f"{p_lido_vs_ent:.1f}%",
            "Respondidos": respondidos,
            "% Resp/Lido": f"{p_resp_vs_lido:.1f}%",
            "% Resp/Disp": f"{p_resp_vs_disp:.1f}%",
            "T. Médio Retorno": f"{int(t_medio)}s" if t_medio > 0 else "0s"
        })
    return pd.DataFrame(resumos).set_index("Item/Grupo")


# --- 🔐 TELA DE LOGIN ---
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

# --- 🚀 AMBIENTE INTERNO LOGADO ---
else:
    # Menu Lateral Principal de Navegação
    st.sidebar.markdown(f"👤 **Vendedor:**\n{st.session_state.usuario_nome}")
    st.sidebar.markdown("---")
    
    # 🗺️ SEPARADOR DE AMBIENTES (DISPAROS VS INDICADORES)
    menu_navegacao = st.sidebar.radio(
        "Navegue pelo Sistema:",
        ["🚀 Fila de Disparos", "📊 Painel de Indicadores"]
    )
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔌 Conexão WhatsApp (API)")
    st.session_state.wpp_status = checar_status_instancia()
    
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


    # =========================================================================
    # MUNDO 1: FILA DE DISPAROS
    # =========================================================================
    if menu_navegacao == "🚀 Fila de Disparos":
        st.title("🚀 Painel de Disparos - CoZapTrigger")
        st.markdown("---")

        aba_upload, aba_colar = st.tabs(["📁 Subir Planilha (CSV/Excel)", "✍️ Copiar e Colar (Ctrl+V)"])
        lista_leads_brutos = []

        with aba_upload:
            st.subheader("Carregar arquivo de dados")
            arquivo_carregado = st.file_uploader("Selecione o arquivo (.csv, .xlsx, .xls)", type=["csv", "xlsx", "xls"])
            if arquivo_carregado is not None:
                try:
                    if arquivo_carregado.name.endswith('.csv'):
                        df_upload = pd.read_csv(arquivo_carregado, sep=None, engine='python', dtype=str)
                    else:
                        df_upload = pd.read_excel(arquivo_carregado, dtype=str)
                    
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
                        st.success(f"📊 {len(lista_leads_brutos)} contatos importados com sucesso!")
                    else:
                        st.error(f"❌ O arquivo precisa conter as colunas: {', '.join(colunas_obrigatorias)}")
                except Exception as e:
                    st.error(f"❌ Erro ao processar o arquivo: {e}")

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

        if lista_leads_brutos:
            st.markdown("---")
            st.subheader("📋 Revisão dos Disparos Dinâmicos")
            st.markdown(f"""
            * 🔢 **Total de registros identificados:** {len(lista_leads_brutos)} contatos carregados.
            * 🛡️ **Estratégia Antiban:** Gerando variação randômica de blocos de texto por lead.
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
                    
                    card_metricas = st.columns(4)
                    barra_progresso = st.progress(0)
                    status_disparo = st.empty()
                    
                    st.markdown("### 📋 Acompanhamento Detalhado (Linha a Linha)")
                    placeholder_tabela_viva = st.empty()
                    historico_envios_locais = []
                    
                    total_leads = len(dados_revisao)
                    enviados_sucesso = 0
                    
                    with card_metricas[0]: metrica_inicio = st.metric("Início dos Disparos", horario_inicio)
                    with card_metricas[1]: metrica_progresso = st.metric("Progresso de Envio", f"0 de {total_leads}")
                    with card_metricas[2]: metrica_sucesso = st.metric("Enviados com Sucesso", "0")
                    with card_metricas[3]: metrica_tempo_medio = st.metric("Tempo Médio / Disparo", "0.0s")

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
                        payload_envio = {"number": telefone, "text": msg_texto, "delay": 1200, "linkPreview": False}
                        
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
                                    "cpf": item["CPF"], "nome": item["Nome"],
                                    "fonte": lead_orig.get("fonte", "Não informada"),
                                    "criado_em_origem": lead_orig.get("criado", ""), "telefone": telefone,
                                    "mensagem_enviada": msg_texto, "wpp_message_id": wpp_message_id,
                                    "horario_disparo": time.strftime("%Y-%m-%d %H:%M:%S"),
                                    "timestamp_disparo": time.time(), "template_blocos": blocos_msg, 
                                    "status_envio": "ENTREGUE", "houve_retorno": False
                                }
                                st.session_state.firebase.salvar_lead_disparado(dados_para_salvar, blocos_msg)
                                st.toast(f"✅ Enviado para {item['Nome']}!")
                            else:
                                st.error(f"❌ Erro na API para {item['Nome']}: Code {response_api.status_code}")
                        except Exception as err:
                            st.error(f"❌ Falha de rede para {item['Nome']}: {err}")
                        
                        historico_envios_locais.append({
                            "Nome": item["Nome"], "Telefone": item["Telefone"],
                            "Mensagem": msg_texto, "Hora do Disparo": time.strftime("%H:%M:%S"),
                            "Status": status_atual_linha
                        })
                        placeholder_tabela_viva.dataframe(pd.DataFrame(historico_envios_locais), use_container_width=True)
                        
                        tempo_decorrido_total = time.time() - timestamp_inicio_total
                        tempo_medio_atual = tempo_decorrido_total / (index + 1)
                        
                        barra_progresso.progress((index + 1) / total_leads)
                        metrica_progresso.metric("Progresso de Envio", f"{index + 1} de {total_leads}")
                        metrica_sucesso.metric("Enviados com Sucesso", str(enviados_sucesso))
                        metrica_tempo_medio.metric("Tempo Médio / Disparo", f"{tempo_medio_atual:.1f}s")
                        
                        if index < total_leads - 1:
                            tempo_espera = random.randint(5, 50)
                            for segundo in range(tempo_espera, 0, -1):
                                status_disparo.warning(f"🛡️ Antiban: Aguardando {segundo} segundos...")
                                time.sleep(1)
                                
                    status_disparo.success(f"🎉 Fila concluída via API! Total enviados com sucesso: {enviados_sucesso}")


    # =========================================================================
    # MUNDO 2: PAINEL DE INDICADORES (O NOVO LUGAR)
    # =========================================================================
    elif menu_navegacao == "📊 Painel de Indicadores":
        st.title("📊 Painel Estratégico de Indicadores")
        st.markdown("---")
        
        with st.spinner("Puxando dados consolidados do Firestore..."):
            try:
                # Puxa a coleção direto do Firebase Manager
                colecao_ref = st.session_state.firebase.db.collection("historico_disparos").stream()
                lista_registros = [doc.to_dict() for doc in colecao_ref]
                df_completo = pd.DataFrame(lista_registros)
            except Exception as e:
                st.error(f"Erro ao carregar dados do Firebase: {e}")
                df_completo = pd.DataFrame()

        if df_completo.empty:
            st.info("Nenhum dado de histórico localizado no Firebase para gerar indicadores.")
        else:
            # 🛡️ BLINDAGEM ANTICRASH: Garante que colunas novas existam mesmo em registros antigos
            colunas_obrigatorias_df = [
                "fonte", "status_envio", "houve_retorno", "tempo_ate_resposta_segundos", 
                "timestamp_disparo", "horario_disparo", "data_envio",
                "bloco_saudacao", "bloco_introducao", "bloco_oferta", "bloco_cta", "bloco_conclusao"
            ]
            for col in colunas_obrigatorias_df:
                if col not in df_completo.columns:
                    df_completo[col] = None

            # 🔍 SEÇÃO DE FILTROS GERAIS (SIDE-BY-SIDE NO TOPO)
            st.subheader("🎛️ Filtros Estratégicos")
            col_f1, col_f2, col_f3, col_f4 = st.columns(4)
            
            with col_f1:
                opcoes_fonte = ["Todos"] + list(df_completo["fonte"].dropna().unique())
                filtro_fonte = st.selectbox("Origem / Fonte do Lead:", opcoes_fonte)
                
            with col_f2:
                # 🕒 Tratamento inteligente e seguro de datas com múltiplos fallbacks
                df_completo['data_formatada'] = pd.to_datetime(df_completo['timestamp_disparo'], unit='s', errors='coerce').dt.date
                
                # Se o timestamp falhar (registros antigos), tenta converter pelo horario_disparo string
                df_completo['data_formatada'] = df_completo['data_formatada'].fillna(
                    pd.to_datetime(df_completo['horario_disparo'], errors='coerce').dt.date
                )
                # Se ainda assim falhar, tenta pela data_envio nativa do Firebase
                df_completo['data_formatada'] = df_completo['data_formatada'].fillna(
                    pd.to_datetime(df_completo['data_envio'], errors='coerce').dt.date
                )
                # Fallback definitivo caso o banco tenha alguma linha totalmente corrompida
                df_completo['data_formatada'] = df_completo['data_formatada'].fillna(datetime.date.today())
                    
                menor_data = df_completo['data_formatada'].min()
                maior_data = df_completo['data_formatada'].max()
                
                periodo = st.date_input("Período do Disparo:", [menor_data, maior_data])
                
            with col_f3:
                filtro_retorno = st.selectbox("Teve Resposta (Retorno):", ["Todos", "Sim (True)", "Não (False)"])
                
            with col_f4:
                opcoes_status = ["Todos"] + list(df_completo["status_envio"].unique())
                filtro_status = st.selectbox("Status Atual do WhatsApp:", opcoes_status)

            # 🛠️ APLICAÇÃO DA MALHA DE FILTROS NO DATAFRAME
            df_filtrado = df_completo.copy()
            
            if filtro_fonte != "Todos":
                df_filtrado = df_filtrado[df_filtrado["fonte"] == filtro_fonte]
                
            if isinstance(periodo, list) or isinstance(periodo, tuple):
                if len(periodo) == 2:
                    df_filtrado = df_filtrado[(df_filtrado["data_formatada"] >= periodo[0]) & (df_filtrado["data_formatada"] <= periodo[1])]
                    
            if filtro_retorno != "Todos":
                valor_bool = True if "Sim" in filtro_retorno else False
                df_filtrado = df_filtrado[df_filtrado["houve_retorno"] == valor_bool]
                
            if filtro_status != "Todos":
                df_filtrado = df_filtrado[df_filtrado["status_envio"] == filtro_status]

            # -----------------------------------------------------------------
            # 📈 1. CABEÇALHO MACRO (MÉTRICAS CARDINAIS)
            # -----------------------------------------------------------------
            st.markdown("### 📊 Visão Geral Macro")
            
            total_disp = len(df_filtrado)
            total_ent = len(df_filtrado[df_filtrado['status_envio'].isin(['ENTREGUE', 'LIDO'])])
            total_lid = len(df_filtrado[df_filtrado['status_envio'] == 'LIDO'])
            total_resp = len(df_filtrado[df_filtrado['houve_retorno'] == True])
            
            pct_entregue = (total_ent / total_disp * 100) if total_disp > 0 else 0
            pct_lido_vs_ent = (total_lid / total_ent * 100) if total_ent > 0 else 0
            pct_resp_vs_lid = (total_resp / total_lid * 100) if total_lid > 0 else 0
            pct_resp_vs_disp = (total_resp / total_disp * 100) if total_disp > 0 else 0
            
            df_com_tempo = df_filtrado[(df_filtrado['houve_retorno'] == True) & (df_filtrado['tempo_ate_resposta_segundos'].notna())]
            t_medio_retorno = df_com_tempo['tempo_ate_resposta_segundos'].mean() if not df_com_tempo.empty else 0

            # Renderização física dos cards
            c_macro = st.columns(5)
            c_macro[0].metric("Total Disparos", f"{total_disp} und")
            c_macro[1].metric("Entregues", f"{total_ent} und", f"{pct_entregue:.1f}% de envio")
            c_macro[2].metric("Lidos (Abertura)", f"{total_lid} und", f"{pct_lido_vs_ent:.1f}% vs Entregue")
            c_macro[3].metric("Respondidos (Retorno)", f"{total_resp} und", f"{pct_resp_vs_lid:.1f}% vs Lido ({pct_resp_vs_disp:.1f}% do Geral)")
            c_macro[4].metric("Tempo Médio Retorno", f"{int(t_medio_retorno)}s" if t_medio_retorno > 0 else "0s")

            st.markdown("---")

            # -----------------------------------------------------------------
            # 🧩 2. DESEMPENHO POR BLOCOS DE MENSAGENS (ABAS)
            # -----------------------------------------------------------------
            st.markdown("### 🧩 Análise de Conversão por Blocos Estruturais")
            st.markdown("Compare a performance de cada frase sorteada pelo algoritmo para entender o que engaja mais o cliente.")
            
            aba_saudacao, aba_intro, aba_oferta, aba_cta, aba_concl = st.tabs([
                "👋 Saudações", "🚀 Introduções", "💰 Ofertas", "🎯 CTAs", "🏢 Conclusões"
            ])
            
            # Helper interno para agrupar e renderizar dataframes limpos por coluna de bloco
            def renderizar_bloco_analise(coluna_bloco):
                if coluna_bloco in df_filtrado.columns:
                    df_agrupado = df_filtrado.groupby(coluna_bloco)
                    df_resultado = calcular_metricas_completas(df_agrupado)
                    if not df_resultado.empty:
                        st.dataframe(df_resultado, use_container_width=True)
                    else:
                        st.info("Dados insuficientes para agrupar este bloco.")
                else:
                    st.warning("Aguardando novos registros contendo essa chave de bloco estrutural.")

            with aba_saudacao: renderizar_bloco_analise("bloco_saudacao")
            with aba_intro: renderizar_bloco_analise("bloco_introducao")
            with aba_oferta: renderizar_bloco_analise("bloco_oferta")
            with aba_cta: renderizar_bloco_analise("bloco_cta")
            with aba_concl: renderizar_bloco_analise("bloco_conclusao")

            st.markdown("---")

            # -----------------------------------------------------------------
            # 🏢 3. DESEMPENHO POR FONTE LADO A LADO
            # -----------------------------------------------------------------
            st.markdown("### 🏢 Comparativo Lado a Lado: Fontes de Leads")
            st.markdown("Visualização analítica de performance agrupada pela origem do banco de dados:")
            
            if "fonte" in df_filtrado.columns:
                df_fontes_agrupado = df_filtrado.groupby("fonte")
                df_fontes_final = calcular_metricas_completas(df_fontes_agrupado)
                if not df_fontes_final.empty:
                    st.dataframe(df_fontes_final, use_container_width=True)
                else:
                    st.info("Nenhuma fonte identificada para agrupamento lateral.")
            else:
                st.warning("Coluna de fontes ausente no DataFrame.")