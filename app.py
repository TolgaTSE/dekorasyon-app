import streamlit as st
import torch
import torchvision.transforms as T
from PIL import Image
import numpy as np
import cv2
import os

# Kişisel erişim tokenınızı ayarlayın (bu satırı güvenli bir şekilde saklayın).
os.environ["GITHUB_TOKEN"] = "tolgatse"

# Modeli yüklüyoruz (DeepLabV3-ResNet101, pre-trained)
@st.cache(allow_output_mutation=True)
def load_segmentation_model():
    model = torch.hub.load('pytorch/vision:v0.10.0', 'deeplabv3_resnet101', pretrained=True)
    model.eval()
    return model

model = load_segmentation_model()

# Ön işleme adımları
preprocess = T.Compose([
    T.ToTensor(),
    T.Normalize(mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225])
])

# Segmentasyon yapacak fonksiyon (model output'unu argmax alıyoruz)
def segment_image(pil_img):
    input_tensor = preprocess(pil_img).unsqueeze(0)
    with torch.no_grad():
        output = model(input_tensor)['out'][0]
    seg_map = output.argmax(0).byte().cpu().numpy()
    return seg_map

# Basit: Belirli segment için ortalama renk hesaplama
def compute_avg_color(np_img, seg_mask, seg_id):
    mask = seg_mask == seg_id
    if np.count_nonzero(mask) == 0:
        return np.array([0, 0, 0], dtype=np.float32)
    avg = np.array(np_img)[mask].mean(axis=0)
    return avg

st.set_page_config(page_title="Otomatik Texture Transfer", layout="wide")
st.title("Otomatik Texture Transfer (Photoshop Benzeri)")

st.write(
    "Bu uygulamada, referans odadaki her yüzeyin (duvar, zemin, mobilya vb.) dokusunu "
    "otomatik olarak algılar ve hedef odadaki en benzer yüzeylere transfer eder. "
    "Kod, semantik segmentasyon ve basit renk benzerliği ölçümü kullanır."
)

#############################
# Resim Yükleme
#############################
ref_file = st.file_uploader("Referans Oda Resmini Yükleyin", type=["jpg", "jpeg", "png"], key="ref")
target_file = st.file_uploader("Hedef Oda Resmini Yükleyin", type=["jpg", "jpeg", "png"], key="target")

if ref_file is not None and target_file is not None:
    ref_img = Image.open(ref_file).convert("RGB")
    target_img = Image.open(target_file).convert("RGB")
    
    st.subheader("Yüklenen Resimler")
    col1, col2 = st.columns(2)
    with col1:
        st.image(ref_img, caption="Referans Oda", use_column_width=True)
    with col2:
        st.image(target_img, caption="Hedef Oda", use_column_width=True)
    
    with st.spinner("Segmentasyon yapılıyor..."):
        ref_seg = segment_image(ref_img)
        target_seg = segment_image(target_img)
    
    st.subheader("Segmentasyon Sonuçları")
    col3, col4 = st.columns(2)
    with col3:
        st.image(ref_seg, caption="Referans Segmentasyonu", use_column_width=True)
    with col4:
        st.image(target_seg, caption="Hedef Segmentasyonu", use_column_width=True)
    
    # Her iki resimdeki benzersiz segment id'leri alınıyor.
    ref_ids = np.unique(ref_seg)
    target_ids = np.unique(target_seg)
    st.write("Referans Segment ID'leri:", ref_ids)
    st.write("Hedef Segment ID'leri:", target_ids)
    
    # Her segment için ortalama renk hesaplanıp eşleşme yapılır.
    ref_np = np.array(ref_img)
    target_np = np.array(target_img)
    mapping = {}
    for seg_id in ref_ids:
        ref_color = compute_avg_color(ref_np, ref_seg, seg_id)
        best_match = None
        best_diff = float('inf')
        for t_seg_id in target_ids:
            target_color = compute_avg_color(target_np, target_seg, t_seg_id)
            diff = np.linalg.norm(ref_color - target_color)
            if diff < best_diff:
                best_diff = diff
                best_match = t_seg_id
        mapping[seg_id] = best_match
    st.write("Segment Eşleştirme (Referans -> Hedef):", mapping)
    
    #############################
    # Texture Transfer (Her Segment için)
    #############################
    output_np = target_np.copy()
    st.subheader("Texture Transfer İşlemi")
    for seg_id, target_seg_id in mapping.items():
        # Her iki resimde ilgili segment maskelerini oluşturuyoruz.
        ref_mask = (ref_seg == seg_id).astype(np.uint8) * 255
        target_mask = (target_seg == target_seg_id).astype(np.uint8) * 255
        
        # Eğer segment alanı çok küçükse atlayabiliriz.
        if cv2.countNonZero(ref_mask) < 50 or cv2.countNonZero(target_mask) < 50:
            continue
        
        # Referans segmentin bounding rectangle'ını alalım.
        contours, _ = cv2.findContours(ref_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            continue
        ref_contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(ref_contour)
        ref_texture = ref_np[y:y+h, x:x+w]
        
        # Hedef segment için de bounding rectangle buluyoruz.
        contours, _ = cv2.findContours(target_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            continue
        target_contour = max(contours, key=cv2.contourArea)
        x_t, y_t, w_t, h_t = cv2.boundingRect(target_contour)
        
        # Referans dokuyu hedef alan boyutuna yeniden ölçeklendiriyoruz.
        ref_texture_resized = cv2.resize(ref_texture, (w_t, h_t))
        
        # Hedef bölgenin merkezini hesaplayalım.
        center = (x_t + w_t//2, y_t + h_t//2)
        
        # SeamlessClone ile transfer uyguluyoruz.
        try:
            output_np = cv2.seamlessClone(ref_texture_resized, output_np, target_mask[y_t:y_t+h_t, x_t:x_t+w_t], center, cv2.NORMAL_CLONE)
        except Exception as e:
            st.write(f"Segment {seg_id} transferinde hata: {e}")
    
    result_img = Image.fromarray(output_np)
    st.subheader("Sonuç")
    st.image(result_img, caption="Texture Transfer Sonucu", use_column_width=True)
