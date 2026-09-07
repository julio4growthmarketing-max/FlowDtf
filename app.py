import streamlit as st
from rembg import remove
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io
import math
from collections import Counter

def apply_edge_choke(image, choke_pixels):
    if choke_pixels <= 0:
        return image
    alpha = image.getchannel('A')
    kernel_size = (choke_pixels * 2) + 1
    alpha = alpha.filter(ImageFilter.MinFilter(kernel_size))
    image.putalpha(alpha)
    return image

def add_white_outline(image, thickness, fill_holes=True):
    if thickness <= 0:
        return image
    
    padding = int(thickness * 3) + 10
    w, h = image.size
    new_w = w + (padding * 2)
    new_h = h + (padding * 2)
    
    new_img = Image.new("RGBA", (new_w, new_h), (0, 0, 0, 0))
    new_img.paste(image, (padding, padding))
    
    alpha = new_img.getchannel('A')
    expanded_alpha = alpha.filter(ImageFilter.GaussianBlur(thickness))
    expanded_alpha = expanded_alpha.point(lambda p: 255 if p > 2 else 0)
    
    if fill_holes:
        ImageDraw.floodfill(expanded_alpha, (0, 0), 127)
        expanded_alpha = expanded_alpha.point(lambda p: 0 if p == 127 else 255)
    
    white_bg = Image.new("RGBA", (new_w, new_h), (255, 255, 255, 255))
    white_bg.putalpha(expanded_alpha)
    white_bg.paste(new_img, (0, 0), new_img)
    
    return white_bg

def process_magic_wand(image, tolerance):
    img_rgb = image.convert("RGB")
    
    small_img = img_rgb.copy()
    small_img.thumbnail((150, 150))
    counts = Counter(small_img.getdata())
    bg_color = counts.most_common(1)[0][0] 
    
    original_data = list(image.getdata())
    rgb_data = list(img_rgb.getdata())
    newData = []
    
    for i in range(len(original_data)):
        item = rgb_data[i]
        orig = original_data[i]
        
        diff = abs(item[0] - bg_color[0]) + abs(item[1] - bg_color[1]) + abs(item[2] - bg_color[2])
        
        if diff <= tolerance:
            newData.append((orig[0], orig[1], orig[2], 0))
        else:
            newData.append((orig[0], orig[1], orig[2], 255))
            
    image.putdata(newData)
    return image

def process_image_ai(uploaded_file, target_size_cm, dpi=300, removal_mode="Só Ajustar Medidas (Rápido)", tolerance=30, choke_pixels=0, hard_edge=True, outline_thickness=0, fill_holes=True, keep_original_size=False):
    image = Image.open(uploaded_file).convert("RGBA")
    
    if removal_mode == "IA (Lento, Para Fotos)":
        image_bytes = uploaded_file.getvalue()
        mask_bytes = remove(image_bytes, only_mask=True)
        mask = Image.open(io.BytesIO(mask_bytes)).convert("L")
        
        if hard_edge:
            mask = mask.point(lambda p: 255 if p > 50 else 0)
            
        image.putalpha(mask)
        
    elif removal_mode == "Varinha Mágica (Médio, Para Logos)":
        image = process_magic_wand(image, tolerance)
    
    if removal_mode != "Só Ajustar Medidas (Rápido)":
        image = apply_edge_choke(image, choke_pixels)
    
    if outline_thickness > 0:
        image = add_white_outline(image, outline_thickness, fill_holes)
        
    # Se o usuário NÃO pediu para manter o tamanho original, nós cortamos o excesso e redimensionamos
    if not keep_original_size:
        bbox = image.getbbox()
        if bbox:
            image = image.crop(bbox)
        
        target_pixels = int((target_size_cm * dpi) / 2.54)
        width, height = image.size
        
        if width > height:
            new_width = target_pixels
            new_height = int(height * (target_pixels / width))
        else:
            new_height = target_pixels
            new_width = int(width * (target_pixels / height))
            
        image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
    return image

