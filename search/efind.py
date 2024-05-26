import requests


def get_description(component_name, efind_token):
    # Define the API endpoint
    endpoint = f"https://efind.ru/api/search/{component_name}"

    # Define the query parameters
    params = {
        "access_token": efind_token,
        # "stock": 1,
        # "hp": 1,
        # "cur": "rur",
    }

    def get_most_informative_note(response):
        max_length = 0
        most_informative_note = ""

        for item in response:
            for row in item["rows"]:
                note = row.get("note", "")
                if len(note) > max_length:
                    max_length = len(note)
                    most_informative_note = note

        return most_informative_note

    # Send a GET request to the API endpoint
    response = requests.get(endpoint, params=params)

    # Check if the request was successful
    if response.status_code == 200:
        # Parse the JSON response
        data = response.json()

        # Extract the component_desc from the data
        if len(data) != 0:
            component_desc = get_most_informative_note(data)
        else:
            print(f"Error: Cant find component {component_name} in the efind database")
            return None

    else:
        print(f"Error: Received status code {response.status_code}")
        return None