import streamlit as st
import requests
import io
import base64
import re
from PIL import Image
from openai import OpenAI
import streamlit.components.v1 as components

# 1. Настройка страницы
st.set_page_config(
    page_title="Hello Kitty Magic Mirror Pro", 
    page_icon="🎀", 
    layout="centered"
)

# 2. Получение ключей из базы (secrets)
OPENAI_KEY = st.secrets.get("OPENAI_API_KEY", "")
GOOGLE_KEY = st.secrets.get("GOOGLE_API_KEY", "")

# Клиент для анализа (GPT-4o)
client_openai = OpenAI(api_key=OPENAI_KEY)

# 3. Премиальный дизайн в стиле iOS 26
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stApp {
        background: linear-gradient(135deg, #fffafa 0%, #f5f7fa 100%);
        font-family: -apple-system, sans-serif;
    }
    .stButton button {
        height: 75px !important;
        border-radius: 35px !important;
        font-size: 24px !important;
        background: linear-gradient(90deg, #ff4b8b 0%, #ff85a1 100%) !important;
        color: white !important;
        border: none !important;
        box-shadow: 0 10px 25px rgba(255, 75, 139, 0.4) !important;
        font-weight: 800 !important;
        width: 100%;
        transition: 0.3s;
    }
    .stButton button:hover {
        transform: scale(1.02);
        box-shadow: 0 15px 30px rgba(255, 75, 139, 0.5) !important;
        cursor: pointer;
    }
    div[data-baseweb="select"] > div {
        border-radius: 20px !important;
        border: 2px solid #ffeef2 !important;
        background-color: white !important;
        height: 60px !important;
    }
    h1 {
        color: #ff4b8b !important;
        text-align: center;
        font-weight: 900 !important;
        font-size: 42px !important;
    }
    .info-text {
        text-align: center;
        color: #666;
        margin-bottom: 30px;
        font-size: 18px;
    }
    </style>
""", unsafe_allow_html=True)

# 4. Функции обработки

def encode_image(image_bytes):
    return base64.b64encode(image_bytes).decode('utf-8')

def analyze_likeness(image_bytes, engine_choice):
    """Глубокий физиономический анализ через выбранную ИИ-модель."""
    base64_image = encode_image(image_bytes)
    
    prompt = (
        "Ты — эксперт-физиономист Pixar. Твоя задача — составить точный анатомический паспорт для 100% узнаваемости КАЖДОГО человека на фото (включая тех, кто на заднем плане).\n\n"
        "ОБЯЗАТЕЛЬНО: Начни ответ СТРОГО с фразы 'Количество людей: [число]'.\n\n"
        "Далее опиши КАЖДОГО человека СТРОГО отдельно (Персонаж 1, Персонаж 2, Персонаж 3 и т.д.), указывая их расположение (слева, справа, на заднем плане):\n"
        "1. ПОЛ, ВОЗРАСТ И ТЕЛОСЛОЖЕНИЕ: (Критически важно! Укажи, если человек стройный, полненький/крупный или если это малыш/ребенок).\n"
        "2. ГЕОМЕТРИЯ ЛИЦА: форма лица, щеки, подбородок.\n"
        "3. ГЛАЗА И БРОВИ: форма, наличие и точное описание ОЧКОВ (солнцезащитные, для зрения, форма оправы).\n"
        "4. ВОЛОСЫ И ГОЛОВНЫЕ УБОРЫ: цвет, длина, ПРИЧЕСКА (особенно челка) или наличие КЕПКИ/панамки.\n"
        "5. ЖЕСТЫ И МИМИКА: улыбка, наклон головы и т.д.\n\n"
        "Твоя цель — описать их максимально контрастно, чтобы 3D-модель поняла, что это абсолютно разные люди."
    )

    if "GPT-4o" in engine_choice:
        try:
            response = client_openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]}
                ],
                max_tokens=1000
            )
            return response.choices[0].message.content
        except Exception as e:
            st.error(f"Ошибка анализа GPT-4o: {e}")
            return None
    else:
        # Логика для Gemini 2.5 Flash
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GOOGLE_KEY}"
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inlineData": {"mimeType": "image/jpeg", "data": base64_image}}
                ]
            }],
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"}
            ]
        }
        try:
            response = requests.post(url, json=payload, timeout=60)
            if response.status_code == 200:
                result = response.json()
                candidates = result.get('candidates', [])
                if candidates and 'content' in candidates[0]:
                    return candidates[0]['content']['parts'][0]['text']
                else:
                    finish_reason = candidates[0].get('finishReason', 'Неизвестно') if candidates else 'Отсутствуют данные'
                    st.warning(f"⚠️ Gemini заблокировал анализ этого фото (Причина: {finish_reason}). Сработали строгие фильтры безопасности Google. Пожалуйста, выберите GPT-4o для этой фотографии.")
                    return None
            else:
                st.error(f"Ошибка анализа Gemini (Код {response.status_code}): {response.text}")
                return None
        except Exception as e:
            st.error(f"Ошибка соединения Gemini: {e}")
            return None

def call_google_generate(prompt, model_id):
    """Универсальная смарт-функция генерации через Google API, настроенная под ваши доступы."""
    if not model_id:
        return None
        
    # Логика для семейства Imagen (метод :predict)
    if "imagen" in model_id:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:predict?key={GOOGLE_KEY}"
        payload = {
            "instances": [{"prompt": prompt}],
            "parameters": {
                "sampleCount": 1,
                "aspectRatio": "16:9" # Широкий формат
            }
        }
        
    # Логика для семейства Gemini (метод :generateContent)
    elif "gemini" in model_id:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={GOOGLE_KEY}"
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseModalities": ["IMAGE"]
            }
        }
    else:
        st.error("Неизвестный формат модели Google.")
        return None
        
    try:
        response = requests.post(url, json=payload, timeout=120)
        
        if response.status_code == 200:
            result = response.json()
            
            # Извлечение картинки для Imagen
            if "imagen" in model_id:
                predictions = result.get('predictions', [])
                if predictions and 'bytesBase64Encoded' in predictions[0]:
                    return base64.b64decode(predictions[0]['bytesBase64Encoded'])
                    
            # Извлечение картинки для Gemini
            elif "gemini" in model_id:
                try:
                    parts = result.get('candidates', [{}])[0].get('content', {}).get('parts', [])
                    for part in parts:
                        if 'inlineData' in part:
                            return base64.b64decode(part['inlineData']['data'])
                except (KeyError, IndexError):
                    st.error("Ошибка парсинга ответа от Gemini.")
            
            st.error("Техническая ошибка: API не вернуло изображение в ожидаемом формате.")
            
        else:
            st.error(f"Ошибка API (Код {response.status_code}): {response.text}")
            
    except Exception as e:
        st.error(f"Сбой соединения: {e}")
        
    return None

# 5. Интерфейс

st.title("🎀 Магическое Зеркало Pro")
st.markdown('<p class="info-text">Выберите вашу идеальную модель для генерации</p>', unsafe_allow_html=True)

# СЛОВАРЬ ВАШИХ ДОСТУПНЫХ МОДЕЛЕЙ (Основано на результатах диагностики)
AVAILABLE_MODELS = {
    "🌟 Imagen 4.0 Ultra (Флагман, Макс. реализм)": "imagen-4.0-ultra-generate-001",
    "🎨 Imagen 4.0 Standard (Быстрый 16:9 рендер)": "imagen-4.0-generate-001",
    "💎 Gemini 3 Pro Image (Продвинутая детализация)": "gemini-3-pro-image-preview",
    "⚡ Gemini 3.1 Flash Image (Сверхбыстрая генерация)": "gemini-3.1-flash-image-preview"
}

selected_model_name = st.selectbox("Движок магии:", list(AVAILABLE_MODELS.keys()))
selected_model_id = AVAILABLE_MODELS[selected_model_name]

CHARACTERS = ["Hello Kitty", "Kuromi", "My Melody", "Cinnamoroll", "Pompompurin", "Pochacco"]
LOCATIONS = ["Розовый замок", "Неоновый концерт", "Сказочный лес", "Кафе сладостей", "Радужное облако"]
ACTIONS = ["Чаепитие", "Танцы", "Прятки", "Концерт"]

col1, col2, col3 = st.columns(3)
with col1: char = st.selectbox("Друг:", CHARACTERS)
with col2: loc = st.selectbox("Место:", LOCATIONS)
with col3: act = st.selectbox("Сюжет:", ACTIONS)

analysis_engine = st.radio("Интеллект для анализа фото:", ["GPT-4o (Строгая структура)", "Gemini 2.5 Flash (Внимание к микродеталям)"], horizontal=True)
source = st.radio("Источник:", ["📸 Селфи", "📁 Из галереи"], horizontal=True)
input_data = None

if source == "📸 Селфи":
    captured = st.camera_input("")
    if captured: input_data = captured.getvalue()
else:
    uploaded = st.file_uploader("", type=['jpg', 'png', 'jpeg'])
    if uploaded: input_data = uploaded.getvalue()

if input_data:
    st.image(input_data, caption="Оригинал", width=250)
    
    if st.button("✨ СОЗДАТЬ МАГИЮ"):
        engine_short_name = analysis_engine.split(' ')[0]
        with st.spinner(f"🪄 {engine_short_name} анализирует детали вашего лица..."):
            description = analyze_likeness(input_data, analysis_engine)
            
            if description:
                match = re.search(r"Количество людей:\s*(\d+)", description)
                p_count = match.group(1) if match else "1"
                
                final_prompt = (
                    f"A masterpiece 3D animation movie still in the exact style of Pixar. "
                    f"Location: {loc}. Action: {act} with {char}. "
                    f"Characters: Convert the {p_count} humans from the photo into HIGHLY DISTINCT, unique 3D stylized characters. "
                    f"Sanrio Character: The official classic {char} is participating in the scene. "
                    f"Likeness Instructions: STRICTLY differentiate each character based on this exact description: {description}. "
                    f"CRITICAL RULES: Do NOT make them clones. Pay extreme attention to their differences! "
                    f"Give them distinct body types (e.g. chubby/plump vs slim), different ages (e.g. adults vs baby/toddler), "
                    f"unique headwear (e.g. caps/hats), distinct eyewear (sunglasses/glasses), and unique hairstyles exactly as described. "
                    f"Cinematic lighting, vibrant colors, ultra-high quality render, 8k resolution."
                )
                
                model_display_name = selected_model_name.split('(')[0].strip()
                with st.spinner(f"🎨 {model_display_name} отрисовывает шедевр..."):
                    img_bytes = call_google_generate(final_prompt, selected_model_id)
                    
                    if img_bytes:
                        st.balloons()
                        st.image(img_bytes, use_container_width=True, caption=f"Результат: {model_display_name}")
                        
                        with st.expander("👤 Анатомический паспорт (Описание внешности)"):
                            st.info("Текст ниже можно скопировать для использования в других приложениях:")
                            st.code(description, language="text")

                        with st.expander("📝 Полный технический промпт"):
                            st.code(final_prompt, language="text")
                            
                        st.download_button("💾 Сохранить", img_bytes, "magic_mirror.jpg", "image/jpeg")

if st.button("🔄 Сброс"):
    st.rerun()

# --- ИСПРАВЛЕНИЕ ДЛЯ ПЛАНШЕТОВ: Блокировка всплывающей клавиатуры ---
# Этот невидимый блок добавляет атрибут inputmode='none' во все списки
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
    // Отключаем клавиатуру при загрузке
    disableKeyboard();
    // И следим за тем, чтобы отключать её при любых обновлениях страницы
    const observer = new MutationObserver(disableKeyboard);
    observer.observe(doc.body, {childList: true, subtree: true});
    </script>
    """,
    height=0, width=0
)
