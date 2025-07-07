# crawler/crawl_chosun.py

import os
import asyncio
from bs4 import BeautifulSoup
from datetime import datetime
from utils.parser_common import get_html, clean_text
from playwright.async_api import async_playwright
import logging

logger = logging.getLogger(__name__)

CATEGORY_URLS = {
    "정치": [
        "https://www.chosun.com/politics/",
        "https://www.chosun.com/politics/?page=1",
        "https://www.chosun.com/politics/?page=2",
        "https://www.chosun.com/politics/?page=3"
    ],
    "사회": [
        "https://www.chosun.com/national/",
        "https://www.chosun.com/national/?page=1", 
        "https://www.chosun.com/national/?page=2",
        "https://www.chosun.com/national/?page=3"
    ],
    "경제": [
        "https://www.chosun.com/economy/",
        "https://www.chosun.com/economy/?page=1",
        "https://www.chosun.com/economy/?page=2", 
        "https://www.chosun.com/economy/?page=3"
    ],
}

async def extract_article_content(page, article_url):
    """조선일보 기사 본문 추출"""
    try:
        # 기존 페이지를 재사용하여 본문 추출
        await page.goto(article_url, wait_until="domcontentloaded", timeout=20000)
        
        # 페이지 로딩 대기
        await page.wait_for_timeout(500)
        
        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')
        
        # 조선일보 기사 본문 셀렉터 시도 (우선순위 순)
        content_selectors = [
            '.article-body',
            '.news-article-body', 
            '.story-content',
            '.entry-content',
            '#article-body',
            '.article-content',
            '.text-content',
            '.content-body',
            '.article-text',
            '.story-body'
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
        logger.error(f"조선일보 본문 추출 실패 - {article_url}: {e}")
        return "본문을 추출할 수 없습니다."

async def get_articles():
    all_articles = []
    
    async with async_playwright() as p:
        # 브라우저 최적화 설정
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-extensions',
                '--disable-plugins',
                '--disable-images',
                '--disable-web-security',
                '--disable-features=TranslateUI',
                '--disable-renderer-backgrounding',
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
                print(f"🔍 조선일보 {category} 카테고리 크롤링 중...")
                
                count = 0
                target_count = 30
                processed_urls = set()
                
                for url_idx, url in enumerate(urls):
                    if count >= target_count:
                        break
                        
                    try:
                        print(f"📄 조선일보 {category} URL {url_idx + 1}/{len(urls)} 처리 중...")
                        
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
                        
                        click_count = 0
                        max_clicks = 35  # 더보기 클릭 횟수 대폭 증가
                        
                        while count < target_count and click_count < max_clicks:
                            # 현재 페이지의 기사 수집
                            html = await page.content()
                            soup = BeautifulSoup(html, "html.parser")
                            
                            # 조선일보 기사 목록 셀렉터 (더 포괄적으로)
                            selectors = [
                                "div.story-card a",
                                ".story-card a",
                                ".article-card a",
                                ".news-card a",
                                "article a",
                                ".headline a",
                                ".story-item a",
                                ".news-item a",
                                "a[href*='/article/']",
                                "a[href*='/news/']",
                                ".list-item a",
                                ".news-list a",
                                ".article-list a",
                                "a[href*='/politics/']",
                                "a[href*='/national/']",
                                "a[href*='/economy/']"
                            ]
                            
                            nodes = []
                            for selector in selectors:
                                nodes = soup.select(selector)
                                if nodes:
                                    if click_count == 0:  # 첫 번째에서만 로그 출력
                                        print(f"📄 조선일보 {category} URL {url_idx + 1}에서 '{selector}' 셀렉터로 {len(nodes)}개 요소 발견")
                                    break
                            
                            if not nodes:
                                print(f"❌ 조선일보 {category} URL {url_idx + 1}: 기사 목록을 찾을 수 없습니다")
                                break
                            
                            # 현재 로드된 기사들 처리
                            new_articles_found = 0
                            for node in nodes:
                                if count >= target_count:
                                    break
                                    
                                try:
                                    link = node.get('href')
                                    title = clean_text(node.get_text())
                                    
                                    if not link or not title or len(title) < 3:
                                        continue
                                    
                                    # link가 리스트인 경우 첫 번째 요소 사용
                                    if isinstance(link, list):
                                        link = link[0] if link else ""
                                    
                                    # 상대 경로를 절대 경로로 변환
                                    if link.startswith('/'):
                                        link = f"https://www.chosun.com{link}"
                                    elif not link.startswith('http'):
                                        link = f"https://www.chosun.com/{link}"
                                    
                                    # 중복 제거
                                    if link in processed_urls:
                                        continue
                                    
                                    if any(article['url'] == link for article in all_articles):
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
                                        'source': 'chosun'
                                    }
                                    
                                    all_articles.append(article)
                                    count += 1
                                    new_articles_found += 1
                                    
                                    print(f"✅ [{count}/{target_count}] {title[:50]}... (본문 {len(content)}자)")
                                    
                                except Exception as e:
                                    print(f"❌ 조선일보 {category} 기사 처리 중 오류: {e}")
                                    continue
                            
                            # 새로운 기사가 없으면 중단
                            if new_articles_found == 0 and click_count > 0:
                                print(f"  📄 조선일보 {category} URL {url_idx + 1}: 새로운 기사가 없어 중단")
                                break
                            
                            # "기사 더보기" 버튼 찾기 및 클릭 (더 적극적으로)
                            try:
                                # 다양한 더보기 버튼 셀렉터 시도
                                more_selectors = [
                                    "button:has-text('기사 더보기')",
                                    "a:has-text('기사 더보기')",
                                    "button:has-text('더보기')",
                                    "a:has-text('더보기')",
                                    ".more-btn",
                                    ".btn-more",
                                    "#more-btn",
                                    "button.more",
                                    "a.more",
                                    "[data-more]",
                                    "[onclick*='more']",
                                    "button:has-text('More')",
                                    ".load-more",
                                    ".btn-load-more",
                                    ".more-articles",
                                    ".load-articles",
                                    "button[data-load]",
                                    "a[data-load]",
                                    ".paging .next",
                                    ".pagination .next",
                                    "a:has-text('다음')",
                                    "button:has-text('다음')",
                                    ".next-page",
                                    ".page-next"
                                ]
                                
                                more_button = None
                                for selector in more_selectors:
                                    try:
                                        more_button = page.locator(selector).first
                                        if await more_button.is_visible():
                                            break
                                    except:
                                        continue
                                
                                if more_button and await more_button.is_visible():
                                    print(f"  🔄 조선일보 {category} URL {url_idx + 1}: 더보기 버튼 클릭 ({click_count + 1}번째)")
                                    await more_button.click()
                                    click_count += 1
                                    
                                    # 새 콘텐츠 로딩 대기
                                    await page.wait_for_timeout(4000)  # 더 긴 대기 시간
                                else:
                                    # 더보기 버튼이 없으면 스크롤 시도
                                    print(f"  🔄 조선일보 {category} URL {url_idx + 1}: 스크롤 시도 ({click_count + 1}번째)")
                                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                                    await page.wait_for_timeout(3000)
                                    
                                    # 페이지 끝까지 스크롤했는지 확인
                                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                                    await page.wait_for_timeout(2000)
                                    
                                    # 새로운 콘텐츠가 로드되었는지 확인
                                    new_html = await page.content()
                                    new_soup = BeautifulSoup(new_html, "html.parser")
                                    new_nodes = []
                                    for selector in selectors:
                                        new_nodes = new_soup.select(selector)
                                        if new_nodes:
                                            break
                                    
                                    if len(new_nodes) <= len(nodes):
                                        print(f"  📄 조선일보 {category} URL {url_idx + 1}: 기사 더보기 버튼을 찾을 수 없어 중단")
                                        break
                                    
                                    click_count += 1
                                    
                            except Exception as e:
                                print(f"  ❌ 조선일보 {category} URL {url_idx + 1}: 더보기 버튼 클릭 중 오류: {e}")
                                break
                        
                        await page.close()
                        print(f"✅ 조선일보 {category} URL {url_idx + 1}에서 {click_count}번 클릭 완료")
                        
                    except Exception as e:
                        print(f"❌ 조선일보 {category} URL {url_idx + 1} 처리 중 오류: {e}")
                        if 'page' in locals():
                            await page.close()
                        continue
                
                print(f"✅ 조선일보 {category}에서 {count}개 기사 수집 완료")
                
            except Exception as e:
                print(f"❌ Error crawling 조선일보 {category}: {e}")
                if 'page' in locals():
                    await page.close()
                continue
        
        await browser.close()
    
    print(f"✅ 조선일보에서 총 {len(all_articles)}개 기사 수집 완료")
    return all_articles

if __name__ == "__main__":
    asyncio.run(get_articles())