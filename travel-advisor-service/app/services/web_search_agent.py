"""
Web Search Agent - Tự động tìm kiếm và extract thông tin từ web khi database không đủ

Flow:
1. Nhận query và context từ expert
2. Tìm kiếm trên Google/VnExpress
3. Extract content từ top results
4. LLM tổng hợp thông tin
5. Trả về kết quả có confidence score
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import quote_plus

from app.services.llm_client import llm_client

logger = logging.getLogger(__name__)


class WebSearchResult:
    """Represents a search result with content"""
    
    def __init__(self, 
                 url: str, 
                 title: str, 
                 content: str,
                 source: str = "web",
                 relevance_score: float = 0.0):
        self.url = url
        self.title = title
        self.content = content
        self.source = source
        self.relevance_score = relevance_score
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'url': self.url,
            'title': self.title,
            'content': self.content[:500],  # Limit for display
            'source': self.source,
            'relevance_score': self.relevance_score,
            'timestamp': self.timestamp.isoformat()
        }


class WebSearchAgent:
    """Agent for searching and extracting information from the web"""
    
    def __init__(self):
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        self.headers = {'User-Agent': self.user_agent}
        
        # Trusted sources for Vietnamese travel info
        self.trusted_sources = [
            'vnexpress.net',
            'dantri.com.vn',
            'vi.wikipedia.org',
            'dulich.cntraveller.vn',
            'travel.com.vn',
            'vietnamnet.vn'
        ]
    
    def search_web(self, 
                   query: str, 
                   province: Optional[str] = None,
                   max_results: int = 5) -> List[WebSearchResult]:
        """
        Tìm kiếm thông tin trên web
        
        Args:
            query: Câu query cần tìm
            province: Tỉnh/thành phố (để tăng độ chính xác)
            max_results: Số lượng kết quả tối đa
            
        Returns:
            List of WebSearchResult
        """
        try:
            # Build search query
            search_query = query
            if province:
                search_query = f"{query} {province} Vietnam"
            
            logger.info(f"🔍 Web search: {search_query}")
            
            # Method 1: Try DuckDuckGo (no API key needed)
            results = self._search_duckduckgo(search_query, max_results)
            
            if not results:
                # Method 2: Try direct VnExpress search
                results = self._search_vnexpress(search_query, max_results)
            
            logger.info(f"📄 Found {len(results)} web results")
            return results
            
        except Exception as e:
            logger.error(f"Error in web search: {e}")
            return []
    
    def _search_duckduckgo(self, query: str, max_results: int) -> List[WebSearchResult]:
        """Search using DuckDuckGo HTML"""
        try:
            url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code != 200:
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            # Parse DuckDuckGo results
            for result_div in soup.find_all('div', class_='result')[:max_results]:
                try:
                    link = result_div.find('a', class_='result__a')
                    if not link:
                        continue
                    
                    title = link.get_text(strip=True)
                    href = link.get('href', '')
                    
                    # Extract actual URL from DuckDuckGo redirect
                    if 'uddg=' in href:
                        actual_url = href.split('uddg=')[1].split('&')[0]
                    else:
                        actual_url = href
                    
                    # Get snippet
                    snippet_div = result_div.find('a', class_='result__snippet')
                    snippet = snippet_div.get_text(strip=True) if snippet_div else ""
                    
                    # Extract content from page
                    content = self._extract_content(actual_url)
                    if not content:
                        content = snippet
                    
                    # Calculate relevance based on source
                    relevance = self._calculate_relevance(actual_url, title, content)
                    
                    results.append(WebSearchResult(
                        url=actual_url,
                        title=title,
                        content=content,
                        source='duckduckgo',
                        relevance_score=relevance
                    ))
                    
                except Exception as e:
                    logger.debug(f"Error parsing result: {e}")
                    continue
            
            return results
            
        except Exception as e:
            logger.error(f"DuckDuckGo search error: {e}")
            return []
    
    def _search_vnexpress(self, query: str, max_results: int) -> List[WebSearchResult]:
        """Search VnExpress travel section"""
        try:
            # VnExpress travel search
            search_url = f"https://vnexpress.net/tim-kiem?q={quote_plus(query)}&cate_code=1003000"
            response = requests.get(search_url, headers=self.headers, timeout=10)
            
            if response.status_code != 200:
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            # Parse VnExpress results
            for article in soup.find_all('article', class_='item-news')[:max_results]:
                try:
                    link = article.find('a')
                    if not link:
                        continue
                    
                    title = link.get('title', '')
                    url = link.get('href', '')
                    
                    # Get description
                    desc = article.find('p', class_='description')
                    snippet = desc.get_text(strip=True) if desc else ""
                    
                    # Extract full content
                    content = self._extract_content(url)
                    if not content:
                        content = snippet
                    
                    results.append(WebSearchResult(
                        url=url,
                        title=title,
                        content=content,
                        source='vnexpress',
                        relevance_score=0.9  # VnExpress is trusted
                    ))
                    
                except Exception as e:
                    logger.debug(f"Error parsing VnExpress result: {e}")
                    continue
            
            return results
            
        except Exception as e:
            logger.error(f"VnExpress search error: {e}")
            return []
    
    def _extract_content(self, url: str, max_length: int = 2000) -> str:
        """Extract main content from a webpage"""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code != 200:
                return ""
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove scripts, styles, ads
            for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                element.decompose()
            
            # Try to find main content
            main_content = None
            
            # Method 1: Common article selectors
            for selector in ['article', '.article-content', '.content', 'main', '.main-content']:
                main_content = soup.select_one(selector)
                if main_content:
                    break
            
            # Method 2: All paragraphs
            if not main_content:
                main_content = soup.find('body')
            
            if not main_content:
                return ""
            
            # Extract text from paragraphs
            paragraphs = main_content.find_all('p')
            text = ' '.join([p.get_text(strip=True) for p in paragraphs])
            
            # Clean up
            text = re.sub(r'\s+', ' ', text)
            text = text.strip()
            
            # Limit length
            if len(text) > max_length:
                text = text[:max_length] + "..."
            
            return text
            
        except Exception as e:
            logger.debug(f"Error extracting content from {url}: {e}")
            return ""
    
    def _calculate_relevance(self, url: str, title: str, content: str) -> float:
        """Calculate relevance score based on source and content"""
        score = 0.5  # Base score
        
        # Bonus for trusted sources
        for source in self.trusted_sources:
            if source in url:
                score += 0.3
                break
        
        # Bonus for content length (more content = more reliable)
        if len(content) > 500:
            score += 0.1
        if len(content) > 1000:
            score += 0.1
        
        return min(score, 1.0)
    
    def synthesize_answer(self,
                         query: str,
                         search_results: List[WebSearchResult],
                         context: Optional[str] = None) -> Dict[str, Any]:
        """
        Sử dụng LLM để tổng hợp thông tin từ web search results
        
        Args:
            query: Câu hỏi gốc
            search_results: Kết quả tìm kiếm từ web
            context: Context bổ sung (database results, user preferences, etc.)
            
        Returns:
            Dict với answer và confidence score
        """
        try:
            if not search_results:
                return {
                    'answer': None,
                    'confidence': 0.0,
                    'sources': []
                }
            
            # Build prompt for LLM
            sources_text = "\n\n".join([
                f"[Nguồn {i+1} - {result.source}]\nTiêu đề: {result.title}\nNội dung: {result.content}"
                for i, result in enumerate(search_results[:3])  # Top 3 results
            ])
            
            context_text = f"\nThông tin từ database:\n{context}\n" if context else ""
            
            prompt = f"""Dựa trên các nguồn thông tin sau, hãy trả lời câu hỏi một cách chính xác và hữu ích.

