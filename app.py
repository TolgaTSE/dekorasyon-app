import streamlit as st
from streamlit_drawable_canvas import st_canvas, st_image
from PIL import Image
import numpy as np
import cv2
import base64
from io import BytesIO

# Yardımcı fonksiyon: PIL image'i base64 veri URL'sine dönüştürür.
def pil_image_to_data_url(image):
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
    return f"data:image/png;base64,{img_str}"

# Custom _resize_img: Eğer img bir PIL.Image ise istenen boyuta yeniden boyutlandırır,
# değilse, olduğu gibi geri döner.
def custom_resize_img(img, new_height, new_width):
    if isinstance(img, Image.Image):
         return img.resize((int(new_width), int(new_height)))
    return img

# Custom image_to_url: _resize_img ile boyutlandırılmış resmi base64 URL'sine çevirir.
def custom_image_to_url(img, height, width):
    resized = custom_resize_img(img, height, width)
    if isinstance(resized, Image.Image):
         return pil_image_to_data_url(resized)
    return resized

# Monkey patch: st_image modülündeki fonksiyonları güncelliyoruz.
st_image._resize_img = custom_resize_img
st_image.image_to_url = custom_image_to_url


# Bu satır ile st_image.image_to_url artık bizim tanımladığımız fonksiyonu gösterecek.
st_image.image_to_url = image_to_url

# Uygulama Başlığı
st.title("Dekorasyon Uygulaması")
st.write("Bu uygulama, yüzey resminiz üzerinde seçtiğiniz alana dekoratif doku uygulamanızı sağlar.")

# Adım 1: Yüzey resmini yükleme
st.header("Adım 1: Yüzey Resmini Yükleyin")
uploaded_surface = st.file_uploader("Dekore edeceğiniz yüzeyin resmini yükleyin (jpg, jpeg, png)", type=["jpg", "jpeg", "png"])

if uploaded_surface:
    base_image = Image.open(uploaded_surface).convert("RGB")
    st.image(base_image, caption="Yüklenen Yüzey Resmi", use_column_width=True)
    
    # Adım 2: Dekorasyon alanını seçme (çizim)
    st.header("Adım 2: Dekorasyon Alanını Belirleyin")
    st.write("Resim üzerinde alan belirlemek için fare ile çokgen çizin (min. 3 nokta, ideal olarak 4 nokta).")
    
    canvas_result = st_canvas(
        fill_color="rgba(255,165,0,0.3)",
        stroke_width=2,
        stroke_color="#FF0000",
        background_color="#eee",
        background_image=base_image,  # PIL.Image nesnesini veriyoruz.
        height=base_image.height,
        width=base_image.width,
        drawing_mode="polygon",
        key="canvas",
    )
    
    # (Devamında çizim verilerini işleme ve sonraki adımlar...)

    
    # Çizim verilerini işleme:
    if canvas_result.json_data is not None:
        objects = canvas_result.json_data.get("objects", [])
        if objects:
            # İlk çizilen çokgeni alıyoruz
            poly = objects[0]
            coords = []
            # Çizim yolundaki komutlardan (M: başlat, L: çizgi) koordinatları çıkarıyoruz.
            for item in poly["path"]:
                if item[0] in ["M", "L"]:
                    coords.append([item[1], item[2]])
            if len(coords) < 3:
                st.error("Lütfen en az 3 nokta seçin!")
            else:
                st.write("Seçtiğiniz Noktalar:", coords)
                # Eğer 3 nokta seçildiyse, otomatik 4. noktayı hesaplayın
                if len(coords) == 3:
                    def compute_fourth_point(points):
                        p0, p1, p2 = points
                        return [p0[0] + p2[0] - p1[0], p0[1] + p2[1] - p1[1]]
                    fourth = compute_fourth_point(coords)
                    coords.append(fourth)
                    st.write("Otomatik eklenen 4. nokta:", fourth)
                if len(coords) > 4:
                    coords = coords[:4]
                    st.write("İlk 4 nokta kullanıldı:", coords)
                    
                # Devam eden adımlar: Dekoratif doku yükleme, boyut girişi ve dekorasyonun uygulanması...
                st.header("Adım 3: Dekoratif Doku Yükleyin")
                uploaded_texture = st.file_uploader("Dekoratif doku resmini yükleyin (jpg, jpeg, png)", type=["jpg", "jpeg", "png"], key="texture")
                if uploaded_texture:
                    texture_image = Image.open(uploaded_texture).convert("RGB")
                    st.image(texture_image, caption="Yüklenen Dekoratif Doku", use_column_width=True)
                    
                    st.header("Adım 4: Boyut Bilgilerini Girin")
                    st.write("Lütfen dekorasyon alanının yaklaşık uzunluk ve genişlik değerlerini ve dekoratif materyalin boyutunu girin. (Örneğin; cm veya m cinsinden, aynı birimde)")
                    area_length = st.number_input("Dekorasyon Alanı Uzunluğu", min_value=1.0, value=100.0)
                    area_width = st.number_input("Dekorasyon Alanı Genişliği", min_value=1.0, value=100.0)
                    deco_width = st.number_input("Dekoratif Materyal Genişliği", min_value=1.0, value=10.0)
                    deco_height = st.number_input("Dekoratif Materyal Yüksekliği", min_value=1.0, value=10.0)
                    
                    if st.button("Dekorasyonu Uygula"):
                        base_np = np.array(base_image)
                        texture_np = np.array(texture_image)
                        dst_pts = np.array(coords, dtype="float32")
                        h_tex, w_tex = texture_np.shape[:2]
                        src_pts = np.array([[0, 0],
                                            [w_tex, 0],
                                            [w_tex, h_tex],
                                            [0, h_tex]], dtype="float32")
                        
                        M = cv2.getPerspectiveTransform(src_pts, dst_pts)
                        warped_texture = cv2.warpPerspective(texture_np, M, (base_np.shape[1], base_np.shape[0]))
                        gray_warp = cv2.cvtColor(warped_texture, cv2.COLOR_BGR2GRAY)
                        _, mask = cv2.threshold(gray_warp, 1, 255, cv2.THRESH_BINARY)
                        mask_inv = cv2.bitwise_not(mask)
                        base_bg = cv2.bitwise_and(base_np, base_np, mask=mask_inv)
                        deco_fg = cv2.bitwise_and(warped_texture, warped_texture, mask=mask)
                        result = cv2.add(base_bg, deco_fg)
                        result_image = Image.fromarray(result)
                        st.image(result_image, caption="Dekore Edilmiş Yüzey", use_column_width=True)
                        st.header("Adım 6: İndir / Devamlı Düzenleme")
                        st.download_button("Dekore Edilmiş Resmi İndir", data=result_image.tobytes(), file_name="decorated.png", mime="image/png")
                        st.success("Dekorasyon uygulandı. Yeni alan ekleyebilir veya mevcut dekorasyonu değiştirebilirsiniz.")
