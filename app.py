import os
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
from datetime import datetime

# Import your existing SEO analysis code
from seo_analyzer import SEOAnalyzer, initialize_nltk

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
app.wsgi_app = ProxyFix(app.wsgi_app)  # Handle proxy headers

# Initialize NLTK resources
initialize_nltk()
analyzer = SEOAnalyzer()

@app.route('/analyze', methods=['POST'])
def analyze_url():
    start_time = datetime.now()
    
    try:
        # Get URL from request
        data = request.json
        url = data.get('url')
        
        if not url:
            return jsonify({
                "error": "No URL provided",
                "metadata": {
                    "analyzedAt": start_time.isoformat(),
                    "analysisDuration": 0
                }
            }), 400
        
        # Perform SEO analysis
        try:
            analysis = analyzer.analyze_url(url)
        except Exception as analysis_error:
            logger.error(f"Analysis failed for {url}: {analysis_error}")
            return jsonify({
                "error": "Failed to analyze URL",
                "metadata": {
                    "analyzedAt": start_time.isoformat(),
                    "analysisDuration": 0
                }
            }), 500
        
        # Calculate analysis duration
        end_time = datetime.now()
        analysis_duration = (end_time - start_time).total_seconds()
        
        # Transform analysis to match SEOAnalysisResponse model
        response = {
            "keywords": analysis.get('keywords', []),
            "content": {
                "readabilityScore": analysis['content_stats']['readability_score'],
                "readabilityInterpretation": _interpret_readability(analysis['content_stats']['readability_score']),
                "wordCount": analysis['content_stats']['word_count']
            },
            "technical": {
                "mobileFriendly": analysis['technical_stats']['mobile_friendly'],
                "ssl": analysis['technical_stats']['ssl_certificate'],
                "structuredData": False  # Add your structured data check
            },
            "links": {
                "internalCount": len(analysis['link_stats']['internal_links']),
                "externalCount": len(analysis['link_stats']['external_links']),
                "totalCount": len(analysis['link_stats']['internal_links']) + len(analysis['link_stats']['external_links'])
            },
            "performance": {
                "totalResources": len(analysis.get('resource_stats', [])),
                "totalSize": analysis.get('total_page_size', 0)
            },
            "metadata": {
                "analyzedAt": start_time.isoformat(),
                "analysisDuration": analysis_duration
            }
        }
        
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"Unexpected error in analysis: {e}")
        return jsonify({
            "error": str(e),
            "metadata": {
                "analyzedAt": start_time.isoformat(),
                "analysisDuration": 0
            }
        }), 500

def _interpret_readability(score):
    """Interpret Flesch Reading Ease score"""
    if score > 80:
        return "Very Easy"
    elif score > 60:
        return "Easy"
    elif score > 40:
        return "Moderate"
    elif score > 20:
        return "Difficult"
    else:
        return "Very Difficult"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
