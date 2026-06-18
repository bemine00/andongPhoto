import streamlit as st
import os
import zipfile
import io
import shutil
import time
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from PIL import Image
import pandas as pd  # 표 구성을 위한 pandas 라이브러리 추가

# 1. 페이지 설정
st.set_page_config(page_title="다존텍 안동물류센터", page_icon="📦", layout="centered")

# 폴더 설정
SAVE_DIR = "uploaded_photos"
ARCHIVE_DIR = "processed_photos"
for folder in [SAVE_DIR, ARCHIVE_DIR]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# 2. 디자인 (CSS)
st.markdown("""
    <style>
    /* 전체 배경 및 폰트 */
    .main { background-color: #f0f2f6; }
    
    /* 헤더 스타일 */
    .header-container {
        background: #1e293b;
        padding: 25px;
        border-radius: 12px;
        margin-bottom: 25px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
        text-align: center;
        color: #f8fafc;
    }
    .header-title { font-size: 32px !important; font-weight: 700; letter-spacing: -0.5px; margin: 0; }
    
    /* 모바일 환경 대응 (화면 너비 600px 이하) */
    @media (max-width: 600px) {
        .header-title { 
            font-size: 18px !important; 
        }
    
    /* 카테고리 헤더 스타일 (세련된 카드 형태) */
    [class^="cat-header-"] { 
        padding: 12px 15px; 
        border-radius: 8px; 
        font-weight: 600; 
        margin: 20px 0 10px 0;
        border-left: 5px solid #64748b;
        background: #ffffff;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .cat-header-1 { border-left-color: #3b82f6; } /* 파랑 */
    .cat-header-2 { border-left-color: #f59e0b; } /* 주황 */
    .cat-header-3 { border-left-color: #10b981; } /* 녹색 */
    .cat-header-4 { border-left-color: #8b5cf6; } /* 보라 */
    .cat-header-5 { border-left-color: #06b6d4; } /* 하늘색 */
    .cat-header-6 { border-left-color: #475569; } /* 슬레이트 */

    /* 버튼 스타일 */
    .stButton>button[kind="primary"] { 
        background-color: #0f172a; color: white; border: none; 
        height: 3.5em; border-radius: 8px; width: 100%; font-weight: 600;
    }
    
    /* 상태 박스 스타일 */
    .status-box { 
        background: white; padding: 20px; border-radius: 12px; 
        border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
    }
    
    /* 표 디자인 최적화 */
    div[data-testid="stTable"] { background-color: white; border-radius: 8px; padding: 10px; }
    div[data-testid="stTable"] th { background-color: #f8fafc !important; color: #1e293b !important; }
    </style>
    <div class="header-container">
        <p class="header-title">📦 삼성전자 안동 물류센터 증빙 관리</p>
    </div>
    """, unsafe_allow_html=True)

# 사진 등록 영역
cat_info = [
    {"name": "① 매장 진열 설치 증빙사진", "class": "cat-header-1", "short": "①매장"},
    {"name": "② 4인1조 증빙사진", "class": "cat-header-2", "short": "②4인1조"},
    {"name": "③ 폐가전 입고 증빙사진", "class": "cat-header-3", "short": "③입고"},
    {"name": "④ 폐가전 출고 증빙사진", "class": "cat-header-4", "short": "④출고"},
    {"name": "⑤ 다수량 설치 증빙상진", "class": "cat-header-1", "short": "⑤다수량"},
    {"name": "⑥ 사다리 및 특수장비 증빙사진", "class": "cat-header-2", "short": "⑥특수장비"}
]

# 3. 사이드바 - 관리자 메뉴
st.sidebar.title("🔐 관리자 모드")
admin_pw = st.sidebar.text_input("접속 암호", type="password")
if admin_pw == "7178":
    st.sidebar.success("✅ 인증 완료")
    target_date = st.sidebar.date_input("조회 날짜", datetime.now().date())
    t_str = target_date.strftime("%Y%m%d")

    all_f = [f for f in os.listdir(SAVE_DIR) if f.endswith(('.png', '.jpg', '.jpeg'))]
    sel_f = [f for f in all_f if t_str in f or datetime.fromtimestamp(os.path.getmtime(os.path.join(SAVE_DIR, f))).strftime("%Y%m%d") == t_str]

    if sel_f:
        st.sidebar.subheader("📥 항목별 다운로드")
        
        # 1. 카테고리별로 파일 분류 (cat_info의 name을 기준으로)
        # 각 카테고리별로 파일을 담을 딕셔너리 생성
        cat_files = {c["name"]: [] for c in cat_info}
        
        for f in sel_f:
            # 파일명에 포함된 접두어(①~⑥)를 기준으로 분류
            for cat_name in cat_files.keys():
                prefix = cat_name[0] # 카테고리의 첫 글자(번호) 추출
                if prefix in f:
                    cat_files[cat_name].append(f)
                    break
        
        # 2. 카테고리별 개별 다운로드 버튼 생성
        for cat_name, files in cat_files.items():
            if files:
                buf = io.BytesIO()
                with zipfile.ZipFile(buf, "w") as z:
                    for f in files:
                        # 폴더 구조 없이 파일만 압축하거나, 필요시 arcname에 폴더명 추가
                        z.write(os.path.join(SAVE_DIR, f), arcname=f.split('_', 1)[-1])
                
                st.sidebar.download_button(
                    label=f"📂 {cat_name} ({len(files)}건)", 
                    data=buf.getvalue(), 
                    file_name=f"{cat_name}_{t_str}.zip"
                )
        
        st.sidebar.divider()
        
        # 3. 전체 다운로드 기능은 유지
        buf_all = io.BytesIO()
        with zipfile.ZipFile(buf_all, "w") as z:
            for f in sel_f: z.write(os.path.join(SAVE_DIR, f), arcname=f)
        st.sidebar.download_button(label="📦 전체 데이터 받기 (Zip)", data=buf_all.getvalue(), file_name=f"DAJON_ALL_{t_str}.zip")

        st.sidebar.divider()
        if st.sidebar.button("✅ 작업 완료 (보관함 이동)"):
            for f in sel_f: shutil.move(os.path.join(SAVE_DIR, f), os.path.join(ARCHIVE_DIR, f))
            st.rerun()
        if st.sidebar.button("🗑️ 미처리 파일 즉시 삭제"):
            for f in sel_f: os.remove(os.path.join(SAVE_DIR, f))
            st.rerun()

