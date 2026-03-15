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

# 2. Получение ключа
apiKey = st.secrets.get("GOOGLE_API_KEY", "")

# Инициализация состояния сессии
if 'generated_img' not in st.session_state:
    st.session_state.generated_img = None

# Настройки безопасности (КРИТИЧЕСКИ ВАЖНО для карикатур)
SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
]

# 3. Дизайн (CSS)
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
            response = requests.post(url, json=payload, timeout=95)
            if response.status_code == 200:
                return response.json(), None
            elif response.status_code in [429, 500, 503]:
                time.sleep(2**i)
                continue
            return None, f"Ошибка {response.status_code}: {response.text[:100]}"
        except Exception as e:
            if i == 4: return None, str(e)
        time.sleep(2**i)
    return None, "Ошибка связи"

def analyze_image_expert(image_bytes, char, act):
    """Этап 1: Экспертный антропологический анализ."""
    compressed = process_image(image_bytes)
    base64_image = base64.b64encode(compressed).decode('utf-8')
    
    prompt = (
        f"Act as an expert forensic anthropologist and world-class character designer. "
        f"Analyze the image for scene: {act} with {char}. Identify EXACT number of people. "
        "Return ONLY a JSON array of objects with fields: demographics, anatomy_and_build, head_and_face_geometry, "
        "skin_texture_and_complexion, facial_features_detailed, hair_and_styling, external_factors."
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
        except: return None, "ИИ заблокировал анализ (фильтр безопасности)"
    return None, err

def generate_pixar_art(prompt):
    """Этап 2: Творческая генерация (Руки)."""
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
                return None, "Генерация заблокирована фильтром безопасности Google"
            
            parts = candidate.get('content', {}).get('parts', [])
            for p in parts:
                if 'inlineData' in p:
                    return base64.b64decode(p['inlineData']['data']), None
            return None, "ИИ не прислал изображение. Попробуйте другой сюжет."
        except: return None, "Ошибка обработки изображения"
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
            st.write("🔬 Анализируем...")
            json_res, err = analyze_image_expert(input_data, char, act)
            
            if json_res:
                try:
                    # Чистим JSON от лишнего текста
                    start = json_res.find('[')
                    end = json_res.rfind(']')
                    clean_json = json_res[start:end+1] if (start != -1 and end != -1) else json_res
                    
                    people_data = json.loads(clean_json)
                    if isinstance(people_data, dict): people_data = [people_data]
                    p_count = len(people_data)
                    
                    st.write(f"🎨 Рисуем мир для {p_count} героев...")
                    
                    final_prompt = (
                        f"Act as a master AI Prompt Engineer and Lead Caricature Artist. Translate the JSON data into a continuous English paragraph.\n"
                        f"Target Canvas: Horizontal landscape orientation (1280x720, aspect ratio 16:9).\n"
                        f"Target Style: High-end 3D animated Pixar/Disney style caricature. Bright, vivid, magical, volumetric lighting.\n"
                        f"Scene Context: {act} with {char} in {loc}.\n"
                        f"Likeness: Exaggerate 1 or 2 distinctive features of each person from JSON by 150% (e.g. comically round faces, noodle-like limbs). "
                        f"Recreate skin textures, moles, freckles, and outfit details exactly. Dynamic horizontal composition.\n\n"
                        f"JSON DATA:\n{clean_json}"
                    )
                    
                    img_bytes, g_err = generate_pixar_art(final_prompt)
                    if img_bytes:
                        st.session_state.generated_img = img_bytes
                        status.update(label="✨ Готово!", state="complete", expanded=False)
                        st.balloons()
                    else: st.error(f"Ошибка генерации: {g_err}")
                except Exception as e: st.error(f"Ошибка данных: {e}")
            else: st.error(f"Ошибка анализа: {err}")

if st.session_state.generated_img:
    st.image(st.session_state.generated_img, use_container_width=True)
    st.download_button("💾 СОХРАНИТЬ КАРТИНКУ", st.session_state.generated_img, "magic_mirror.jpg", "image/jpeg")

# --- JS блокировка клавиатуры ---
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