Câu hỏi: {query}
{context_text}
Thông tin từ web:
{sources_text}

Yêu cầu:
- Tổng hợp thông tin từ các nguồn trên
- Ưu tiên thông tin từ nguồn uy tín (VnExpress, Wikipedia)
- Trả lời ngắn gọn, đầy đủ
- Nếu thông tin không đủ hoặc không chính xác, hãy nói rõ

Trả lời:"""
            
            # Get LLM response
            response = llm_client.complete(prompt, max_tokens=500)
            
            # Calculate confidence based on:
            # 1. Number of sources
            # 2. Average relevance of sources
            # 3. LLM response quality
            avg_relevance = sum(r.relevance_score for r in search_results) / len(search_results)
            source_count_factor = min(len(search_results) / 3, 1.0)
            confidence = (avg_relevance * 0.6 + source_count_factor * 0.4)
            
            return {
                'answer': response,
                'confidence': confidence,
                'sources': [r.to_dict() for r in search_results[:3]],
                'method': 'web_search',
                'query': query
            }
            
        except Exception as e:
            logger.error(f"Error synthesizing answer: {e}")
            return {
                'answer': None,
                'confidence': 0.0,
                'sources': []
            }


# Global instance
web_search_agent = WebSearchAgent()


def search_and_synthesize(query: str, 
                          province: Optional[str] = None,
                          context: Optional[str] = None,
                          max_results: int = 5) -> Dict[str, Any]:
    """
    Convenience function for one-step search and synthesis
    
    Usage:
        result = search_and_synthesize(
            query="Những địa điểm nổi tiếng ở Huế",
            province="Thừa Thiên Huế",
            context="User đang tìm địa điểm lịch sử"
        )
        
        print(result['answer'])
        print(f"Confidence: {result['confidence']}")
        print(f"Sources: {len(result['sources'])}")
    """
    search_results = web_search_agent.search_web(query, province, max_results)
    return web_search_agent.synthesize_answer(query, search_results, context)
