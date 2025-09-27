import streamlit as st
import pandas as pd
from fpdf import FPDF
from PIL import Image
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase
import av
import io
import os # Necessário para remover arquivos temporários

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

def delete_captured_photo(index_to_delete):
    """Remove uma foto da lista de fotos capturadas pelo seu índice."""
    if 0 <= index_to_delete < len(st.session_state.fotos_capturadas):
        # O método pop(index) remove o item e o retorna (embora não precisemos usá-lo)
        st.session_state.fotos_capturadas.pop(index_to_delete)
        # Não é necessário st.rerun() dentro de um callback, pois o Streamlit fará isso.


# A função de geração de PDF foi atualizada para aceitar objetos PIL.Image 
# e objetos st.uploaded_file/BytesIO, que são os formatos que teremos
def create_pdf(data_ocorrencia, tipo_devolucao, transportadora, nota_fiscal, delivery, pedido, rastreio, materiais, fotos):
    pdf = FPDF()
    pdf.add_page()
    # Usando fonte 'Arial' padrão. Se houver problemas com acentuação, 
    # pode ser necessário usar 'Arial' com um charset específico ou outra fonte.
    pdf.set_font("Arial", size=12)

    # Título
    pdf.cell(200, 10, txt="Relatório de Ocorrência em Devolução", ln=True, align="C")
    pdf.ln(10)

    # Detalhes da Ocorrência
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, "Detalhes da Ocorrência:", ln=True)
    pdf.set_font("Arial", size=12)
    # Convertendo data_ocorrencia para string no formato DD/MM/AAAA para o PDF
    data_formatada = data_ocorrencia.strftime("%d/%m/%Y") 
    pdf.cell(200, 10, f"Data da Ocorrência: {data_formatada}", ln=True)
    pdf.cell(200, 10, f"Tipo de Devolução: {tipo_devolucao}", ln=True)
    pdf.cell(200, 10, f"Transportadora: {transportadora}", ln=True)
    pdf.cell(200, 10, f"Nota Fiscal: {nota_fiscal}", ln=True)
    pdf.cell(200, 10, f"Delivery: {delivery}", ln=True)
    pdf.cell(200, 10, f"Pedido: {pedido}", ln=True)
    pdf.cell(200, 10, f"Rastreio: {rastreio}", ln=True)
    pdf.ln(5)

    # Materiais da Ocorrência
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, "Materiais da Ocorrência:", ln=True)
    pdf.set_font("Arial", size=12)
    if not materiais:
        pdf.cell(200, 10, "Nenhum material adicionado.", ln=True)
    else:
        for material in materiais:
            pdf.cell(200, 10, f"- Material: {material['Material']}, Lote: {material['Lote']}, Quantidade: {material['Quantidade']}, Tipo de Ocorrência: {material['Tipo de Ocorrência']}", ln=True)
    pdf.ln(5)

    # Fotos Anexadas
    temp_files = [] # Lista para rastrear arquivos temporários
    if fotos:
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(200, 10, "Fotos Anexadas:", ln=True)
        pdf.ln(5)
        
        for i, foto_data in enumerate(fotos):
            temp_filename = f"temp_image_{i}.jpg"
            
            if isinstance(foto_data, Image.Image):
                # Se for uma imagem PIL (capturada pela câmera)
                foto_data.save(temp_filename, "JPEG")
            elif hasattr(foto_data, 'read'):
                # Se for um st.uploaded_file ou objeto BytesIO (upload ou convertido)
                foto_data.seek(0) # Volta ao início do arquivo
                with open(temp_filename, "wb") as f:
                    f.write(foto_data.read())
            else:
                continue

            # Adiciona a imagem ao PDF
            try:
                pdf.image(temp_filename, w=150)
                pdf.ln(5)
                temp_files.append(temp_filename)
            except Exception as e:
                # O fpdf pode falhar se a imagem estiver corrompida ou em formato não suportado
                print(f"Erro ao adicionar imagem {temp_filename} ao PDF: {e}")
                
        # Limpa os arquivos temporários
        for filename in temp_files:
            if os.path.exists(filename):
                os.remove(filename)

    # O método output retorna o conteúdo do PDF como bytes. 'S' significa retorno como string/bytes.
    # Usando 'latin1' ou 'iso-8859-1' para compatibilidade com caracteres especiais do português
    pdf_output = pdf.output(dest="S").encode('latin1')
    return pdf_output

