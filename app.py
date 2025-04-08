import streamlit as st
from PIL import Image
import numpy as np
import cv2

st.set_page_config(page_title="Furniture & Surface Transfer", layout="wide")

st.title("Furniture & Surface Transfer Uygulaması")
st.write(
    "Bu uygulamada iki resim yükleyin: "
    "Birincisi referans oda (içerik aktarılacak) ve ikincisi dekore etmek istediğiniz oda. "
    "‘Transfer’ düğmesine bastığınızda referans odanın tüm içeriği, hedef odanın geometrik boyutlarına uyarlanarak aktarılacaktır."
)

#############################
# Resim Yükleme (Adım 1)
#############################
ref_file = st.file_uploader("Referans Oda Resmini Yükleyin", type=["jpg", "jpeg", "png"], key="ref")
target_file = st.file_uploader("Dekore Edilecek Oda Resmini Yükleyin", type=["jpg", "jpeg", "png"], key="target")

if ref_file and target_file:
    ref_img = Image.open(ref_file).convert("RGB")
    target_img = Image.open(target_file).convert("RGB")
    
    st.subheader("Yüklenen Resimler")
    col1, col2 = st.columns(2)
    with col1:
        st.image(ref_img, caption="Referans Oda", use_column_width=True)
    with col2:
        st.image(target_img, caption="Hedef Oda", use_column_width=True)
    
    #############################
    # Transfer İşlemi (Adım 2,3,4 İptal Edildi)
    #############################
    if st.button("Transfer"):
        # Resimleri numpy dizisine dönüştürelim
        ref_np = np.array(ref_img)
        target_np = np.array(target_img)
        
        # Kaynak (referans) ve hedef (oda) noktaları: 
        # Tam resmin köşeleri kullanılıyor.
        src_pts = np.float32([
            [0, 0],
            [ref_np.shape[1], 0],
            [ref_np.shape[1], ref_np.shape[0]],
            [0, ref_np.shape[0]]
        ])
        dst_pts = np.float32([
            [0, 0],
            [target_np.shape[1], 0],
            [target_np.shape[1], target_np.shape[0]],
            [0, target_np.shape[0]]
        ])
        
        # Perspektif dönüşüm matrisini hesaplayın.
        M = cv2.getPerspectiveTransform(src_pts, dst_pts)
        warped_ref = cv2.warpPerspective(ref_np, M, (target_np.shape[1], target_np.shape[0]))
        
        # İsteğe bağlı karışım oranı: Kaynak warp edilmiş resim ile hedef oda resmi arasında blend yapılır.
        alpha = st.slider("Referans Resim Ağırlığı (Alpha)", 0.0, 1.0, 0.7)
        result_np = cv2.addWeighted(warped_ref, alpha, target_np, 1 - alpha, 0)
        
        result_img = Image.fromarray(result_np)
        st.subheader("Transfer Sonucu")
        st.image(result_img, caption="Transfer Edilmiş Oda", use_column_width=True)
