import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import numpy as np
import cv2

# Yardımcı fonksiyon: Eğer kullanıcı 3 nokta seçerse, 4. köşeyi hesaplar.
def compute_fourth_point(points):
    # Basit bir varsayım: 4. köşe = p0 + p2 - p1
    p0, p1, p2 = points
    return [p0[0] + p2[0] - p1[0], p0[1] + p2[1] - p1[1]]

# Uygulama Başlığı
st.title("Dekorasyon Uygulaması")
st.write("Bu uygulama, yüzey resminiz üzerinde seçtiğiniz alana dekoratif doku uygulamanızı sağlar.")

# Adım 1: Dekore edilecek yüzey resmini yükleme
st.header("Adım 1: Yüzey Resmini Yükleyin")
uploaded_surface = st.file_uploader("Dekore edeceğiniz yüzeyin resmini yükleyin (jpg, jpeg, png)", type=["jpg", "jpeg", "png"])
if uploaded_surface:
    base_image = Image.open(uploaded_surface).convert("RGB")
    st.image(base_image, caption="Yüklenen Yüzey Resmi", use_column_width=True)
    
    # Adım 2: Dekor edilecek alanı seçme (çokgen çizimi)
    st.header("Adım 2: Dekorasyon Alanını Belirleyin")
    st.write("Resim üzerinde alan belirlemek için fare ile çokgen çiziniz (min. 3 nokta, ideal olarak 4 nokta).")
    
    # streamlit-drawable-canvas ile interaktif çizim alanı
    canvas_result = st_canvas(
        fill_color="rgba(255,165,0,0.3)",  # Yarı saydam dolgu rengi
        stroke_width=2,
        stroke_color="#FF0000",
        background_color="#eee",
        background_image=base_image,
        height=base_image.height,
        width=base_image.width,
        drawing_mode="polygon",
        key="canvas",
    )
    
    # Kullanıcının çizdiği verileri al
    if canvas_result.json_data is not None:
        objects = canvas_result.json_data.get("objects", [])
        if objects:
            # İlk çizilen nesneyi (çokgen) alıyoruz
            poly = objects[0]
            coords = []
            # Her çizim komutundan (M: Başlangıç, L: Çizgi) koordinatları çıkartıyoruz
            for item in poly["path"]:
                if item[0] in ["M", "L"]:
                    coords.append([item[1], item[2]])
            if len(coords) < 3:
                st.error("Lütfen en az 3 nokta seçin!")
            else:
                st.write("Seçtiğiniz Noktalar:", coords)
                # Eğer kullanıcı 3 nokta seçmişse, otomatik 4. noktayı ekle
                if len(coords) == 3:
                    fourth = compute_fourth_point(coords)
                    coords.append(fourth)
                    st.write("Otomatik eklenen 4. nokta:", fourth)
                # Eğer 4’ten fazla nokta çizildiyse, ilk 4 nokta kullanılıyor.
                if len(coords) > 4:
                    coords = coords[:4]
                    st.write("İlk 4 nokta kullanıldı:", coords)
                
                # Adım 3: Dekoratif doku (texture) resmini yükleme
                st.header("Adım 3: Dekoratif Doku Yükleyin")
                uploaded_texture = st.file_uploader("Dekoratif doku resmini yükleyin (jpg, jpeg, png)", type=["jpg", "jpeg", "png"], key="texture")
                if uploaded_texture:
                    texture_image = Image.open(uploaded_texture).convert("RGB")
                    st.image(texture_image, caption="Yüklenen Dekoratif Doku", use_column_width=True)
                    
                    # Adım 4: Boyut bilgilerini girin
                    st.header("Adım 4: Boyut Bilgilerini Girin")
                    st.write("Lütfen dekorasyon alanının yaklaşık uzunluk ve genişlik değerlerini ve dekoratif materyalin boyutunu girin. (Örneğin; cm veya m cinsinden, aynı birimde)")
                    area_length = st.number_input("Dekorasyon Alanı Uzunluğu", min_value=1.0, value=100.0)
                    area_width = st.number_input("Dekorasyon Alanı Genişliği", min_value=1.0, value=100.0)
                    deco_width = st.number_input("Dekoratif Materyal Genişliği", min_value=1.0, value=10.0)
                    deco_height = st.number_input("Dekoratif Materyal Yüksekliği", min_value=1.0, value=10.0)
                    
                    # Not: Girilen fiziksel boyutlar, ölçeklendirme ve tekrarlama (tiling) hesaplamalarında ileride kullanılabilir.
                    # Bu örnekte, basitçe dekoratif dokunun seçili alana perspektif dönüşümü uygulanarak "yerleştirilmesi" sağlanacaktır.
                    
                    # Adım 5: Dekorasyonu uygula
                    if st.button("Dekorasyonu Uygula"):
                        # Görüntüleri OpenCV ile işleyebilmek için numpy dizisine çeviriyoruz.
                        base_np = np.array(base_image)
                        texture_np = np.array(texture_image)
                        
                        # Seçilen 4 nokta (hedef çokgen) için numpy dizisine çevirme
                        dst_pts = np.array(coords, dtype="float32")
                        
                        # Kaynak nokta seti: dekoratif doku resminin köşeleri
                        h_tex, w_tex = texture_np.shape[:2]
                        src_pts = np.array([[0, 0],
                                            [w_tex, 0],
                                            [w_tex, h_tex],
                                            [0, h_tex]], dtype="float32")
                        
                        # Perspektif dönüşüm matrisini hesapla
                        M = cv2.getPerspectiveTransform(src_pts, dst_pts)
                        
                        # Temel resmi boyutlarında bir sonuç resmi oluşturabilmek için dönüşümü uyguluyoruz.
                        warped_texture = cv2.warpPerspective(texture_np, M, (base_np.shape[1], base_np.shape[0]))
                        
                        # Maske oluşturma: Dönüştürülmüş dekoratif dokunun var olduğu alanı belirlemek için
                        gray_warp = cv2.cvtColor(warped_texture, cv2.COLOR_BGR2GRAY)
                        _, mask = cv2.threshold(gray_warp, 1, 255, cv2.THRESH_BINARY)
                        mask_inv = cv2.bitwise_not(mask)
                        
                        # Temel resmin, dekoratif dokunun uygulanacağı alanı temizle
                        base_bg = cv2.bitwise_and(base_np, base_np, mask=mask_inv)
                        # Dönüştürülmüş dekoratif doku bölgesini al
                        deco_fg = cv2.bitwise_and(warped_texture, warped_texture, mask=mask)
                        
                        # İki resmi birleştir
                        result = cv2.add(base_bg, deco_fg)
                        
                        # Sonucu PIL Image formatına dönüştürüp göster
                        result_image = Image.fromarray(result)
                        st.image(result_image, caption="Dekore Edilmiş Yüzey", use_column_width=True)
                        
                        # Adım 6: İndir veya yeni alan ekleme seçeneği sunma
                        st.header("Adım 6: İndir / Devamlı Düzenleme")
                        # Uygulama, mevcut dekore edilmiş resim üzerinden ek alanlar seçip dekorasyon değişikliği yapılmasına imkan verecek şekilde geliştirilebilir.
                        st.download_button("Dekore Edilmiş Resmi İndir", data=result_image.tobytes(), file_name="decorated.png", mime="image/png")
                        
                        st.success("Dekorasyon uygulandı. Yeni alan ekleyebilir veya mevcut dekorasyonu değiştirebilirsiniz.")
