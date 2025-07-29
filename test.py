from google.oauth2 import service_account
import google.auth.transport.requests

# Load your service account JSON file
SCOPES = ["https://www.googleapis.com/auth/firebase.messaging"]  # 🔥 Add the correct scope
credentials = service_account.Credentials.from_service_account_file(
    "google_service.json", scopes=SCOPES  # ✅ Specify the required scope
)

# Request an access token
request = google.auth.transport.requests.Request()
credentials.refresh(request)

# Use this access token in your API request
FIREBASE_ACCESS_TOKEN = credentials.token

print("Access Token:", FIREBASE_ACCESS_TOKEN)
