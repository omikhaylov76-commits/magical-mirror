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

# 4. Функции обработки

def process_image(image_bytes):
    """Сжатие изображения для стабильной работы API."""
    img = Image.open(io.BytesIO(image_bytes))
    if max(img.size) > 1600:
        img.thumbnail((1600, 1600))
    output = io.BytesIO()
    img.convert('RGB').save(output, format='JPEG', quality=85)
    return output.getvalue()

def make_request_with_retry(url, payload):
    """Запрос с повторными попытками для стабильности."""
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
    """Этап 1: Дословный 'Криминалистический анализ'."""
    compressed = process_image(image_bytes)
    base64_image = base64.b64encode(compressed).decode('utf-8')
    
    prompt = (
        f"Act as a highly observant character designer and forensic animator. Analyze the photo for a scene: {act} with {char}.\n"
        "Identify EXACT headcount. Your goal is to capture the unique, distinguishing features of each person to avoid generating generic \"stock\" faces.\n\n"
        "For each person, return a JSON array of objects with the following structure:\n"
        "- id: integer (1..N)\n"
        "- gender: 'male'/'female'/'unknown'\n"
        "- age_group: 'toddler'/'child'/'preteen'/'adult'\n"
        "- body_structure_and_posture: detailed description (e.g., 'thin/slender with a long neck', 'plump/chubby build', 'slouching/stooped shoulders', 'broad shoulders', 'tall and lanky')\n"
        "- face_shape: e.g. 'round', 'oval', 'heart', 'square', 'diamond', 'long'\n"
        "- eye_characteristics: detailed description (e.g., 'deep-set narrow green eyes', 'large round brown eyes with long lashes', 'hooded blue eyes')\n"
        "- eyebrow_style: e.g., 'thick arched eyebrows', 'thin straight eyebrows', 'bushy unkempt eyebrows'\n"
        "- nose_shape: e.g., 'prominent straight bridge', 'small button nose', 'wide base', 'hooked'\n"
        "- jawline_and_chin: e.g., 'soft jaw with pointed chin', 'strong square jawline', 'cleft chin'\n"
        "- distinctive_features: array of specific markers (e.g., ['deep dimples', 'freckles across nose', 'mole on left cheek', 'prominent cheekbones', 'slight asymmetry'])\n"
        "- facial_hair: 'none' or highly specific description (e.g., 'patchy light stubble', 'full bushy beard', 'thin mustache')\n"
        "- expression_label: one of ['gentle_smile', 'big_smile', 'laughing', 'neutral', 'surprised', 'silly_face_with_tongue']\n"
        "- expression_nuance: factual description of how the expression affects the face (e.g., 'crinkles around the eyes', 'one corner of the mouth raised')\n"
        "- hair: {'color': '...', 'style': '...', 'texture': 'straight/wavy/curly/coily'}\n"
        "- eyewear: '...' or 'no eyewear'\n"
        "- outfit_details: list of strings\n\n"
        "Output ONLY valid JSON array. No extra text."
    )
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image-preview:generateContent?key={apiKey}"
    payload = {
        "contents": [{"parts": [{"text": prompt}, {"inlineData": {"mimeType": "image/jpeg", "data": base64_image}}]}],
        "generationConfig": {"responseMimeType": "application/json"}
    }
    
    res, err = make_request_with_retry(url, payload)
    if res:
        try:
            return res['candidates'][0]['content']['parts'][0]['text'], None
        except:
            return None, "Ошибка формата ответа."
    return None, err

def generate_image(prompt):
    """Этап 2: Дословный 'Кинематографический рендер'."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image-preview:generateContent?key={apiKey}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}], 
        "generationConfig": {"responseModalities": ["IMAGE"], "candidateCount": 1}
    }
    
    res, err = make_request_with_retry(url, payload)
    if res:
        try:
            parts = res['candidates'][0]['content']['parts']
            for p in parts:
                if 'inlineData' in p:
                    return base64.b64decode(p['inlineData']['data']), None
        except: pass
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
                    # Защищенный парсинг JSON
                    start_idx = json_res.find('[')
                    end_idx = json_res.rfind(']')
                    if start_idx != -1 and end_idx != -1:
                        clean_json = json_res[start_idx:end_idx+1]
                    else:
                        clean_json = json_res.replace('```json', '').replace('```', '').strip()
                    
                    people_data = json.loads(clean_json)
                    if isinstance(people_data, dict): people_data = [people_data]
                    p_count = len(people_data)
                    
                    st.write(f"🎨 Рисуем мир для {p_count} героев...")
                    
                    final_prompt = (
                        f"Create a high-quality, professional 3D animated character portrait in Pixar/Disney style.\n"
                        f"Scene: {loc}, Action: {act} with {char}.\n"
                        f"EXACTLY {p_count} human characters as recognizable caricatures of the people in the photo.\n\n"
                        f"Likeness Instructions:\n"
                        f"1. Base 3D geometry STRICTLY on the provided JSON (face_shape, nose, jawline).\n"
                        f"2. Playful Exaggeration: Playfully exaggerate physical traits from 'body_structure_and_posture' (chubby = round and bouncy, tall = lanky, long neck = elegantly elongated). Make it fun but charming.\n"
                        f"3. Integrate all 'distinctive_features' as defining markers. Do not smooth them out.\n"
                        f"4. Expression Nuance: Faithfully recreate facial expressions from JSON (expression_label and nuance).\n"
                        f"5. Lighting: Cinematic three-point lighting, warm rim light, volumetric atmosphere.\n\n"
                        f"JSON PROFILES: {clean_json}"
                    )
                    
                    img_bytes, g_err = generate_image(final_prompt)
                    
                    if img_bytes:
                        st.session_state.generated_img = img_bytes
                        status.update(label="✨ Волшебство готово!", state="complete", expanded=False)
                        st.balloons()
                    else: st.error(f"Ошибка генерации: {g_err}")
                except Exception as e: st.error(f"Ошибка данных: {e}")
            else: st.error(f"Ошибка анализа: {err}")

if st.session_state.generated_img:
    st.success("🎉 Твой шедевр готов!")
    st.image(st.session_state.generated_img, use_container_width=True)
    st.download_button("💾 СОХРАНИТЬ КАРТИНКУ", st.session_state.generated_img, "magic_mirror.jpg", "image/jpeg")

st.markdown("<br>", unsafe_allow_html=True)
if st.button("🔄 Начать заново"):
    st.session_state.generated_img = None
    st.rerun()

# --- Блокировка клавиатуры для планшетов ---
components.html(
    """
    <script>
    const doc = window.parent.document;
    const disableKeyboard = () => {
        const inputs = doc.querySelectorAll('div[data-baseweb="select"] input');
        inputs.forEach(input => {
            input.setAttribute('inputmode', 'none');
            input.setAttribute('readonly', 'true');
        });
    };
    disableKeyboard();
    const observer = new MutationObserver(disableKeyboard);
    observer.observe(doc.body, {childList: true, subtree: true});
    </script>
    """,
    height=0, width=0
)
