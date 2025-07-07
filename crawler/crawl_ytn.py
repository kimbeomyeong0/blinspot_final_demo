# crawler/crawl_ytn.py

import os
import asyncio
from bs4 import BeautifulSoup
from datetime import datetime
from utils.parser_common import get_html, clean_text
from playwright.async_api import async_playwright
import logging
import re

logger = logging.getLogger(__name__)

CATEGORY_URLS = {
    "정치": [
        "https://www.ytn.co.kr/news/list.php?mcd=0101",
        "https://www.ytn.co.kr/news/list.php?mcd=0101&page=1",
        "https://www.ytn.co.kr/news/list.php?mcd=0101&page=2",
        "https://www.ytn.co.kr/news/list.php?mcd=0101&page=3",
        "https://www.ytn.co.kr/news/list.php?mcd=0101&page=4",
        "https://www.ytn.co.kr/news/list.php?mcd=0101&page=5",
        "https://www.ytn.co.kr/news/list.php?mcd=0101&page=6",
        "https://www.ytn.co.kr/news/list.php?mcd=0101&page=7",
        "https://www.ytn.co.kr/news/list.php?mcd=0101&page=8"
    ],
    "사회": [
        "https://www.ytn.co.kr/news/list.php?mcd=0103",
        "https://www.ytn.co.kr/news/list.php?mcd=0103&page=1",
        "https://www.ytn.co.kr/news/list.php?mcd=0103&page=2",
        "https://www.ytn.co.kr/news/list.php?mcd=0103&page=3",
        "https://www.ytn.co.kr/news/list.php?mcd=0103&page=4",
        "https://www.ytn.co.kr/news/list.php?mcd=0103&page=5",
        "https://www.ytn.co.kr/news/list.php?mcd=0103&page=6",
        "https://www.ytn.co.kr/news/list.php?mcd=0103&page=7",
        "https://www.ytn.co.kr/news/list.php?mcd=0103&page=8"
    ],
    "경제": [
        "https://www.ytn.co.kr/news/list.php?mcd=0102",
        "https://www.ytn.co.kr/news/list.php?mcd=0102&page=1",
        "https://www.ytn.co.kr/news/list.php?mcd=0102&page=2",
        "https://www.ytn.co.kr/news/list.php?mcd=0102&page=3",
        "https://www.ytn.co.kr/news/list.php?mcd=0102&page=4",
        "https://www.ytn.co.kr/news/list.php?mcd=0102&page=5",
        "https://www.ytn.co.kr/news/list.php?mcd=0102&page=6",
        "https://www.ytn.co.kr/news/list.php?mcd=0102&page=7",
        "https://www.ytn.co.kr/news/list.php?mcd=0102&page=8"
    ],
}

