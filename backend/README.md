# BlindSpot Backend

BlindSpot 프로젝트의 백엔드 컴포넌트입니다.

## 📁 구조

```
backend/
├── supabase_uploader.py  # JSON → Supabase 업로드 스크립트
├── requirements.txt      # Python 의존성
├── env.example          # 환경 변수 예시
└── README.md           # 이 파일
```

## 🚀 설정 및 실행

### 1. 의존성 설치
```bash
pip install -r requirements.txt
```

### 2. 환경 변수 설정
```bash
# env.example을 .env로 복사
cp env.example .env

# .env 파일 편집하여 실제 Supabase 정보 입력
# SUPABASE_URL=https://your-project-id.supabase.co
# SUPABASE_ANON_KEY=your-anon-key-here
```

### 3. Supabase 업로드 실행
```bash
# 크롤링된 JSON 데이터를 Supabase에 업로드
python supabase_uploader.py
```

## 🔧 주요 기능

### SupabaseUploader 클래스
- **JSON 파일 로드**: 크롤링된 기사 데이터 읽기
- **데이터 변환**: JSON → Supabase 스키마 형식 변환
- **중복 체크**: URL 기반 중복 기사 필터링
- **배치 업로드**: 100개씩 배치 단위로 효율적 업로드
- **에러 처리**: 실패한 업로드 재시도 및 로깅

### 지원 기능
- ✅ 언론사별 ID 자동 매핑
- ✅ 날짜 형식 자동 변환
- ✅ 중복 기사 자동 스킵
- ✅ 배치 처리로 성능 최적화
- ✅ 상세한 업로드 결과 리포트

## 📊 예상 결과

```
📊 업로드 결과 요약
==================================================
처리된 파일: 4개
총 기사 수: 295개
업로드 성공: 290개
업로드 실패: 0개
중복 스킵: 5개
성공률: 98.3%

📋 언론사별 결과:
  hani: 90/90개 업로드
  chosun: 90/90개 업로드
  ytn: 90/90개 업로드
  kbs: 25/25개 업로드
```

## 🚨 주의사항

1. **환경 변수**: SUPABASE_URL과 SUPABASE_ANON_KEY 필수 설정
2. **네트워크**: 안정적인 인터넷 연결 필요
3. **권한**: Supabase 프로젝트에 대한 INSERT 권한 필요
4. **용량**: 기사 본문 포함 시 데이터베이스 용량 고려 