# Função para converter Image PIL em objeto BytesIO que simula um uploaded_file
def pil_image_to_bytesio(img: Image.Image, filename: str):
    """Converte Image PIL em BytesIO para tratar de forma unificada no PDF."""
    byte_io = io.BytesIO()
    img.save(byte_io, format='JPEG')
    byte_io.name = filename
    return byte_io

# --- Crie esta função no topo do seu script, antes do st.title() ---

def add_material_and_clear():
    """Adiciona o material e limpa os campos de input via session_state."""
    material = st.session_state.input_material
    lote = st.session_state.input_lote
    quantidade = st.session_state.input_quantidade
    tipo_ocorrencia = st.session_state.input_tipo_ocorrencia
    
    if material and lote and quantidade and tipo_ocorrencia:
        st.session_state.materiais.append({
            "Material": material.upper(),
            "Lote": lote.upper(),
            "Quantidade": int(quantidade),
            "Tipo de Ocorrência": tipo_ocorrencia
        })
        st.success(f"Material {material} adicionado com sucesso!")
        
        # Limpa os campos de input de forma segura
        st.session_state["input_material"] = ""
        st.session_state["input_lote"] = ""
        # Limpar o number_input para o valor padrão (1)
        st.session_state["input_quantidade"] = 1 
    else:
        st.error("Preencha todos os campos do material antes de adicionar.")


# --- Configuração e Estado do Streamlit ---

st.set_page_config(layout="wide") # Para usar a tela toda

caminho_imagem = "Assets/NestleDolceGusto.jpg"

st.image(
    caminho_imagem,
    use_container_width=True
)

# Armazenamento dos materiais e fotos em uma lista na sessão do Streamlit
if 'materiais' not in st.session_state:
    st.session_state.materiais = []
if 'fotos_capturadas' not in st.session_state:
    st.session_state.fotos_capturadas = []

# Injetar CSS para centralizar a tag H1 (que é usada pelo st.title)
st.markdown("""
<style>
.st-emotion-cache-16txto3 { /* Esta classe pode variar um pouco, mas é a mais comum para o container do st.title */
    text-align: center;
}     
/* Opcional: Se o código acima não funcionar (devido a atualizações do Streamlit), tente este: */
h1 {
    width: 100%;
    text-align: center;
}
            </style>
""", unsafe_allow_html=True)

st.title("Devolução Nestle")

# --- Campos de dados da ocorrência ---
st.header("Detalhes da Ocorrência")
col1, col2 = st.columns(2)
with col1:
    data_ocorrencia = st.date_input("Data da Ocorrência", format="DD/MM/YYYY")
    tipo_devolucao = st.selectbox("Tipo de Devolução", ["INSUCESSO","COLETA"])
    transportadora = st.selectbox("Transportadora", ["CORREIOS","DISSUDES","JAD LOG","REDE SUL","LOGAN","FAST SERVICE","FAST SHOP", "DIALOGO" ])
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
        # Note que o 'value' não precisa ser definido, o Streamlit o pega do session_state
        material = st.text_input("Material", key="input_material")
    with col_mat2:
        lote = st.text_input("Lote", key="input_lote")
    with col_mat3:
        # Inicialize o number_input para garantir que o session_state tenha um valor
        if "input_quantidade" not in st.session_state:
             st.session_state.input_quantidade = 1
        quantidade = st.number_input("Quantidade", min_value=1, step=1, key="input_quantidade")
    with col_mat4:
        tipo_ocorrencia = st.selectbox("Tipo de Ocorrência", ["AVARIA", "FALTA", "SOBRA", "INVERSÃO", "VENCIDO"], key="input_tipo_ocorrencia")

    # Botão para adicionar o material
    # A mágica: usamos o on_click para chamar a função de adição e limpeza
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