# 4. 정보 입력
q_params = st.query_params
saved_d, saved_c = q_params.get("d", ""), q_params.get("c", "")

with st.container():
    c1, c2 = st.columns(2)
    with c1: driver = st.text_input("👤 기사님 성함", value=saved_d)
    with c2: car = st.text_input("🚛 차량 번호", value=saved_c)
    rep_date = st.date_input("📅 작업 날짜", datetime.now().date())

st.divider()

if "multi_rows" not in st.session_state:
    st.session_state.multi_rows = {c["name"]: [{"no": "", "files": []}] for c in cat_info}

def add_entry(cat): st.session_state.multi_rows[cat].append({"no": "", "files": []})
def del_entry(cat, idx): 
    if len(st.session_state.multi_rows[cat]) > 1: st.session_state.multi_rows[cat].pop(idx)

for cat in cat_info:
    c_name = cat["name"]
    st.markdown(f'<div class="{cat["class"]}">{c_name}</div>', unsafe_allow_html=True)
    for i, entry in enumerate(st.session_state.multi_rows[c_name]):
        col_no, col_file, col_del = st.columns([1.5, 3, 0.5])
        with col_no: entry["no"] = st.text_input(f"번호##{c_name}_{i}", value=entry["no"], key=f"no_{c_name}_{i}", placeholder="납품번호", label_visibility="collapsed")
        with col_file: entry["files"] = st.file_uploader(f"파일##{c_name}_{i}", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True, key=f"f_{c_name}_{i}", label_visibility="collapsed")
        with col_del:
            if len(st.session_state.multi_rows[c_name]) > 1:
                if st.button("❌", key=f"del_{c_name}_{i}"): del_entry(c_name, i); st.rerun()
    st.button(f"➕ {cat['short']} 추가", key=f"add_{c_name}", on_click=add_entry, args=(c_name,), use_container_width=False)

st.divider()

# 6. 전송 로직 + 이미지 압축
if st.button("🚀 모든 사진 데이터 일괄 전송", type="primary"):
    rows_to_send = []
    for c_name, entries in st.session_state.multi_rows.items():
        for entry in entries:
            if entry["files"]:
                if not entry["no"]: st.error(f"❌ {c_name}의 번호를 입력해주세요."); st.stop()
                rows_to_send.append({"cat": c_name, "no": entry["no"], "files": entry["files"]})

    if not driver or not car: st.error("⚠️ 기사님 정보를 확인해주세요.")
    elif not rows_to_send: st.warning("⚠️ 전송할 사진이 없습니다.")
    else:
        with st.spinner("📧 이미지 최적화 및 메일 전송 중..."):
            try:
                car4 = car.replace(" ", "")[-4:]
                d_pre = rep_date.strftime("%Y%m%d")
                saved_files = []

                for row in rows_to_send:
                    clean_no = "".join(filter(str.isdigit, row["no"]))
                    prefix = "①" if "①" in row["cat"] else "②" if "②" in row["cat"] else "③" if "③" in row["cat"] else \
                             "④" if "④" in row["cat"] else "⑤" if "⑤" in row["cat"] else "⑥"
                    
                    for idx, f in enumerate(row["files"]):
                        ext = os.path.splitext(f.name)[1].lower()
                        if ext not in ['.jpg', '.jpeg', '.png']: ext = '.jpg'
                        
                        fn = f"{prefix}_{d_pre}_{clean_no}_{car4}_{idx+1}{ext}"
                        
                        img = Image.open(f)
                        if img.mode in ("RGBA", "P"): img = img.convert("RGB")
                        
                        max_size = 1280
                        if img.width > max_size:
                            w_percent = (max_size / float(img.width))
                            h_size = int((float(img.height) * float(w_percent)))
                            img = img.resize((max_size, h_size), Image.Resampling.LANCZOS)
                        
                        img_io = io.BytesIO()
                        img.save(img_io, format="JPEG", quality=70, optimize=True)
                        f_bytes = img_io.getvalue()
                        
                        with open(os.path.join(SAVE_DIR, fn), "wb") as sf: sf.write(f_bytes)
                        saved_files.append((fn, f_bytes))

                # 메일 발송 설정
                naver_user = st.secrets["NAVER_USER"]
                naver_pw = st.secrets["NAVER_PW"]
                msg = MIMEMultipart()
                msg['Subject'] = f"[안동증빙관리] {driver}_{car}_{rep_date.strftime('%m%d')}"
                msg['From'] = f"{naver_user}@naver.com"
                msg['To'] = f"{naver_user}@naver.com"
                msg.attach(MIMEText(f"기사: {driver}\n차량: {car}\n일자: {rep_date}\n(이미지 최적화 전송 완료)"))

                for fname, fdata in saved_files:
                    part = MIMEBase('image', 'jpeg')
                    part.set_payload(fdata)
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', 'attachment', filename=("utf-8", "", fname))
                    msg.attach(part)

                server = smtplib.SMTP_SSL('smtp.naver.com', 465)
                server.login(naver_user, naver_pw)
                server.send_message(msg)
                server.quit()

                st.balloons(); st.success("✅ 최적화 전송 완료!"); time.sleep(2)
                st.session_state.multi_rows = {c["name"]: [{"no": "", "files": []}] for c in cat_info}
                st.rerun()
            except Exception as e: st.error(f"❌ 오류: {e}")

