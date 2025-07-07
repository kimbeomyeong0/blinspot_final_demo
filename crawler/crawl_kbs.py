# crawler/crawl_kbs.py

import os
import asyncio
from bs4 import BeautifulSoup
from datetime import datetime
from utils.parser_common import get_html, clean_text
from playwright.async_api import async_playwright
import logging
import re

logger = logging.getLogger(__name__)

# KBS 뉴스 카테고리별 URL (올바른 카테고리 코드)
CATEGORY_URLS = {
    "정치": [
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0003",  # 정치
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0003&page=1",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0003&page=2",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0003&page=3",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0003&page=4",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0003&page=5",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0003&page=6",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0003&page=7",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0003&page=8",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0003&page=9",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0003&page=10",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0003&page=11",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0003&page=12",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0003&page=13",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0003&page=14",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0003&page=15",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0003&page=16",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0003&page=17",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0003&page=18",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0003&page=19",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0003&page=20"
    ],
    "사회": [
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0004",  # 사회
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0004&page=1",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0004&page=2",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0004&page=3",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0004&page=4",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0004&page=5",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0004&page=6",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0004&page=7",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0004&page=8",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0004&page=9",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0004&page=10",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0004&page=11",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0004&page=12",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0004&page=13",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0004&page=14",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0004&page=15",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0004&page=16",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0004&page=17",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0004&page=18",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0004&page=19",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0004&page=20"
    ],
    "경제": [
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0002",  # 경제
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0002&page=1",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0002&page=2",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0002&page=3",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0002&page=4",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0002&page=5",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0002&page=6",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0002&page=7",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0002&page=8",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0002&page=9",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0002&page=10",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0002&page=11",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0002&page=12",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0002&page=13",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0002&page=14",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0002&page=15",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0002&page=16",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0002&page=17",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0002&page=18",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0002&page=19",
        "https://news.kbs.co.kr/news/pc/category/category.do?ctcd=0002&page=20"
    ]
}

async def extract_article_content(page, article_url):
    """KBS 기사 본문 추출"""
    try:
        # 기존 페이지를 재사용하여 본문 추출 (새 탭 생성하지 않음)
        await page.goto(article_url, wait_until="domcontentloaded", timeout=20000)
        
        # 페이지 로딩 대기
        await page.wait_for_timeout(500)
        
        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')
        
        # KBS 기사 본문 셀렉터 시도 (우선순위 순)
        content_selectors = [
            '#cont_newstext',
            '.article-body',
            '.news-article-body',
            '.story-content',
            '.entry-content',
            '#article-body',
            '.article-content',
            '.text-content',
            '.content-body',
            '.detail-content'
        ]
        
        content = ""
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                content = clean_text(content_elem.get_text())
                if len(content) > 100:  # 충분한 길이면 즉시 반환
                    break
        
        # 본문이 너무 짧으면 기본 메시지 반환
        if not content or len(content.strip()) < 50:
            content = "본문을 추출할 수 없습니다."
            
        return content
        
    except Exception as e:
        logger.error(f"KBS 본문 추출 실패 - {article_url}: {e}")
        return "본문을 추출할 수 없습니다."

