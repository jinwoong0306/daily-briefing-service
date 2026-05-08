"""
네이버 뉴스 기사 본문 스크래퍼 모듈

네이버 뉴스 및 원본 언론사 URL에서 기사 전문(full text)을 추출합니다.
HTML 파싱에 BeautifulSoup을 사용합니다.
"""

import re
import time
import logging
import warnings

warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL.*")

import requests
import googlenewsdecoder
from bs4 import BeautifulSoup, Comment
from typing import Optional

logging.getLogger("urllib3.connection").setLevel(logging.ERROR)


class NaverNewsScraper:
    """뉴스 기사 본문 스크래퍼 (네이버 뉴스 + 일반 언론사 지원)"""

    # 네이버 뉴스 본문 CSS 셀렉터 (우선순위 순)
    NAVER_SELECTORS = [
        "#dic_area",
        "#newsct_article",
        "#articeBody",
        "#articleBodyContents",
    ]

    # 일반 언론사에서 자주 사용하는 본문 셀렉터 (우선순위 순)
    GENERIC_SELECTORS = [
        "#article-view-content-div",    # 많은 한국 언론사 (보드 기반)
        ".article_view",                # 일반적인 기사 본문
        ".article-body",
        ".article_body",
        "#articleBody",
        "#article_body",
        ".news_body",
        ".news-body",
        "#newsBody",
        ".view_article",
        "#view_article",
        ".entry-content",              # 블로그형 뉴스
        ".post-content",
        "article .content",
        "article .text",
        "#content .article",
        ".story-body",
        "#article-body",
        "#articleContent",
        ".article-content",
        ".article_content",
        "#news_body_area",
        ".viewConts",                  # 일부 언론사
        "#textBody",
        ".article_txt",
        ".newsCont",                   # dnews 등
        "#_article",                   # tvdaily 등
    ]

    # 본문에서 제거할 불필요 요소
    UNWANTED_TAGS = [
        "script", "style", "iframe", "noscript",
        "header", "footer", "nav", "aside",
        "figure", "figcaption",
    ]

    UNWANTED_CLASSES = [
        "ads", "adv", "advertisement", "ad-banner", "ad_banner",
        "social-share", "share_btn", "comment_area", "related_news",
        "sidebar", "copyright",
        "photo_caption", "img_desc", "end_photo_org",
    ]

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    def __init__(self, delay: float = 0.3, timeout: tuple = (3.0, 7.0)):
        """
        스크래퍼 초기화

        Args:
            delay: 각 요청 간 대기 시간(초) - 서버 부하 방지
            timeout: (연결 타임아웃, 읽기 타임아웃)
        """
        self.delay = delay
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def _is_naver_news_url(self, url: str) -> bool:
        """네이버 뉴스 URL인지 확인"""
        return "n.news.naver.com" in url or "news.naver.com" in url

    def _clean_text(self, text: str) -> str:
        """
        추출된 텍스트 정리

        - 불필요한 공백/개행 정리
        - 특수 문자 정규화
        """
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        text = text.strip()
        return text

    def _remove_unwanted_elements(self, soup: BeautifulSoup):
        """불필요한 HTML 요소 제거"""
        # HTML 주석 제거
        for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
            comment.extract()

        # 불필요 태그 제거
        for tag_name in self.UNWANTED_TAGS:
            for tag in soup.find_all(tag_name):
                tag.decompose()

        # 불필요 클래스 제거 (정확한 클래스명 매칭)
        for cls in self.UNWANTED_CLASSES:
            for tag in soup.find_all(class_=lambda c: c and cls in c.lower().split()):
                tag.decompose()

    def _extract_by_selectors(self, soup: BeautifulSoup, selectors: list[str]) -> Optional[str]:
        """셀렉터 목록에서 순서대로 본문 추출 시도"""
        for selector in selectors:
            el = soup.select_one(selector)
            if el:
                text = el.get_text(separator="\n", strip=True)
                cleaned = self._clean_text(text)
                # 너무 짧으면 본문이 아닐 가능성 높음
                if len(cleaned) >= 100:
                    return cleaned
        return None

    def _extract_by_heuristic(self, soup: BeautifulSoup) -> Optional[str]:
        """
        휴리스틱 기반 본문 추출 (폴백)

        페이지에서 가장 텍스트가 많은 블록 요소를 본문으로 간주
        """
        candidates = []

        for tag in soup.find_all(["div", "article", "section", "main", "td"]):
            # 자식 태그 중 <p> 또는 <br> 태그가 있는 블록만 후보로
            paragraphs = tag.find_all(["p", "br"], recursive=True)
            if len(paragraphs) >= 1:
                text = tag.get_text(separator="\n", strip=True)
                cleaned = self._clean_text(text)
                if len(cleaned) >= 200:
                    candidates.append((len(cleaned), cleaned, tag))

        if not candidates:
            return None

        # 가장 긴 텍스트 블록 선택 (단, 너무 길면 전체 페이지일 수 있으므로 필터)
        candidates.sort(key=lambda x: x[0], reverse=True)

        # 최적 후보 선택: 너무 크지 않은 것 중 가장 긴 텍스트
        for length, text, tag in candidates:
            # body 전체나 wrapper급은 건너뜀
            tag_id = tag.get("id", "")
            tag_classes = " ".join(tag.get("class", []))
            if tag_id in ("wrap", "wrapper", "__next", "root", "app"):
                continue
            if any(skip in tag_classes for skip in ("wrap", "wrapper", "container")):
                continue
            return text

        return None

    def _resolve_google_news_url(self, url: str) -> str:
        """
        구글 뉴스 RSS 링크(news.google.com/rss/articles/...)의 실제 목적지 URL을 가져옴
        """
        if "news.google.com" not in url:
            return url

        try:
            # googlenewsdecoder 패키지를 사용하여 디코딩
            # 이는 base64 인코딩된 URL과 자바스크립트 리다이렉트를 처리해줌
            res = googlenewsdecoder.new_decoderv1(url)
            if res.get("status") and res.get("decoded_url"):
                return res["decoded_url"]
        except Exception:
            pass

        # 디코딩 실패 시 기존 방식(requests head/get)으로 시도
        try:
            resp = self.session.head(url, allow_redirects=True, timeout=self.timeout)
            return resp.url
        except Exception:
            try:
                resp = self.session.get(url, allow_redirects=True, timeout=self.timeout)
                return resp.url
            except Exception:
                return url

    def _fetch_html(self, url: str) -> tuple[Optional[BeautifulSoup], str]:
        """URL에서 HTML을 가져와 BeautifulSoup 객체와 최종 URL 반환"""
        try:
            response = self.session.get(url, timeout=self.timeout, allow_redirects=True)
            response.raise_for_status()

            # EUC-KR 등 인코딩이 깨지는 현상을 방지하기 위해
            # requests가 임의로 추측한 텍스트(.text) 대신 순수 바이트(.content)를 넘김
            return BeautifulSoup(response.content, "lxml"), response.url
        except requests.exceptions.RequestException:
            return None, url

    def scrape_article(self, url: str) -> Optional[str]:
        """
        단일 기사 본문 추출 (네이버 뉴스 + 일반 언론사 지원)

        Args:
            url: 기사 URL

        Returns:
            str: 기사 본문 텍스트 또는 None (추출 실패 시)
        """
        url = self._resolve_google_news_url(url)

        soup, final_url = self._fetch_html(url)
        if not soup:
            return None

        self._remove_unwanted_elements(soup)

        # 1단계: 네이버 뉴스 셀렉터 시도
        if self._is_naver_news_url(final_url):
            result = self._extract_by_selectors(soup, self.NAVER_SELECTORS)
            if result:
                return result

        # 2단계: 일반 언론사 셀렉터 시도
        result = self._extract_by_selectors(soup, self.GENERIC_SELECTORS)
        if result:
            return result

        # 3단계: 휴리스틱 폴백
        return self._extract_by_heuristic(soup)

    def scrape_articles(self, articles: list[dict]) -> list[dict]:
        """
        여러 기사의 본문을 일괄 추출하여 원본 데이터에 추가

        Args:
            articles: API에서 받은 기사 리스트

        Returns:
            list[dict]: 각 기사에 'fullText' 필드가 추가된 리스트
        """
        enriched = []

        for i, article in enumerate(articles):
            naver_link = article.get("link", "")
            original_link = article.get("originallink", "")
            full_text = None

            # 네이버 뉴스 링크 우선 시도, 실패 시 원본 링크 시도
            for url in [naver_link, original_link]:
                if url:
                    full_text = self.scrape_article(url)
                    if full_text:
                        break

            enriched_article = dict(article)
            enriched_article["fullText"] = full_text or ""
            enriched_article["fullTextAvailable"] = full_text is not None
            enriched.append(enriched_article)

            # 서버 부하 방지 대기 (마지막 항목 제외)
            if i < len(articles) - 1:
                time.sleep(self.delay)

        return enriched
