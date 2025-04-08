import streamlit as st
from PIL import Image
import numpy as np
import cv2
import base64
from io import BytesIO

##############################################
# Monkey-Patch: st_image Fonksiyonlarını Yeniden Tanımlama
##############################################

# Yardımcı fonksiyon: PIL.Image'i base64 veri URL'sine dönüştürür.
def pil_image_to_data_url(image):
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{img_str}"

# Eğer gelen nesne bir PIL.Image ise, istenen boyuta yeniden boyutlandırır; değilse olduğu gibi döndürür.
def custom_resize_img(img, new_height, new_width):
    if isinstance(img, Image.Image):
        return img.resize((int(new_width), int(new_height)))
    return img

# _resize_img ile boyutlandırılmış görüntüyü base64 URL'sine dönüştürür.
def custom_image_to_url(img, height, width):
    resized = custom_resize_img(img, height, width)
    if isinstance(resized, Image.Image):
        return pil_image_to_data_url(resized)
    return resized

# Önce st_image ve st_canvas'yı import ediyoruz, ardından st_image üzerinden monkey-patch işlemi yapıyoruz.
from streamlit_drawable_canvas import st_image, st_canvas
st_image._resize_img = custom_resize_img
st_image.image_to_url = custom_image_to_url

##############################################
# Uygulama Başlangıcı
##############################################

st.title("Dekorasyon Uygulaması")
st.write("Bu uygulama, yüklediğiniz yüzey resmi üzerinde seçtiğiniz alana dekoratif doku yerleştirmenizi sağlar.")

##############################################
# Adım 1: Yüzey Resmini Yükleme
##############################################
st.header("Adım 1: Yüzey Resmini Yükleyin")
uploaded_surface = st.file_uploader("Dekore edeceğiniz yüzeyin resmini yükleyin (jpg, jpeg, png)", type=["jpg", "jpeg", "png"])

if uploaded_surface:
    base_image = Image.open(uploaded_surface).convert("RGB")
    st.image(base_image, caption="Yüklenen Yüzey Resmi", use_column_width=True)
    
    ##############################################
    # Adım 2: Dekorasyon Alanını Belirleyin (Çizim)
    ##############################################
    st.header("Adım 2: Dekorasyon Alanını Belirleyin")
    st.write("Resim üzerinde alan belirlemek için fare ile çokgen çizin (en az 3 nokta, ideal olarak 4 nokta).")
    
    # Arka plan resmi olarak doğrudan PIL.Image nesnesini gönderiyoruz.
    canvas_result = st_canvas(
        fill_color="rgba(255,165,0,0.3)",   # Yarı saydam dolgu rengi
        stroke_width=2,
        stroke_color="#FF0000",
        background_color="#eee",
        background_image=base_image,
        height=base_image.height,
        width=base_image.width,
        drawing_mode="polygon",
        key="canvas"
    )
    
    # Çizim verilerini işleme
    if canvas_result.json_data is not None:
        objects = canvas_result.json_data.get("objects", [])
        if objects:
            poly = objects[0]  # İlk çizilen çokgeni alıyoruz.
            coords = []
            # Çokgen çiziminde "M" (başlat) ve "L" (çizgi) komutlarından koordinatları alıyoruz.
            for item in poly["path"]:
                if item[0] in ["M", "L"]:
                    coords.append([item[1], item[2]])
            if len(coords) < 3:
                st.error("Lütfen en az 3 nokta seçin!")
            else:
                st.write("Seçtiğiniz Noktalar:", coords)
                # Eğer tam olarak 3 nokta seçildiyse
