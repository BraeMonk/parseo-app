import os
import re
import requests
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
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        words = [word for word in text.split() if word and word not in self.stop_words and len(word) > 2]
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
            readability_interpretation = self.get_readability_interpretation(readability)
        except:
            readability = 0
            readability_interpretation = "Unable to calculate"
        
        return {
            'readabilityScore': readability,
            'wordCount': len(text.split()),
            'readabilityInterpretation': readability_interpretation,
            'headingDistribution': self.count_headings(soup),
            'contentTags': {
                'strong': len(soup.find_all('strong')),
                'em': len(soup.find_all('em')),
                'blockquote': len(soup.find_all('blockquote')),
                'images': len(soup.find_all('img'))
            }
        }

    def get_readability_interpretation(self, readability_score):
        """Interpret readability score."""
        if readability_score > 60:
            return "Good"
        elif readability_score > 40:
            return "Fair"
        else:
            return "Needs Improvement"

    def analyze_technical(self, url, soup):
        """Analyze technical SEO elements."""
        return {
            'title': self.get_meta_content(soup, 'title'),
            'metaDescription': self.get_meta_content(soup, 'description'),
            'canonical': self.get_canonical(soup),
            'mobileFriendly': bool(soup.find('meta', attrs={'name': 'viewport'})),
            'ssl': self.check_ssl(url),
            'structuredData': bool(soup.find_all('script', type='application/ld+json'))
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
            'internalCount': len(internal_links),
            'externalCount': len(external_links),
            'totalCount': len(internal_links) + len(external_links)
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
            content = self.fetch_url_content(url)
            
            if not content or len(content) < 100:
                return {
                    'error': 'Insufficient content',
                    'keywords': [],
                    'content': {},
                    'technical': {},
                    'links': {},
                    'performance': {},
                    'metadata': {}
                }
            
            soup = BeautifulSoup(content, 'lxml')
            text = soup.get_text(separator=' ', strip=True)
            
            cleaned_words = self.clean_text(text)
            word_freq = Counter(cleaned_words)
            keywords = [word for word, _ in word_freq.most_common(10)]
            
            analysis = {
                'url': url,
                'keywords': keywords,
                'content': self.analyze_content(soup),
                'technical': self.analyze_technical(url, soup),
                'links': self.analyze_links(url, soup),
                'performance': {
                    'totalResources': len(soup.find_all('script')) + len(soup.find_all('link')) + len(soup.find_all('img')),
                    'totalSize': len(content)  # Approximate total size (could be refined further)
                },
                'metadata': {
                    'analysisDuration': time.time() - time.time(),  # This can be adjusted to actual time taken
                    'analyzedAt': datetime.now().isoformat()
                }
            }
            
            if report_file:
                self.write_report(analysis, report_file)
                
            return analysis
        
        except Exception as e:
            print(f"Comprehensive analysis error: {e}")
            return {
                'error': str(e),
                'keywords': [],
                'content': {},
                'technical': {},
                'links': {},
                'performance': {},
                'metadata': {}
            }

    def write_report(self, analysis, report_file):
        try:
            os.makedirs(os.path.dirname(report_file), exist_ok=True)
            with open(report_file, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*50}\n")
                f.write(f"SEO Analysis Report for {analysis['url']}\n")
                f.write(f"Generated on: {datetime.now()}\n")
                f.write(f"{'='*50}\n\n")
                
                f.write("Keywords\n--------\n")
                f.write(', '.join(analysis['keywords']) + '\n\n')
                
                f.write("Content Statistics\n------------------\n")
                for key, value in analysis['content'].items():
                    f.write(f"{key}: {value}\n")
                
                f.write("\nTechnical Analysis\n-------------------\n")
                for key, value in analysis['technical'].items():
                    f.write(f"{key}: {value}\n")
                
                f.write("\nLink Analysis\n-------------\n")
                f.write(f"Internal Links: {analysis['links']['internalCount']}\n")
                f.write(f"External Links: {analysis['links']['externalCount']}\n")
                
                f.write("\nPerformance\n-----------\n")
                f.write(f"Total Resources: {analysis['performance']['totalResources']}\n")
                f.write(f"Total Size: {analysis['performance']['totalSize']} bytes\n")
                
                f.write("\nMetadata\n--------\n")
                f.write(f"Analysis Duration: {analysis['metadata']['analysisDuration']} seconds\n")
                f.write(f"Analyzed At: {analysis['metadata']['analyzedAt']}\n")
                
                f.write("\n" + "="*50 + "\n")
                
        except Exception as e:
            print(f"Error writing report: {e}")

def setup():
    initialize_nltk()
    return SEOAnalyzer()

analyzer = setup()

    return SEOAnalyzer()

analyzer = setup()
