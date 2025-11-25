import streamlit as st
import json
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

# ==========================================
# 1. 설정 및 초기화 (디버깅 모드)
# ==========================================
st.set_page_config(page_title="소유한의원 문진표", layout="wide")

# 비밀번호 확인용 디버깅 (보안상 실제 비번은 출력 안 함)
try:
    SENDER_PASSWORD = st.secrets["naver_password"]
    is_password_set = "✅ 비밀번호 설정됨"
except Exception as e:
    SENDER_PASSWORD = ""
    is_password_set = f"❌ 비밀번호 로드 실패: {e}"

SENDER_EMAIL = "kmdchoi84@naver.com"
RECEIVER_EMAIL = "kmdchoi84@naver.com"

if 'agreed' not in st.session_state:
    st.session_state['agreed'] = False

query_params = st.query_params
default_name = query_params.get("name", "")
default_phone = query_params.get("phone", "")
reserved_date_raw = query_params.get("date", "")
reserved_date = reserved_date_raw.replace("_", " ").replace("+", " ")

# ==========================================
# 2. 이메일 전송 함수 (에러 적나라하게 표시)
# ==========================================
def send_email_with_json(final_data):
    # 비밀번호 없으면 바로 리턴
    if not SENDER_PASSWORD:
        return "SECRET_KEY_MISSING_ERROR"

    try:
        smtp = smtplib.SMTP('smtp.naver.com', 587)
        smtp.ehlo()
        smtp.starttls()
        # 여기서 로그인 시도
        smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
        
        msg = MIMEMultipart()
        patient_name = final_data['환자정보']['성함']
        msg['Subject'] = f"[소유한의원] {patient_name}님 문진표 도착"
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECEIVER_EMAIL
        
        job_env = final_data['기초정보'].get('생활환경', [])
        job_env_str = ", ".join(job_env) if job_env else "선택 없음"
        
        body_text = f"""
        환자명: {patient_name}
        예약정보: {final_data['환자정보'].get('예약일시', '정보없음')}
        연락처: {final_data['환자정보']['연락처']}
        """
        msg.attach(MIMEText(body_text, 'plain', 'utf-8'))
        
        json_str = json.dumps(final_data, indent=4, ensure_ascii=False)
        attachment = MIMEApplication(json_str.encode('utf-8'), _subtype='json')
        filename = f"{patient_name}_문진표.json"
        attachment.add_header('Content-Disposition', 'attachment', filename=filename)
        msg.attach(attachment)
        
        smtp.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        smtp.quit()
        return "SUCCESS"
    
    except smtplib.SMTPAuthenticationError:
        return "AUTH_ERROR: 아이디나 비밀번호(앱비번)가 틀렸습니다."
    except Exception as e:
        # 그 외 모든 에러를 문자열로 반환
        return f"UNKNOWN_ERROR: {str(e)}"

# ==========================================
# 3. 화면 로직
# ==========================================

# [화면 A] 동의서 페이지
if not st.session_state['agreed']:
    st.title("소유한의원 사전 문진")
    st.markdown("---")
    
    # 디버깅용 메시지 (원장님만 확인 후 삭제하세요)
    # st.caption(f"시스템 상태: {is_password_set}") 
    
    if reserved_date:
        st.info(f"📅 예약일시: {reserved_date}")
        
    st.write("원활한 진료를 위해 개인정보 수집 및 이용에 동의해 주세요.")
    
    agreement_text = """
    **[필수] 개인정보 및 민감정보 수집·이용 동의**
    
    1. **수집 목적**: 진료 예약 확인 및 사전 증상 파악
    2. **수집 항목**: 성명, 연락처, 신체정보, 건강 관련 증상(민감정보)
    3. **보유 기간**: **전송 완료 후 서버에서 즉시 삭제 (원장 이메일로 전송)**
    4. **거부 권리**: 동의를 거부할 수 있으나, 이 경우 사전 문진 이용이 제한됩니다.
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

# [화면 B] 문진표 작성 페이지
else:
    # 스타일 코드 (유지)
    custom_css = """
    <style>
        #MainMenu, header, footer {visibility: hidden; height: 0;}
        [data-testid="stToolbar"] {visibility: hidden; height: 0;}
        [data-testid="stDecoration"] {visibility: hidden; height: 0;}
        .stDeployButton {display:none;}
        
        div[data-testid="stAppViewContainer"] > .main { padding-top: 0px !important; }
        
        @media (min-width: 769px) {
            .pc-header {
                position: fixed; top: 0; left: 0; width: 100%; height: 120px;
                background-color: white; z-index: 99999; border-bottom: 1px solid #ddd;
                text-align: center; padding-top: 15px; display: block;
            }
            .block-container { padding-top: 140px !important; }
            div.stButton > button:first-child {
                position: fixed !important; top: 70px !important; left: 50% !important;
                transform: translateX(-50%) !important; z-index: 100000 !important;
                width: 400px !important;
                background-color: #ff4b4b !important; color: white !important;
                border-radius: 8px !important; box-shadow: 0 4px 6px rgba(0,0,0,0.2) !important;
            }
            .mobile-only-title { display: none !important; }
        }

        @media (max-width: 768px) {
            .pc-header { display: none !important; }
            .block-container { padding-top: 1rem !important; }
            div.stButton > button:first-child {
                width: 100% !important; background-color: #ff4b4b !important; color: white !important;
                border-radius: 8px !important; height: 50px !important;
                font-size: 18px !important; font-weight: bold !important; margin-top: 20px !important;
            }
            .mobile-only-title { display: block !important; }
            header[data-testid="stHeader"] { z-index: -1; opacity: 0; pointer-events: none; }
        }
        
        .header-title-small {font-size: 1.0rem; color: #666; margin-bottom: 0px;}
        .header-title-large {font-size: 1.8rem; font-weight: 800; color: #333; margin-top: 0px;}
    </style>

    <div class="pc-header">
        <div class="header-title-small">소유한의원</div>
        <div class="header-title-large">사전 문진표</div>
    </div>
    """
    st.markdown(custom_css, unsafe_allow_html=True)

    main_container = st.empty()

    with main_container.container():
        st.markdown(f"""
        <div class="mobile-only-title" style='text-align:center; margin-bottom: 20px;'>
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
            st.info("💡 현재 드시고 계신 약의 이름이나 처방 목적을 최대한 자세히 적어주세요.")
            med = st.text_area("입력란", height=80, key="med_input", placeholder="예: 고혈압약(아침 1알), 당뇨약, 최근 감기약 복용 중...")
            if med: medical_history["복약정보"] = med

        with st.expander("14. 현재 복용 중인 건강기능식품"):
            st.info("💡 비타민, 홍삼, 유산균 등 드시는 영양제를 모두 적어주시면 치료에 도움이 됩니다.")
            sup = st.text_area("입력란", height=80, key="sup_input", placeholder="예: 종합비타민, 오메가3, 홍삼진액...")
            if sup: medical_history["건강기능식품"] = sup

        with st.expander("15. 수술 및 기타 과거력"):
            st.info("💡 수술 이력, 입원 병력, 혹은 크게 앓았던 질환과 그 시기(몇 년 전)를 적어주세요.")
            hist = st.text_area("입력란", height=80, key="hist_input", placeholder="예: 3년 전 맹장수술, 10년 전 교통사고로 허리 입원치료...")
            if hist: medical_history["과거력"] = hist

        st.write("\n\n")
        
        # ------------------------------------------------
        # 제출 버튼