async def extract_article_content(page, article_url):
    """YTN 기사 본문 추출"""
    try:
        # 기존 페이지를 재사용하여 본문 추출
        await page.goto(article_url, wait_until="domcontentloaded", timeout=20000)
        
        # 페이지 로딩 대기
        await page.wait_for_timeout(1000)
        
        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')
        
        # YTN 기사 본문 셀렉터 시도 (실제 사이트 구조 기반)
        content_selectors = [
            '.paragraph',  # 실제 본문 영역
            '.content',    # 본문 컨테이너
            '.news_view_wrap .inner',  # 뉴스 보기 영역
            '.article-body',
            '.news-article-body',
            '.story-content',
            '.entry-content',
            '#article-body',
            '.article-content',
            '.text-content',
            '.content-body',
            '.detail-content',
            '.article-text',
            '.article_txt',
            '.article_content',
            '.news_content',
            '.text',
            '.story_text',
            '.article_wrap',
            '.article-wrap',
            '.news-content',
            '.story-body',
            '.content-text',
            '.view_content',
            '.news_view',
            '.article_view',
            '.content_view',
            '.detail_content',
            '.news_detail',
            '.article_detail',
            '.view_text',
            '.news_text',
            '.article_text'
        ]
        
        content = ""
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                # 광고나 불필요한 텍스트 제거
                for ad in content_elem.find_all(['script', 'style', 'iframe', 'ins']):
                    ad.decompose()
                
                text = content_elem.get_text(separator=' ', strip=True)
                # 광고 텍스트 제거
                text = re.sub(r'AD\s*', '', text)
                text = re.sub(r'\s+', ' ', text)
                
                if len(text) > 100:  # 충분한 길이면 즉시 반환
                    content = text
                    break
        
        # 본문이 너무 짧으면 기본 메시지 반환
        if not content or len(content.strip()) < 50:
            content = "본문을 추출할 수 없습니다."
            
        return content
        
    except Exception as e:
        logger.error(f"YTN 본문 추출 실패 - {article_url}: {e}")
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
                print(f"🔍 YTN {category} 카테고리 크롤링 중...")
                
                count = 0
                target_count = 30
                processed_urls = set()
                
                for url_idx, url in enumerate(urls):
                    if count >= target_count:
                        break
                        
                    try:
                        print(f"📄 YTN {category} URL {url_idx + 1}/{len(urls)} 처리 중...")
                        
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
                        
                        # YTN 기사 목록 셀렉터 (더 포괄적으로)
                        selectors = [
                            "div.news_list div.title a",
                            "div.list_cont div.title a",
                            ".news_list .title a",
                            "ul.news_list li a",
                            "div.title a",
                            "a[href*='/_ln/']",  # YTN 기사 URL 패턴
                            "a[href*='/news/']",
                            ".list_news a",
                            ".news_item a",
                            ".article_item a",
                            ".news_link",
                            "a[href*='ytn.co.kr']",
                            ".list_item a",
                            ".article_link a",
                            ".content_link a",
                            ".news-card a",
                            ".story-item a",
                            "li.news-item a",
                            ".news-list-item a",
                            "a[href*='article_view']",
                            ".item-title a",
                            ".headline-link a",
                            ".news-headline a",
                            "a[href*='view.php']"
                        ]
                        
                        articles = []
                        for selector in selectors:
                            elements = await page.query_selector_all(selector)
                            if elements:
                                for element in elements:
                                    try:
                                        href = await element.get_attribute('href')
                                        if href and href not in processed_urls:
                                            if href.startswith('/'):
                                                href = f"https://www.ytn.co.kr{href}"
                                            elif not href.startswith('http'):
                                                href = f"https://www.ytn.co.kr/{href}"
                                            
                                            # 중복 체크를 더 관대하게 - URL 기반으로만 체크
                                            if href not in processed_urls:
                                                processed_urls.add(href)
                                                
                                                title = await element.text_content()
                                                if title and title.strip():
                                                    articles.append({
                                                        'title': title.strip(),
                                                        'url': href,
                                                        'category': category
                                                    })
                                                    
                                                    if len(articles) >= 30:
                                                        break
                                    except Exception as e:
                                        continue
                                break
                        
                        if not articles:
                            print(f"❌ YTN {category} URL {url_idx + 1}: 기사 목록을 찾을 수 없습니다")
                            break
                        
                        # 더보기 버튼 클릭 (최대 50번)
                        max_clicks = 50
                        click_count = 0
                        consecutive_no_new_articles = 0
                        
                        # 다양한 더보기 버튼 셀렉터 시도
                        more_selectors = [
                            "button:has-text('더보기')",
                            "a:has-text('더보기')",
                            ".more_btn",
                            ".btn_more",
                            "#more_btn",
                            "button.more",
                            "a.more",
                            "[onclick*='more']",
                            "button:has-text('More')",
                            ".load_more",
                            ".more_list",
                            ".btn_load_more",
                            "button[data-more]",
                            "a[data-more]",
                            ".paging .next",
                            ".next_page",
                            "a:has-text('다음')",
                            "button:has-text('다음')",
                            ".pagination .next",
                            ".page-next",
                            ".more-news",
                            ".load-more-news",
                            "button[onclick*='more']",
                            "a[onclick*='more']",
                            ".btn-more-news",
                            ".more-articles",
                            "#loadMore",
                            ".load-more-btn",
                            "button:has-text('기사 더보기')",
                            "a:has-text('기사 더보기')"
                        ]
                        
                        while click_count < max_clicks and len(articles) < 30:
                            print(f"  🔄 YTN {category} URL {url_idx+1}: 더보기 버튼 클릭 ({click_count+1}번째)")
                            
                            # 더보기 버튼 클릭 전 현재 기사 수 저장
                            before_click_count = len(articles)
                            
                            # 더보기 버튼 클릭
                            clicked = False
                            for selector in more_selectors:
                                try:
                                    await page.click(selector, timeout=3000)
                                    clicked = True
                                    break
                                except:
                                    continue
                            
                            if not clicked:
                                print(f"  📄 YTN {category} URL {url_idx+1}: 더보기 버튼을 찾을 수 없습니다")
                                break
                            
                            # 새 콘텐츠 로딩 대기
                            await page.wait_for_timeout(5000)  # 더 긴 대기 시간
                            
                            # 기사 링크 다시 수집
                            for selector in selectors:
                                try:
                                    elements = await page.query_selector_all(selector)
                                    if elements:
                                        for element in elements:
                                            try:
                                                href = await element.get_attribute('href')
                                                if href and href not in processed_urls:
                                                    if href.startswith('/'):
                                                        href = f"https://www.ytn.co.kr{href}"
                                                    elif not href.startswith('http'):
                                                        href = f"https://www.ytn.co.kr/{href}"
                                                    
                                                    # 중복 체크를 더 관대하게 - URL 기반으로만 체크
                                                    if href not in processed_urls:
                                                        processed_urls.add(href)
                                                        
                                                        title = await element.text_content()
                                                        if title and title.strip():
                                                            articles.append({
                                                                'title': title.strip(),
                                                                'url': href,
                                                                'category': category
                                                            })
                                                            
                                                            if len(articles) >= 30:
                                                                break
                                            except Exception as e:
                                                continue
                                        break
                                except Exception as e:
                                    continue
                            
                            # 새로운 기사가 추가되었는지 확인
                            after_click_count = len(articles)
                            if after_click_count > before_click_count:
                                consecutive_no_new_articles = 0
                                print(f"  📄 YTN {category} URL {url_idx+1}: {after_click_count - before_click_count}개 새 기사 발견")
                            else:
                                consecutive_no_new_articles += 1
                                print(f"  📄 YTN {category} URL {url_idx+1}: 새로운 기사 없음 (연속 {consecutive_no_new_articles}번)")
                            
                            # 연속으로 5번 새 기사가 없으면 중단
                            if consecutive_no_new_articles >= 5:
                                print(f"  📄 YTN {category} URL {url_idx+1}: 연속 5번 새 기사 없어 중단")
                                break
                            
                            click_count += 1
                        
                        print(f"✅ YTN {category} URL {url_idx+1}에서 {click_count}번 클릭 완료")
                        
                        # 수집된 기사들의 본문 추출
                        for i, article in enumerate(articles):
                            if count >= target_count:
                                break
                                
                            try:
                                # 본문 추출
                                print(f"📄 [{count+1}/{target_count}] {article['title']} - 본문 추출 중...")
                                content = await extract_article_content(page, article_url=article['url'])
                                
                                final_article = {
                                    'title': article['title'],
                                    'url': article['url'],
                                    'category': category,
                                    'content': content,
                                    'published_at': datetime.now().isoformat(),
                                    'source': 'ytn'
                                }
                                
                                all_articles.append(final_article)
                                count += 1
                                
                                print(f"✅ [{count}/{target_count}] {article['title'][:50]}... (본문 {len(content)}자)")
                                
                            except Exception as e:
                                print(f"❌ YTN {category} 기사 처리 중 오류: {e}")
                                continue
                        
                        await page.close()
                        
                    except Exception as e:
                        print(f"❌ YTN {category} URL {url_idx + 1} 처리 중 오류: {e}")
                        if 'page' in locals():
                            await page.close()
                        continue
                
                print(f"✅ YTN {category}에서 {count}개 기사 수집 완료")
                
            except Exception as e:
                print(f"❌ Error crawling YTN {category}: {e}")
                if 'page' in locals():
                    await page.close()
                continue
        
        await browser.close()
    
    print(f"✅ YTN에서 총 {len(all_articles)}개 기사 수집 완료")
    return all_articles

if __name__ == "__main__":
    asyncio.run(get_articles())