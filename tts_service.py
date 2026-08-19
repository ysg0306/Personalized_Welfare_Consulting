import os
from typing import List
from gtts import gTTS

def generate_policy_tts(summary_list: List[str], policy_id: str) -> str:
   
    # 1. 예외 처리: 요약 리스트가 비어 있거나 올바르지 않은 경우 기본 메시지 설정
    if not summary_list or not isinstance(summary_list, list):
        summary_list = ["안내할 요약 내용이 없습니다.", "상세 내용은 공고 원문을 확인해 주세요."]
    
    # 2. 음성 파일을 저장할 디렉토리 생성 (정적 파일 폴더)
    output_dir = os.path.join("static", "audio")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    # 3. 3줄 요약을 TTS로 읽기 자연스럽도록 친절한 구어체 문장으로 결합
    # 단순히 붙여 읽으면 기계음이 너무 급하게 넘어가므로, 쉼표(,)와 적절한 휴지(pause)를 위한 문장 정제 진행
    formatted_sentences = []
    
    # 순서대로 안내 멘트 추가하여 친절함 극대화 (배리어프리 가치 반영)
    headers = [
        "첫 번째 내용입니다. ",
        "두 번째 내용입니다. ",
        "마지막 세 번째 내용입니다. "
    ]
    
    for i, line in enumerate(summary_list):
        clean_line = line.strip()
        # 문장 끝에 마침표가 없으면 자연스러운 끊어 읽기를 위해 마침표 추가
        if not clean_line.endswith(('.', '!', '?')):
            clean_line += '.'
            
        # 3줄 요약 규격(원소 3개)에 맞게 머리말 결합, 초과하는 줄은 그대로 결합
        if i < len(headers):
            formatted_sentences.append(f"{headers[i]}{clean_line}")
        else:
            formatted_sentences.append(clean_line)
            
    # 전체 문장을 한 글의 형태로 병합
    full_text = " 안녕 하세요. 해당 복지 정책에 대한 쉬운 3줄 요약 안내입니다. " + " ".join(formatted_sentences)
    
    # 4. 파일 저장 경로 지정
    file_path = os.path.join(output_dir, f"{policy_id}.mp3")
    
    # 5. gTTS를 활용하여 한국어 음성 생성 및 파일 저장
    # lang='ko'로 한국어 지정, slow=False로 자연스러운 말하기 속도 유지
    tts = gTTS(text=full_text, lang='ko', slow=False)
    tts.save(file_path)
    
    # 6. 저장된 상대 경로 반환 (FastAPI와 Streamlit에서 서빙하기 좋은 규격)
    return file_path

# 테스트용 코드 (직접 실행 시에만 작동) (필요없으면 삭제하면됨)
if __name__ == "__main__":
    sample_summary = [
        "임차보증금 5천만 원 이하 및 월세 60만 원 이하 건물의 무주택 청년이 지원 대상입니다.",
        "실제 내는 월세 범위 안에서 매달 최대 20만 원씩, 가장 길게는 12달 동안 지원합니다.",
        "복지로 누리집에서 온라인으로 신청하거나 주민센터를 방문해서 신청하세요."
    ]
    
    print("TTS 음성 생성 테스트 중...")
    try:
        saved_path = generate_policy_tts(sample_summary, "test_policy")
        print(f"성공적으로 오디오 파일이 생성되었습니다! 저장 경로: {saved_path}")
        print(f"파일 존재 여부: {os.path.exists(saved_path)}")
    except Exception as e:
        print(f"에러 발생: {e}")
