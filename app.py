import streamlit as st
import requests
import io
import base64
import re
import json
import time
from PIL import Image
import streamlit.components.v1 as components

# 1. Настройка страницы
st.set_page_config(
    page_title="Magical Mirror Pro", 
    page_icon="🎀", 
    layout="centered"
)

# 2. Получение ключа из secrets
apiKey = st.secrets.get("GOOGLE_API_KEY", "")

# Инициализация состояния
if 'generated_img' not in st.session_state:
    st.session_state.generated_img = None

# Настройки безопасности (ОБЯЗАТЕЛЬНО для карикатур и анализа)
SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
]

# 3. Дизайн «Магического Зеркала»
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

# 4. Функции обработки

def process_image(image_bytes):
    img = Image.open(io.BytesIO(image_bytes))
    if max(img.size) > 1600:
        img.thumbnail((1600, 1600))
    output = io.BytesIO()
    img.convert('RGB').save(output, format='JPEG', quality=85)
    return output.getvalue()

def make_request_with_retry(url, payload):
    for i in range(5):
        try:
            response = requests.post(url, json=payload, timeout=90)
            if response.status_code == 200:
                return response.json(), None
            elif response.status_code in [429, 500, 503]:
                time.sleep(2**i)
                continue
            return None, f"Status {response.status_code}: {response.text}"
        except Exception as e:
            if i == 4: return None, str(e)
        time.sleep(2**i)
    return None, "Error"

def analyze_likeness_structured(image_bytes, char, act):
    """Этап 1: Экспертный антропологический анализ (JSON)."""
    compressed = process_image(image_bytes)
    base64_image = base64.b64encode(compressed).decode('utf-8')
    
    prompt = (
        f"Act as an expert forensic anthropologist and world-class character designer. Analyze the provided image with microscopic precision within the context of the scene: {act} with {char}. "
        "Identify the EXACT number of people. For each person, return a JSON array of objects with this structure: demographics, anatomy_and_build, head_and_face_geometry, skin_texture_and_complexion, facial_features_detailed, hair_and_styling, external_factors. "
        "Output ONLY a valid JSON array. Do NOT include any extra text. Start with [ and end with ]."
    )
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image-preview:generateContent?key={apiKey}"
    payload = {
        "contents": [{"parts": [{"text": prompt}, {"inlineData": {"mimeType": "image/jpeg", "data": base64_image}}]}],
        "generationConfig": {"responseMimeType": "application/json"},
        "safetySettings": SAFETY_SETTINGS
    }
    
    res, err = make_request_with_retry(url, payload)
    if res:
        try:
            return res['candidates'][0]['content']['parts'][0]['text'], None
        except: return None, "Ошибка анализа фото"
    return None, err

def generate_image(prompt):
    """Этап 2: Творческая генерация (Hands)."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image-preview:generateContent?key={apiKey}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}], 
        "generationConfig": {"responseModalities": ["IMAGE"], "candidateCount": 1},
        "safetySettings": SAFETY_SETTINGS
    }
    
    res, err = make_request_with_retry(url, payload)
    if res:
        try:
            candidate = res['candidates'][0]
            if candidate.get('finishReason') == 'SAFETY':
                return None, "Заблокировано фильтром безопасности."
            parts = candidate.get('content', {}).get('parts', [])
            for p in parts:
                if 'inlineData' in p:
                    return base64.b64decode(p['inlineData']['data']), None
            return None, "ИИ не прислал изображение."
        except: return None, "Ошибка отрисовки"
    return None, err

# 5. Интерфейс

col1, col2, col3 = st.columns(3)
with col1: char = st.selectbox("Друг:", ["Hello Kitty", "Kuromi", "My Melody", "Cinnamoroll", "Pompompurin", "Keroppi", "Badtz-Maru"])
with col2: loc = st.selectbox("Место:", ["Розовый замок", "Кафе сладостей", "Сказочный лес", "Радужное облако", "Неоновый Токио"])
with col3: act = st.selectbox("Сюжет:", ["Чаепитие", "Танцы", "Обнимашки", "Концерт", "Пикник на траве"])

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
            json_res, err = analyze_likeness_structured(input_data, char, act)
            
            if json_res:
                try:
                    # Очистка JSON
                    start_idx = json_res.find('[')
                    end_idx = json_res.rfind(']')
                    clean_json = json_res[start_idx:end_idx+1] if (start_idx != -1 and end_idx != -1) else json_res
                    
                    people_data = json.loads(clean_json)
                    if isinstance(people_data, dict): people_data = [people_data]
                    p_count = len(people_data)
                    
                    st.write(f"🎨 Мастер-промптинг...")
                    
                    # МАСТЕР-ПРОМПТ ДЛЯ ГОРИЗОНТАЛЬНОЙ ГЕНЕРАЦИИ (1280x720)
                    final_prompt = (
                        f"Act as a master AI Prompt Engineer and Lead Caricature Artist for a top-tier 3D animation studio. "
                        f"Translate the clinical JSON profile of real people into a highly descriptive, continuous English paragraph.\n\n"
                        f"Target Canvas: Horizontal landscape orientation (1280x720).\n"
                        f"Target Style: High-end 3D animated Pixar/Disney style caricature. Bright, vivid, magical, volumetric lighting.\n\n"
                        f"Scene Context: {act} with {char} in {loc}.\n"
                        f"Instructions:\n"
                        f"1. Playful Twist: Exaggerate 1-2 distinctive features of each person from JSON by 150% (round faces comically round, lanky limbs noodle-like). "
                        f"2. Micro-Details: Include skin texture, freckles, facial hair, and exact outfit colors from JSON.\n"
                        f"3. Cinematography: Warm rim light, rich volumetric atmosphere, dynamic horizontal 16:9 composition.\n\n"
                        f"JSON DATA:\n{clean_json}"
                    )
                    
                    img_bytes, g_err = generate_image(final_prompt)
                    if img_bytes:
                        st.session_state.generated_img = img_bytes
                        status.update(label="✨ Готово!", state="complete", expanded=False)
                        st.balloons()
                    else: st.error(f"Ошибка: {g_err}")
                except Exception as e: st.error(f"Ошибка данных: {e}")
            else: st.error(f"Ошибка анализа: {err}")

if st.session_state.generated_img:
    st.image(st.session_state.generated_img, use_container_width=True)
    st.download_button("💾 СОХРАНИТЬ КАРТИНКУ", st.session_state.generated_img, "magic_mirror.jpg", "image/jpeg")

st.markdown("<br>", unsafe_allow_html=True)
if st.button("🔄 Начать заново"):
    st.session_state.generated_img = None
    st.rerun()

# Блокировка клавиатуры
components.html("""
<script>
const doc = window.parent.document;
const fix = () => {
    doc.querySelectorAll('div[data-baseweb="select"] input').forEach(i => {
        i.setAttribute('inputmode', 'none');
        i.setAttribute('readonly', 'true');
    });
};
fix();
new MutationObserver(fix).observe(doc.body, {childList: true, subtree: true});
</script>
""", height=0, width=0)
