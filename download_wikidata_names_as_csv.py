from urllib.parse import urlencode

import requests

select = """
SELECT DISTINCT ?label ?item WHERE {
  ?item wdt:P225 ?taxonname.
  ?item rdfs:label ?label. FILTER (langMatches( lang(?label), "EN" ) ) 
}
"""

result = requests.get('https://query.wikidata.org/sparql?%s' % urlencode([('query', select)]), headers={'Accept': 'text/tab-separated-values'}).text

with open('names.csv', 'w') as f:
    f.write(result)
