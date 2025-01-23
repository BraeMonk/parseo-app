#!/bin/sh

# Start the main app
python app.py &

# Start the SEO analyzer
python seo_analyzer.py &

# Wait for any process to exit
wait -n

# Exit with the status of the first process to exit
exit $?
