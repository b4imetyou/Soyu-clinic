import streamlit as st
import json
import smtplib
import time  # 딜레이 효과용
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

# ==========================================
# 1. 설정 및 URL 정보 가져오기
# ==========================================
# 실제 배포 시엔 st.secrets 사용 권장
try:
    SENDER_PASSWORD = st.secrets["naver_password"]
except:
    SENDER_PASSWORD = "" # 로컬 테스트용

SENDER_EMAIL = "kmdchoi84@naver.com"
RECEIVER_EMAIL = "kmdchoi84@naver.com"

st.set_page_config(page_title="소유한의원 문진표", layout="wide")

# URL에서 파라미터 읽어오기 (없으면 빈칸)
query_params = st.query_params
default_name = query_params.get("name", "")
default_phone = query_params.get("phone", "")
reserved_date = query_params.get("date", "") # 예약 날짜 정보

# ==========================================
# 2. CSS 스타일 (PC/모바일 분리 + 로고 삭제)
# ==========================================
custom_css = """
<style>
    /* 1. 스트림릿 기본 UI 요소 싹 숨기기 (메뉴, 푸터, 헤더, 깃허브 아이콘 등) */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    [data-testid="stToolbar"] {visibility: hidden; height: 0%;}
    [data-testid="stDecoration"] {visibility: hidden;}
    .stDeployButton {display:none;}
    
    /* 우측 하단 뷰어 배지(왕관/해골) 숨기기 시도 */
    .viewerBadge_container__1QSob {display: none !important;}
    
    /* 2. PC 버전 스타일 (화면 너비 769px 이상) */
    @media (min-width: 769px) {
        /* 상단 고정 헤더 보이기 */
        .pc-header {
            position: fixed; top: 0; left: 0; width: 100%; height: 120px;
            background-color: white; z-index: 9998; border-bottom: 1px solid #ddd;
            text-align: center; padding-top: 15px;
            display: block;
        }
        /* 본문 상단 여백 (헤더 가림 방지) */
        .block-container {
            padding-top: 140px !important;
        }
        /* 버튼을 상단으로 강제 이동 */
        div.stButton > button:first-child {
            position: fixed !important; 
            top: 70px !important; 
            left: 50% !important;
            transform: translateX(-50%) !important; 
            z-index: 9999 !important;
            width: 400px !important;
            background-color: #ff4b4b !important; color: white !important;
            border-radius: 8px !important;
            box-shadow: 0 4px 6px rgba(0,0,0,0.2) !important;
        }
    }

    /* 3. 모바일 버전 스타일 (화면 너비 768px 이하) */
    @media (max-width: 768px) {
        /* 상단 고정 헤더 숨기기 */
        .pc-header { display: none; }
        
        /* 본문 상단 여백 정상화 */
        .block-container {
            padding-top: 2rem !important;
        }
        /* 버튼을 원래 위치(맨 아래)로, 디자인만 예쁘게 */
        div.stButton > button:first-child {
            width: 100% !important;
            background-color: #ff4b4b !important; color: white !important;
            border-radius: 8px !important;
            height: 50px !important;
            font-size: 18px !important;
            font-weight: bold !important;
            margin-top: 20px !important;
        }
    }
    
    /* 공통 폰트 스타일 */
    .header-title-small {font-size: 1.0rem; color: #666; margin-bottom: 0px;}
    .header-title-large {font-size: 1.8rem; font-weight: 800; color: #333; margin-top: 0px;}
</style>

<div class="pc-header">
    <div class="header-title-small">소유한의원</div>
    <div class="header-title-large">사전 문진표</div>
</div>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# ==========================================
# 3. 함수 정의
# ==========================================
def send_email_with_json(final_data):
    try:
        smtp = smtplib.SMTP('smtp.naver.com', 587)
        smtp.ehlo()
        smtp.starttls()
        smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
        
        msg = MIMEMultipart()
        patient_name = final_data['환자정보']['성함']
        
        msg['Subject'] = f"[소유한의원] {patient_name}님 문진표 도착"
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECEIVER_EMAIL
        
        # 메일 본문
        job_env = final_data['기초정보'].get('생활환경', [])
        job_env_str = ", ".join(job_env) if job_env else "선택 없음"
        
        body_text = f"""
        환자명: {patient_name}
        예약정보: {final_data['환자정보'].get('예약일시', '정보없음')}
        연락처: {final_data['환자정보']['연락처']}
        
        [기초 정보]
        - 신체: {final_data['기초정보'].get('신체정보', '미입력')}
        - 환경: {job_env_str}
        
        *상세 문진 내용은 첨부된 JSON 파일을 확인하세요.
        """
        msg.attach(MIMEText(body_text, 'plain', 'utf-8'))
        
        json_str = json.dumps(final_data, indent=4, ensure_ascii=False)
        attachment = MIMEApplication(json_str.encode('utf-8'), _subtype='json')
        filename = f"{patient_name}_문진표.json"
        attachment.add_header('Content-Disposition', 'attachment', filename=filename)
        msg.attach(attachment)
        
        smtp.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        smtp.quit()
        return True
    except Exception as e:
        return False

# ==========================================
# 4. 화면 구성 (컨테이너 사용으로 화면 전환 효과)
# ==========================================

# 메인 화면을 담을 그릇 (나중에 싹 지우기 위해 사용)
main_container = st.empty()

# 문진표 작성 화면이 들어갈 컨테이너
with main_container.container():
    # 모바일용 타이틀 (PC에선 헤더가 있으니 작게, 모바일에선 크게)
    st.markdown("<h3 style='text-align:center; color:#333;'>소유한의원 사전 문진표</h3>", unsafe_allow_html=True)
    if reserved_date:
        st.markdown(f"<p style='text-align:center; color:#0068c3; font-weight:bold;'>📅 예약일시: {reserved_date}</p>", unsafe_allow_html=True)
    st.markdown("---")

    # ------------------------------------------------
    # 입력 폼 시작
    # ------------------------------------------------
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("성함", value=default_name, placeholder="예: 홍길동")
    with col2:
        phone = st.text_input("연락처", value=default_phone, placeholder="예: 010-0000-0000")

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
        "2. 식욕 및 소화": ["식후 더부룩함/속쓰림/트림", "공복 시 속 불편감", "스트레스 받으면 체함", "기름진 음식 소화불량", "물 없이 밥 못 먹음"],
        "3. 대변": ["변비/설사 반복", "대변이 가늘거나 무름", "잔변감", "변 냄새/방귀 냄새 심함", "식후 바로 화장실"],
        "4. 소변": ["거품뇨/냄새", "야간뇨(자다 깸)", "급박뇨(못 참음)", "잔뇨감/배뇨통"],
        "5. 수면": ["입면장애(잠들기 힘듦)", "수면유지장애(자주 깸)", "다몽(꿈 많음)", "기상 후 피로"],
        "6. 한열/땀": ["추위를 많이 탐", "더위를 많이 탐", "식은땀/잘 때 땀", "상체로 열이 오름"],
        "7. 통증/관절": ["날씨 흐리면 아픔", "조조강직(아침에 뻣뻣)", "손발 저림/시림", "어깨/허리 만성 통증"],
        "8. 두면/호흡": ["두통/어지러움", "비염/코막힘", "가슴 답답함/두근거림", "숨참/한숨"],
        "9. 여성/남성": ["생리통/생리불순", "냉대하", "갱년기 증상", "전립선/성기능 저하"]
    }
    # (원장님 기존 데이터로 내용 채우시면 됩니다. 예시로 줄였습니다.)
    
    user_responses = {}
    for category, items in questionnaire_data.items():
        with st.expander(category):
            selected = []
            for item in items:
                if st.checkbox(item, key=f"{category}_{item}"): selected.append(item)
            other = st.text_input(f"기타 증상", key=f"other_{category}")
            if selected or other: user_responses[category] = {"선택증상": selected, "기타메모": other}

    # 3. 상세 정보
    medical_history = {}
    with st.expander("10. 상세 정보 (복약/수술)", expanded=True):
        med = st.text_area("복용 중인 약/건강기능식품", placeholder="고혈압약, 비타민 등")
        hist = st.text_area("수술 이력 및 과거 병력", placeholder="3년 전 맹장수술 등")
        if med: medical_history["복약정보"] = med
        if hist: medical_history["과거력"] = hist

    st.write("\n\n")
    
    # ------------------------------------------------
    # 제출 버튼 로직 (진행 바 + 화면 전환)
    # ------------------------------------------------
    if st.button("문진표 제출하기"):
        # 1. 유효성 검사
        if not name or not phone:
            st.warning("⚠️ 성함과 연락처는 필수입니다.")
        elif not (user_responses or basic_info_data.get('생활환경') or medical_history):
            st.warning("⚠️ 증상이나 정보를 하나라도 입력해주세요.")
        else:
            # 2. 화면 비우기 (메인 컨테이너 비움)
            main_container.empty()
            
            # 3. 진행 상태 보여주기 (3단계)
            progress_text = st.empty()
            my_bar = st.progress(0)
            
            # 단계 1
            progress_text.markdown("#### 📝 작성하신 내용을 정리하고 있습니다... (1/3)")
            my_bar.progress(33)
            time.sleep(1) # 연출용 딜레이
            
            # 단계 2
            progress_text.markdown("#### 🔄 AI 분석을 위해 데이터를 변환 중입니다... (2/3)")
            my_bar.progress(66)
            time.sleep(1)
            
            # 단계 3
            progress_text.markdown("#### 🚀 소유한의원 원장님께 전송 중입니다... (3/3)")
            
            # 실제 메일 전송
            final_data = {
                "환자정보": {"성함": name, "연락처": phone, "예약일시": reserved_date},
                "기초정보": basic_info_data,
                "문진내용": user_responses,
                "상세정보": medical_history
            }
            
            if send_email_with_json(final_data):
                my_bar.progress(100)
                time.sleep(0.5)
                
                # 4. 최종 완료 화면 (모든 것 삭제 후 메시지 출력)
                progress_text.empty()
                my_bar.empty()
                
                # 완료 메시지 UI
                st.markdown(f"""
                <div style="text-align: center; padding: 50px 20px;">
                    <h1 style="color: #0068c3;">제출이 완료되었습니다!</h1>
                    <br>
                    <h3>{name} 님, <br>{reserved_date if reserved_date else ""} 진료 예약이 확인되었습니다.</h3>
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
            else:
                st.error("전송에 실패했습니다. 잠시 후 다시 시도해주세요.")
