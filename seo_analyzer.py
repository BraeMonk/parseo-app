import os
import re
import requests
import time
from lxml import html
from bs4 import BeautifulSoup
from collections import Counter, defaultdict
from datetime import datetime
from textstat import flesch_reading_ease
from urllib.parse import urljoin, urlparse
import nltk
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer

def initialize_nltk():
    """Initialize NLTK with only required packages."""
    try:
        nltk.data.find('corpora/stopwords')
    except LookupError:
        print("Downloading stopwords package...")
        nltk.download('stopwords', quiet=True)

class SEOAnalyzer:
    def __init__(self):
        self.stemmer = PorterStemmer()
        # Add common English stop words
        self.stop_words = set(stopwords.words('english')).union({
            'the', 'and', 'is', 'in', 'to', 'it', 'that', 'we', 'for', 'an', 'are', 
            'by', 'be', 'this', 'with', 'i', 'you', 'not', 'or', 'on', 'your'
        })
        self.keyword_library = defaultdict(int)
        self.session = requests.Session()
        
    def clean_text(self, text):
        """Clean and normalize text without using NLTK tokenizer."""
        if not text:
            return []
        # Convert to lowercase and replace non-word characters with spaces
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        # Split on whitespace and filter
        words = [word for word in text.split() 
                if word and word not in self.stop_words and len(word) > 2]
        # Stem words
        return [self.stemmer.stem(word) for word in words]

    def fetch_url_content(self, url):
        """Fetch URL content with error handling and user agent."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = self.session.get(url, timeout=10, headers=headers)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None

    def analyze_content(self, soup):
        """Analyze content quality and structure."""
        text = soup.get_text(separator=' ', strip=True)
        try:
            readability = flesch_reading_ease(text)
        except:
            readability = 0
            
        return {
            'readability_score': readability,
            'word_count': len(text.split()),
            'heading_distribution': self.count_headings(soup),
            'content_tags': {
                'strong': len(soup.find_all('strong')),
                'em': len(soup.find_all('em')),
                'blockquote': len(soup.find_all('blockquote')),
                'images': len(soup.find_all('img'))
            }
        }

    def analyze_technical(self, url, soup):
        """Analyze technical SEO elements."""
        return {
            'title': self.get_meta_content(soup, 'title'),
            'meta_description': self.get_meta_content(soup, 'description'),
            'canonical': self.get_canonical(soup),
            'mobile_friendly': bool(soup.find('meta', attrs={'name': 'viewport'})),
            'ssl_certificate': self.check_ssl(url),
            'structured_data': bool(soup.find_all('script', type='application/ld+json'))
        }

    def analyze_links(self, base_url, soup):
        """Analyze internal and external links."""
        links = soup.find_all('a', href=True)
        parsed_base = urlparse(base_url)
        
        internal_links = []
        external_links = []
        
        for link in links:
            href = link['href']
            try:
                full_url = urljoin(base_url, href)
                parsed_href = urlparse(full_url)
                
                if parsed_href.netloc == parsed_base.netloc:
                    internal_links.append(href)
                else:
                    external_links.append(href)
            except:
                continue
                
        return {
            'internal_links': internal_links,
            'external_links': external_links
        }

    def get_meta_content(self, soup, meta_name):
        """Extract meta tag content."""
        if meta_name == 'title':
            return soup.title.string if soup.title else None
        meta = soup.find('meta', attrs={'name': meta_name})
        return meta['content'] if meta else None

    def get_canonical(self, soup):
        """Get canonical URL."""
        canonical = soup.find('link', rel='canonical')
        return canonical['href'] if canonical else None

    def count_headings(self, soup):
        """Count heading tags distribution."""
        return {f'h{i}': len(soup.find_all(f'h{i}')) for i in range(1, 7)}

    def check_ssl(self, url):
        """Check if URL uses HTTPS."""
        return url.startswith('https://')
    def analyze_url(self, url, report_file=None):
        try:
            # Step 1: Fetch content from the URL
            print(f"Fetching content from {url}...")
            content = self.fetch_url_content(url)
            
            # Step 2: Check for insufficient content
            if not content or len(content) < 100:
                return {
                    'error': 'Insufficient content',
                    'keywords': [],
                    'content_stats': {},
                    'technical_stats': {},
                    'link_stats': {}
                }
            
            # Step 3: Parse the content
            print("Parsing content...")
            soup = BeautifulSoup(content, 'lxml')
            text = soup.get_text(separator=' ', strip=True)
            
            # Step 4: Process text and update keyword library
            print("Processing text and updating keyword library...")
            cleaned_words = self.clean_text(text)
            for word in cleaned_words:
                self.keyword_library[word] += 1
            
            # Step 5: Generate keywords
            print("Generating keywords...")
            word_freq = Counter(cleaned_words)
            keywords = [word for word, _ in word_freq.most_common(10)]
            
            # Step 6: Perform SEO analysis
            print("Performing SEO analysis...")
            analysis = {
                'url': url,
                'keywords': keywords,
                'content_stats': self.analyze_content(soup),
                'technical_stats': self.analyze_technical(url, soup),
                'link_stats': self.analyze_links(url, soup)
            }
            
            # Step 7: Write report if required
            if report_file:
                print("Writing report...")
                self.write_report(analysis, report_file)
                
            return analysis
        
        except Exception as e:
            print(f"Comprehensive analysis error: {e}")
            return {
                'error': str(e),
                'keywords': [],
                'content_stats': {},
                'technical_stats': {},
                'link_stats': {}
            }

    def write_report(self, analysis, report_file):
        """Write analysis results to file."""
        try:
            os.makedirs(os.path.dirname(report_file), exist_ok=True)
            with open(report_file, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*50}\n")
                f.write(f"SEO Analysis Report for {analysis['url']}\n")
                f.write(f"Generated on: {datetime.now()}\n")
                f.write(f"{'='*50}\n\n")
                
                # Write Keywords
                f.write("Keywords\n--------\n")
                f.write(', '.join(analysis['keywords']) + '\n\n')
                
                # Write Content Statistics
                f.write("Content Statistics\n------------------\n")
                for key, value in analysis['content_stats'].items():
                    f.write(f"{key}: {value}\n")
                
                # Write Technical Analysis
                f.write("\nTechnical Analysis\n-------------------\n")
                for key, value in analysis['technical_stats'].items():
                    f.write(f"{key}: {value}\n")
                
                # Write Link Analysis
                f.write("\nLink Analysis\n-------------\n")
                f.write(f"Internal Links: {len(analysis['link_stats']['internal_links'])}\n")
                f.write(f"External Links: {len(analysis['link_stats']['external_links'])}\n")
                
                f.write("\n" + "="*50 + "\n")
                
        except Exception as e:
            print(f"Error writing report: {e}")

def setup():
    initialize_nltk()
    return SEOAnalyzer()

analyzer = setup()
