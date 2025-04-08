import streamlit as st
from PIL import Image
import numpy as np
import cv2
from streamlit_drawable_canvas import st_canvas

st.set_page_config(page_title="Swap Uygulaması", layout="wide")

st.title("Swap Uygulaması: Referans Oda ile Dekore Edilen Oda")
st.write("Bu uygulamada, referans resimdeki içeriği, hedef odada belirlediğiniz alana geometrik olarak uyarlayarak swap yapabilirsiniz.")

#############################
# Adım 1: İki Resim Yükleme
#############################

st.sidebar.header("1. Resimleri Yükleyin")
ref_file = st.sidebar.file_uploader("Referans Oda Resmini Yükleyin", type=["jpg", "jpeg", "png"], key="ref")
target_file = st.sidebar.file_uploader("Dekore Edilecek Oda Resmini Yükleyin", type=["jpg", "jpeg", "png"], key="target")

if ref_file and target_file:
    ref_img = Image.open(ref_file).convert("RGB")
    target_img = Image.open(target_file).convert("RGB")
    
    st.subheader("Yüklenen Resimler")
    cols = st.columns(2)
    with cols[0]:
        st.image(ref_img, caption="Referans Oda Resmi", use_column_width=True)
    with cols[1]:
        st.image(target_img, caption="Dekore Edilecek Oda Resmi", use_column_width=True)
    
    ###################################
    # Adım 2: Hedef Alanda Alan Seçimi
    ###################################
    st.header("Adım 2: Hedef Oda Üzerinde Alan Belirleyin")
    st.write("Hedef oda resmi üzerinde swap işleminin uygulanacağı alanı belirlemek için fare ile çokgen çizin. "
             "En az 3 nokta seçin; 3 nokta seçilirse otomatik olarak 4. nokta hesaplanır, 4'ten fazla nokta seçilirse ilk 4 nokta kullanılır.")
    
    # St_canvas kullanarak hedef oda resmi üzerinde çizim yapıyoruz.
    # st_canvas fonksiyonu PIL.Image nesnesi de kabul edebiliyor.
    canvas_result = st_canvas(
        fill_color="rgba(255,165,0,0.3)",  # Yarı saydam dolgu
        stroke_width=2,
        stroke_color="#FF0000",
        background_color="#eee",           # Arka plan rengi (şeffaf için "rgba(0,0,0,0)")
        background_image=target_img,       # Doğrudan PIL.Image kullanıyoruz
        height=target_img.height,
        width=target_img.width,
        drawing_mode="polygon",
        key="canvas"
    )
    
    ##################################################
    # Adım 3: Seçilen Alanın Koordinatlarını İşleme
    ##################################################
    if canvas_result.json_data is not None:
        objects = canvas_result.json_data.get("objects", [])
        if objects:
            poly = objects[0]  # İlk çizilen çokgeni kullanıyoruz
            points = []
            # Çizim verisinde "M" (moveto) ve "L" (lineto) komutları kullanılmıştır.
            for item in poly.get("path", []):
                if item[0] in ["M", "L"]:
                    points.append([item[1], item[2]])
            if len(points) < 3:
                st.error("Lütfen en az 3 nokta seçin!")
            else:
                st.write("Seçilen Noktalar:", points)
                # Eğer 3 nokta seçilmişse, otomatik olarak 4. nokta hesaplayalım.
                if len(points) == 3:
                    def compute_fourth_point(p0, p1, p2):
                        return [p0[0] + p2[0] - p1[0], p0[1] + p2[1] - p1[1]]
                    p0, p1, p2 = points
                    p3 = compute_fourth_point(p0, p1, p2)
                    points.append(p3)
                    st.write("Otomatik Eklenen 4. Nokta:", p3)
                # Eğer 4'ten fazla nokta seçildiyse, sadece ilk 4 nokta alınır.
                if len(points) > 4:
                    points = points[:4]
                    st.write("Kullanılan 4 Nokta:", points)
                
                ########################################################
                # Adım 4: Perspektif Dönüşümü ve Swap İşleminin Uygulanması
                ########################################################
                st.header("Adım 4: Swap İşlemi Uygulandı")
                
                # Referans resmin tamamını kaynaktan alıyoruz.
                ref_np = np.array(ref_img)
                # Kaynak köşe noktaları (referans resmin tam köşeleri)
                src_pts = np.float32([[0, 0],
                                      [ref_np.shape[1], 0],
                                      [ref_np.shape[1], ref_np.shape[0]],
                                      [0, ref_np.shape[0]]])
                # Hedef köşe noktaları: kullanıcı tarafından belirlenen alan
                dst_pts = np.float32(points)
                
                # Perspektif dönüşüm matrisini hesaplayın
                M = cv2.getPerspectiveTransform(src_pts, dst_pts)
                target_np = np.array(target_img)
                # Referans resmi hedef odanın boyutlarına göre warp (dönüştürme) yapıyoruz.
                warped_ref = cv2.warpPerspective(np.array(ref_img), M, (target_np.shape[1], target_np.shape[0]))
                
                # Mask oluşturuyoruz: Warped referans resimdeki dolu alanları belirlemek için (siyah olmayan bölgeler)
                warped_gray = cv2.cvtColor(warped_ref, cv2.COLOR_BGR2GRAY)
                _, mask = cv2.threshold(warped_gray, 1, 255, cv2.THRESH_BINARY)
                mask_inv = cv2.bitwise_not(mask)
                
                # Hedef odanın, warp edilmiş bölge dışında kalan kısmını koruyoruz.
                target_bg = cv2.bitwise_and(target_np, target_np, mask=mask_inv)
                # İki resmi birleştiriyoruz.
                combined = cv2.add(target_bg, warped_ref)
                result_img = Image.fromarray(combined)
                
                st.image(result_img, caption="Swap Sonucu", use_column_width=True)