# 7. 기사님별 실시간 당일 전송 현황판 및 [리뉴얼] 표(Table) 형식의 리스트 제공
if driver and car:
    st.markdown("### 📊 나의 오늘 자 사진 전송 현황")
    car4_search = car.replace(" ", "")[-4:]
    today_str = rep_date.strftime("%Y%m%d")
    
    try:
        if os.path.exists(SAVE_DIR):
            uploaded_files = os.listdir(SAVE_DIR)
            my_files = [f for f in uploaded_files if car4_search in f and today_str in f]
            
            if my_files:
                st.markdown(f'<div class="status-box"><b>{driver} 기사님</b>의 오늘 전송 성공 데이터: <b>총 {len(my_files)}건</b></div>', unsafe_allow_html=True)
                
                history_data = {
                    "① 매장진열": set(), 
                    "② 4인1조": set(), 
                    "③ 폐가전입고": set(), 
                    "④ 폐가전출고": set(), 
                    "⑤ 다수량": set(), 
                    "⑥ 특수장비": set() 
                }
                
                table_rows = []
                cat_mapping = {
                    "①": "① 매장진열", "②": "② 4인1조", "③": "③ 폐가전입고",
                    "④": "④ 폐가전출고", "⑤": "⑤ 다수량", "⑥": "⑥ 특수장비"
                }

                for f in sorted(my_files):
                    parts = f.split('_')
                    if len(parts) >= 5:
                        pref = parts[0]
                        no_item = parts[2]
                        
                        display_cat = cat_mapping.get(pref, "기타")
                        
                        # 키를 딕셔너리 정의와 100% 일치시킴
                        if pref in cat_mapping:
                            history_data[cat_mapping[pref]].add(no_item)
                        
                        table_rows.append({
                            "분류": display_cat,
                            "납품번호": no_item,
                            "상태": "🟢 전송완료"
                        })
                
                # 메트릭 스코어 출력
                c1, c2, c3 = st.columns(3)
                c4, c5, c6 = st.columns(3)
                with c1: st.metric("① 매장진열", len([f for f in my_files if "①" in f]))
                with c2: st.metric("② 4인1조", len([f for f in my_files if "②" in f]))
                with c3: st.metric("③ 폐가전입고", len([f for f in my_files if "③" in f]))

                with c4: st.metric("④ 폐가전출고", len([f for f in my_files if "④" in f]))
                with c5: st.metric("⑤ 다수량", len([f for f in my_files if "⑤" in f]))
                with c6: st.metric("⑥ 특수장비", len([f for f in my_files if "⑥" in f]))
                
                # --- [★핵심 기능: 표 형식 정리] ---
                if table_rows:
                    st.write("")  # 여백
                    st.markdown("##### 📝 상세 전송 번호 리스트")
                    
                    # 중복 데이터 제거 후 가독성 좋게 DataFrame 생성
                    df = pd.DataFrame(table_rows).drop_duplicates().reset_index(drop=True)
                    df.index = df.index + 1  # 인덱스를 1부터 시작하는 '순번' 개념으로 사용
                    df.index.name = "순번"
                    
                    # Streamlit의 정적 HTML 표를 활용해 중앙 정렬이 깔끔하게 먹히도록 출력
                    st.table(df)
                # ---------------------------------
            else:
                st.info("💡 오늘 전송된 사진 내역이 없습니다. 정보를 입력하고 사진을 제출해 주세요.")
    except Exception as e:
        st.error(f"현황판 로드 오류: {e}")