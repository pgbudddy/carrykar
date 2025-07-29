from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# Firebase Server Key (Replace this with your own key from Firebase Console)
FIREBASE_SERVER_KEY = "AIzaSyDEVX0Iv8pnEGTpdHa2rhQgZxqdlhlBBYc"

FIREBASE_ACCESS_TOKEN = "ya29.c.c0ASRK0GZ7SUxdl9wOOO-GT0-97OJw-nkUm8UO0M_iyz6jGDpxjWpaiBaeUidmqO6gUsvxW2LgnHKl-_LsDacWixAgah1VnBbFMB5e3SA9kZmxqw3mlo6fXmN9xfJ_2vt2Zkv2ZEP98Wat7nBXphqBcSD-Yxkj25w5wREcYho0a-DOdp9S4V-foaQje1l-S_SlZ2buHzRa05_qxHfGTRRrvZ0dTbQ6ErQoQfkV_Ah_dJYB1U5ZOkK1DF5R1afH2-yjeNX3fpyG9Lyhqn1Dj7Nfnnyytve1elek768au-VDKRlR2hpervdo_i9TnKM8pded6JdSFzUmydGfOnPVyIheLtBk_i0qHhhkJTmM8hxH4d0ip4WOWOarAglfN385P3SZum4BUVYd5vVj55ayXWk20g8VqyO6IZWeOgVip-Xzw9Yvmjd3SXtur28jlyRcUyvJ6y0tZkb1ebzolQI8veFccv4j-zq-qm3rpvIuVR2j1dUuvm_womXg83B82ot2c_z6wgWy7YMO2qma2Fnx76eSqQu_lOFQcaag8X9Qp06UVMqhbkXo1vz9M24BekRVOi6SviZld3wZ524ReXlZprUdu0BFX6qpv9Vlo-ZlZ10dfwRRtqRo2fOjijw3Jp8IieqwlBmeF6Ul_8sVc8mR5-BJ66VMIJUpvIgadg2bom4sY2y15URqFb5QImJMfrnx3V2nZcR7Ui_bM96Z8rwJwpj3xUs4cne8r7Fbq6dxrsQZha1mecBig79USv12dwZl_axrqj5Yyf6e2rc3-4xvZjq3zkb3a2ivyrtpbJqXYVM9Sx2OwJtz1SJ5ROovcfds8BObSRVrr3Umo0j50nhqcJodpnrpIRnksgpfmnUnxBsIOac3uUdq51oY-uuOwQBbF1w7-bBnJvaSbX_ZcXwR7k0l4t9FMJjw2jjJ_MmqQkkutQMrinc2wyx2xa0mUwnJ58r3Se9gQ66-r-6eda3QFhQ2OSgun_Bk77S06yugo8Zt85eXr62asjzR5W3"

# Function to send push notifications
def send_fcm_notification(token, title, message):
    url = f"https://fcm.googleapis.com/v1/projects/carrykar/messages:send"
    headers = {
        "Authorization": f"Bearer {FIREBASE_ACCESS_TOKEN}",  # 🔥 Use OAuth 2.0 Access Token
        "Content-Type": "application/json",
    }
    payload = {
        "message": {
            "token": token,
            "notification": {
                "title": title,
                "body": message
            }
        }
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code != 200:
        return {"error": f"FCM request failed with status code {response.status_code}", "response": response.text}

    try:
        return response.json()
    except requests.exceptions.JSONDecodeError:
        return {"error": "Invalid JSON response from FCM", "response": response.text}
    

@app.route("/send_notification", methods=['GET', 'POST'])
def send_notification():
    if request.method == "GET":
        # Extract parameters from the URL
        token = request.args.get("token")
        title = request.args.get("title", "Default Title")
        message = request.args.get("message", "Default Message")s
    else:
        # Extract parameters from JSON body
        data = request.get_json(silent=True)  # Handles cases where JSON is missing
        if not data:
            return jsonify({"error": "Invalid JSON data"}), 400
        token = data.get("token")
        title = data.get("title", "Default Title")
        message = data.get("message", "Default Message")

    if not token:
        return jsonify({"error": "Token is required"}), 400

    response = send_fcm_notification(token, title, message)
    return jsonify(response)

#cuxO1YOuSrqRT_JcVM7aFn:APA91bHcTsVJ5JmCyBwELyYDjyE-VL894LTjuQtVNdaoV6K41mU20VPd7zcmsKtT-RDEEWsJ8dt3VUhB6n2dSTsgh55pv2xQ19rstbyRYblS7tFW-LDj060


@app.route("/register_token", methods=['GET', 'POST'])
def register_token():
    if request.method == "GET":
        token = request.args.get("token")  # Get token from URL
    else:
        data = request.json
        token = data.get("token")

    print("Received Token:", token)
    return {"message": "Token received", "token": token}, 200


if __name__ == "__main__":
    app.run(debug=True, port=5000)
