from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
import os
from dotenv import load_dotenv
from supabase.client import create_client
from pydantic import BaseModel
from datetime import datetime
import uuid

# 환경 변수 로드
load_dotenv()

app = FastAPI(
    title="BlindSpot News API",
    description="편향성 분석 뉴스 이슈 API 🔍",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발용, 실제 배포시 수정 필요
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Supabase 클라이언트 초기화
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_ANON_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL과 SUPABASE_ANON_KEY 환경 변수를 설정해주세요.")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 응답 모델들
class BiasGauge(BaseModel):
    left: int
    center: int
    right: int
    
class IssueCard(BaseModel):
    id: str
    title: str
    summary: str
    category: str
    article_count: int
    bias_gauge: BiasGauge
    created_at: str

class ArticleInfo(BaseModel):
    id: str
    title: str
    url: str
    media_outlet: str
    category: str
    published_at: str
    bias: str  # 'left', 'center', 'right' 중 하나

class StatsInfo(BaseModel):
    total_issues: int
    total_articles: int
    categories: Dict[str, int]
    media_outlets: Dict[str, int]

@app.get("/")
async def root():
    """API 상태 확인"""
    return {
        "message": "🔍 BlindSpot News API",
        "status": "운영 중",
        "endpoints": [
            "/api/issues - 이슈 목록",
            "/api/issues/{issue_id} - 이슈 상세",
            "/api/articles/{issue_id} - 이슈별 기사 목록",
            "/api/stats - 전체 통계",
            "/docs - API 문서"
        ]
    }

@app.get("/api/issues", response_model=List[IssueCard])
async def get_issues(category: Optional[str] = None, limit: int = 20):
    """이슈 목록 조회 (편향성 게이지 포함)"""
    try:
        query = supabase.table('issues').select('*')
        
        if category:
            query = query.eq('category', category)
            
        response = query.order('created_at', desc=True).limit(limit).execute()
        
        issues = []
        for issue in response.data:
            issues.append(IssueCard(
                id=str(issue['id']),
                title=issue['title'],
                summary=issue['summary'],
                category=issue['category'],
                article_count=issue['article_count'],
                bias_gauge=BiasGauge(
                    left=issue['bias_left'],
                    center=issue['bias_center'],
                    right=issue['bias_right']
                ),
                created_at=issue['created_at']
            ))
        
        return issues
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"이슈 목록 조회 실패: {str(e)}")

@app.get("/api/issues/{issue_id}")
async def get_issue_detail(issue_id: str):
    """이슈 상세 정보 조회"""
    try:
        response = supabase.table('issues').select('*').eq('id', issue_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="이슈를 찾을 수 없습니다")
        
        issue = response.data[0]
        
        # 편향성 게이지 생성
        total = issue['bias_left'] + issue['bias_center'] + issue['bias_right']
        left_pct = (issue['bias_left'] / total * 100) if total > 0 else 0
        center_pct = (issue['bias_center'] / total * 100) if total > 0 else 0
        right_pct = (issue['bias_right'] / total * 100) if total > 0 else 0
        
        gauge_bar = '🟥' * int(left_pct // 5) + '⬜' * int(center_pct // 5) + '🟦' * int(right_pct // 5)
        
        return {
            "id": issue['id'],
            "title": issue['title'],
            "summary": issue['summary'],
            "category": issue['category'],
            "article_count": issue['article_count'],
            "bias_gauge": {
                "left": issue['bias_left'],
                "center": issue['bias_center'],
                "right": issue['bias_right'],
                "left_percent": round(left_pct, 1),
                "center_percent": round(center_pct, 1),
                "right_percent": round(right_pct, 1),
                "visual_bar": gauge_bar
            },
            "created_at": issue['created_at']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"이슈 상세 조회 실패: {str(e)}")

@app.get("/api/articles/{issue_id}", response_model=List[ArticleInfo])
async def get_issue_articles(issue_id: str):
    """이슈별 기사 목록 조회 (bias 포함)"""
    try:
        # issue_id를 UUID로 변환 (타입 불일치 방지)
        try:
            issue_uuid = str(uuid.UUID(issue_id))
        except Exception:
            issue_uuid = issue_id  # fallback: 원본 사용
        mapping_response = supabase.table('issue_articles').select('article_id').eq('issue_id', issue_uuid).execute()
        if not mapping_response.data:
            return []
        article_ids = [item['article_id'] for item in mapping_response.data]
        # bias 정보는 issues 테이블에서 가져옴
        issue_response = supabase.table('issues').select('*').eq('id', issue_uuid).execute()
        if not issue_response.data:
            return []
        issue = issue_response.data[0]
        bias_left = issue.get('bias_left', 0)
        bias_center = issue.get('bias_center', 0)
        bias_right = issue.get('bias_right', 0)
        # bias별로 기사 id를 분배
        bias_labels = (['left'] * bias_left) + (['center'] * bias_center) + (['right'] * bias_right)
        if len(article_ids) != len(bias_labels):
            bias_labels = ['unknown'] * len(article_ids)
        articles_response = supabase.table('articles').select('id, title, url, category, published_at, media_outlet_id').in_('id', article_ids).execute()
        media_response = supabase.table('media_outlets').select('id, name').execute()
        media_map = {outlet['id']: outlet['name'] for outlet in media_response.data}
        articles = []
        id_to_bias = {str(aid): bias_labels[idx] for idx, aid in enumerate(article_ids)}
        for article in articles_response.data:
            aid = str(article['id'])
            media_outlet_id = article.get('media_outlet_id')
            if media_outlet_id is None:
                media_outlet_id = ''
            else:
                media_outlet_id = str(media_outlet_id)
            articles.append(ArticleInfo(
                id=aid,
                title=str(article.get('title', '')),
                url=str(article.get('url', '')),
                media_outlet=media_map.get(media_outlet_id, 'Unknown'),
                category=str(article.get('category', '')),
                published_at=str(article.get('published_at', '')),
                bias=id_to_bias.get(aid, 'unknown')
            ))
        return articles
    except Exception as e:
        print(f"❌ Articles API Error: {str(e)}")  # 서버 로그용
        raise HTTPException(status_code=500, detail=f"기사 목록 조회 실패: {str(e)}")

@app.get("/api/stats", response_model=StatsInfo)
async def get_stats():
    """전체 통계 정보 조회"""
    try:
        # 이슈 수
        issues_response = supabase.table('issues').select('category').execute()
        total_issues = len(issues_response.data)
        
        # 카테고리별 이슈 수
        categories = {}
        for issue in issues_response.data:
            cat = issue['category']
            categories[cat] = categories.get(cat, 0) + 1
        
        # 기사 수
        articles_response = supabase.table('articles').select('media_outlet_id').execute()
        total_articles = len(articles_response.data)
        
        # 언론사별 기사 수
        media_response = supabase.table('media_outlets').select('id, name').execute()
        media_map = {outlet['id']: outlet['name'] for outlet in media_response.data}
        
        media_outlets = {}
        for article in articles_response.data:
            outlet_id = article['media_outlet_id']
            outlet_name = media_map.get(outlet_id, 'Unknown')
            media_outlets[outlet_name] = media_outlets.get(outlet_name, 0) + 1
        
        return StatsInfo(
            total_issues=total_issues,
            total_articles=total_articles,
            categories=categories,
            media_outlets=media_outlets
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"통계 조회 실패: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    print("🚀 BlindSpot API 서버 시작...")
    print("📖 API 문서: http://localhost:8000/docs")
    print("🔍 이슈 목록: http://localhost:8000/api/issues")
    uvicorn.run(app, host="0.0.0.0", port=8000) 