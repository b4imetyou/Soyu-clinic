import streamlit as st
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

# ==========================================
# 1. 기본 설정 및 데이터 정의
# ==========================================
st.set_page_config(page_title="소유한의원 예진표", layout="wide")

# 비밀번호 로드
try:
    SENDER_PASSWORD = st.secrets["naver_password"]
except:
    SENDER_PASSWORD = ""

SENDER_EMAIL = "kmdchoi84@naver.com"
RECEIVER_EMAIL = "kmdchoi84@naver.com"

# 세션 상태 초기화 (단계별 진행을 위해 step 변수 사용)
# 0: 동의서 / 1: 작성가이드 / 2: 문진표작성 / 3: 제출완료
if 'step' not in st.session_state:
    st.session_state['step'] = 0

# URL 파라미터 처리
query_params = st.query_params
default_name = query_params.get("name", "")
reserved_date_raw = query_params.get("date", "")
reserved_date = reserved_date_raw.replace("_", " ").replace("+", " ")

# -------------------------------------------------------
# [데이터] 문진표 계층 구조 정의 (대분류 -> 소분류 -> 항목)
# -------------------------------------------------------
questionnaire_structure = {
    "1. 식욕 및 소화 (食慾/消化)": {
        "식후 증상 (밥 먹고 나서)": [
            "식후(1~2시간 이내) 트림, 복통, 더부룩함, 속쓰림",
            "고기나 기름진 음식 섭취 후 속 불편함",
            "스트레스를 받으면 속이 불편함"
        ],
        "공복/식전 증상 (밥 먹기 전)": [
            "공복 시 속 불편감, 신경 예민",
            "식전에 물을 먹어야 밥이 넘어감"
        ],
        "식욕 및 구역감": [
            "속이 울렁거리고 토할 것 같음 (오심/구토)",
            "입맛이 통 없어서 식사를 거름 (식욕부진)"
        ]
    },
    "2. 대변 (大便)": {
        "변의 모양과 색": [
            "대변에 밥알, 고기 덩어리, 야채 등이 보임",
            "설사처럼 무르거나 돌처럼 단단한 변",
            "회색변, 검은변, 혈변"
        ],
        "배변 감각 및 가스": [
            "대변 냄새 및 방귀 냄새가 심함",
            "잔변감이 있음",
            "식사 중 또는 식사 후에 바로 방귀나 설사가 나옴"
        ],
        "배변 습관": [
            "아침에 대변을 못 보면 하루가 힘듦"
        ]
    },
    "3. 소변 (小便)": {
        "소변의 양상": [
            "소변에 거품이 많음, 냄새가 심함"
        ],
        "배뇨 습관 및 통증": [
            "자다가 소변 때문에 깸 (야간뇨)",
            "잔뇨감, 소변을 참기 어려움 (급박뇨)",
            "소변을 보려면 한참 기다려야 함 (지연뇨), 배뇨통"
        ]
    },
    "4. 땀 및 피부 (汗/皮)": {
        "땀 (Sweat)": [
            "다른 사람들보다 땀이 많이 남",
            "땀 냄새가 심함",
            "몸에 열감은 있는데 땀은 전혀 안 남"
        ],
        "피부 (Skin)": [
            "피부가 자주 가렵다",
            "손발 껍질이 잘 벗겨짐",
            "상처 회복이 느림, 피부질환 있음, 닭살이 잘 생김"
        ]
    },
    "5. 수면 (睡眠)": {
        "잠들기/깨기": [
            "잠들기 어려움 (입면장애), 자다가 자주 깬다 (수면유지장애)",
            "꿈을 많이 꿈"
        ],
        "수면의 질": [
            "아침에 일어나기 힘듦",
            "코를 심하게 곯음"
        ]
    },
    "6. 두면 및 이비인후과 (頭面)": {
        "코/호흡기": [
            "재채기, 콧물, 코막힘, 기침, 가래, 천식",
            "환절기 알레르기성 비염"
        ],
        "머리/눈/입/귀": [
            "잦은 두통",
            "앉았다 일어날 때 어지럼증이 있다",
            "눈알이 뻑뻑하고 뻐근하게 아픔",
            "입이 쓰다 (구고)",
            "목구멍의 이물감/불편함",
            "이명 (현재 또는 피곤할 때), 탈모 진행, 잦은 구내염/헤르페스"
        ]
    },
    "7. 한열 (寒熱)": {
        "추위와 더위": [
            "갑자기 열이 오르고 땀이 남",
            "남들보다 추위를 많이 탐",
            "더웠다 추웠다 한다 (한열왕래)"
        ]
    },
    "8. 수족, 사지 및 통증 (手足/四肢)": {
        "통증의 양상": [
            "움직이면 더 아프거나 덜 아픔, 누워서 쉬면 편해짐",
            "누워서 쉬어도 불편함",
            "아침 혹은 오후에 통증이 심해짐",
            "세게 누르면 아프거나(압통) 오히려 시원함"
        ],
        "부종 및 감각": [
            "손발 혹은 관절이 잘 부음 (아침/저녁)",
            "몸이 비틀어져 있는 느낌",
            "손이나 다리에 쥐가 자주 난다",
            "손발이 찌릿거리거나 남의 살처럼 감각이 둔하다"
        ]
    },
    "9. 흉부 및 정신 (胸部)": {
        "가슴/호흡": [
            "숨 쉬는 게 불편함",
            "한숨을 자주 쉼, 조금만 걸어도 숨이 참",
            "가끔 옆구리가 결린 느낌이 있다",
            "가슴이 타는 듯한 느낌이 든다",
            "심장이 두근거리는 느낌 (심계)",
            "최근 딸꾹질을 한 적이 있음"
        ],
        "정신/기억력": [
            "사소한 일에 깜짝깜짝 잘 놀람",
            "말을 더듬거나 단어가 생각나지 않음, 건망증 심화",
            "의욕이 없고 무기력함"
        ]
    },
    "10. 기타 (其他)": {
        "전신 컨디션": [
            "최근 3개월간 3kg 이상 체중 변화",
            "아침 혹은 오후에 컨디션 변화가 있음"
        ]
    },
    "11. 남성 (男性)": {
        "남성 기능": [
            "발기 문제, 조루 (컨디션 저하 시)",
            "성관계 시 통증",
            "아침 발기 부전, 사정 후 정액 흘러나옴"
        ]
    },
    "12. 여성 (女性)": {
        "생리/임신": [
            "생리주기 불규칙",
            "심한 생리통 (진통제 복용 필요)",
            "출산 후 급격한 체중 증가"
        ],
        "기타 여성 증상": [
            "생리/배란기 증상: 가슴/겨드랑이 통증, 몸 무거움, 식욕 항진, 감정 조절 불가",
            "냉대하 이상 (양 많음, 황색, 냄새)",
            "잦은 질염, 방광염",
            "성교통, 질건조증, 불감증"
        ]
    }
}