def create_gang_sheet(single_image, copies, roll_width_cm, dpi=300, footer_text="", spacing_x_cm=0.20, spacing_y_cm=0.20):
    roll_width_px = int((roll_width_cm * dpi) / 2.54)
    space_x_px = int((spacing_x_cm * dpi) / 2.54)
    space_y_px = int((spacing_y_cm * dpi) / 2.54)
    
    img_w, img_h = single_image.size
    cell_w = img_w + space_x_px
    cell_h = img_h + space_y_px
    
    cols = max(1, int((roll_width_px + space_x_px) // cell_w))
    rows = math.ceil(copies / cols)
    
    footer_height = 0
    if footer_text:
        footer_height = 300 
        
    canvas_width = roll_width_px
    canvas_height = (rows * cell_h) + footer_height
    
    sheet = Image.new("RGBA", (canvas_width, canvas_height), (255, 255, 255, 0))
    
    for i in range(copies):
        r = i // cols
        c = i % cols
        x = c * cell_w
        y = r * cell_h
        sheet.paste(single_image, (x, y), single_image)
        
    if footer_text:
        draw = ImageDraw.Draw(sheet)
        try:
            font = ImageFont.truetype("arial.ttf", 80)
        except:
            font = ImageFont.load_default()
            
        text_bbox = draw.textbbox((0, 0), footer_text, font=font)
        text_w = text_bbox[2] - text_bbox[0]
        text_x = (canvas_width - text_w) // 2
        text_y = (rows * cell_h) + 100
        draw.text((text_x, text_y), footer_text, fill="black", font=font)
        
    return sheet

st.set_page_config(page_title="DTF Master Prep", layout="wide")

st.title("👕 DTF Master Prep (Nesting Rápido + IA)")
st.write("Recorte impecável, contornos sólidos e montagem inteligente para o rolo da impressora DTF.")

uploaded_file = st.file_uploader("Escolha a Arte Original", type=["jpg", "jpeg", "png", "webp"])

col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Preparação da Arte")
    
    keep_original_size = st.checkbox("Manter tamanho original do arquivo (Não redimensionar nem cortar bordas)", value=False, help="Se marcado, o sistema não vai alterar em nada a sua arte (ideal se ela já estiver na medida exata no Photoshop).")
    
    if keep_original_size:
        target_size_cm = 9.5
    else:
        target_size_cm = st.number_input("Tamanho da arte (maior lado em cm):", min_value=1.0, max_value=50.0, value=9.5, step=0.5)
        
    dpi = st.number_input("DPI da Impressora (Obrigatório para converter CM em Pixels):", min_value=72, max_value=600, value=300, step=1)
    
    st.markdown("---")
    st.write("✂️ **Modo de Operação**")
    removal_mode = st.radio(
        "Ferramenta:",
        ["Só Ajustar Medidas (Rápido)", "Varinha Mágica (Médio, Para Logos)", "IA (Lento, Para Fotos)"],
        index=0,
        label_visibility="collapsed"
    )
    
    tolerance = 30
    if removal_mode == "Varinha Mágica (Médio, Para Logos)":
        st.info("Apaga a cor de fundo predominante. Aumente se sobrar restos do fundo.")
        tolerance = st.slider("Tolerância da Varinha", 0, 200, 30)

    st.markdown("---")
    st.write("✨ **Efeitos Opcionais**")
    
    outline_thickness = st.slider("Contorno Branco (Offset)", min_value=0, max_value=50, value=0, help="Cria uma borda branca arredondada ao redor da arte (ótimo para dar destaque em camisas escuras).")
    
    fill_holes = False
    if outline_thickness > 0:
        fill_holes = st.checkbox("Tapar Buracos Internos (Fundo Sólido)", value=True, help="Se marcado, preenche com branco todos os buraquinhos dentro da arte, deixando a silhueta 100% fechada.")
    
    choke_pixels = 0
    hard_edge = False
    if removal_mode != "Só Ajustar Medidas (Rápido)":
        choke_pixels = st.slider("Comer Borda (Anti-Halo)", min_value=0, max_value=10, value=0, help="Encolhe o recorte original. Ideal se não for usar contorno branco e quiser tirar rebarbas claras.")
        
        if removal_mode == "IA (Lento, Para Fotos)":
            hard_edge = st.checkbox("Corte Seco (Desativar Transparência da IA)", value=False)

with col2:
    st.subheader("2. Montagem no Rolo (Nesting)")
    multiplicar = st.checkbox("Multiplicar Arte para Impressão?", value=True)
    if multiplicar:
        roll_width_cm = st.number_input("Largura Útil do Rolo (cm):", min_value=10.0, max_value=100.0, value=28.9, step=0.1)
        copies = st.number_input("Quantidade de Cópias:", min_value=1, max_value=1000, value=20, step=1)
        
        st.markdown("---")
        st.write("✂️ **Espaçamento para a Tesoura**")
        esp_col1, esp_col2 = st.columns(2)
        with esp_col1:
            spacing_x = st.number_input("↔️ Horizontal (cm)", min_value=0.0, value=0.20, step=0.05)
        with esp_col2:
            spacing_y = st.number_input("↕️ Vertical (cm)", min_value=0.0, value=0.20, step=0.05)
        st.markdown("---")
        
        footer_text = st.text_input("📝 Nome do Pedido / Cliente (Rodapé):", value="")

if uploaded_file is not None:
    if st.button("✨ Gerar Arquivo Final DTF", type="primary", use_container_width=True):
        with st.spinner("Processando..."):
            try:
                base_image = process_image_ai(uploaded_file, target_size_cm, dpi, removal_mode, tolerance, choke_pixels, hard_edge, outline_thickness, fill_holes, keep_original_size)
                
                if multiplicar:
                    final_image = create_gang_sheet(base_image, copies, roll_width_cm, dpi, footer_text, spacing_x, spacing_y)
                    st.success(f"Matriz montada com espaçamento de {spacing_x}cm ↔️ e {spacing_y}cm ↕️!")
                else:
                    final_image = base_image
                    st.success(f"Arte processada pronta para uso!")
                
                st.image(final_image, caption="Pré-visualização do Arquivo Final", use_container_width=True)
                
                buf = io.BytesIO()
                final_image.save(buf, format="PNG")
                byte_im = buf.getvalue()
                
                file_name = f"Pedido_{footer_text.strip()}_{copies}x_{target_size_cm}cm.png" if footer_text else "arquivo_dtf.png"
                
                st.download_button(
                    label=f"⬇️ Baixar Arquivo de Impressão",
                    data=byte_im,
                    file_name=file_name,
                    mime="image/png",
                    type="primary"
                )
            except Exception as e:
                st.error(f"Erro no processamento: {e}")
