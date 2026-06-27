import httpx

token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJvd25lckB1YWJlLmNvbSIsInJvbGUiOiJvd25lciIsImV4cCI6MTc4MjY1OTc2OH0.CLkuh5KfnYrUY1il1cSzVftFQE_NslhC7juBwIoG5N8"
url = "http://localhost:8000/api/v1/sandbox/execute"

headers = {"Authorization": f"Bearer {token}"}
payload = {"code": 'print("Calculated sales pipeline: 15 leads generated!")'}

response = httpx.post(url, json=payload, headers=headers)
print(response.json())
