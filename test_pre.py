import streamlit as st
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

# ==========================================
# 1. 기본 설정
# ==========================================
st.set_page_config(page_title="소유한의원 문진표", layout="wide")

# 비밀번호 로드
try:
    SENDER_PASSWORD = st.secrets["naver_password"]
except:
    SENDER_PASSWORD = ""

SENDER_EMAIL = "kmdchoi84@naver.com"
RECEIVER_EMAIL = "kmdchoi84@naver.com"

# 세션 상태 초기화
if 'agreed' not in st.session_state:
    st.session_state['agreed'] = False
if 'submitted' not in st.session_state:
    st.session_state['submitted'] = False

# URL 파라미터 처리
query_params = st.query_params
default_name = query_params.get("name", "")
default_phone = query_params.get("phone", "")
reserved_date_raw = query_params.get("date", "")
reserved_date = reserved_date_raw.replace("_", " ").replace("+", " ")

# ==========================================
# 2. 이메일 전송 함수
# ==========================================
def send_email_with_json(final_data):
    if not SENDER_PASSWORD:
        return "NO_PASSWORD"

    try:
        smtp = smtplib.SMTP('smtp.naver.com', 587, timeout=20) # 타임아웃 넉넉히
        smtp.ehlo()
        smtp.starttls()
        smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
        
        msg = MIMEMultipart()
        patient_name = final_data['환자정보']['성함']
        msg['Subject'] = f"[소유한의원] {patient_name}님 문진표 도착"
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECEIVER_EMAIL
        
        # 본문 작성
        job_env = final_data['기초정보'].get('생활환경', [])
        job_env_str = ", ".join(job_env) if job_env else "선택 없음"
        
        body_text = f"""
        환자명: {patient_name}
        예약정보: {final_data['환자정보'].get('예약일시', '정보없음')}
        연락처: {final_data['환자정보']['연락처']}
        """
        msg.attach(MIMEText(body_text, 'plain', 'utf-8'))
        
        # JSON 첨부
        json_str = json.dumps(final_data, indent=4, ensure_ascii=False)
        attachment = MIMEApplication(json_str.encode('utf-8'), _subtype='json')
        filename = f"{patient_name}_문진표.json"
        attachment.add_header('Content-Disposition', 'attachment', filename=filename)
        msg.attach(attachment)
        
        smtp.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        smtp.quit()
        return "SUCCESS"
        
    except smtplib.SMTPAuthenticationError:
        return "AUTH_ERROR"
    except Exception as e:
        return f"ERROR: {str(e)}"

# ==========================================
# 3. 화면 로직
# ==========================================

# [A] 완료 화면 (전송 성공 시 표시)
if st.session_state['submitted']:
    # 완료 스타일
    st.markdown("""
    <style>
        #MainMenu, header, footer {visibility: hidden;}
        [data-testid="stToolbar"] {visibility: hidden;}
        .stDeployButton {display:none;}
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div style="text-align: center; padding: 50px 20px;">
        <h1 style="color: #0068c3;">제출이 완료되었습니다!</h1>
        <br>
        <h3>{default_name if default_name else "환자"} 님,<br>
        {reserved_date if reserved_date else ""} 진료 예약이 확인되었습니다.</h3>
        <br>
        <p style="font-size: 18px; line-height: 1.8; color: #555;">
        작성해주신 소중한 정보를 바탕으로<br>
        정성을 담아 치료에 최선을 다해 임하겠습니다.<br>
        진료실에서 뵙겠습니다.
        </p>
        <br><br>
        <h4>소유한의원 원장 최아랑 올림</h4>
    </div>
    """, unsafe_allow_html=True)
    st.balloons()

# [B] 동의서 페이지
elif not st.session_state['agreed']:
    st.title("소유한의원 사전 문진")
    st.markdown("---")
    if reserved_date:
        st.info(f"📅 예약일시: {reserved_date}")
        
    agreement_text = """
    **[필수] 개인정보 및 민감정보 수집·이용 동의**
    
    1. **수집 목적**: 진료 예약 확인 및 사전 증상 파악
    2. **수집 항목**: 성명, 연락처, 신체정보, 건강 관련 증상
    3. **보유 기간**: **전송 완료 후 서버에서 즉시 삭제**
    4. **거부 권리**: 동의를 거부할 수 있으나, 문진 이용이 제한됩니다.
    """
    st.markdown(agreement_text)
    check = st.checkbox("위 내용을 확인하였으며, 이에 동의합니다.")
    st.write("")
    if st.button("문진표 작성하기", type="primary"):
        if check:
            st.session_state['agreed'] = True
            st.rerun()
        else:
            st.warning("동의 항목에 체크해주셔야 합니다.")

