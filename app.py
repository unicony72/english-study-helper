import streamlit as st
import streamlit.components.v1 as components
import google.generativeai as genai
import json
import os
import re
from datetime import datetime

# --- Page Config ---
st.set_page_config(
    page_title="🦄 워니비니 영어 도우미",
    page_icon="📚",
    layout="wide"
)

# --- Functions ---
def save_to_history(data, topic):
    if not os.path.exists('history'):
        os.makedirs('history')
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_topic = re.sub(r'[^a-zA-Z0-9가-힣]', '_', topic)
    filename = f"history/{timestamp}_{safe_topic}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    return filename

def load_from_history(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_history_files():
    if not os.path.exists('history'):
        return []
    files = [f for f in os.listdir('history') if f.endswith('.json')]
    files.sort(reverse=True) # Newest first
    return files

def delete_history_file(filename):
    if os.path.exists(filename):
        os.remove(filename)

def generate_problem_set(api_key, school_level, grade, topic, difficulty_level, question_type):
    # Configure Gemini API
    genai.configure(api_key=api_key)
    
    # Using 'gemini-2.5-flash' as it is the current standard available model.
    model_name = 'gemini-2.5-flash' 
    model = genai.GenerativeModel(model_name, generation_config={"response_mime_type": "application/json"})
    
    difficulty_guide = ""
    if school_level == "중학교":
        if grade == "1학년":
            difficulty_guide = "Middle School Grade 1 Level. Length: 120-150 words. Vocab: ~800 words. Basic sentence structures."
        elif grade == "2학년":
            difficulty_guide = "Middle School Grade 2 Level. Length: 150-200 words. Vocab: ~1000 words. Comparison, Infinitives."
        else: # 3학년
            difficulty_guide = "Middle School Grade 3 Level. Length: 200-250 words. Vocab: ~1250 words. Pre-High School difficulty. Relative clauses, passive voice."
    else: # 고등학교
        if grade == "1학년":
            difficulty_guide = "High School Grade 1 Level. Length: 250-350 words. Vocab: ~1800 words. Mock Exam standard. Complex sentence structures."
        elif grade == "2학년":
            difficulty_guide = "High School Grade 2 Level. Length: 300-400 words. Vocab: ~2500 words. Abstract topics, Participial constructions."
        else: # 3학년
            difficulty_guide = "CSAT (SuNeung) Level. Length: 350-500 words. Vocab: 5000-8000 words level. Highly abstract, academic topics. Complex syntax. Vocabulary based on EBS SuNeung Teukgang."

    # Logic to adjust prompt based on CSAT Question Type
    question_count_req = "5"
    type_instruction = ""
    
    if "종합" in question_type:
        question_count_req = "5"
        type_instruction = """
        - Create exactly 5 multiple-choice questions (5 options each) with VARIED formats (Avoid too many blanks):
          - Q1: Main Idea/Title (Subject/Title).
          - Q2: Detail/Content Match (Correct/Incorrect statement).
          - Q3: Grammar (Error Finding). **Highlight 5 parts in the passage as (1)~(5)**. The options MUST include the highlighted word (e.g., "(1) live").
          - Q4: Vocabulary Appropriateness. **Highlight 5 words in the passage as (a)~(e)**. The options MUST include the highlighted word (e.g., "(a) happy").
          - Q5: Blank Inference. **Insert exactly ONE blank (_______)** in the passage. The question text should be simple (e.g., "다음 빈칸에 들어갈 말로 가장 적절한 것은?") WITHOUT quoting the sentence again.
        """
    elif "41-42" in question_type:
        question_count_req = "2"
        type_instruction = f"""
        - Create exactly 2 multiple-choice questions (Standard CSAT Q41-42 Format):
          - Q1: Title Inference (제목 추론)
          - Q2: Vocabulary appropriateness in context (문맥상 낱말의 쓰임) - **Mark target words as (a), (b), (c), (d), (e) in the passage.**
        - Passage Length: 500-600 words (Long Passage).
        """
    elif "43-45" in question_type:
        question_count_req = "3"
        type_instruction = f"""
        - Create exactly 3 multiple-choice questions (Standard CSAT Q43-45 Format):
          - Passage Structure: Divide the story into (A), (B), (C), (D) paragraphs.
          - Q1: Order of paragraphs (B-D) following (A).
          - Q2: Pointing Inference (Targeting pronouns a,b,c,d,e) - **Mark pronouns clearly in the text.**
          - Q3: Content Match/Mismatch (내용 일치/불일치).
        - Passage Style: Narrative/Storytelling.
        """
    else:
        # Single Question Types (18-40)
        question_count_req = "1"
        type_instruction = f"""
        - **PRIMARY GOAL**: Create exactly 1 multiple-choice question modeled after **{question_type}**.
        - **Passage Style**: Must perfectly suit the chosen type (e.g., for '빈칸추론', use high abstraction and logical gaps; for '심경', use descriptive/narrative tone).
        - **Question**:
          - Create ONE perfect replica of the {question_type}.
          - **CRITICAL**: If the question type involves a blank ( 빈칸 ), you MUST insert the '_______' marker directly into the passage text.
          - **CRITICAL - Standard Formatting**:
            - **Grammar (어법)**: Mark targets in the passage as **(1) word**, **(2) word**, etc. (Number before word).
            - **Vocabulary (어휘)**: Mark targets in the passage as **(a) word**, **(b) word**, etc. (Letter before word).
        """
        # Override difficulty for specific types
        if "빈칸" in question_type or "순서" in question_type or "삽입" in question_type or "함축" in question_type:
             difficulty_level += " (Upgrade to HARD/KILLER due to Question Type)"

    prompt = f"""
    You are an expert English teacher for Korean students, specialized in creating content for the Korean CSAT (Sooneung) and Mock Exams.
    Create a reading passage and QUESTIONS based on the following STRICT criteria:
    
    - **Topic**: {topic}
    - **Target Audience**: Korean {school_level} student, {grade}
    - **Base Difficulty Standard**: {difficulty_guide}
    - **Selected Question Type**: {question_type}
    - **Specific Difficulty Adjustment**: {difficulty_level} (within the grade level)
    
    **Requirements**:
    1. Write an English reading passage that perfectly matches the requested difficulty and style.
    2. **Question Structure**:
       {type_instruction}
    3. **CRITICAL - Handling Blanks/Context**:
       - If a question asks to fill in a blank (Usage/Expression/Blank Inference), and the blank is NOT in the main passage, **you MUST include the specific sentence with the '_______' marker inside the 'question' field.**
    4. Provide the correct answer and a detailed explanation in Korean for each question.
    5. Extract 5-10 difficult vocabulary words or idioms from the passage and provide their Korean meanings.
    
    **Output Format**:
    Return ONLY a valid JSON object with the following structure:
    {{
        "title": "Passage Title",
        "passage": "Full text...",
        "questions": [
            {{
                "type": "Type Name",
                "question": "Question Text...",
                "options": ["1. A", "2. B", "3. C", "4. D", "5. E"],
                "answer": "3",
                "explanation": "..."
            }}
        ],
        "vocabulary": [
            {{ "word": "example word", "meaning": "예시 단어 뜻" }},
            {{ "word": "idiom", "meaning": "숙어 뜻" }}
        ]
    }}
    """

    try:
        response = model.generate_content(prompt)
        text_response = response.text
        
        # Clean up JSON string (Remove Markdown code blocks if present)
        if "```json" in text_response:
            text_response = text_response.split("```json")[1].split("```")[0]
        elif "```" in text_response:
            text_response = text_response.split("```")[1].split("```")[0]
            
        # Remove trailing commas which cause JSON errors
        text_response = re.sub(r',\s*]', ']', text_response)
        text_response = re.sub(r',\s*}', '}', text_response)
        
        return json.loads(text_response)
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg:
            try:
                available_models = []
                for m in genai.list_models():
                    if 'generateContent' in m.supported_generation_methods:
                        available_models.append(m.name)
                return {"error": f"지정한 모델을 찾을 수 없습니다. (404 Error)\n\n현재 사용 가능한 모델 목록:\n{', '.join(available_models)}\n\n상세 에러: {error_msg}"}
            except Exception as list_e:
                return {"error": f"모델을 찾을 수 없으며, 목록 조회도 실패했습니다.\n{error_msg}"}
        return {"error": str(e)}

# --- Constants ---
TOPICS = [
    "환경 문제 (Environmental Issues)",
    "과학 기술 (Science & Technology)",
    "인공지능과 윤리 (AI & Ethics)",
    "문화적 다양성 (Cultural Diversity)",
    "역사와 전통 (History & Tradition)",
    "경제와 소비 (Economy & Consumption)",
    "심리학과 인간 행동 (Psychology & Human Behavior)",
    "예술과 문학 (Art & Literature)",
    "진로와 직업 (Career & Jobs)",
    "건강과 운동 (Health & Exercise)"
]

# --- Session State Initialization ---
if 'generated_content' not in st.session_state:
    st.session_state.generated_content = None
if 'graded' not in st.session_state:
    st.session_state.graded = False
if 'is_generating' not in st.session_state:
    st.session_state.is_generating = False

def start_generation():
    st.session_state.is_generating = True

def stop_generation():
    st.session_state.is_generating = False

# --- Main Content ---
st.markdown("### 🦄 워니비니 영어 도우미")

# --- Tabs: Settings & History ---
tab1, tab2 = st.tabs(["⚙️ 문제 생성 (Generator)", "📂 히스토리 (History)"])

# --- Tab 1: Settings & Generator ---
with tab1:
    # Disable inputs while generating
    input_disabled = st.session_state.is_generating

    with st.expander("⚙️ 설정 및 주제 선택 (Settings)", expanded=True):
        # Try to load API Key from secrets.toml first
        if "GEMINI_API_KEY" in st.secrets:
            api_key = st.secrets["GEMINI_API_KEY"]
        else:
            api_key = st.text_input("Google Gemini API Key를 입력하세요", type="password", disabled=input_disabled)
            st.caption("매번 입력하기 귀찮다면 `.streamlit/secrets.toml` 파일에 키를 저장하세요.")
        
        # Layout: 3 Columns for School, Grade, Difficulty
        col1, col2, col3 = st.columns(3)
        
        with col1:
            school_level = st.radio("학교 선택", ["중학교", "고등학교"], horizontal=True, disabled=input_disabled)
        with col2:
            grade = st.selectbox("학년 선택", ["1학년", "2학년", "3학년"], disabled=input_disabled)
        with col3:
            difficulty_level = st.select_slider("난이도 선택", options=["하 (Easy)", "중 (Medium)", "상 (Hard)"], value="중 (Medium)", disabled=input_disabled)
        
        # Question Type Selection
        question_type = st.selectbox(
            "수능/모의고사 유형 선택 (Type)",
            [
                "종합 (General Practice) - 5문제",
                "18-19번: 목적/심경 (1문제)",
                "20-24번: 대의파악 (주제/제목/요지) (1문제)",
                "21번: 함축의미 추론 (1문제)",
                "29번: 어법 (Grammar) (1문제)",
                "30번: 어휘 (Vocabulary) (1문제)",
                "31-34번: 빈칸추론 (Killer) (1문제)",
                "35번: 흐름과 관계없는 문장 (1문제)",
                "36-39번: 글의 순서/문장 삽입 (1문제)",
                "40번: 요약문 완성 (1문제)",
                "41-42번: 장문 독해 (2문제)",
                "43-45번: 복합 장문 (3문제)"
            ],
            disabled=input_disabled
        )
        
        st.divider()
        
        topic_mode = st.radio("주제 선택 방식", ["직접 입력", "추천 주제 선택"], horizontal=True, disabled=input_disabled)
        
        topic = ""
        if topic_mode == "직접 입력":
            topic = st.text_input("주제를 입력하세요", placeholder="예: 우주 여행, K-Pop, 기후 변화", disabled=input_disabled)
        else:
            topic_options = ["(주제를 선택해주세요)"] + TOPICS
            selected_topic = st.selectbox("추천 주제를 선택하세요", topic_options, disabled=input_disabled)
            if selected_topic != "(주제를 선택해주세요)":
                topic = selected_topic
        
        st.write("")
        
        if st.session_state.is_generating:
            st.button("⛔ 생성 중단 (Stop)", on_click=stop_generation, type="primary", use_container_width=True)
        else:
            st.button("📝 문제 생성하기", on_click=start_generation, type="primary", use_container_width=True)

if not api_key:
    st.warning("☝️ 위 설정 메뉴에서 Gemini API Key를 입력하거나 secrets.toml에 설정해주세요.")
    st.markdown("[Google AI Studio](https://aistudio.google.com/)에서 무료 키를 발급받을 수 있습니다.")
    st.stop()

# --- Generation Logic ---
if st.session_state.is_generating:
    if not topic:
        st.error("주제를 입력하거나 선택해주세요.")
        st.session_state.is_generating = False
    else:
        with st.spinner("문제를 생성하고 있습니다... (약 10~20초 소요)"):
            try:
                result = generate_problem_set(api_key, school_level, grade, topic, difficulty_level, question_type)
                
                if "error" in result:
                    st.error(f"오류가 발생했습니다: {result['error']}")
                else:
                    st.session_state.generated_content = result
                    st.session_state.graded = False
            except Exception as e:
                st.error(f"예상치 못한 오류 발생: {e}")
            finally:
                st.session_state.is_generating = False
                st.rerun()

# --- Tab 2: History Logic ---
with tab2:
    st.markdown("### 📂 저장된 문제 목록")
    history_files = get_history_files()
    
    if not history_files:
        st.info("아직 저장된 문제가 없습니다. '문제 생성' 탭에서 문제를 만들고 저장해 보세요!")
    else:
        selected_file = st.selectbox("불러올 파일을 선택하세요", history_files)
        
        col_h1, col_h2 = st.columns([0.2, 0.8])
        with col_h1:
            if st.button("📂 불러오기 (Load)"):
                try:
                    data = load_from_history(f"history/{selected_file}")
                    st.session_state.generated_content = data
                    st.session_state.graded = False
                    st.success(f"불러오기 완료!")
                    st.rerun()
                except Exception as e:
                    st.error(f"파일 불러오기 실패: {e}")
        with col_h2:
            if st.button("🗑️ 삭제 (Delete)"):
                delete_history_file(f"history/{selected_file}")
                st.success("삭제되었습니다.")
                st.rerun()

# --- Display Content ---
if st.session_state.generated_content:
    result = st.session_state.generated_content
    
    # Save Button (Top Right of Content)
    col_s1, col_s2 = st.columns([0.8, 0.2])
    with col_s2:
        if st.button("💾 저장 (Save)"):
            file_path = save_to_history(result, topic if topic else "Untitled")
            st.toast(f"저장 완료! ({os.path.basename(file_path)})", icon="✅")

    # Display Passage with Box Style
    st.divider()
    st.subheader(f"📖 {result.get('title', 'Reading Passage')}")
    
    passage_text = result.get('passage', '')
    # Convert Markdown to HTML for the box display
    passage_text = passage_text.replace(chr(10), '<br>')
    passage_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', passage_text) # Bold
    passage_text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', passage_text) # Italic
    
    passage_html = f"""
    <div style="
        background-color: #FFFFFF;
        padding: 25px;
        border: 2px solid #333;
        font-family: 'Times New Roman', serif;
        font-size: 18px;
        line-height: 1.8;
        color: #000;
        margin-bottom: 20px;
    ">
        {passage_text}
    </div>
    """
    st.markdown(passage_html, unsafe_allow_html=True)
    
    st.divider()
    
    questions = result.get('questions', [])
    user_answers = {}

    # Form for submission
    with st.form("quiz_form"):
        for idx, q in enumerate(questions):
            # Clean up question text to prevent markdown conflicts
            q_text = q.get('question', '').strip().replace('**', '')
            st.markdown(f"**{idx+1}.** {q_text}")
            
            # Show Options using Radio Buttons
            options = q.get('options', [])
            user_choice = st.radio(
                f"Question {idx+1} Options",
                options,
                index=None,
                key=f"q_{idx}",
                label_visibility="collapsed"
            )
            user_answers[idx] = user_choice
            
            st.write("") # Spacer between questions
        
        # Submit Button
        submitted = st.form_submit_button("💯 채점하기 (Grade Me)")
        if submitted:
            # Check if all questions are answered
            if len(user_answers) < len(questions) or any(v is None for v in user_answers.values()):
                st.warning("⚠️ 모든 문제를 풀어야 채점할 수 있습니다. (답안을 선택하지 않은 문제가 있습니다)")
            else:
                st.session_state.graded = True
                st.rerun()

    # --- Grading Results ---
    if st.session_state.graded:
        st.divider()
        st.subheader("📊 채점 결과 (Results)")
        
        score = 0
        total = len(questions)
        
        for idx, q in enumerate(questions):
            correct_answer_raw = str(q.get('answer')).strip()
            user_choice = user_answers.get(idx)
            
            # Logic to extract number from "3. Option C"
            user_number = user_choice.split('.')[0].strip() if user_choice else None
            correct_number = correct_answer_raw.split('.')[0].strip()
            
            is_correct = (user_number == correct_number)
            if is_correct:
                score += 1
                st.success(f"**{idx+1}번 정답!** (선택: {user_number})")
            else:
                st.error(f"**{idx+1}번 오답** (선택: {user_number if user_number else '미선택'} / 정답: {correct_number})")
        
        final_score = (score / total) * 100
        st.markdown(f"### 🏆 당신의 점수는 **{int(final_score)}점** 입니다!")

        # Show Detailed Explanations
        st.divider()
        with st.expander("📝 정답 및 상세 해설 보기", expanded=True):
            for idx, q in enumerate(questions):
                st.markdown(f"**[{idx+1}번 문제]**")
                st.markdown(f"- **정답**: {q.get('answer')}")
                st.markdown(f"- **유형**: {q.get('type')}")
                st.markdown(f"- **해설**: {q.get('explanation')}")
                st.divider()
        
        # Vocabulary Section with TTS
        st.divider()
        with st.expander("📚 주요 어휘 및 숙어 정리 (Vocabulary + 듣기)"):
            vocab_list = result.get('vocabulary', [])
            if vocab_list:
                # Use HTML/JS for client-side TTS (Text-to-Speech)
                vocab_html = """
                <style>
                    .vocab-item { margin-bottom: 8px; font-family: sans-serif; font-size: 16px; display: flex; align-items: center; }
                    .speak-btn { 
                        background-color: #f0f2f6; border: 1px solid #dce4ef; border-radius: 4px; 
                        cursor: pointer; margin-right: 10px; padding: 2px 6px; font-size: 14px;
                    }
                    .speak-btn:hover { background-color: #e0e5eb; }
                </style>
                <script>
                    function speak(text) {
                        if ('speechSynthesis' in window) {
                            var msg = new SpeechSynthesisUtterance();
                            msg.text = text;
                            msg.lang = 'en-US';
                            window.speechSynthesis.speak(msg);
                        } else {
                            alert("이 브라우저는 TTS를 지원하지 않습니다.");
                        }
                    }
                </script>
                <div style="padding: 10px;">
                """
                
                for v in vocab_list:
                    word = v.get('word', '').replace("'", "\\'") # Escape quotes
                    meaning = v.get('meaning', '')
                    vocab_html += f"""
                    <div class="vocab-item">
                        <button class="speak-btn" onclick="speak('{word}')">🔊</button>
                        <span><b>{word}</b> : {meaning}</span>
                    </div>
                    """
                
                vocab_html += "</div>"
                
                # Render HTML component
                components.html(vocab_html, height=len(vocab_list) * 40 + 50, scrolling=True)
                st.caption("🔊 스피커 버튼을 누르면 원어민 발음을 들을 수 있습니다.")
            else:
                st.info("정리된 어휘가 없습니다.")