# 2. Captura por Câmera
st.header("Registrar Fotos")
col_camera, col_capture = st.columns([3, 1])

with col_camera:
    # O webrtc_streamer deve usar o nosso VideoProcessor
    webrtc_ctx = webrtc_streamer(
        key="camera", 
        video_processor_factory=VideoProcessor, 
        media_stream_constraints={"video": True, "audio": False}
    )

with col_capture:
    st.write("") # Espaçamento
    st.write("") # Espaçamento
    
    if webrtc_ctx.video_processor:
        # Pega o último frame do processador de vídeo
        latest_frame_av = webrtc_ctx.video_processor.latest_frame
        
        if st.button("Tirar Foto", use_container_width=True, type="secondary"):
            if latest_frame_av:
                # Converte o frame AV em uma imagem PIL (Pillow)
                image_pil = latest_frame_av.to_image()
                st.session_state.fotos_capturadas.append(image_pil)
                st.success("Foto capturada!")
            else:
                st.warning("Aguardando o stream da câmera... Tente novamente.")
    else:
        st.info("Câmera desligada ou aguardando permissão.")
    
    # Botão para limpar fotos capturadas
    # if st.session_state.fotos_capturadas:
        # if st.button("Limpar Fotos Capturadas", use_container_width=True):
            # st.session_state.fotos_capturadas = []
            # st.rerun() # Recarrega a tela para limpar as miniaturas

# Exibe as miniaturas das fotos capturadas
if st.session_state.fotos_capturadas:
    st.subheader("Galeria de Fotos")
    
    # Use um loop para criar uma coluna para cada foto capturada
    # Vamos usar colunas dinâmicas, limitando o máximo a 6 por linha
    num_fotos = len(st.session_state.fotos_capturadas)
    max_cols = 6
    cols = st.columns(min(num_fotos, max_cols))
    
    for i, img in enumerate(st.session_state.fotos_capturadas):
        # Calcula qual coluna usar
        col_index = i % max_cols
        
        with cols[col_index]:
            st.image(img, use_container_width=True)
            
            # Adiciona o botão de exclusão
            # A KEY deve ser única (usamos o índice 'i')
            # O on_click chama a função de callback, passando o índice como argumento
            st.button(
                "❌ Excluir", 
                key=f"delete_photo_{i}",
                use_container_width=True,
                on_click=delete_captured_photo,
                args=(i,) # <-- Argumento passado para a função (o índice da foto)
            )

# --- Anexar Fotos ---
st.markdown("---")
st.header("Ou Anexar Fotos")

# 1. Upload de Arquivos
uploaded_files = st.file_uploader("Escolha as fotos para upload...", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

# --- Finalizar ---
st.markdown("---")

# Botão para registrar a ocorrência e gerar o PDF
if st.button("Registrar Ocorrência", type="primary", use_container_width=True):
    if not st.session_state.materiais:
        st.error("Adicione pelo menos um material à ocorrência.")
    else:
        # Juntando todas as fotos em uma lista unificada para a função create_pdf
        todas_fotos = []
        
        # 1. Adiciona as fotos de upload
        if uploaded_files:
            todas_fotos.extend(uploaded_files)
            
        # 2. Adiciona as fotos capturadas (convertendo PIL.Image para BytesIO
        #    para padronizar o tratamento, embora a função create_pdf aceite PIL.Image)
        #    Usaremos o PIL.Image diretamente no PDF, como implementado na nova função.
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
            fotos=todas_fotos # Passa todas as fotos
        )
        
        # Oferece o arquivo para download
        st.download_button(
            label="Baixar PDF do Relatório",
            data=pdf_file,
            file_name=f"Relatorio_Devolucao_{nota_fiscal}_{data_ocorrencia.strftime('%Y%m%d')}.pdf",
            mime="application/pdf"
        )
        st.success("Ocorrência registrada e PDF gerado com sucesso!")