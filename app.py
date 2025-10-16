import streamlit as st
import pandas as pd
from fpdf import FPDF
from PIL import Image
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase
import av
import io
import os


# Inicialização do session_state (no topo do script)
if 'materiais' not in st.session_state:
    st.session_state.materiais = []
if 'fotos_capturadas' not in st.session_state:
    st.session_state.fotos_capturadas = []
if 'uploaded_photos' not in st.session_state: # Chave para o uploader
    st.session_state.uploaded_photos = None
# --- Funções e Classes Auxiliares ---

# Classe Customizada para processar o vídeo e armazenar o último frame
class VideoProcessor(VideoProcessorBase):
    def __init__(self):
        # Inicializa o último frame como None
        self.latest_frame = None

    # Este método é chamado para cada frame do vídeo
    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
        # Armazena o frame atual. O Streamlit-webrtc roda em um thread separado.
        self.latest_frame = frame
        # Retorna o frame para ser exibido (se não for retornado, a webcam fica preta)
        return frame

# =========================================================================
# FUNÇÃO DE LIMPEZA (CALLBACK) - CORRIGIDA
# =========================================================================
def clear_form_state():

    # 1. Limpa os materiais e fotos adicionadas (session_state listas)
    st.session_state.materiais = []
    st.session_state.fotos_capturadas = []
    st.session_state["uploaded_photos"] = None
    
    # 2. Limpa os campos de input de material (session_state keys)
    # NOTA: Isso deve limpar os campos "Material", "Lote" e redefinir "Quantidade"
    st.session_state["input_material"] = ""
    st.session_state["input_lote"] = ""
    st.session_state["input_quantidade"] = 1 
    
    # 3. Força a re-execução para limpar os widgets sem chave (text_input e file_uploader)
    st.rerun()

def delete_captured_photo(index_to_delete):
    """Remove uma foto da lista de fotos capturadas pelo seu índice."""
    if 0 <= index_to_delete < len(st.session_state.fotos_capturadas):
        st.session_state.fotos_capturadas.pop(index_to_delete)
        # Não é necessário st.rerun() dentro de um callback, pois o Streamlit fará isso.


# A FUNÇÃO DE GERAÇÃO DE PDF FOI REESCRITA PARA USAR TABELAS
def create_pdf(data_ocorrencia, tipo_devolucao, transportadora, nota_fiscal, delivery, pedido, rastreio, materiais, fotos):
    # Inicializa o PDF (P = Portrait, mm = milímetros, A4)
    pdf = FPDF('P', 'mm', 'A4')
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15) # Habilita quebra de página automática
    
    # ----------------------------------------------------
    # 1. TÍTULO
    # ----------------------------------------------------
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, txt="Relatório de Ocorrência em Devolução", align="C", ln=1)
    pdf.ln(5)

    pdf.cell(0, 10, txt="Nestle - Hub E-commerce Dolce Gusto - Araçariguama (SP)", align="C", ln=1)
    pdf.ln(5)
    # ----------------------------------------------------
    # 2. TABELA DE DETALHES DA OCORRÊNCIA
    # ----------------------------------------------------
    
    # Dados para a tabela de detalhes
    data_formatada = data_ocorrencia.strftime("%d/%m/%Y") 
    detalhes_data = [
        ("Data da Ocorrência", data_formatada),
        ("Tipo de Devolução", tipo_devolucao),
        ("Transportadora", transportadora),
        ("Nota Fiscal", nota_fiscal),
        ("Pedido", pedido),
        ("Delivery", delivery),
        ("Rastreio", rastreio)
    ]

    # Cabeçalho da seção
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Detalhes da Ocorrência:", ln=1)
    
    # Configurações da tabela de detalhes
    col_largura = 95 # Largura de cada coluna para a tabela de duas colunas
    pdf.set_line_width(0.2)
    
    pdf.set_font("Arial", 'B', 10)
    
    for label, value in detalhes_data:
        # Coluna 1: Rótulo (em negrito)
        pdf.set_fill_color(220, 220, 220) # Cor de fundo cinza
        pdf.cell(col_largura, 8, label, border=1, fill=True, align='L')
        
        # Coluna 2: Valor (normal)
        pdf.set_font("Arial", '', 10)
        pdf.cell(col_largura, 8, value, border=1, fill=False, align='L', ln=1)
        pdf.set_font("Arial", 'B', 10) # Volta para negrito para o próximo rótulo

    pdf.ln(5)

    # ----------------------------------------------------
    # 3. TABELA DE MATERIAIS DA OCORRÊNCIA
    # ----------------------------------------------------
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Materiais da Ocorrência:", ln=1)
    
    if not materiais:
        pdf.set_font("Arial", '', 10)
        pdf.multi_cell(0, 8, "Nenhum material adicionado.")
    else:
        # Larguras das colunas (total A4 é ~190mm)
        col_widths = [45, 30, 30, 85]
        headers = ["Material", "Lote", "Quantidade", "Tipo de Ocorrência"]
        row_height = 8

        # Linha de Cabeçalho da Tabela
        pdf.set_font("Arial", 'B', 10)
        pdf.set_fill_color(180, 180, 180) # Cor de fundo mais escura
        for col_w, header in zip(col_widths, headers):
            pdf.cell(col_w, row_height, header, border=1, fill=True, align='C')
        pdf.ln(row_height) # Quebra de linha após o cabeçalho

        # Linhas de Dados da Tabela
        pdf.set_font("Arial", '', 10)
        for material in materiais:
            # Garante que o texto se ajuste e quebre a linha se necessário (MultiCell)
            # Para manter a linha da tabela consistente, usamos 'cell' para um bom layout:
            
            # Material
            pdf.cell(col_widths[0], row_height, str(material['Material']), border='LR', align='L') 
            # Lote
            pdf.cell(col_widths[1], row_height, str(material['Lote']), border='LR', align='C')
            # Quantidade
            pdf.cell(col_widths[2], row_height, str(material['Quantidade']), border='LR', align='C')
            # Tipo de Ocorrência
            pdf.cell(col_widths[3], row_height, str(material['Tipo de Ocorrência']), border='LR', align='L', ln=1)
            
        # Linha de fechamento (apenas para estética)
        pdf.cell(sum(col_widths), 0, "", border='T', ln=1)

    pdf.ln(5)

    # ----------------------------------------------------
    # 4. FOTOS ANEXADAS (Manteremos sua lógica)
    # ----------------------------------------------------
    
    temp_files = [] # Lista para rastrear arquivos temporários
    if fotos:
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "Fotos Anexadas:", ln=1)
        pdf.ln(5)
        
        for i, foto_data in enumerate(fotos):
            temp_filename = f"temp_image_{i}.jpg"
            
            # Lógica para salvar a imagem temporariamente
            if isinstance(foto_data, Image.Image):
                foto_data.save(temp_filename, "JPEG")
            elif hasattr(foto_data, 'read'):
                foto_data.seek(0)
                with open(temp_filename, "wb") as f:
                    f.write(foto_data.read())
            else:
                continue

            # Adiciona a imagem ao PDF
            try:
                # Diminuído o tamanho W para caber na página e evitar quebra
                # A altura é ajustada automaticamente
                pdf.image(temp_filename, w=120) 
                pdf.ln(5)
                temp_files.append(temp_filename)
            except Exception as e:
                print(f"Erro ao adicionar imagem {temp_filename} ao PDF: {e}")
                
        # Limpa os arquivos temporários
        for filename in temp_files:
            if os.path.exists(filename):
                os.remove(filename)

    # O método output retorna o conteúdo do PDF como bytes.
    pdf_bytes = pdf.output(dest="S")
    pdf_output = io.BytesIO(pdf_bytes)
    pdf_output.name = "Relatorio_Devolucao.pdf"
    return pdf_output

