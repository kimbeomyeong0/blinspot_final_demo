# crawler/utils/parser_common.py

import asyncio
from playwright.async_api import async_playwright
import re

async def get_html(url: str, max_retries: int = 3) -> str:
    """
    Playwright를 사용해 웹페이지의 HTML을 가져옵니다.
    타임아웃 시 재시도 로직 포함
    """
    for attempt in range(max_retries):
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                try:
                    page = await browser.new_page()
                    # 타임아웃 시간 증가 (30초 → 60초)
                    await page.goto(url, timeout=60000)
                    # 페이지 로딩 완료 대기
                    await page.wait_for_load_state('networkidle', timeout=30000)
                    content = await page.content()
                    return content
                finally:
                    await browser.close()
        except Exception as e:
            print(f"Error fetching {url} (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {(attempt + 1) * 2} seconds...")
                await asyncio.sleep((attempt + 1) * 2)  # 2초, 4초, 6초 대기
            else:
                print(f"Failed to fetch {url} after {max_retries} attempts")
                return ""  # 빈 문자열 반환
    return ""

def clean_text(text: str) -> str:
    """
    텍스트를 정리합니다.
    """
    if not text:
        return ""
    
    # 여러 공백을 하나로 통합
    text = re.sub(r'\s+', ' ', text)
    # 앞뒤 공백 제거
    text = text.strip()
    
    return text