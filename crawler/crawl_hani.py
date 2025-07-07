# crawler/crawl_hani.py

import os
import asyncio
from bs4 import BeautifulSoup
from datetime import datetime
from utils.parser_common import get_html, clean_text
from playwright.async_api import async_playwright
import logging

logger = logging.getLogger(__name__)

CATEGORY_URLS = {
    "정치": "https://www.hani.co.kr/arti/politics",
    "사회": "https://www.hani.co.kr/arti/society",
    "경제": "https://www.hani.co.kr/arti/economy",
}

async def extract_article_content(page, article_url):
    """한겨레 기사 본문 추출"""
    try:
        # 기존 페이지를 재사용하여 본문 추출
        await page.goto(article_url, wait_until="domcontentloaded", timeout=20000)
        
        # 페이지 로딩 대기
        await page.wait_for_timeout(500)
        
        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')
        
        # 한겨레 기사 본문 셀렉터 시도
        selectors = [
            ".ArticleText",  # 한겨레 주요 본문
            ".article-text",
            ".article-body", 
            ".news-article-body",
            ".story-content",
            ".entry-content",
            "#article-body",
            ".article-content",
            ".text",
            ".content"
        ]
        
        content = ""
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                content = clean_text(element.get_text())
                if len(content) > 100:  # 충분한 길이의 본문이 있으면 즉시 반환
                    break
        
        # 본문이 너무 짧으면 기본 메시지
        if len(content) < 50:
            content = "본문을 추출할 수 없습니다."
            
        return content
        
    except Exception as e:
        logger.error(f"한겨레 본문 추출 실패 - {article_url}: {e}")
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
        
        for category, url in CATEGORY_URLS.items():
            try:
                print(f"🔍 한겨레 {category} 카테고리 크롤링 중...")
                
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
                
                # 페이지가 완전히 로드될 때까지 대기
                await page.wait_for_selector('li.ArticleList_item___OGQO', timeout=30000)
                
                count = 0
                target_count = 30
                page_num = 1
                max_pages = 20  # 페이지 수 증가
                
                while count < target_count and page_num <= max_pages:
                    try:
                        print(f"📄 한겨레 {category} 페이지 {page_num} 처리 중...")
                        
                        # 현재 페이지의 기사 링크들 수집
                        try:
                            await page.wait_for_selector('li.ArticleList_item___OGQO a', timeout=15000)
                        except:
                            # 첫 번째 페이지가 아니면 다른 방법으로 시도
                            if page_num > 1:
                                # URL 직접 조작으로 페이지 이동
                                base_url = url
                                if '?' in base_url:
                                    page_url = f"{base_url}&page={page_num}"
                                else:
                                    page_url = f"{base_url}?page={page_num}"
                                
                                print(f"📄 한겨레 {category} 페이지 {page_num} 직접 URL 접근: {page_url}")
                                await page.goto(page_url, wait_until="domcontentloaded", timeout=30000)
                                await page.wait_for_timeout(3000)
                                
                                try:
                                    await page.wait_for_selector('li.ArticleList_item___OGQO a', timeout=10000)
                                except:
                                    print(f"❌ 한겨레 {category} 페이지 {page_num}: 기사 목록 없음")
                                    break
                        
                        # 페이지 HTML 가져오기
                        html = await page.content()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # 기사 링크 추출 (더 포괄적으로)
                        article_selectors = [
                            'li.ArticleList_item___OGQO a',
                            '.article-list a',
                            '.news-list a',
                            'article a',
                            '.headline a',
                            'a[href*="/arti/"]'
                        ]
                        
                        article_links = []
                        for selector in article_selectors:
                            article_links = soup.select(selector)
                            if article_links:
                                break
                        
                        if not article_links:
                            print(f"⚠️ 한겨레 {category} 페이지 {page_num}: 기사 링크를 찾을 수 없습니다.")
                            break
                        
                        print(f"📄 한겨레 {category} 페이지 {page_num}에서 {len(article_links)}개 기사 발견")
                        
                        # 각 기사 링크 처리
                        processed_in_page = 0
                        for link in article_links:
                            if count >= target_count:
                                break
                                
                            href = link.get('href')
                            if not href:
                                continue
                            
                            # href가 리스트인 경우 첫 번째 요소 사용
                            if isinstance(href, list):
                                href = href[0] if href else ""
                                
                            # 상대 경로를 절대 경로로 변환
                            if href.startswith('/'):
                                article_url = f"https://www.hani.co.kr{href}"
                            else:
                                article_url = href
                            
                            # 중복 체크
                            if any(article['url'] == article_url for article in all_articles):
                                continue
                            
                            # 제목 추출
                            title_elem = link.select_one('.BaseArticleCard_title__TVFqt')
                            if not title_elem:
                                continue
                                
                            title = clean_text(title_elem.get_text().strip())
                            
                            # 제목 길이 체크 (너무 짧은 제목 제외)
                            if len(title) < 3:
                                continue
                            
                            # 본문 추출
                            print(f"📄 [{count+1}/{target_count}] {title} - 본문 추출 중...")
                            content = await extract_article_content(page, article_url)
                            
                            # 기사 정보 저장
                            article_info = {
                                'title': title,
                                'url': article_url,
                                'category': category,
                                'content': content,
                                'source': 'hani',
                                'published_at': datetime.now().isoformat()
                            }
                            
                            all_articles.append(article_info)
                            count += 1
                            processed_in_page += 1
                            
                            print(f"✅ [{count}/{target_count}] {title[:50]}... (본문 {len(content)}자)")
                            
                            if count >= target_count:
                                break
                        
                        print(f"📄 한겨레 {category} 페이지 {page_num}에서 {processed_in_page}개 기사 처리 완료")
                        
                        # 다음 페이지로 이동
                        try:
                            # 목표 개수에 도달했으면 중단
                            if count >= target_count:
                                break
                            
                            # 방법 1: 페이지네이션 버튼 클릭 시도
                            next_selectors = [
                                'a[aria-label="다음 페이지"]',
                                'button[aria-label="다음 페이지"]',
                                '.pagination .next',
                                '.paging .next',
                                'a:has-text("다음")',
                                'button:has-text("다음")',
                                '.page-next',
                                '.btn-next',
                                f'a[href*="page={page_num + 1}"]',
                                '.pagination a:last-child',
                                '.paging a:last-child'
                            ]
                            
                            next_clicked = False
                            for selector in next_selectors:
                                try:
                                    next_button = page.locator(selector).first
                                    if await next_button.is_visible() and await next_button.is_enabled():
                                        await next_button.click()
                                        await page.wait_for_timeout(3000)
                                        
                                        # 페이지가 실제로 변경되었는지 확인
                                        try:
                                            await page.wait_for_selector('li.ArticleList_item___OGQO a', timeout=10000)
                                            next_clicked = True
                                            page_num += 1
                                            print(f"✅ 한겨레 {category} 페이지 {page_num}로 이동 성공 (버튼 클릭)")
                                            break
                                        except:
                                            print(f"  ❌ 버튼 클릭 후 페이지 로딩 실패")
                                            continue
                                except Exception as next_error:
                                    continue
                            
                            # 방법 2: 버튼 클릭이 실패하면 URL 직접 조작
                            if not next_clicked:
                                page_num += 1
                                base_url = url
                                if '?' in base_url:
                                    next_url = f"{base_url}&page={page_num}"
                                else:
                                    next_url = f"{base_url}?page={page_num}"
                                
                                print(f"📄 한겨레 {category} 페이지 {page_num} URL 직접 접근: {next_url}")
                                
                                try:
                                    await page.goto(next_url, wait_until="domcontentloaded", timeout=30000)
                                    await page.wait_for_timeout(3000)
                                    
                                    # 페이지가 실제로 변경되었는지 확인
                                    await page.wait_for_selector('li.ArticleList_item___OGQO a', timeout=10000)
                                    print(f"✅ 한겨레 {category} 페이지 {page_num}로 이동 성공 (URL 조작)")
                                except Exception as url_error:
                                    print(f"❌ 한겨레 {category} URL 직접 접근 실패: {url_error}")
                                    break
                                
                        except Exception as e:
                            print(f"❌ 한겨레 {category}: 페이지 이동 중 오류 - {e}")
                            break
                            
                    except Exception as e:
                        print(f"❌ 한겨레 {category} 페이지 처리 중 오류: {e}")
                        break
                
                await page.close()
                print(f"✅ 한겨레 {category}에서 {count}개 기사 수집 완료")
                
            except Exception as e:
                print(f"❌ Error crawling 한겨레 {category}: {e}")
                if 'page' in locals():
                    await page.close()
                continue
        
        await browser.close()
    
    print(f"✅ 한겨레에서 총 {len(all_articles)}개 기사 수집 완료")
    return all_articles

if __name__ == "__main__":
    articles = asyncio.run(get_articles())
    print(f"한겨레 총 {len(articles)}개 기사 수집 완료")
    for article in articles:
        print(f"- {article['category']}: {article['title']}")