# Função para converter Image PIL em objeto BytesIO que simula um uploaded_file
def pil_image_to_bytesio(img: Image.Image, filename: str):
    """Converte Image PIL em BytesIO para tratar de forma unificada no PDF."""
    byte_io = io.BytesIO()
    img.save(byte_io, format='JPEG')
    byte_io.name = filename
    return byte_io

def add_material_and_clear():
    """Adiciona o material e limpa os campos de input via session_state."""
    material = st.session_state.input_material
    lote = st.session_state.input_lote
    quantidade = st.session_state.input_quantidade
    tipo_ocorrencia = st.session_state.input_tipo_ocorrencia
    
    # Aplica caixa alta
    material_upper = material.upper() if material else ""
    lote_upper = lote.upper() if lote else ""
    
    if material and lote and quantidade and tipo_ocorrencia:
        st.session_state.materiais.append({
            "Material": material_upper,
            "Lote": lote_upper,
            "Quantidade": int(quantidade),
            "Tipo de Ocorrência": tipo_ocorrencia
        })
        st.success(f"Material {material} adicionado com sucesso!")
        
        # Limpa os campos de input de forma segura
        st.session_state["input_material"] = ""
        st.session_state["input_lote"] = ""
        st.session_state["input_quantidade"] = 1 
    else:
        st.error("Preencha todos os campos do material antes de adicionar.")


# --- Configuração e Estado do Streamlit ---

st.set_page_config(layout="wide") # Para usar a tela toda

caminho_imagem = "Assets/NestleDolceGusto.jpg"

# **********************************************
# NOTE: O CAMINHO DA IMAGEM DEVE ESTAR CORRETO NO SEU AMBIENTE!
# **********************************************
try:
    st.image(
        caminho_imagem,
        use_container_width=True
    )
except FileNotFoundError:
    st.error(f"Erro: Imagem de logo não encontrada em {caminho_imagem}. Verifique o caminho.")

# Armazenamento dos materiais e fotos em uma lista na sessão do Streamlit
if 'materiais' not in st.session_state:
    st.session_state.materiais = []
if 'fotos_capturadas' not in st.session_state:
    st.session_state.fotos_capturadas = []

