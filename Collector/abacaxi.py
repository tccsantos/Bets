import requests

response = requests.get("https://www.googleapis.com/youtube/v3/channels?part=contentDetails")

print(response.status_code)
print(response.reason)
print(response.json())