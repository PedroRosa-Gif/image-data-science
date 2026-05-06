import os
import torch
import numpy as np
import nibabel as nib
import scipy.ndimage as ndi

from monai.bundle import ConfigParser, download

# =========================
# CONFIG
# =========================
BUNDLE_NAME = "brats_mri_segmentation"
BUNDLE_DIR = "./models-saved"

T1_PATH    = "t1.nii.gz"
T1C_PATH   = "t1c.nii.gz"
T2_PATH    = "t2.nii.gz"
FLAIR_PATH = "flair.nii.gz"

OUTPUT_SEEDS = "seeds.scn"

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

CONF_THRESH = 0.9


# =========================
# 1. DOWNLOAD + LOAD MODEL
# =========================
def load_model():
    print("Baixando bundle do MONAI (se necessário)...")
    download(name=BUNDLE_NAME, bundle_dir=BUNDLE_DIR)

    config_path = os.path.join(
        BUNDLE_DIR,
        BUNDLE_NAME,
        "configs",
        "inference.json"
    )

    parser = ConfigParser()
    parser.read_config(config_path)

    print("Criando modelo...")
    model = parser.get_parsed_content("network")

    weights_path = parser.get_parsed_content("load_path")

    print("Carregando pesos...")
    model.load_state_dict(torch.load(weights_path, map_location=DEVICE))

    model.to(DEVICE)
    model.eval()

    return model


# =========================
# 2. LOAD MRI (4 canais)
# =========================
def load_mri():
    def load(path):
        img = nib.load(path).get_fdata()
        img = (img - img.min()) / (img.max() - img.min() + 1e-8)
        return img

    print("Carregando volumes MRI...")
    t1    = load(T1_PATH)
    t1c   = load(T1C_PATH)
    t2    = load(T2_PATH)
    flair = load(FLAIR_PATH)

    # stack canais
    image = np.stack([t1, t1c, t2, flair], axis=0)

    # adiciona batch
    image = np.expand_dims(image, axis=0)

    return torch.tensor(image, dtype=torch.float32)


# =========================
# 3. INFERÊNCIA
# =========================
def predict(model, image):
    print("Rodando inferência...")
    with torch.no_grad():
        image = image.to(DEVICE)

        logits = model(image)

        prob = torch.softmax(logits, dim=1)
        confidence, label = torch.max(prob, dim=1)

    return prob.cpu(), confidence.cpu(), label.cpu()


# =========================
# 4. GERAR SEEDS
# =========================
def generate_seeds(label, confidence):
    print("Gerando seeds...")

    label = label.squeeze().numpy()
    confidence = confidence.squeeze().numpy()

    seeds = np.zeros_like(label, dtype=np.int32)

    # BraTS: tudo que é tumor vira objeto
    obj = (label > 0) & (confidence > CONF_THRESH)
    bg  = (label == 0) & (confidence > CONF_THRESH)

    # erosão pra robustez
    obj = ndi.binary_erosion(obj, iterations=2)
    bg  = ndi.binary_erosion(bg, iterations=2)

    seeds[obj] = 1
    seeds[bg]  = 2

    print("Valores únicos nas seeds:", np.unique(seeds))

    return seeds


# =========================
# 5. SALVAR .SCN
# =========================
def save_scn(filename, volume, bits=16):
    z, y, x = volume.shape
    volume = (volume - volume.min()) / (volume.max() - volume.min() + 1e-8)
    volume = (volume * 65535).astype(np.uint16)

    with open(filename, "wb") as f:
        f.write(b"SCN\n")
        f.write(f"{x} {y} {z}\n".encode())
        f.write(b"1.0 1.0 1.0\n")
        f.write(f"{bits}\n".encode())
        volume.tofile(f)


# =========================
# MAIN
# =========================
def main():
    model = load_model()
    image = load_mri()
    prob, confidence, label = predict(model, image)
    seeds = generate_seeds(label, confidence)
    save_scn(seeds, OUTPUT_SEEDS)
    print("✅ Pipeline completo finalizado!")

if __name__ == "__main__":
    main()