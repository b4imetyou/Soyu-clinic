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
# [데이터] 문진표 구조 정의
# 1. 생활환경 추가 / 2. 한자 제거 / 3. 번호 재정렬
# -------------------------------------------------------
questionnaire_data = {
    "1. 평소 생활 및 근무 환경": {
        "생활 패턴 및 업무 환경": [
            {"code": "LIFE_01", "text": "하루 종일 앉아 있는 편이다"},
            {"code": "LIFE_02", "text": "하루 종일 서서 일한다"},
            {"code": "LIFE_03", "text": "반복적인 동작을 많이 한다"},
            {"code": "LIFE_04", "text": "눈을 많이 쓰고 집중력이 필요하다"},
            {"code": "LIFE_05", "text": "말을 많이 하는 편이다"},
            {"code": "LIFE_06", "text": "무거운 물건을 들거나 힘을 쓴다"},
            {"code": "LIFE_07", "text": "사람을 상대하며 감정 소모가 심하다"},
            {"code": "LIFE_08", "text": "야간 근무 또는 교대 근무를 한다"},
            {"code": "LIFE_09", "text": "식사 시간이 불규칙하다"},
            {"code": "LIFE_10", "text": "회식이나 술자리가 잦다"}
        ]
    },
    "2. 식욕 및 소화, 음수량": {
        "식후 반응 (밥 먹고 1~2시간 이내)": [
            {"code": "DIG_01", "text": "트림이 계속 나온다"},
            {"code": "DIG_02", "text": "배가 아프다 (복통)"},
            {"code": "DIG_03", "text": "속이 꽉 막힌 듯 더부룩하다"},
            {"code": "DIG_04", "text": "속이 쓰리다"},
            {"code": "DIG_05", "text": "신물이 올라온다"}
        ],
        "특정 음식 및 스트레스 반응": [
            {"code": "DIG_06", "text": "고기나 기름진 음식을 먹으면 불편하다"},
            {"code": "DIG_07", "text": "스트레스를 받으면 체하거나 속이 불편하다"}
        ],
        "공복/식전 증상 (밥 먹기 전)": [
            {"code": "DIG_08", "text": "공복에 속이 쓰리다"},
            {"code": "DIG_09", "text": "공복에 속이 미식거리거나 불편하다"},
            {"code": "DIG_10", "text": "배가 고프면 신경이 날카로워진다"},
            {"code": "DIG_11", "text": "식전에 물을 마셔야 밥이 넘어간다"}
        ],
        "복부의 자각 증상": [
            {"code": "DIG_12", "text": "명치 끝이 답답하다 (심하비)"},
            {"code": "DIG_13", "text": "배가 가스가 찬 듯 빵빵하다 (복만)"}
        ],
        "식욕 및 구역감": [
            {"code": "DIG_14", "text": "속이 울렁거린다 (오심)"},
            {"code": "DIG_15", "text": "토할 것 같다 (구토감)"},
            {"code": "DIG_16", "text": "입맛이 아예 없다 (식욕부진)"},
            {"code": "DIG_17", "text": "식욕을 참을 수 없다 (과식/폭식)"}
        ],
        "음수 (물 마시는 습관)": [
            {"code": "DIG_18", "text": "갈증이 심해 물을 많이 마신다"},
            {"code": "DIG_19", "text": "입은 마르는데 물은 안 마시고 싶다"},
            {"code": "DIG_20", "text": "물 대신 커피나 음료수를 주로 마신다"}
        ]
    },
    "3. 대변": {
        "변의 모양과 색 (최근 상태)": [
            {"code": "STL_01", "text": "음식물(밥알, 야채)이 그대로 보인다"},
            {"code": "STL_02", "text": "설사 혹은 물처럼 풀어진 변"},
            {"code": "STL_03", "text": "돌처럼 단단한 변 (변비 경향)"},
            {"code": "STL_04", "text": "처음엔 단단하다가 뒤에는 풀어지는 변"},
            {"code": "STL_05", "text": "색이 회색이거나 희미하다"},
            {"code": "STL_06", "text": "색이 짜장면처럼 검다"},
            {"code": "STL_07", "text": "피가 섞여 나온다 (혈변)"}
        ],
        "배변 감각 및 가스": [
            {"code": "STL_08", "text": "대변 냄새가 유독 심하다"},
            {"code": "STL_09", "text": "방귀 냄새가 지독하다"},
            {"code": "STL_10", "text": "대변을 봐도 남은 느낌이 있다 (잔변감)"},
            {"code": "STL_11", "text": "식사 도중/직후에 화장실을 가야 한다"},
            {"code": "STL_12", "text": "가스가 너무 자주 찬다"}
        ],
        "배변 습관": [
            {"code": "STL_13", "text": "아침에 대변을 못 보면 하루가 힘들다"},
            {"code": "STL_14", "text": "변이 나올 때까지 시간이 한참 걸린다"}
        ]
    },
    "4. 소변": {
        "소변의 양상": [
            {"code": "URI_01", "text": "거품이 많다"},
            {"code": "URI_02", "text": "냄새가 심하다"},
            {"code": "URI_03", "text": "색이 붉거나 아주 진하다"}
        ],
        "배뇨 습관": [
            {"code": "URI_04", "text": "자다가 소변 때문에 깬다 (야간뇨)"},
            {"code": "URI_05", "text": "소변을 보고 나서도 시원하지 않다 (잔뇨감)"},
            {"code": "URI_06", "text": "마려우면 참기 힘들다 (급박뇨)"},
            {"code": "URI_07", "text": "한참 기다려야 나온다 (지연뇨)"},
            {"code": "URI_08", "text": "소변 볼 때 아프다 (배뇨통)"}
        ]
    },
    "5. 땀 및 피부": {
        "땀 (Sweat)": [
            {"code": "SKN_01", "text": "남들보다 땀이 많다"},
            {"code": "SKN_02", "text": "땀 냄새가 심하다"},
            {"code": "SKN_03", "text": "열감은 있는데 땀은 전혀 안 난다"}
        ],
        "피부 증상": [
            {"code": "SKN_04", "text": "자주 가렵다"},
            {"code": "SKN_05", "text": "손발 껍질이 벗겨진다"},
            {"code": "SKN_06", "text": "상처가 잘 안 낫는다"},
            {"code": "SKN_07", "text": "닭살 피부다"},
            {"code": "SKN_08", "text": "각질이 자주 일어난다"},
            {"code": "SKN_09", "text": "피부 속에 단단한 덩어리가 만져진다"},
            {"code": "SKN_10", "text": "고름(농포)이 잡히는 여드름이 난다"},
            {"code": "SKN_11", "text": "블랙헤드가 심하다"}
        ]
    },
    "6. 수면": {
        "잠들기/깨기": [
            {"code": "SLP_01", "text": "자리에 누워도 잠이 안 온다 (입면장애)"},
            {"code": "SLP_02", "text": "자다가 자꾸 깬다 (수면유지장애)"},
            {"code": "SLP_03", "text": "새벽에 꼭 정해진 시간에 깬다"}
        ],
        "수면의 질": [
            {"code": "SLP_04", "text": "꿈을 많이 꾼다"},
            {"code": "SLP_05", "text": "아침에 일어나기 너무 힘들다"},
            {"code": "SLP_06", "text": "코를 심하게 곤다"},
            {"code": "SLP_07", "text": "자다가 목말라서 물을 마신다"}
        ]
    },
    "7. 두면 및 이비인후과": {
        "코/호흡기 증상": [
            {"code": "ENT_01", "text": "재채기"},
            {"code": "ENT_02", "text": "맑은 콧물"},
            {"code": "ENT_03", "text": "코막힘"},
            {"code": "ENT_04", "text": "기침"},
            {"code": "ENT_05", "text": "가래"},
            {"code": "ENT_06", "text": "천식 기운이 있다"},
            {"code": "ENT_07", "text": "환절기 비염"},
            {"code": "ENT_08", "text": "목소리가 쉰다"},
            {"code": "ENT_09", "text": "말을 오래 하면 목이 아프다"},
            {"code": "ENT_10", "text": "콧물이 목 뒤로 넘어간다 (후비루)"}
        ],
        "머리/눈/입/귀": [
            {"code": "ENT_11", "text": "두통"},
            {"code": "ENT_12", "text": "어지러움 (앉았다 일어날 때 등)"},
            {"code": "ENT_13", "text": "눈이 뻑뻑하고 아프다"},
            {"code": "ENT_14", "text": "입이 쓰다 (구고)"},
            {"code": "ENT_15", "text": "목에 뭐가 걸린 느낌 (매핵기)"},
            {"code": "ENT_16", "text": "이명 (귀에서 소리)"},
            {"code": "ENT_17", "text": "탈모"},
            {"code": "ENT_18", "text": "잦은 구내염/헤르페스"},
            {"code": "ENT_19", "text": "입술 건조/갈라짐"}
        ]
    },
    "8. 한열": {
        "더위와 열감": [
            {"code": "TMP_01", "text": "갑자기 열이 오르고 땀이 난다 (상열감)"},
            {"code": "TMP_02", "text": "더위를 남들보다 많이 탄다"},
            {"code": "TMP_03", "text": "잘 때 손발이 뜨거워 이불을 걷어찬다"},
            {"code": "TMP_04", "text": "얼굴이 자주 붉어진다"}
        ],
        "추위": [
            {"code": "TMP_05", "text": "추위를 남들보다 많이 탄다"},
            {"code": "TMP_06", "text": "손발이 차갑다"}
        ],
        "한열왕래": [
            {"code": "TMP_07", "text": "더웠다 추웠다 하는 증상이 반복된다"}
        ]
    },
    "9. 근골격계 통증": {
        "통증의 양상 (악화/완화 요인)": [
            {"code": "MSK_01", "text": "몸을 움직이면 더 아프다"},
            {"code": "MSK_02", "text": "몸을 움직이면 오히려 덜 아프다"},
            {"code": "MSK_03", "text": "누워서 쉬면 편하다"},
            {"code": "MSK_04", "text": "누워서 쉬어도 계속 불편하다"},
            {"code": "MSK_05", "text": "아침 기상 시 가장 아프다"},
            {"code": "MSK_06", "text": "오후/저녁으로 갈수록 아프다"},
            {"code": "MSK_07", "text": "누르면 더 아프다 (압통)"},
            {"code": "MSK_08", "text": "꾹 누르면 시원하다 (희안)"}
        ],
        "부종 및 감각": [
            {"code": "MSK_09", "text": "아침에 잘 붓는다 (얼굴/손)"},
            {"code": "MSK_10", "text": "저녁에 잘 붓는다 (다리)"},
            {"code": "MSK_11", "text": "몸이 비틀어진 느낌이다"},
            {"code": "MSK_12", "text": "쥐가 자주 난다"},
            {"code": "MSK_13", "text": "저림 (찌릿찌릿)"},
            {"code": "MSK_14", "text": "감각 둔화 (남의 살 느낌)"}
        ]
    },
    "10. 흉부 및 정신": {
        "가슴/호흡": [
            {"code": "CHM_01", "text": "숨 쉬는 게 불편하다"},
            {"code": "CHM_02", "text": "한숨을 자주 쉰다"},
            {"code": "CHM_03", "text": "조금만 걸어도 숨이 찬다"},
            {"code": "CHM_04", "text": "옆구리가 결린다"},
            {"code": "CHM_05", "text": "가슴이 타는 듯하다"},
            {"code": "CHM_06", "text": "심장이 두근거린다"},
            {"code": "CHM_07", "text": "딸꾹질"}
        ],
        "정신/기억력": [
            {"code": "CHM_08", "text": "잘 놀란다"},
            {"code": "CHM_09", "text": "말을 더듬거나 단어가 생각 안 난다"},
            {"code": "CHM_10", "text": "건망증"},
            {"code": "CHM_11", "text": "무기력/의욕저하"}
        ]
    },
    "11. 기타": {
        "체중": [
            {"code": "ETC_01", "text": "최근 3개월간 3kg 이상 체중 변화"}
        ]
    },
    "12. 남성": {
        "남성 기능": [
            {"code": "MEN_01", "text": "발기 부전 / 강직도 저하"},
            {"code": "MEN_02", "text": "조루 (컨디션 저하 시)"},
            {"code": "MEN_03", "text": "성관계 시 통증"},
            {"code": "MEN_04", "text": "정액이 저절로 흐름 (유정)"}
        ]
    },
    "13. 여성": {
        "생리/임신": [
            {"code": "WMN_01", "text": "생리주기 불규칙"},
            {"code": "WMN_02", "text": "심한 생리통 (진통제 필수)"},
            {"code": "WMN_03", "text": "생리양 과다"},
            {"code": "WMN_04", "text": "생리양 과소"},
            {"code": "WMN_05", "text": "출산 후 급격한 비만"},
            {"code": "WMN_06", "text": "산후풍 (출산 후 관절통 등)"}
        ],
        "기타 여성 증상": [
            {"code": "WMN_07", "text": "생리 전 가슴/겨드랑이 통증"},
            {"code": "WMN_08", "text": "생리 전 감정 조절 불가"},
            {"code": "WMN_09", "text": "냉대하 (양, 냄새, 색 이상)"},
            {"code": "WMN_10", "text": "잦은 질염"},
            {"code": "WMN_11", "text": "잦은 방광염"},
            {"code": "WMN_12", "text": "성교통"},
            {"code": "WMN_13", "text": "질건조증"}
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
        msg['Subject'] = f"[소유한의원] {patient_name}님 문진표 도착 (Ver.Final)"
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECEIVER_EMAIL

        # 본문 작성
        body_text = f"""
        환자명: {patient_name}
        생년월일: {final_data['환자정보'].get('생년월일', '미입력')}
        예약정보: {final_data['환자정보'].get('예약일시', '정보없음')}

        [주소증]
        {final_data.get('주소증', '없음')}

        * 상세 내용은 첨부된 JSON 파일을 확인하세요.
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
        width: 100%; height: 50px; font-weight: bold; font-size: 18px;
    }

    /* 체크박스 선택 시 상세 입력칸 스타일 */
    .stTextInput input {
        background-color: #f9f9f9;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================================
# STEP 3: 제출 완료 화면
# ==========================================================
if st.session_state['step'] == 3:
    st.markdown("""
    <style> .block-container { padding-top: 50px !important; } </style>
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
# STEP 1: 설문지 작성 방법 안내 (복구 완료)
# ==========================================================
elif st.session_state['step'] == 1:
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
# STEP 2: 문진표 작성 (기능 수정 완료)
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
        name = st.text_input("성함", value=default_name, placeholder="예: 홍길동")
        height = st.text_input("키 (cm)")
    with c2:
        birth = st.text_input("생년월일 (6자리)", placeholder="예: 841121")
        weight = st.text_input("체중 (kg)")

    st.markdown("---")
    st.markdown("#### 2. 증상 체크리스트")
    st.info("💡 항목을 체크하면 상세 내용을 적을 수 있는 칸이 열립니다.")

    # ----------------------------------------------------
    # 데이터 수집 (Code 기준)
    # ----------------------------------------------------
    symptoms_log = {}

    # 루프: 대분류 -> 소분류(Context Header) -> 항목리스트
    for main_cat, sub_structure in questionnaire_data.items():
        with st.expander(main_cat):
            for sub_cat, items in sub_structure.items():
                st.markdown(f"**[{sub_cat}]**")

                for item in items:
                    code = item["code"]
                    text = item["text"]

                    # 체크박스
                    is_checked = st.checkbox(text, key=f"chk_{code}")

                    if is_checked:
                        # 상세 내용 입력 (Placeholder 제거됨)
                        detail_val = st.text_input(
                            f"└─ 상세 내용 ({text})",
                            key=f"txt_{code}"
                        )
                        symptoms_log[code] = {
                            "증상명": text,
                            "상세내용": detail_val
                        }
                st.write("")  # 간격

            # 대분류 기타란
            etc_key = f"ETC_{main_cat[:2]}"
            etc_val = st.text_area(f"[{main_cat}] 관련 기타 메모", height=60, key=f"note_{main_cat}")
            if etc_val:
                symptoms_log[etc_key] = {"증상명": "기타메모", "상세내용": etc_val}

    # 3. 과거력
    st.markdown("---")
    history_log = {}
    with st.expander("14. 복용 약물 및 과거력 (필수)"):  # 순서가 밀려 14번으로 변경
        c1, c2 = st.columns(2)
        with c1:
            med = st.text_area("현재 복용 중인 양약/한약", height=80)
            if med: history_log["복약"] = med
        with c2:
            sup = st.text_area("복용 중인 건강기능식품", height=80)
            if sup: history_log["건기식"] = sup

        op = st.text_area("수술 이력 및 치료 중인 질병", height=80)
        if op: history_log["수술/지병"] = op

    # 4. 주소증
    st.markdown("---")
    st.markdown("#### 🎯 가장 치료하고 싶은 증상 (주소증)")
    st.markdown("여러 증상 중, **가장 힘들어서 먼저 치료하고 싶은 1~2가지**를 구체적으로 적어주세요.")
    chief_complaint = st.text_area("주소증 입력란", height=100)

    st.write("\n\n")

    # 5. 제출
    _, btn_col, _ = st.columns([1, 2, 1])
    with btn_col:
        if st.button("문진표 제출하기", type="primary"):
            # 검증
            clean_birth = birth.replace("-", "").replace(" ", "").strip()
            if len(clean_birth) == 8: clean_birth = clean_birth[2:]

            if not name or len(clean_birth) != 6:
                st.warning("⚠️ 성함과 생년월일(6자리)을 정확히 입력해주세요.")
            elif not chief_complaint:
                st.warning("⚠️ '가장 치료하고 싶은 증상'을 반드시 적어주세요.")
            elif not symptoms_log and not history_log:
                st.warning("⚠️ 증상을 하나라도 체크하거나 적어주세요.")
            else:
                # [복구됨] 전송 중 메시지
                st.info("🔄 AI 분석 시스템으로 데이터를 전송 중입니다... 잠시만 기다려주세요.")

                final_dataset = {
                    "meta": {
                        "version": "v3.0_final_clean",
                        "timestamp": "auto_generated"
                    },
                    "환자정보": {
                        "성함": name,
                        "생년월일": clean_birth,
                        "신체": f"{height}cm / {weight}kg",
                        "예약일시": reserved_date
                    },
                    "주소증": chief_complaint,
                    "증상데이터": symptoms_log,
                    "과거력": history_log
                }

                res = send_email_with_json(final_dataset)
                if res == "SUCCESS":
                    st.session_state['step'] = 3
                    st.rerun()
                elif res == "NO_PASSWORD":
                    st.error("🚨 서버 설정 오류: Secrets 비밀번호가 없습니다.")
                elif res == "AUTH_ERROR":
                    st.error("🚨 인증 실패: 네이버 아이디나 앱비밀번호를 확인하세요.")
                else:
                    st.error(f"🚨 전송 실패: {res}")
