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

# 세션 상태 초기화
if 'step' not in st.session_state:
    st.session_state['step'] = 0

# URL 파라미터 처리
query_params = st.query_params
default_name = query_params.get("name", "")
reserved_date_raw = query_params.get("date", "")
reserved_date = reserved_date_raw.replace("_", " ").replace("+", " ")

# -------------------------------------------------------
# [데이터] 문진표 구조 정의 (코드 매핑 적용)
# 구조: { 대분류: { 소분류: [ { "code": "ID", "text": "화면표시텍스트" }, ... ] } }
# -------------------------------------------------------
questionnaire_data = {
    "1. 식욕 및 소화, 음수량 (食慾/消化)": {
        "식후 증상 (밥 먹고 나서)": [
            {"code": "DIG_01", "text": "식후(1~2시간 이내) 트림, 복통, 더부룩함, 속쓰림"},
            {"code": "DIG_02", "text": "고기나 기름진 음식 섭취 후 속 불편함"},
            {"code": "DIG_03", "text": "스트레스를 받으면 속이 불편함"}
        ],
        "공복/식전 증상 (밥 먹기 전)": [
            {"code": "DIG_04", "text": "공복 시 속 불편감, 공복시 신경 예민"},
            {"code": "DIG_05", "text": "식전에 물을 먹어야 밥이 넘어감"}
        ],
        "소화 (복부 자각)": [
            {"code": "DIG_06", "text": "상복부가 답답한 느낌이 자주 발생함"},
            {"code": "DIG_07", "text": "자주 배가 빵빵하게 불러오는 느낌이 있음"}
        ],
        "식욕 및 구역감": [
            {"code": "DIG_08", "text": "속이 울렁거리고 토할 것 같음 (오심/구토)"},
            {"code": "DIG_09", "text": "입맛이 통 없어서 식사를 거름 (식욕부진)"},
            {"code": "DIG_10", "text": "식욕을 참을수 없음 (과식, 폭식)"}
        ],
        "음수 (마시는 물)": [
            {"code": "DIG_11", "text": "평소 갈증이 심해서 자주 물을 마심"},
            {"code": "DIG_12", "text": "입은 자주 마르지만 물은 마시지 않음"},
            {"code": "DIG_13", "text": "커피나 각종 음료를 자주 마심"}
        ]
    },
    "2. 대변 (大便)": {
        "변의 모양과 색": [
            {"code": "STL_01", "text": "대변에 밥알, 고기 덩어리, 야채 등이 보일때가 많음"},
            {"code": "STL_02", "text": "설사 혹은 풀어진 변이 자주 나타남, 돌처럼 단단한 변"},
            {"code": "STL_03", "text": "대변이 처음 나올때는 단단하다가 끝에는 풀어지는 상태"},
            {"code": "STL_04", "text": "회색변, 검은변, 혈변"}
        ],
        "배변 감각 및 가스": [
            {"code": "STL_05", "text": "대변 냄새 및 방귀 냄새가 심함"},
            {"code": "STL_06", "text": "잔변감이 있음"},
            {"code": "STL_07", "text": "식사 중 또는 식사 후에 바로 방귀나 설사가 나옴"},
            {"code": "STL_08", "text": "평소에 가스가 너무 자주 배출됨"}
        ],
        "배변 습관": [
            {"code": "STL_09", "text": "아침에 대변을 못 보면 하루가 힘듦"},
            {"code": "STL_10", "text": "배변이 나올때까지 너무 오래 걸림"}
        ]
    },
    "3. 소변 (小便)": {
        "소변의 양상": [
            {"code": "URI_01", "text": "소변에 거품이 많음, 냄새가 심함"},
            {"code": "URI_02", "text": "붉은색 소변이 나옴"}
        ],
        "배뇨 습관 및 통증": [
            {"code": "URI_03", "text": "자다가 소변 때문에 깸 (야간뇨)"},
            {"code": "URI_04", "text": "잔뇨감이 지속됨, 소변을 참기 어려움 (급박뇨)"},
            {"code": "URI_05", "text": "소변을 보려면 한참 기다려야 함 (지연뇨)"},
            {"code": "URI_06", "text": "배뇨통이 있음"}
        ]
    },
    "4. 땀 및 피부 (汗/皮)": {
        "땀 (Sweat)": [
            {"code": "SKN_01", "text": "다른 사람들보다 땀이 많이 남"},
            {"code": "SKN_02", "text": "땀 냄새가 심함"},
            {"code": "SKN_03", "text": "몸에 열감은 있는데 땀은 전혀 안 남"}
        ],
        "피부 (Skin)": [
            {"code": "SKN_04", "text": "피부가 자주 가려움"},
            {"code": "SKN_05", "text": "손발 껍질이 잘 벗겨짐"},
            {"code": "SKN_06", "text": "상처 회복이 느림, 닭살이 잘 생김"},
            {"code": "SKN_07", "text": "각질이 자주 나타남"},
            {"code": "SKN_08", "text": "진단받은 피부질환이 있음"},
            {"code": "SKN_09", "text": "피부 안쪽으로 덩어리가 잡힘"},
            {"code": "SKN_10", "text": "화농성 피부(농포)가 나타남"},
            {"code": "SKN_11", "text": "블랙헤드가 심함"}
        ]
    },
    "5. 수면 (睡眠)": {
        "잠들기/깨기": [
            {"code": "SLP_01", "text": "잠들기 어려움 (입면장애), 자다가 자주 깬다 (수면유지장애)"},
            {"code": "SLP_02", "text": "새벽에 꼭 한번씩 잠에서 깸"}
        ],
        "수면의 질": [
            {"code": "SLP_03", "text": "꿈을 많이 꿈"},
            {"code": "SLP_04", "text": "아침에 일어나기 힘듦"},
            {"code": "SLP_05", "text": "코를 심하게 곯음"},
            {"code": "SLP_06", "text": "자다가 일어나서 물을 마셔야 함"}
        ]
    },
    "6. 두면 및 이비인후과 (頭面)": {
        "코/호흡기": [
            {"code": "ENT_01", "text": "재채기, 콧물, 코막힘, 기침, 가래, 천식"},
            {"code": "ENT_02", "text": "환절기 알레르기성 비염"},
            {"code": "ENT_03", "text": "목소리가 자주 쉬거나 갈라짐"},
            {"code": "ENT_04", "text": "말을 오래 못함"},
            {"code": "ENT_05", "text": "후비루 증상이 있음"}
        ],
        "머리/눈/입/귀": [
            {"code": "ENT_06", "text": "두통이 자주 발생"},
            {"code": "ENT_07", "text": "앉았다 일어날 때 어지럼증이 있음"},
            {"code": "ENT_08", "text": "눈알이 뻑뻑하고 뻐근하게 아픔"},
            {"code": "ENT_09", "text": "입에서 자주 쓴맛이 남 (구고)"},
            {"code": "ENT_10", "text": "목구멍의 이물감/불편함이 있음"},
            {"code": "ENT_11", "text": "이명, 탈모 진행, 잦은 구내염/헤르페스"},
            {"code": "ENT_12", "text": "입술이 자주 갈라짐"}
        ]
    },
    "7. 한열 (寒熱)": {
        "더위": [
            {"code": "TMP_01", "text": "갑자기 열이 오르고 땀이 남"},
            {"code": "TMP_02", "text": "몸이 뜨겁고 더위를 많이 탐"},
            {"code": "TMP_03", "text": "수면 시 손발이 화끈거림"},
            {"code": "TMP_04", "text": "안면부 홍조가 자주 나타남"}
        ],
        "추위": [
            {"code": "TMP_05", "text": "남들보다 추위를 많이 탐"},
            {"code": "TMP_06", "text": "손이 차가움, 발이 차가움, 손발이 차가움"}
        ],
        "한열왕래": [
            {"code": "TMP_07", "text": "더웠다 추웠다 하는 증상이 있음"}
        ]
    },
    "8. 근골격계 증상 및 통증 (筋骨/痛症)": {
        "통증의 양상": [
            {"code": "MSK_01", "text": "움직이면 더 아픔, 움직이면 덜 아픔, 누워서 쉬면 편해짐"},
            {"code": "MSK_02", "text": "누워서 쉬어도 불편함"},
            {"code": "MSK_03", "text": "아침에 통증이 심해짐, 오후에 통증이 심해짐"},
            {"code": "MSK_04", "text": "통증부위를 누르면 아픔, 통증부위를 누르면 시원함"}
        ],
        "부종 및 감각": [
            {"code": "MSK_05", "text": "아침에 손발 혹은 관절이 부음, 저녁에 손발 혹은 관절이 부음"},
            {"code": "MSK_06", "text": "몸이 비틀어져 있는 느낌"},
            {"code": "MSK_07", "text": "손이나 다리에 쥐가 자주 난다"},
            {"code": "MSK_08", "text": "손발이 찌릿거리거나 남의 살처럼 감각이 둔하다"}
        ]
    },
    "9. 흉부 및 정신 (胸部/精神)": {
        "가슴/호흡": [
            {"code": "CHM_01", "text": "숨 쉬는 게 불편함"},
            {"code": "CHM_02", "text": "한숨을 자주 쉼, 조금만 걸어도 숨이 참"},
            {"code": "CHM_03", "text": "가끔 옆구리가 결린 느낌이 있다"},
            {"code": "CHM_04", "text": "가슴이 타는 듯한 느낌이 든다"},
            {"code": "CHM_05", "text": "심장이 두근거리는 느낌 (심계)"},
            {"code": "CHM_06", "text": "딸꾹질을 자주 하는 편"}
        ],
        "정신/기억력": [
            {"code": "CHM_07", "text": "사소한 일에 깜짝깜짝 잘 놀람"},
            {"code": "CHM_08", "text": "말을 더듬거나 단어가 생각나지 않음, 건망증이 심함"},
            {"code": "CHM_09", "text": "의욕이 없고 무기력함"}
        ]
    },
    "10. 기타 (其他)": {
        "체중": [
            {"code": "ETC_01", "text": "최근 3개월간 3kg 이상 체중 변화가 있음"}
        ]
    },
    "11. 남성 (男性)": {
        "남성 기능": [
            {"code": "MEN_01", "text": "발기 문제가 있음, 컨디션 저하 시 조루"},
            {"code": "MEN_02", "text": "성관계 시 통증이 있음"},
            {"code": "MEN_03", "text": "사정 후 정액이 계속 흘러나옴"}
        ]
    },
    "12. 여성 (女性)": {
        "생리/임신": [
            {"code": "WMN_01", "text": "생리주기 불규칙"},
            {"code": "WMN_02", "text": "심한 생리통 (진통제 복용 필요)"},
            {"code": "WMN_03", "text": "생리양이 너무 많음, 생리양이 너무 적음"},
            {"code": "WMN_04", "text": "출산 후 급격한 체중 증가"},
            {"code": "WMN_05", "text": "출산 후 자주 아픔"}
        ],
        "기타 여성 증상": [
            {"code": "WMN_06", "text": "생리/배란기 증상: 통증, 몸 무거움, 식욕항진, 감정조절 불가 등"},
            {"code": "WMN_07", "text": "냉이 많음, 냄새가 심함, 색이 이상함"},
            {"code": "WMN_08", "text": "질염이 자주 발생, 방광염이 자주 발생"},
            {"code": "WMN_09", "text": "성교통이 있음, 질건조증이 있음, 불감증이 있음"}
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
        msg['Subject'] = f"[소유한의원] {patient_name}님 문진표 도착 (Code Ver.)"
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECEIVER_EMAIL

        # 본문 작성
        body_text = f"""
        환자명: {patient_name}
        생년월일: {final_data['환자정보'].get('생년월일', '미입력')}
        예약정보: {final_data['환자정보'].get('예약일시', '정보없음')}

        [주소증]
        {final_data.get('주소증', '없음')}

        * 상세 증상 데이터는 첨부된 JSON 파일을 확인하세요.
        * 각 항목은 고유 코드(ID)로 기록되어 있습니다.
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
    header, #MainMenu, footer {visibility: hidden; height: 0;}
    [data-testid="stToolbar"] {visibility: hidden; height: 0;}
    .stDeployButton {display:none;}
    .pc-header {
        position: fixed; top: 0; left: 0; width: 100%; 
        height: 120px; 
        background-color: white; z-index: 1000; border-bottom: 1px solid #ddd;
        text-align: center; padding-top: 20px; display: block;
    }
    .header-title-small {font-size: 1.0rem; color: #666; margin: 0;}
    .header-title-large {font-size: 1.8rem; font-weight: 800; color: #333; margin-top: 5px;}
    .block-container { padding-top: 140px !important; max-width: 800px; }
    @media (max-width: 768px) {
        .pc-header { display: none !important; }
        .block-container { padding-top: 2rem !important; }
    }
    div.stButton > button {
        width: 100%; height: 50px; font-weight: bold; font-size: 18px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================================
# STEP 3: 제출 완료
# ==========================================================
if st.session_state['step'] == 3:
    st.markdown("""
    <style> .block-container { padding-top: 50px !important; } </style>
    <div style="text-align: center; padding: 20px;">
        <h1 style="color: #0068c3;">제출이 완료되었습니다!</h1>
        <div style="background-color: #f8f9fa; padding: 30px; border-radius: 15px; margin: 30px 0;">
            <p style="font-size: 18px; color: #555;">
                작성해주신 소중한 정보를 바탕으로<br>
                최선을 다해 진료하겠습니다.
            </p>
        </div>
        <h4 style="color: #333;">소유한의원 원장 최아랑 올림</h4>
    </div>
    """, unsafe_allow_html=True)

# ==========================================================
# STEP 0: 동의
# ==========================================================
elif st.session_state['step'] == 0:
    st.markdown("""
    <div class="pc-header">
        <div class="header-title-small">소유한의원</div>
        <div class="header-title-large">개인정보 동의</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style='text-align:center; margin-bottom: 20px;'>
        <h3 style='color:#333; margin:0;'>소유한의원 사전 문진</h3>
        <p style='color:#0068c3; font-weight:bold; margin-top:5px;'>📅 예약일시: {reserved_date if reserved_date else '미지정'}</p>
        <hr>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    **[필수] 개인정보 및 민감정보 수집·이용 동의**
    1. **수집 목적**: 진료 예약 확인 및 사전 증상 분석
    2. **보유 기간**: **전송 완료 후 서버에서 즉시 삭제**
    """)

    if st.checkbox("위 내용을 확인하였으며, 이에 동의합니다."):
        if st.button("다음 (작성 방법 안내)", type="primary"):
            st.session_state['step'] = 1
            st.rerun()

# ==========================================================
# STEP 1: 안내
# ==========================================================
elif st.session_state['step'] == 1:
    st.markdown("""
    <div class="pc-header">
        <div class="header-title-small">소유한의원</div>
        <div class="header-title-large">문진표 작성 안내</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    ### 📝 작성 방법
    1. **증상 선택**: 해당되는 항목을 체크해 주세요.
    2. **상세 기록**: 체크 후 나타나는 입력창에 **구체적인 증상(언제부터, 통증 양상 등)**을 적어주세요.
    3. **데이터 분석**: 작성된 내용은 암호화된 코드(Code)로 변환되어 AI 분석 시스템에 전달됩니다.
    """)

    st.write("")
    if st.button("문진표 작성 시작하기", type="primary"):
        st.session_state['step'] = 2
        st.rerun()

# ==========================================================
# STEP 2: 문진표 작성
# ==========================================================
elif st.session_state['step'] == 2:
    st.markdown("""
    <div class="pc-header">
        <div class="header-title-small">소유한의원</div>
        <div class="header-title-large">상세 증상 기록</div>
    </div>
    """, unsafe_allow_html=True)

    # 1. 기초 정보
    st.markdown("#### 1. 환자 기초 정보")
    c1, c2 = st.columns(2)
    with c1:
        name = st.text_input("성함", value=default_name)
        height = st.text_input("키 (cm)")
    with c2:
        birth = st.text_input("생년월일 (6자리)", placeholder="예: 841121")
        weight = st.text_input("체중 (kg)")

    st.markdown("---")
    st.markdown("#### 2. 증상 체크리스트")
    st.info("💡 항목을 체크하면 상세 내용을 적을 수 있는 칸이 열립니다.")

    # ----------------------------------------------------
    # 데이터 수집용 딕셔너리 (Code 기준 저장)
    # ----------------------------------------------------
    symptoms_log = {}  # {"CODE_01": {"text": "...", "detail": "..."}, ...}

    # 루프: 대분류 -> 소분류 -> 항목리스트(딕셔너리)
    for main_cat, sub_structure in questionnaire_data.items():
        with st.expander(main_cat):
            for sub_cat, items in sub_structure.items():
                st.markdown(f"**[{sub_cat}]**")

                for item in items:
                    code = item["code"]
                    text = item["text"]

                    # 체크박스 (Key는 코드로 유니크하게)
                    is_checked = st.checkbox(text, key=f"chk_{code}")

                    if is_checked:
                        # 상세 내용 입력
                        detail_val = st.text_input(
                            f"└─ 상세 내용 ({text})",                            
                            key=f"txt_{code}"
                        )
                        # 데이터 저장 (코드 기준)
                        symptoms_log[code] = {
                            "증상명": text,  # 나중에 확인용 (Optional)
                            "상세내용": detail_val
                        }
                st.write("")  # 소분류 간 간격

            # 대분류 기타
            etc_key = f"ETC_{main_cat[:2]}"
            etc_val = st.text_area(f"[{main_cat}] 관련 기타 메모", height=60, key=f"note_{main_cat}")
            if etc_val:
                symptoms_log[etc_key] = {"증상명": "기타메모", "상세내용": etc_val}

    # 3. 과거력
    st.markdown("---")
    history_log = {}
    with st.expander("13. 복용 약물 및 과거력 (필수)"):
        c1, c2 = st.columns(2)
        with c1:
            med = st.text_area("복용 중인 양약/한약", height=80)
            if med: history_log["복약"] = med
        with c2:
            sup = st.text_area("건강기능식품", height=80)
            if sup: history_log["건기식"] = sup

        op = st.text_area("수술 이력 및 치료 중인 질병", height=80)
        if op: history_log["수술/지병"] = op

    # 4. 주소증
    st.markdown("---")
    st.markdown("#### 🎯 가장 치료하고 싶은 증상 (주소증)")
    chief_complaint = st.text_area("가장 힘든 증상 1~2가지를 적어주세요.", height=100)

    st.write("\n")

    # 5. 제출
    _, btn_col, _ = st.columns([1, 2, 1])
    with btn_col:
        if st.button("문진표 제출하기", type="primary"):
            # 검증
            clean_birth = birth.replace("-", "").strip()
            if len(clean_birth) == 8: clean_birth = clean_birth[2:]

            if not name or len(clean_birth) != 6:
                st.warning("⚠️ 성함과 생년월일(6자리)을 정확히 입력해주세요.")
            elif not chief_complaint:
                st.warning("⚠️ '가장 치료하고 싶은 증상'을 반드시 적어주세요.")
            elif not symptoms_log and not history_log:
                st.warning("⚠️ 증상을 하나라도 체크해 주세요.")
            else:
                st.info("데이터 처리 중입니다...")

                # 최종 데이터 패키징 (JSON 구조 최적화)
                final_dataset = {
                    "meta": {
                        "version": "v2.0_code_based",
                        "timestamp": "auto_generated"
                    },
                    "환자정보": {
                        "성함": name,
                        "생년월일": clean_birth,
                        "신체": f"{height}cm / {weight}kg",
                        "예약일시": reserved_date
                    },
                    "주소증": chief_complaint,
                    "증상데이터": symptoms_log,  # { "DIG_01": { ... }, "STL_03": { ... } }
                    "과거력": history_log
                }

                res = send_email_with_json(final_dataset)
                if res == "SUCCESS":
                    st.session_state['step'] = 3
                    st.rerun()
                else:
                    st.error(f"전송 실패: {res}")
