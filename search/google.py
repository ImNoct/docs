from bs4 import BeautifulSoup
import requests, json, lxml


def get_description(component_name, component_class=''):
    query = component_name

    # if component_class:
    #     query = name(component_class) + query
        
    params = {
        "q": query,          # query example
        "hl": "ru",          # language
        "gl": "ru",          # country of the search, UK -> United Kingdom
        "start": 0,          # number page by default up to 0
        "num": 10            # parameter defines the maximum number of results to return.
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
    }

    page_limit = 1          # page limit if you don't need to fetch everything
    page_num = 0

    data = []

    while True:
        page_num += 1
        response = requests.get("https://www.google.com/search", params=params, headers=headers, timeout=30)

        if response.status_code != 200:
            print(f"Error: Received status code {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, 'lxml')

        for result in soup.select(".tF2Cxc"):
            title = result.select_one(".DKV0Md").text
            try:
                snippet = result.select_one(".VwiC3b span").text
            except:
                snippet = None
            link = result.select_one(".yuRUbf a")["href"]

            data.append({
            "title": title,
            "description": snippet,
            "link": link
            })

        if page_num == page_limit:
            break

        if soup.select_one(".d6cvqb a[id=pnnext]"):
            params["start"] += 10
        else:
            break

    # print(json.dumps(data, indent=2, ensure_ascii=False))

    # return only first one
    return ' '.join([component_name, data[0]['description']])