async def get_articles():
    all_articles = []
    processed_urls = set()  # URL 기반 중복 체크를 위한 집합
    
    async with async_playwright() as p:
        # 브라우저 최적화 설정 (안전한 옵션만 사용)
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
                '--disable-extensions',
                '--disable-plugins',
                '--disable-images',  # 이미지 로딩 비활성화 (성능 향상)
                '--disable-web-security',
                '--disable-features=TranslateUI',
                '--disable-renderer-backgrounding',
                '--disable-backgrounding-occluded-windows',
                '--disable-background-timer-throttling',
                '--disable-default-apps',
                '--disable-sync',
                '--disable-translate',
                '--hide-scrollbars',
                '--mute-audio',
                '--no-first-run',
                '--no-default-browser-check',
                '--disable-component-update',
                '--disable-domain-reliability',
                '--disable-print-preview',
                '--disable-speech-api',
                '--disable-web-bluetooth',
                '--disable-client-side-phishing-detection',
                '--disable-hang-monitor',
                '--disable-prompt-on-repost',
                '--disable-breakpad',
                '--disable-dev-tools',
                '--disable-in-process-stack-traces',
                '--disable-histogram-customizer',
                '--disable-gl-extensions',
                '--disable-3d-apis',
                '--disable-accelerated-2d-canvas',
                '--disable-accelerated-jpeg-decoding',
                '--disable-accelerated-mjpeg-decode',
                '--disable-accelerated-video-decode',
            ]
        )
        
        for category, urls in CATEGORY_URLS.items():
            try:
                print(f"🔍 KBS {category} 카테고리 크롤링 중...")
                
                count = 0
                target_count = 30
                
                for url_idx, url in enumerate(urls):
                    if count >= target_count:
                        break
                        
                    try:
                        print(f"📄 KBS {category} URL {url_idx + 1}/{len(urls)} 처리 중...")
                        
                        page = await browser.new_page()
                        
                        # 페이지 최적화 설정
                        await page.set_extra_http_headers({
                            'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
                            'Cache-Control': 'no-cache'
                        })
                        
                        # 불필요한 리소스 차단 (성능 향상)
                        await page.route('**/*.{png,jpg,jpeg,gif,svg,ico,webp,css,woff,woff2,ttf,eot}', 
                                       lambda route: route.abort())
                        
                        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                        
                        # 페이지 로딩 대기
                        try:
                            await page.wait_for_selector('a.box-content.flex-style', timeout=15000)
                        except:
                            print(f"❌ KBS {category} URL {url_idx + 1}: 기사 목록 로딩 실패")
                            await page.close()
                            continue
                        
                        # 현재 페이지의 기사 수집
                        html = await page.content()
                        soup = BeautifulSoup(html, "html.parser")
                        
                        # KBS 기사 목록 셀렉터 (더 포괄적으로)
                        selectors = [
                            "a.box-content.flex-style",
                            ".box-content a",
                            ".news-item a",
                            ".article-item a",
                            "article a",
                            ".headline a",
                            "a[href*='/news/']",
                            ".news-list a",
                            ".article-list a",
                            ".list-item a",
                            "a[href*='kbs.co.kr']",
                            ".content-link a",
                            ".story-item a",
                            ".news-card a",
                            ".list-cont a",
                            "li a[href*='/news/view.do']",
                            ".article-link a",
                            ".news-link a",
                            ".item-link a",
                            "div.item a",
                            ".news-item-link",
                            "a[href*='view.do?ncd=']"
                        ]
                        
                        nodes = []
                        for selector in selectors:
                            nodes = soup.select(selector)
                            if nodes:
                                print(f"📄 KBS {category} URL {url_idx + 1}에서 '{selector}' 셀렉터로 {len(nodes)}개 요소 발견")
                                break
                        
                        if not nodes:
                            print(f"❌ KBS {category} URL {url_idx + 1}: 기사 목록을 찾을 수 없습니다")
                            await page.close()
                            continue
                        
                        # 현재 페이지에서 처리된 기사 수
                        processed_in_page = 0
                        
                        # 각 기사 처리
                        for node in nodes:
                            if count >= target_count:
                                break
                                
                            try:
                                link = node.get('href')
                                
                                # 제목 추출 (다양한 셀렉터 시도)
                                title_selectors = [
                                    '.title',
                                    '.headline',
                                    '.news-title',
                                    'h3',
                                    'h4',
                                    '.subject'
                                ]
                                
                                title = ""
                                for title_selector in title_selectors:
                                    title_elem = node.select_one(title_selector)
                                    if title_elem:
                                        title = clean_text(title_elem.get_text())
                                        break
                                
                                # 제목이 없으면 전체 텍스트에서 추출
                                if not title:
                                    title = clean_text(node.get_text())
                                
                                if not link or not title or len(title) < 3:
                                    continue
                                
                                # link가 리스트인 경우 첫 번째 요소 사용
                                if isinstance(link, list):
                                    link = link[0] if link else ""
                                
                                # 상대 경로를 절대 경로로 변환
                                if link.startswith('/'):
                                    link = f"https://news.kbs.co.kr{link}"
                                elif not link.startswith('http'):
                                    link = f"https://news.kbs.co.kr/{link}"
                                
                                # 중복 제거 (URL 기반으로만 체크)
                                if link in processed_urls:
                                    continue
                                
                                processed_urls.add(link)
                                
                                # 본문 추출
                                print(f"📄 [{count+1}/{target_count}] {title} - 본문 추출 중...")
                                content = await extract_article_content(page, article_url=link)
                                
                                article = {
                                    'title': title,
                                    'url': link,
                                    'category': category,
                                    'content': content,
                                    'published_at': datetime.now().isoformat(),
                                    'source': 'kbs'
                                }
                                
                                all_articles.append(article)
                                count += 1
                                processed_in_page += 1
                                
                                print(f"✅ [{count}/{target_count}] {title[:50]}... (본문 {len(content)}자)")
                                
                            except Exception as e:
                                print(f"❌ KBS {category} 기사 처리 중 오류: {e}")
                                continue
                        
                        print(f"📄 KBS {category} URL {url_idx + 1}에서 {processed_in_page}개 기사 처리 완료")
                        await page.close()
                        
                    except Exception as e:
                        print(f"❌ KBS {category} URL {url_idx + 1} 처리 중 오류: {e}")
                        if 'page' in locals():
                            await page.close()
                        continue
                
                print(f"✅ KBS {category}에서 {count}개 기사 수집 완료")
                
            except Exception as e:
                print(f"❌ Error crawling KBS {category}: {e}")
                if 'page' in locals():
                    await page.close()
                continue
        
        print(f"✅ KBS에서 총 {len(all_articles)}개 기사 수집 완료")
        return all_articles

if __name__ == "__main__":
    asyncio.run(get_articles())