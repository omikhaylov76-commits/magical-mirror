import streamlit as st
import requests
import base64
import json
import re
import time
import io
from PIL import Image

# 1. Настройка страницы (Wide mode для планшетов)
st.set_page_config(
    page_title="Magical Mirror", 
    page_icon="🎀", 
    layout="centered"
)

# 2. Получение ключа из secrets.toml (Ваш ключ №3)
apiKey = st.secrets.get("GOOGLE_API_KEY", "")

# Инициализация сессии
if 'generated_img' not in st.session_state:
    st.session_state.generated_img = None

# 3. ДИЗАЙН (Glassmorphism + Адаптивность)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Dancing+Script:wght@700&family=Nunito:wght@600;800;900&display=swap');

    #MainMenu, footer, header {visibility: hidden;}
    
    .stApp {
        background: radial-gradient(circle at top, #ffe6eb 0%, #fad0c4 40%, #fbc2eb 100%);
        font-family: 'Nunito', sans-serif;
    }

    .magical-title {
        font-family: 'Dancing Script', cursive;
        font-size: 80px;
        text-align: center;
        color: #ff4781;
        text-shadow: 4px 4px 0px #ffffff, 0px 0px 25px rgba(255, 71, 129, 0.7);
        margin-bottom: 20px;
        line-height: 1.1;
    }

    [data-testid="stImage"] img {
        border-radius: 30px !important;
        border: 5px solid rgba(255, 255, 255, 0.9) !important;
        box-shadow: 0 15px 35px rgba(255, 71, 129, 0.3) !important;
    }

    div[data-baseweb="select"] > div {
        background: rgba(255, 255, 255, 0.8) !important;
        border-radius: 20px !important;
        border: 2px solid #fff !important;
        color: #d14d72 !important;
        font-weight: 800 !important;
        height: 60px !important;
    }
    
    div[role="radiogroup"] {
        display: flex !important;
        flex-direction: row !important;
        gap: 10px !important;
        background: rgba(255, 255, 255, 0.3);
        padding: 10px;
        border-radius: 25px;
        border: 2px solid rgba(255,255,255,0.7);
    }

    div[role="radiogroup"] > label {
        flex: 1 !important; 
        background: rgba(255, 255, 255, 0.7) !important;
        border-radius: 20px !important;
        padding: 15px 5px !important;
        cursor: pointer;
        display: flex !important;
        justify-content: center !important;
        position: relative;
    }

    div[role="radiogroup"] label > div:first-child {
        position: absolute !important;
        opacity: 0 !important;
        width: 0 !important;
    }

    div[role="radiogroup"] > label:has(input:checked) {
        background: radial-gradient(circle at 50% 50%, #ff85a1 0%, #ff4b8b 100%) !important;
        box-shadow: 0 8px 20px rgba(255, 75, 139, 0.5) !important;
        border: 2px solid #fff !important;
        transform: scale(1.02);
    }

    div[role="radiogroup"] p {
        font-weight: 900 !important;
        font-size: 20px !important;
        color: #d14d72 !important;
        margin: 0 !important;
    }
    div[role="radiogroup"] > label:has(input:checked) p {
        color: #fff !important;
    }

    .stButton button, [data-testid="stDownloadButton"] button {
        background: radial-gradient(circle at 30% 30%, #ff85a1 0%, #ff4b8b 100%) !important;
        border-radius: 40px !important;
        border: 4px solid #fff !important;
        box-shadow: 0 12px 25px rgba(255, 75, 139, 0.5) !important;
        color: white !important;
        font-size: 24px !important;
        font-weight: 900 !important;
        padding: 20px 30px !important; 
        width: 100% !important;
        margin-top: 15px !important;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="magical-title">Magical Mirror</div>', unsafe_allow_html=True)

# 4. ФУНКЦИИ ОБРАБОТКИ
def process_image_for_api(image_bytes):
    """Сжимает тяжелые фото для стабильной работы API."""
    img = Image.open(io.BytesIO(image_bytes))
    if max(img.size) > 1600:
        img.thumbnail((1600, 1600))
    output = io.BytesIO()
    img.convert('RGB').save(output, format='JPEG', quality=85)
    return output.getvalue()

def make_request_with_retry(url, payload):
    for i in range(5):
        try:
            response = requests.post(url, json=payload, timeout=60)
            if response.status_code == 200:
                return response.json(), None
            else:
                return None, f"Status {response.status_code}: {response.text}"
        except Exception as e:
            if i == 4: return None, str(e)
        time.sleep(2**i)
    return None, "Timeout"

def analyze_likeness_structured(image_bytes, char, act):
    # Предварительная обработка (сжатие)
    compressed_bytes = process_image_for_api(image_bytes)
    base64_image = base64.b64encode(compressed_bytes).decode('utf-8')
    
    prompt = (
        f"Act as a forensic Pixar-style animator. Analyze the photo for a scene: {act} with {char}.\n"
        "Identify EXACT headcount. For each person, return a JSON array of objects with:\n"
        "- id: integer (1..N)\n"
        "- gender: 'male'/'female'/'unknown'\n"
        "- age_group: 'toddler'/'child'/'preteen'/'adult'\n"
        "- face_shape: e.g. 'round', 'oval', 'heart'\n"
        "- expression_label: one of ['gentle_smile', 'big_smile', 'laughing', 'neutral', 'surprised', 'silly_face_with_tongue']\n"
        "- expression_description: factual description\n"
        "- emotion: 'happy', 'curious', 'playful'\n"
        "- hair: {{'color': '...', 'style': '...', 'bangs': '...'}}\n"
        "- eyewear: '...' or 'no eyewear'\n"
        "- outfit_colors: list of strings\n"
        "- accessories: list of strings\n\n"
        "Output ONLY valid JSON array. No extra text."
    )
    
    # ИСПРАВЛЕНО: Используем стабильное имя модели gemini-2.5-flash
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={apiKey}"
    payload = {
        "contents": [{"parts": [{"text": prompt}, {"inlineData": {"mimeType": "image/jpeg", "data": base64_image}}]}],
        "generationConfig": {"responseMimeType": "application/json"}
    }
    
    result, error = make_request_with_retry(url, payload)
    if result:
        return result['candidates'][0]['content']['parts'][0]['text'], None
    return None, error

def call_google_generate(prompt):
    # Используем Gemini 3.1 для генерации изображения (как в рабочей версии)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image-preview:generateContent?key={apiKey}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}], 
        "generationConfig": {"responseModalities": ["IMAGE"], "candidateCount": 1}
    }
    
    result, error = make_request_with_retry(url, payload)
    if result:
        try:
            parts = result['candidates'][0]['content']['parts']
            for p in parts:
                if 'inlineData' in p:
                    return base64.b64decode(p['inlineData']['data']), None
        except: pass
    return None, error

# 5. ИНТЕРФЕЙС
col1, col2, col3 = st.columns(3)
with col1: char = st.selectbox("Друг", ["Hello Kitty", "Kuromi", "My Melody", "Cinnamoroll", "Pompompurin"])
with col2: loc = st.selectbox("Место", ["Розовый замок", "Кафе сладостей", "Сказочный лес", "Радужное облако"])
with col3: act = st.selectbox("Сюжет", ["Чаепитие", "Танцы", "Обнимашки", "Концерт"])

st.markdown("<br>", unsafe_allow_html=True)
source = st.radio("✨ Выбери свою фотографию ✨", ["📸 СЕЛФИ", "🖼️ ГАЛЕРЕЯ"], horizontal=True)

input_data = None
if source == "📸 СЕЛФИ":
    captured = st.camera_input("")
    if captured: input_data = captured.getvalue()
else:
    uploaded = st.file_uploader("", type=['jpg', 'png', 'jpeg'])
    if uploaded: input_data = uploaded.getvalue()

if input_data:
    st.image(input_data, use_container_width=True)
    
    if st.button("✨ CREATE MAGIC ✨"):
        with st.status("🪄 Творим волшебство...", expanded=True) as status:
            st.write("👀 Анализируем детали...")
            json_response, err_msg = analyze_likeness_structured(input_data, char, act)
            
            if json_response:
                try:
                    clean_json = re.sub(r'```json\n|\n```', '', json_response).strip()
                    people_data = json.loads(clean_json)
                    if isinstance(people_data, dict): people_data = [people_data]
                    p_count = len(people_data)
                    
                    st.write(f"🎨 Рисуем мир (Gemini 3.1) для {p_count} героев...")
                    
                    final_prompt = (
                        f"Create a joyful, Pixar-inspired 3D animation still.\n"
                        f"Scene: {loc}, Action: {act} with {char}.\n"
                        f"EXACTLY {p_count} humans from the photo transformed into recognizable 3D cartoon characters.\n"
                        f"Style: warm, friendly, rounded 3D cartoon style. Lighting: warm cinematic glow.\n"
                        f"Resolution: 2K (2560x1440).\n"
                        f"Interaction: {char} must be interacting with these people.\n"
                        f"Use this visual analysis for likeness and expressions:\n{clean_json}"
                    )
                    
                    img_bytes, gen_err = call_google_generate(final_prompt)
                    
                    if img_bytes:
                        st.session_state.generated_img = img_bytes
                        status.update(label="✨ Волшебство готово!", state="complete", expanded=False)
                        st.balloons()
                    else: st.error(f"Ошибка генерации: {gen_err}")
                except Exception as e: st.error(f"Ошибка обработки данных: {e}")
            else: st.error(f"Ошибка анализа: {err_msg}. Проверьте фото или ключ.")

if st.session_state.generated_img:
    st.success("🎉 Готово! Твой шедевр!")
    st.image(st.session_state.generated_img, use_container_width=True)
    st.download_button("💾 СОХРАНИТЬ КАРТИНКУ", st.session_state.generated_img, "magic_mirror.jpg", "image/jpeg")

st.markdown("<br>", unsafe_allow_html=True)
if st.button("🔄 Начать заново"):
    st.session_state.generated_img = None
    st.rerun()
