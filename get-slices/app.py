import streamlit as st
import subprocess
import os
from PIL import Image
import numpy as np

# Configuration
SCN_FILE = "data/brain.scn"  # Path to your input medical image
os.makedirs("results/plans", exist_ok=True)
os.makedirs("results/colors", exist_ok=True)

def run_c_logic():
    """This function calls your C binaries with current slider values."""
    w = st.session_state.win_val
    l = st.session_state.lev_val
    
    subprocess.run(["./get-slices", SCN_FILE, str(w), str(l)])

def get_displayable_image(path):
    """Converts 16-bit PNG to 8-bit for browser display."""
    if not os.path.exists(path):
        return None
    
    img = Image.open(path)
    
    if img.mode == 'I;16':
        nda = np.array(img)
        nda = (nda / 256).astype(np.uint8)
        return Image.fromarray(nda)
    
    return img

st.set_page_config(layout="wide", page_title="IFT Medical Study Tool")

st.header("1. Linear Stretching & Orthogonal Slicing")

if 'win_val' not in st.session_state:
    st.session_state.win_val = 50.0
    st.session_state.lev_val = 50.0
    run_c_logic()

col1, col2 = st.columns([1, 3])

with col1:
    st.subheader("Parameters")
    window = st.slider("Window", 0.0, 100.0, key="win_val", on_change=run_c_logic)
    level = st.slider("Level", 0.0, 100.0, key="lev_val", on_change=run_c_logic)

with col2:
    base = "brain"
    
    tab1, tab2 = st.tabs(["Grayscale Slices", "Color-Mapped Slices"])
    
    with tab1:
        c1, c2, c3 = st.columns(3)

        axial_path = f"results/plans/{base}_axial.png"
        coronal_path = f"results/plans/{base}_coronal.png"
        sagital_path = f"results/plans/{base}_sagital.png"

        display_axial_img = get_displayable_image(axial_path)
        display_coronal_img = get_displayable_image(coronal_path)
        display_sagital_img = get_displayable_image(sagital_path)
        
        if display_axial_img:
            c1.image(display_axial_img, caption="Axial")
        else:
            c1.warning("Axial slice not found.")

        if display_coronal_img:
            c2.image(display_coronal_img, caption="Coronal")
        else:
            c2.warning("Coronal slice not found.")
    
        if display_sagital_img:
            c3.image(display_sagital_img, caption="Sagital")
        else:
            c3.warning("Sagital slice not found.")

    with tab2:
        cc1, cc2, cc3 = st.columns(3)
        try:
            cc1.image(f"results/colors/{base}_axial_color.png", caption="Axial Color")
            cc2.image(f"results/colors/{base}_coronal_color.png", caption="Coronal Color")
            cc3.image(f"results/colors/{base}_sagital_color.png", caption="Sagital Color")
        except:
            st.info("Color maps will appear here.")