# ==========================================
# 2. 이메일 전송 함수
# ==========================================
def send_email_with_json(final_data):
    if not SENDER_PASSWORD:
        return "NO_PASSWORD"

    try:
        smtp = smtplib.SMTP('smtp.naver.com', 587, timeout=20)
        smtp.ehlo()
        smtp.starttls()
        smtp.login(SENDER_EMAIL, SENDER_PASSWORD)

        msg = MIMEMultipart()
        patient_name = final_data['환자정보']['성함']
        msg['Subject'] = f"[소유한의원] {patient_name}님 문진표 도착"
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECEIVER_EMAIL

        # 본문 작성
        body_text = f"""
        환자명: {patient_name}
        생년월일: {final_data['환자정보'].get('생년월일', '미입력')}
        예약정보: {final_data['환자정보'].get('예약일시', '정보없음')}

        [주요 호소 증상]
        {final_data.get('주소증', '없음')}
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
# 3. 화면 UI & 로직
# ==========================================

# ----------------------------------------
# 공통 스타일 정의
# ----------------------------------------
st.markdown("""
<style>
    /* 기본 숨김 */
    header, #MainMenu, footer {visibility: hidden; height: 0;}
    [data-testid="stToolbar"] {visibility: hidden; height: 0;}
    .stDeployButton {display:none;}

    /* 헤더 스타일 */
    .pc-header {
        position: fixed; top: 0; left: 0; width: 100%; 
        height: 120px; 
        background-color: white; z-index: 1000; border-bottom: 1px solid #ddd;
        text-align: center; padding-top: 20px; display: block;
    }
    .header-title-small {font-size: 1.0rem; color: #666; margin: 0;}
    .header-title-large {font-size: 1.8rem; font-weight: 800; color: #333; margin-top: 5px;}

    /* 컨테이너 여백 */
    .block-container { padding-top: 140px !important; max-width: 800px; }

    /* 모바일 반응형 */
    @media (max-width: 768px) {
        .pc-header { display: none !important; }
        .block-container { padding-top: 2rem !important; }
    }

    /* 버튼 스타일 통일 */
    div.stButton > button {
        width: 100%;
        height: 50px;
        font-weight: bold;
        font-size: 18px;
    }

    /* 체크박스 선택 시 텍스트 인풋 강조 */
    .detail-input {
        background-color: #f0f8ff;
        padding: 10px;
        border-radius: 5px;
        margin-top: 5px;
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================================
# STEP 3: 제출 완료 화면
# ==========================================================
if st.session_state['step'] == 3:
    st.markdown("""
    <style>
        .block-container { padding-top: 50px !important; }
    </style>
    <div style="text-align: center; padding: 20px;">
        <h1 style="color: #0068c3; margin-bottom: 20px;">제출이 완료되었습니다!</h1>
        <div style="background-color: #f8f9fa; padding: 30px; border-radius: 15px; margin-bottom: 30px;">
            <p style="font-size: 18px; color: #555; line-height: 1.6;">
                작성해주신 소중한 정보를 바탕으로<br>
                정성을 담아 치료에 최선을 다해 임하겠습니다.<br>
                진료실에서 뵙겠습니다.
            </p>
        </div>
        <h4 style="color: #333;">소유한의원 원장 최아랑 올림</h4>
    </div>
    """, unsafe_allow_html=True)


# ==========================================================
# STEP 0: 개인정보 동의 화면
# ==========================================================
elif st.session_state['step'] == 0:
    # PC 헤더
    st.markdown("""
    <div class="pc-header">
        <div class="header-title-small">소유한의원</div>
        <div class="header-title-large">개인정보 동의</div>
    </div>
    """, unsafe_allow_html=True)

    # 모바일 헤더
    st.markdown(f"""
    <div style='text-align:center; margin-bottom: 20px;'>
        <h3 style='color:#333; margin:0;'>소유한의원 사전 문진</h3>
        <p style='color:#0068c3; font-weight:bold; margin-top:5px;'>📅 예약일시: {reserved_date if reserved_date else '미지정'}</p>
        <hr>
    </div>
    """, unsafe_allow_html=True)

    agreement_text = """
    **[필수] 개인정보 및 민감정보 수집·이용 동의**

    1. **수집 목적**: 진료 예약 확인 및 사전 증상 파악
    2. **수집 항목**: 성명, 생년월일, 신체정보, 건강 관련 증상
    3. **보유 기간**: **전송 완료 후 서버에서 즉시 삭제**
    4. **거부 권리**: 동의를 거부할 수 있으나, 문진 이용이 제한됩니다.
    """
    st.markdown(agreement_text)

    check = st.checkbox("위 내용을 확인하였으며, 이에 동의합니다.")
    st.write("")

    if st.button("다음 (작성 방법 안내)", type="primary"):
        if check:
            st.session_state['step'] = 1
            st.rerun()
        else:
            st.warning("동의 항목에 체크해주셔야 합니다.")


# ==========================================================
# STEP 1: 설문지 작성 방법 안내 (New!)
# ==========================================================
elif st.session_state['step'] == 1:
    # PC 헤더
    st.markdown("""
    <div class="pc-header">
        <div class="header-title-small">소유한의원</div>
        <div class="header-title-large">문진표 작성 안내</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    ### 📝 설문지 작성 방법

    보다 정확한 진단을 위해 아래 내용을 확인해 주세요.

    1. **증상 선택**: 불편하신 증상을 각 분류에서 선택해 주세요.
    2. **상세 기록**: 항목 선택 후 나타나는 입력창에 **"언제부터, 어떻게 불편한지"** 자세히 적어주시면 더 정확한 치료가 가능합니다.
    3. **기타 작성**: 선택지에 없는 내용은 각 항목의 '기타' 란에 적어주세요.

    ---

    ### 🏥 진료 프로세스 안내

    작성하신 문진표는 다음 순서로 분석되어 진료에 활용됩니다.

    1. **1차 진단**: 원장이 문진표를 바탕으로 환자분의 상태를 파악합니다.
    2. **2차 정밀 분석**: 전문 의료 AI 시스템을 통해 현재 증상을 입체적으로 분석합니다.
    3. **3차 검증 및 생성**: 원장이 직접 설계하고 학습시킨 AI 모델로 1, 2차 내용을 종합 검증하여 분석 자료를 생성합니다.
    4. **최종 진단**: 내원 후 맥진, 복진 등 상세 진찰을 통해 최종적인 치료 방향을 결정합니다.

    """, unsafe_allow_html=True)

    st.write("")
    st.write("")

    if st.button("문진표 작성 시작하기", type="primary"):
        st.session_state['step'] = 2
        st.rerun()


# ==========================================================
# STEP 2: 문진표 작성 (Main)
# ==========================================================
elif st.session_state['step'] == 2:
    # PC 헤더
    st.markdown("""
    <div class="pc-header">
        <div class="header-title-small">소유한의원</div>
        <div class="header-title-large">상세 증상 기록</div>
    </div>
    """, unsafe_allow_html=True)

    # 기본 정보 입력
    st.markdown("#### 1. 환자 기초 정보")
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("성함", value=default_name, placeholder="예: 홍길동")
        height = st.text_input("키 (cm)")
    with col2:
        birth_date_input = st.text_input("생년월일 (6자리)", placeholder="예: 841121")
        weight = st.text_input("체중 (kg)")

    st.markdown("---")
    st.markdown("#### 2. 증상 체크리스트")
    st.info("💡 각 항목을 누르면 세부 내용이 나옵니다. 해당되는 증상을 체크하고 자세한 내용을 적어주세요.")

    # 문진 데이터 수집용 딕셔너리
    collected_responses = {}

    # ----------------------------------------------------------------
    # 루프: 대분류 -> 소분류 -> 항목 -> 상세입력
    # ----------------------------------------------------------------
    for main_category, sub_structure in questionnaire_structure.items():
        with st.expander(main_category):
            category_data = {}

            # 소분류 루프
            for sub_category, items in sub_structure.items():
                st.markdown(f"**[{sub_category}]**")

                selected_items = []
                for item in items:
                    # 고유 키 생성
                    key_check = f"chk_{main_category}_{sub_category}_{item}"
                    key_text = f"txt_{main_category}_{sub_category}_{item}"

                    is_checked = st.checkbox(item, key=key_check)

                    if is_checked:
                        detail = st.text_input(
                            f"└─ '{item}'에 대해 자세히 적어주세요.",
                            placeholder="예: 3일 전부터 심해짐, 밤에 더 아픔 등",
                            key=key_text
                        )
                        selected_items.append({"증상": item, "상세내용": detail})

                if selected_items:
                    category_data[sub_category] = selected_items

                st.write("")  # 간격

            # 대분류별 기타란
            other_note = st.text_area(f"[{main_category}] 관련 기타 증상이나 메모", height=60,
                                      placeholder="위 항목에 없는 증상이 있다면 적어주세요.", key=f"other_{main_category}")
            if other_note:
                category_data["기타메모"] = other_note

            # 데이터 저장 (입력된게 있을때만)
            if category_data:
                collected_responses[main_category] = category_data

    # ----------------------------------------------------------------
    # 과거력 및 약물 (기존 유지)
    # ----------------------------------------------------------------
    st.markdown("---")
    medical_history = {}
    with st.expander("13. 복용 약물 및 과거력 (필수)"):
        c1, c2 = st.columns(2)
        with c1:
            med = st.text_area("현재 복용 중인 양약/한약", placeholder="약 이름이나 처방 목적", height=80)
            if med: medical_history["복약정보"] = med
        with c2:
            sup = st.text_area("복용 중인 건강기능식품", placeholder="비타민, 오메가3 등", height=80)
            if sup: medical_history["건강기능식품"] = sup

        hist = st.text_area("수술 이력 및 치료 중인 질병", placeholder="수술명, 시기, 현재 치료중인 지병 등", height=80)
        if hist: medical_history["과거력"] = hist

    # ----------------------------------------------------------------
    # [NEW] 주소증 (가장 치료하고 싶은 증상)
    # ----------------------------------------------------------------
    st.markdown("---")
    st.markdown("#### 🎯 가장 치료하고 싶은 증상 (중요)")
    st.markdown("여러 증상 중, **가장 힘들어서 먼저 치료하고 싶은 1~2가지**를 구체적으로 적어주세요.")
    chief_complaint = st.text_area("주소증 입력란", height=100, placeholder="예: 소화가 안 되면 머리가 아픈 게 제일 힘듭니다. / 허리 통증이 제일 급합니다.")

    st.write("\n\n")

    # ----------------------------------------------------------------
    # 제출 버튼 로직
    # ----------------------------------------------------------------
    submit_col1, submit_col2, submit_col3 = st.columns([1, 2, 1])
    with submit_col2:
        if st.button("문진표 제출하기", type="primary"):
            # 1. 필수값 검증
            cleaned_birth = birth_date_input.replace("-", "").replace(" ", "").replace(".", "")
            if len(cleaned_birth) == 8: cleaned_birth = cleaned_birth[2:]

            if not name or not cleaned_birth:
                st.warning("⚠️ 성함과 생년월일은 필수입니다.")
            elif len(cleaned_birth) != 6:
                st.warning("⚠️ 생년월일은 6자리로 입력해주세요. (예: 841121)")
            elif not collected_responses and not medical_history and not chief_complaint:
                st.warning("⚠️ 증상을 하나라도 체크하거나 적어주세요.")
            elif not chief_complaint:
                st.warning("⚠️ '가장 치료하고 싶은 증상'을 적어주셔야 정확한 진료가 가능합니다.")
            else:
                # 2. 전송 중 메시지
                st.info("🔄 AI 분석 시스템으로 데이터를 전송 중입니다... 잠시만 기다려주세요.")

                # 3. 데이터 패키징
                final_data = {
                    "환자정보": {
                        "성함": name,
                        "생년월일": cleaned_birth,
                        "신체정보": f"{height}cm / {weight}kg",
                        "예약일시": reserved_date
                    },
                    "주소증": chief_complaint,
                    "문진내용": collected_responses,
                    "과거력및약물": medical_history
                }

                # 4. 이메일 전송
                result = send_email_with_json(final_data)

                if result == "SUCCESS":
                    st.session_state['step'] = 3
                    st.rerun()
                elif result == "NO_PASSWORD":
                    st.error("🚨 서버 설정 오류: Secrets 비밀번호가 없습니다.")
                elif result == "AUTH_ERROR":
                    st.error("🚨 인증 실패: 네이버 아이디나 앱비밀번호를 확인하세요.")
                else:
                    st.error(f"🚨 전송 실패: {result}")