# [C] 문진표 작성 페이지
else:
    # ----------------------------------------
    # UI 스타일 (PC 버튼 위치 수정됨)
    # ----------------------------------------
    custom_css = """
    <style>
        /* 기본 숨김 */
        header, #MainMenu, footer {visibility: hidden; height: 0;}
        [data-testid="stToolbar"] {visibility: hidden; height: 0;}
        .stDeployButton {display:none;}
        
        /* PC 스타일 (769px 이상) */
        @media (min-width: 769px) {
            .pc-header {
                position: fixed; top: 0; left: 0; width: 100%; height: 140px; /* 헤더 높이 늘림 */
                background-color: white; z-index: 1000; border-bottom: 1px solid #ddd;
                text-align: center; padding-top: 20px; display: block;
            }
            .block-container { padding-top: 160px !important; } /* 본문 여백 더 늘림 */
            
            div.stButton > button:first-child {
                position: fixed !important; 
                top: 85px !important; /* 버튼을 헤더 안쪽 하단으로 배치 */
                left: 50% !important;
                transform: translateX(-50%) !important; 
                z-index: 2000 !important;
                width: 300px !important;
                background-color: #ff4b4b !important; color: white !important;
                box-shadow: 0 4px 6px rgba(0,0,0,0.2) !important;
            }
            .mobile-title { display: none !important; }
        }

        /* 모바일 스타일 (768px 이하) */
        @media (max-width: 768px) {
            .pc-header { display: none !important; }
            .block-container { padding-top: 1rem !important; }
            div.stButton > button:first-child {
                width: 100% !important; background-color: #ff4b4b !important; color: white !important;
                margin-top: 20px !important; z-index: 1 !important;
            }
            .mobile-title { display: block !important; }
        }
        
        .header-title-small {font-size: 1.0rem; color: #666; margin: 0;}
        .header-title-large {font-size: 2.0rem; font-weight: 800; color: #333; margin-top: 5px;}
    </style>

    <div class="pc-header">
        <div class="header-title-small">소유한의원</div>
        <div class="header-title-large">사전 문진표</div>
    </div>
    """
    st.markdown(custom_css, unsafe_allow_html=True)

    # 모바일용 제목
    st.markdown(f"""
    <div class="mobile-title" style='text-align:center; margin-bottom: 20px;'>
        <h3 style='color:#333; margin:0;'>소유한의원 사전 문진표</h3>
        <p style='color:#0068c3; font-weight:bold; margin-top:5px;'>📅 예약일시: {reserved_date if reserved_date else '미지정'}</p>
        <hr>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1: name = st.text_input("성함", value=default_name, placeholder="예: 홍길동")
    with col2: phone = st.text_input("연락처", value=default_phone, placeholder="예: 010-0000-0000")

    # 1. 기초 정보
    basic_info_data = {}
    with st.expander("1. 기초 정보 (신체 및 생활패턴)", expanded=True):
        c1, c2 = st.columns(2)
        with c1: height = st.text_input("키 (cm)")
        with c2: weight = st.text_input("체중 (kg)")
        
        st.markdown("##### 🩺 평소 생활 및 근무 환경")
        job_conditions = ["하루 종일 앉아 있는 편이다", "하루 종일 서서 일한다", "반복적인 동작을 많이 한다", 
                          "눈을 많이 쓰고 집중력이 필요하다", "말을 많이 하는 편이다", "무거운 물건을 들거나 힘을 쓴다", 
                          "사람을 상대하며 감정 소모가 심하다", "야간 근무 또는 교대 근무를 한다", 
                          "식사 시간이 불규칙하다", "회식이나 술자리가 잦다"]
        
        selected_job_conditions = []
        jc1, jc2 = st.columns(2)
        for i, condition in enumerate(job_conditions):
            if (i % 2 == 0 and jc1.checkbox(condition, key=f"job_{i}")) or \
               (i % 2 != 0 and jc2.checkbox(condition, key=f"job_{i}")):
                selected_job_conditions.append(condition)
        
        other_lifestyle = st.text_input("기타 참고사항", placeholder="그 외 특이사항")
        basic_info_data = {"신체정보": f"{height}cm / {weight}kg", "생활환경": selected_job_conditions, "기타메모": other_lifestyle}

    # 2. 증상 체크리스트
    questionnaire_data = {
        "2. 식욕 및 소화 (食慾/消化)": ["식후(1~2시간 이내) 트림, 복통, 더부룩함, 속쓰림", "공복 시 속 불편감, 신경 예민", "스트레스를 받으면 속이 불편함", "고기나 기름진 음식 섭취 후 속 불편함", "식전에 물을 먹어야 밥이 넘어감"],
        "3. 대변 (大便)": ["대변에 밥알, 고기 덩어리, 야채 등이 보임", "설사처럼 무르거나 돌처럼 단단한 변", "회색변, 검은변, 혈변", "대변 냄새 및 방귀 냄새가 심함", "잔변감이 있음", "아침에 대변을 못 보면 하루가 힘듦", "식사 중 또는 식사 후에 바로 방귀나 설사가 나옴"],
        "4. 소변 (小便)": ["소변에 거품이 많음, 냄새가 심함", "자다가 소변 때문에 깸 (야간뇨)", "잔뇨감, 소변을 참기 어려움 (급박뇨)", "소변을 보려면 한참 기다려야 함 (지연뇨), 배뇨통"],
        "5. 땀 및 피부 (汗/皮)": ["다른 사람들보다 땀이 많이 남", "땀 냄새가 심함", "손발 껍질이 잘 벗겨짐", "상처 회복이 느림, 피부질환 있음, 닭살이 잘 생김"],
        "6. 수면 (睡眠)": ["잠들기 어려움 (입면장애), 자다가 자주 깬다 (수면유지장애)", "꿈을 많이 꿈", "아침에 일어나기 힘듦", "코를 심하게 곯음"],
        "7. 두면 및 이비인후과 (頭面)": ["재채기, 콧물, 코막힘, 기침, 가래, 천식", "환절기 알레르기성 비염", "잦은 두통", "눈알이 뻑뻑하고 뻐근하게 아픔", "목구멍의 이물감/불편함", "이명 (현재 또는 피곤할 때), 탈모 진행, 잦은 구내염/헤르페스"],
        "8. 한열 (寒熱)": ["갑자기 열이 오르고 땀이 남", "남들보다 추위를 많이 탐"],
        "9. 수족, 사지 및 통증 (手足/四肢)": ["움직이면 더 아프거나 덜 아픔, 누워서 쉬면 편해짐", "누워서 쉬어도 불편함", "아침 혹은 오후에 통증이 심해짐", "세게 누르면 아프거나(압통) 오히려 시원함", "손발 혹은 관절이 잘 부음 (아침/저녁)", "몸이 비틀어져 있는 느낌"],
        "10. 흉부 및 정신 (胸部)": ["숨 쉬는 게 불편함", "심장이 두근거리는 느낌 (심계)", "최근 딸꾹질을 한 적이 있음", "사소한 일에 깜짝깜짝 잘 놀람", "한숨을 자주 쉼, 조금만 걸어도 숨이 참", "말을 더듬거나 단어가 생각나지 않음, 건망증 심화", "의욕이 없고 무기력함"],
        "11. 기타 (其他)": ["최근 3개월간 3kg 이상 체중 변화", "아침 혹은 오후에 컨디션 변화가 있음"],
        "12. 남성 (男性)": ["발기 문제, 조루 (컨디션 저하 시)", "성관계 시 통증", "아침 발기 부전, 사정 후 정액 흘러나옴"],
        "12. 여성 (女性)": ["생리주기 불규칙", "심한 생리통 (진통제 복용 필요)", "생리/배란기 증상: 가슴/겨드랑이 통증, 몸 무거움, 식욕 항진, 감정 조절 불가", "냉대하 이상 (양 많음, 황색, 냄새)", "출산 후 급격한 체중 증가", "잦은 질염, 방광염", "성교통, 질건조증, 불감증"]
    }
    
    user_responses = {}
    for category, items in questionnaire_data.items():
        with st.expander(category):
            selected = []
            for item in items:
                if st.checkbox(item, key=f"{category}_{item}"): selected.append(item)
            other = st.text_input(f"기타 증상", key=f"other_{category}")
            if selected or other: user_responses[category] = {"선택증상": selected, "기타메모": other}

    medical_history = {}
    with st.expander("13. 현재 복약 중인 약 (양약/한약)"):
        st.info("💡 자세히 적어주세요.")
        med = st.text_area("입력란", height=80, key="med_input")
        if med: medical_history["복약정보"] = med

    with st.expander("14. 현재 복용 중인 건강기능식품"):
        st.info("💡 영양제 이름을 적어주세요.")
        sup = st.text_area("입력란", height=80, key="sup_input")
        if sup: medical_history["건강기능식품"] = sup

    with st.expander("15. 수술 및 기타 과거력"):
        st.info("💡 수술 이력, 병력을 적어주세요.")
        hist = st.text_area("입력란", height=80, key="hist_input")
        if hist: medical_history["과거력"] = hist

    st.write("\n\n")
    
    # ------------------------------------------------
    # 제출 버튼 (심플 스피너 로직)
    # ------------------------------------------------
    if st.button("문진표 제출하기"):
        if not name or not phone:
            st.warning("⚠️ 성함과 연락처는 필수입니다.")
        elif not (user_responses or basic_info_data.get('생활환경') or medical_history):
            st.warning("⚠️ 증상이나 정보를 하나라도 입력해주세요.")
        else:
            # 심플하게 스피너 하나만!
            with st.spinner("AI 분석을 위해 변환 및 전송중..."):
                final_data = {
                    "환자정보": {"성함": name, "연락처": phone, "예약일시": reserved_date},
                    "기초정보": basic_info_data,
                    "문진내용": user_responses,
                    "상세정보": medical_history
                }
                result = send_email_with_json(final_data)
            
            # 전송 끝나면 여기 실행
            if result == "SUCCESS":
                st.session_state['submitted'] = True
                st.rerun() # 화면 새로고침하여 완료 화면으로 이동
                
            elif result == "NO_PASSWORD":
                st.error("🚨 서버 설정 오류: Secrets 비밀번호가 없습니다.")
            elif result == "AUTH_ERROR":
                st.error("🚨 인증 실패: 네이버 아이디나 앱비밀번호를 확인하세요.")
            else:
                st.error(f"🚨 전송 실패: {result}")
