import requests
from bs4 import BeautifulSoup
import re

def search_medical_info(query):
    try:
        search_url = f"https://www.baidu.com/s?wd={requests.utils.quote(query)}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        response = requests.get(search_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        results = []
        for item in soup.find_all('div', class_='result-op')[:5]:
            title_tag = item.find('h3')
            link_tag = item.find('a')
            content_tag = item.find('div', class_='c-abstract')
            
            if title_tag and link_tag:
                result = {
                    'title': title_tag.get_text(strip=True),
                    'url': link_tag.get('href', ''),
                    'content': content_tag.get_text(strip=True) if content_tag else ''
                }
                results.append(result)
        
        return results
    except Exception as e:
        print(f"搜索失败: {e}")
        return []

def fetch_nhc_content(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        content = soup.find('div', class_='article') or soup.find('div', class_='content') or soup.find('main')
        
        if content:
            text = content.get_text(strip=True)
            text = re.sub(r'\s+', ' ', text)
            return text[:3000]
        
        return None
    except Exception as e:
        print(f"获取内容失败: {e}")
        return None

def crawl_medical_knowledge():
    base_urls = [
        'https://www.nhc.gov.cn/',
        'http://www.nhfpc.gov.cn/'
    ]
    
    knowledge_items = []
    
    for url in base_urls:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            links = soup.find_all('a', href=True)
            for link in links[:20]:
                href = link['href']
                if not href.startswith('http'):
                    href = url + href
                
                if 'http' in href and ('health' in href.lower() or 'medical' in href.lower() or 'disease' in href.lower()):
                    title = link.get_text(strip=True)
                    content = fetch_nhc_content(href)
                    
                    if content and len(content) > 100:
                        knowledge_items.append({
                            'title': title,
                            'content': content,
                            'source_url': href,
                            'category': 'health'
                        })
        except Exception as e:
            print(f"爬取失败: {e}")
    
    return knowledge_items
