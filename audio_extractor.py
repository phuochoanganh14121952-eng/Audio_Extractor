import streamlit as st
import yt_dlp
import os
import time
import re
import json
import google.generativeai as genai

# ==========================================
# 1. CẤU HÌNH HỆ THỐNG (PC phuoc tran - RTX 3050)
# ==========================================
st.set_page_config(page_title="AI ENGLISH CENTER", page_icon="🎯", layout="wide")
st.title("🎯 AI English Center - Cloud Ready Edition")

SAVE_PATH = "Downloads" 
KEY_FILE = "my_key.txt"

if not os.path.exists(SAVE_PATH): os.makedirs(SAVE_PATH)

def get_api_key():
    # CHỈNH ĐỐN: Kiểm tra an toàn để không báo lỗi khi chạy máy nhà
    try:
        if hasattr(st, "secrets") and "api_key" in st.secrets:
            return st.secrets["api_key"]
    except:
        pass # Bỏ qua nếu không có secrets (chạy local)
        
    # Đọc file my_key.txt ở máy Boss
    try:
        with open(KEY_FILE, "r") as f: return f.read().strip()
    except: return None

# KÍCH HOẠT HỆ THỐNG AI
api_key = get_api_key()
model = None

if api_key:
    try:
        genai.configure(api_key=api_key)
        # Quét model khả dụng
        valid_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        priority_list = ['models/gemini-1.5-flash', 'models/gemini-1.5-flash-8b', 'models/gemini-2.0-flash-exp']
        selected_name = next((p for p in priority_list if p in valid_models), valid_models[0] if valid_models else None)
            
        if selected_name:
            model = genai.GenerativeModel(selected_name)
            st.sidebar.success(f"✅ Đã kết nối: {selected_name}")
    except Exception as e:
        st.sidebar.error(f"Lỗi AI: {e}")

def timestamp_to_seconds(ts):
    match = re.search(r'(\d+):(\d+)', ts)
    if match: return int(match.group(1)) * 60 + int(match.group(2))
    return 0

# ==========================================
# 2. QUẢN LÝ DỮ LIỆU
# ==========================================
if 'ai_result' not in st.session_state: st.session_state.ai_result = None
if 'start_time' not in st.session_state: st.session_state.start_time = 0
if 'file_path' not in st.session_state: st.session_state.file_path = None

# ==========================================
# 3. LOGIC TÁC CHIẾN
# ==========================================
def download_audio(link):
    ts = int(time.time())
    ydl_opts = {
        'format': 'bestaudio/best',
        'ffmpeg_location': 'C:/bin' if os.path.exists('C:/bin') else None,
        'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}],
        'outtmpl': f'{SAVE_PATH}/audio_{ts}.%(ext)s', 'quiet': True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([link])
        return f"{SAVE_PATH}/audio_{ts}.mp3"

# ==========================================
# 4. GIAO DIỆN
# ==========================================
st.sidebar.title("🎮 Nguồn dữ liệu")
mode = st.sidebar.radio("Chọn nguồn:", ["Dán Link", "Tải file máy tính"])

if mode == "Dán Link":
    url = st.text_input("Link Video YouTube/FB:")
    if st.button("🚀 Trích xuất"):
        with st.spinner('Đang xử lý link...'):
            st.session_state.file_path = download_audio(url)
            st.session_state.ai_result = None
            st.rerun()
else:
    uploaded = st.file_uploader("Chọn file Video/Audio:", type=["mp4", "mp3", "m4a"])
    if uploaded:
        p = os.path.join(SAVE_PATH, uploaded.name)
        with open(p, "wb") as f: f.write(uploaded.getbuffer())
        if st.session_state.file_path != p:
            st.session_state.file_path = p
            st.session_state.ai_result = None
            st.rerun()

# 5. THỰC THI AI & HIỂN THỊ
if st.session_state.file_path:
    st.write("### 🎧 Trình phát nhạc")
    with open(st.session_state.file_path, "rb") as f:
        st.audio(f.read(), format="audio/mp3", start_time=st.session_state.start_time)
    
    if st.button("🧠 Nhờ AI lập bảng học tập chuyên sâu"):
        with st.spinner('AI đang tập trung nghe...'):
            try:
                raw_file = genai.upload_file(path=st.session_state.file_path)
                while raw_file.state.name == "PROCESSING":
                    time.sleep(2)
                    raw_file = genai.get_file(raw_file.name)
                
                prompt = """
                Bạn là chuyên gia ngôn ngữ học. Hãy phân tích audio và trả về JSON:
                {
                  "transcription": [{"speaker": "A", "time": "mm:ss", "en": "Text", "vi": "Dịch"}],
                  "vocabulary": ["Từ mới - Nghĩa"],
                  "collocations": [{"phrase": "Cụm", "example_en": "Example", "example_vi": "Ví dụ"}]
                }
                Chỉ trả JSON.
                """
                response = model.generate_content([raw_file, prompt])
                match = re.search(r'\{.*\}', response.text, re.DOTALL)
                if match:
                    st.session_state.ai_result = json.loads(match.group())
                    st.rerun()
            except Exception as e:
                st.error(f"Lỗi AI: {e}")

    res = st.session_state.ai_result
    if res:
        st.divider()
        st.subheader("📝 Bảng luyện nghe chủ động")
        cols = st.columns([1, 1, 3, 3, 1])
        for i, h in enumerate(["**Nhân vật**", "**Thời gian**", "**Tiếng Anh**", "**Tiếng Việt**", "**Nghe**"]): cols[i].write(h)
        
        for idx, item in enumerate(res['transcription']):
            c = st.columns([1, 1, 3, 3, 1])
            c[0].write(item['speaker'])
            c[1].write(item['time'])
            c[2].write(item['en'])
            c[3].write(item['vi'])
            if c[4].button("🔊", key=f"btn_{idx}"):
                st.session_state.start_time = timestamp_to_seconds(item['time'])
                st.rerun()

        st.divider()
        cl, cr = st.columns(2)
        with cl:
            st.subheader("💡 Từ vựng")
            for v in res['vocabulary']: st.write(f"👉 {v}")
        with cr:
            st.subheader("🔗 Collocations & Ví dụ")
            for c in res.get('collocations', []):
                st.info(f"**{c['phrase']}**\n\n* {c['example_en']}\n* {c['example_vi']}")

st.sidebar.info(f"💻 RTX 3050 Optimized\n🎯 Path: {SAVE_PATH}")