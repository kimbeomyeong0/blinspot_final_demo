# crawler/main_crawler.py

import json
import asyncio
import os
from datetime import datetime
from crawl_hani import get_articles as get_hani
from crawl_chosun import get_articles as get_chosun
from crawl_kbs import get_articles as get_kbs
from crawl_ytn import get_articles as get_ytn

OUTPUT_DIR = "data/raw/"

def save_json(source_name, articles):
    # 디렉토리가 없으면 자동 생성
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    now = datetime.now().strftime("%Y%m%d")
    path = f"{OUTPUT_DIR}{source_name}_{now}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    print(f"💾 {path}에 저장 완료")

def analyze_articles(articles):
    """기사 분석 및 통계 정보 반환"""
    total_count = len(articles)
    content_success = sum(1 for article in articles if article.get('content') != "본문을 추출할 수 없습니다.")
    content_fail = total_count - content_success
    
    # 카테고리별 통계
    categories = {}
    for article in articles:
        category = article.get('category', 'Unknown')
        if category not in categories:
            categories[category] = {'total': 0, 'content_success': 0}
        categories[category]['total'] += 1
        if article.get('content') != "본문을 추출할 수 없습니다.":
            categories[category]['content_success'] += 1
    
    return {
        'total_count': total_count,
        'content_success': content_success,
        'content_fail': content_fail,
        'success_rate': round((content_success / total_count * 100), 1) if total_count > 0 else 0,
        'categories': categories
    }

async def main():
    sources = {
        "hani": get_hani,
        "chosun": get_chosun,
        "kbs": get_kbs,
        "ytn": get_ytn
    }

    tasks = {name: asyncio.create_task(fn()) for name, fn in sources.items()}
    
    results = {}
    analysis_results = {}
    
    for name, task in tasks.items():
        try:
            print(f"🔍 Crawling {name}...")
            articles = await task
            results[name] = articles
            save_json(name, articles)
            
            # 기사 분석
            analysis = analyze_articles(articles)
            analysis_results[name] = analysis
            
            print(f"✅ {name}: {analysis['total_count']}개 기사 수집 완료")
            print(f"   📄 본문 추출 성공: {analysis['content_success']}개 ({analysis['success_rate']}%)")
            if analysis['content_fail'] > 0:
                print(f"   ❌ 본문 추출 실패: {analysis['content_fail']}개")
            
        except Exception as e:
            print(f"❌ Error crawling {name}: {e}")
            results[name] = []
            analysis_results[name] = {'total_count': 0, 'content_success': 0, 'content_fail': 0, 'success_rate': 0}
    
    # 전체 요약
    total_articles = sum(len(articles) for articles in results.values())
    total_content_success = sum(analysis['content_success'] for analysis in analysis_results.values())
    total_content_fail = sum(analysis['content_fail'] for analysis in analysis_results.values())
    overall_success_rate = round((total_content_success / total_articles * 100), 1) if total_articles > 0 else 0
    
    print(f"\n📊 전체 크롤링 결과 요약:")
    print(f"   📰 총 수집 기사: {total_articles}개")
    print(f"   ✅ 본문 추출 성공: {total_content_success}개 ({overall_success_rate}%)")
    if total_content_fail > 0:
        print(f"   ❌ 본문 추출 실패: {total_content_fail}개")
    
    print(f"\n📋 언론사별 상세 결과:")
    for name, analysis in analysis_results.items():
        if analysis['total_count'] > 0:
            print(f"   {name.upper()}: {analysis['total_count']}개 (본문 성공률: {analysis['success_rate']}%)")
            if 'categories' in analysis:
                for category, stats in analysis['categories'].items():
                    success_rate = round((stats['content_success'] / stats['total'] * 100), 1) if stats['total'] > 0 else 0
                    print(f"      - {category}: {stats['total']}개 (본문 성공률: {success_rate}%)")

if __name__ == "__main__":
    asyncio.run(main())