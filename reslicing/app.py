import streamlit as st
import subprocess
import os

# Configurações de pastas
TEMP_DIR = "temp_uploads"
RESULT_DIR = "output"
os.makedirs(RESULT_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

st.set_page_config(layout="wide", page_title="IFT Reslicing & Preview")

st.title("3D Reslicing + Real-time Preview")

# Estado da sessão para controlar se a imagem precisa ser atualizada
if 'reslice_done' not in st.session_state:
    st.session_state.reslice_done = False

col1, col2 = st.columns([1, 1.5])

with col1:
    st.subheader("1. Configuração do Volume")
    uploaded_file = st.file_uploader("Escolha o arquivo .scn original", type=["scn"])
    
    st.divider()
    
    st.subheader("2. Parâmetros do Reslicing")
    # Coordenadas
    m1, m2 = st.columns(2)
    with m1:
        st.caption("Ponto Inicial (P0)")
        x0 = st.number_input("x0", value=0.0)
        y0 = st.number_input("y0", value=0.0)
        z0 = st.number_input("z0", value=0.0)
    with m2:
        st.caption("Ponto Final (Pn-1)")
        xn = st.number_input("xn-1", value=100.0)
        yn = st.number_input("yn-1", value=100.0)
        zn = st.number_input("zn-1", value=100.0)
    
    n_slices = st.slider("Número de Fatias (Resolução Z)", 1, 512, 100)
    
    if st.button("Executar Reslicing", type="primary", disabled=(uploaded_file is None)):
        temp_path = os.path.join(TEMP_DIR, uploaded_file.name)
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
            
        output_volume = os.path.join(RESULT_DIR, "resliced_output.scn")
        
        with st.spinner("Gerando novo volume..."):
            # Executa o Reslicing
            subprocess.run([
                "/app/ift/bin/reslicing", temp_path, 
                str(x0), str(y0), str(z0), 
                str(xn), str(yn), str(zn), 
                str(n_slices), output_volume
            ])
            st.session_state.reslice_done = True
            st.success("Volume reamostrado!")

with col2:
    st.subheader("3. Visualização MIP do Corte")
    
    # Sliders de visualização (sempre visíveis para ajuste)
    v1, v2 = st.columns(2)
    view_alpha = v1.slider("Ângulo Alpha (X)", 0, 360, 0, key="v_alpha")
    view_beta = v2.slider("Ângulo Beta (Y)", 0, 360, 0, key="v_beta")
    
    preview_path = os.path.join(RESULT_DIR, "reslice_preview")
    resliced_volume = os.path.join(RESULT_DIR, "resliced_output.scn")

    # Só tenta gerar o MIP se o volume já foi criado pelo menos uma vez
    if st.session_state.reslice_done and os.path.exists(resliced_volume):
        # Executa o MIP sobre o volume gerado pelo Reslicing
        subprocess.run([
            "/app/ift/bin/MIP", 
            resliced_volume, 
            str(view_alpha), 
            str(view_beta), 
            preview_path
        ])
        
        # Exibe os resultados
        img_col1, img_col2 = st.columns(2)
        if os.path.exists(f"{preview_path}.png"):
            img_col1.image(f"{preview_path}.png", caption="MIP (Grayscale)")
        if os.path.exists(f"{preview_path}_colored.png"):
            img_col2.image(f"{preview_path}_colored.png", caption="MIP (Color)")
            
        # Botão de download do arquivo .scn gerado
        st.divider()
        with open(resliced_volume, "rb") as f:
            st.download_button("Baixar Novo Volume (.scn)", f, file_name="resliced_volume.scn")
    else:
        st.info("Execute o Reslicing na coluna ao lado para visualizar o resultado aqui.")