# Injetar CSS para centralizar a tag H1 (que é usada pelo st.title)
st.markdown("""
<style>
/* Força a centralização do título */
h1 {
    width: 100%;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

st.title("Devolução Nestle")

# --- Anexar Fotos ---
st.markdown("---")
st.header("Registrar ou Anexar")

# 1. Upload de Arquivos
# Não possui 'key', será limpo automaticamente no rerun
uploaded_files = st.file_uploader("Registre novas fotos ou escolha fotos da galeria para upload...", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True, key="uploaded_photos")

st.markdown("---")

# --- Campos de dados da ocorrência ---
st.header("Detalhes da Ocorrência")
col1, col2 = st.columns(2)
with col1:
    # Nota: text_input, date_input e selectbox SEM 'key' resetam
    # na re-execução (rerun), o que é ideal para a limpeza.
    data_ocorrencia = st.date_input("Data da Ocorrência", format="DD/MM/YYYY")
    tipo_devolucao = st.selectbox("Tipo de Devolução", ["INSUCESSO","COLETA"])
    transportadora = st.selectbox("Transportadora", ["CORREIOS","DISSUDES","J&T","JAD LOG","REDE SUL","LOGAN","DIALOGO" , "FAVELA LOG","SAC SERVICE","FAST SERVICE","FAST SHOP"])
    nota_fiscal = st.text_input("Nota Fiscal")
with col2:
    pedido = st.text_input("Pedido")
    delivery = st.text_input("Delivery")
    rastreio = st.text_input("Rastreio")
    st.text("") # Espaço para alinhar

# --- Materiais da Ocorrência ---
st.markdown("---")
st.header("Materiais da Ocorrência")

# O armazenamento e a lógica de callback usam as chaves de estado

with st.expander("Adicionar Material", expanded=True):
    col_mat1, col_mat2, col_mat3, col_mat4 = st.columns(4)
    with col_mat1:
        material = st.text_input("Material", key="input_material")
    with col_mat2:
        lote = st.text_input("Lote", key="input_lote")
    with col_mat3:
        if "input_quantidade" not in st.session_state:
             st.session_state.input_quantidade = 1
        quantidade = st.number_input("Quantidade", min_value=1, step=1, key="input_quantidade")
    with col_mat4:
        tipo_ocorrencia = st.selectbox("Tipo de Ocorrência", ["AVARIA", "FALTA", "SOBRA", "INVERSÃO", "VENCIDO"], key="input_tipo_ocorrencia")

    # Botão para adicionar o material
    st.button(
        "Adicionar Material", 
        use_container_width=True, 
        on_click=add_material_and_clear # <-- Chamada da função de callback
    )

# Exibe e permite editar os materiais adicionados
if st.session_state.materiais:
    df_materiais = pd.DataFrame(st.session_state.materiais)

    st.subheader("Materiais da Ocorrência:")
    edited_df = st.data_editor(
        df_materiais,
        use_container_width=True,
        num_rows="dynamic",
        key="editor_materiais", # É importante para o Streamlit rastrear as edições
        hide_index=True
    )

    # Atualiza a lista de materiais na session_state com os dados editados
    st.session_state.materiais = edited_df.to_dict('records')
else:
    st.info("Nenhum material adicionado ainda.")

# --- Finalizar ---
st.markdown("---")

# Use um placeholder para o botão de "Nova Ocorrência" para que ele apareça no final
limpar_placeholder = st.empty()

# Botão para iniciar o processamento e gerar o PDF
if st.button("Registrar", type="primary", use_container_width=True):
    if data_ocorrencia and tipo_devolucao and transportadora and nota_fiscal and pedido and delivery and rastreio:
        if not st.session_state.materiais:
            st.error("Adicione pelo menos um material à ocorrência.")
        else:
            todas_fotos = []
            
            # Adiciona as fotos
            if uploaded_files:
                todas_fotos.extend(uploaded_files)
            if st.session_state.fotos_capturadas:
                todas_fotos.extend(st.session_state.fotos_capturadas)
            
            # Chama a função para gerar o PDF
            pdf_file = create_pdf(
                data_ocorrencia=data_ocorrencia,
                tipo_devolucao=tipo_devolucao,
                transportadora=transportadora,
                nota_fiscal=nota_fiscal,
                delivery=delivery,
                pedido=pedido,
                rastreio=rastreio,
                materiais=st.session_state.materiais,
                fotos=todas_fotos
            )
            
            st.success("Ocorrência registrada! Salve o relatório e clique em 'Nova Ocorrência'.")

            nome_arquivo_pdf = f"PEDIDO-{delivery}-TRANSPORTADORA-{transportadora}.pdf" 
            
            # Exibe o botão de download
            st.download_button(
                label="Salvar",
                data=pdf_file,
                file_name=nome_arquivo_pdf,
                mime="application/pdf",
            )

    else:
        st.error("Preencha todos os campos obrigatórios da ocorrência antes de registrar.")

st.button(
    "Nova Ocorrência", 
    type="secondary", 
    use_container_width=True,
    on_click=clear_form_state
)