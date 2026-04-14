import streamlit as st
import subprocess
import os

TEMP_DIR = "temp_uploads"
RESULT_DIR = "output"
os.makedirs(RESULT_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

st.set_page_config(layout="wide", page_title="IFT Medical Study Tool")

st.header("2. 3D Maximum Intensity Projection (MIP)")

col1, col2 = st.columns([1, 2])

with col1:
    uploaded_file = st.file_uploader("Escolha um arquivo .scn do seu computador", type=["scn"])
    
    st.divider()
    
    alpha = st.slider("Rotation Alpha (X)", 0, 360, 0)
    beta = st.slider("Rotation Beta (Y)", 0, 360, 0)
    out_name = "mip_result"
    
    if st.button("Generate MIP", disabled=(uploaded_file is None)):
        temp_path = os.path.join(TEMP_DIR, uploaded_file.name)
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
            
        with st.spinner(f"Processando {uploaded_file.name}..."):
            subprocess.run([
                "./MIP", 
                temp_path, 
                str(alpha), 
                str(beta), 
                f"{RESULT_DIR}/{out_name}"
            ])
            
        st.success("Projeção concluída!")

with col2:
    m_col1, m_col2 = st.columns(2)
    result_path = f"{RESULT_DIR}/{out_name}.png"
    result_colored_path = f"{RESULT_DIR}/{out_name}_colored.png"

    if os.path.exists(result_path):
        m_col1.image(result_path, caption="Grayscale MIP Result")
    
    if os.path.exists(result_colored_path):
        m_col2.image(result_colored_path, caption="Color-Mapped MIP Result")