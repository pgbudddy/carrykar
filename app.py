import eventlet
eventlet.monkey_patch()


from flask import Flask, render_template, request, redirect, url_for, session, make_response, jsonify
import api
import datetime
from flask_caching import Cache
import requests
import googlemaps
import os
import uuid
from PIL import Image, UnidentifiedImageError
import random
from asgiref.wsgi import WsgiToAsgi
import razorpay
import re
from urllib.parse import quote


from cashfree_pg.models.create_order_request import CreateOrderRequest
from cashfree_pg.api_client import Cashfree
from cashfree_pg.models.customer_details import CustomerDetails
from cashfree_pg.models.order_meta import OrderMeta
from cashfree_pg.models import (  # ✅ Import missing models
    PaymentMethodAppInPaymentsEntity,
    PaymentMethodUPIInPaymentsEntity,
    PaymentMethodNetBankingInPaymentsEntity,
    PaymentMethodCardInPaymentsEntity
)
import uuid
import urllib3

# Disable SSL warnings (for testing only, not recommended for production)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


from flask_socketio import SocketIO, emit
from concurrent.futures import ThreadPoolExecutor
from threading import Thread
from io import BytesIO


app = Flask(__name__, static_folder='static')
app.secret_key = 'your_secret_key'  # Ensure you use a secure key for session
app.config['SESSION_PERMANENT'] = True  # Make session persistent
app.config['SESSION_TYPE'] = 'filesystem'  # Store session on server

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")
# app.config['SESSION_TYPE'] = 'redis'
# app.config['SESSION_PERMANENT'] = False
# Session(app)


# # Configure Flask-Caching with Redis
# app.config['CACHE_TYPE'] = 'redis'
# app.config['CACHE_REDIS_HOST'] = 'localhost'
# app.config['CACHE_REDIS_PORT'] = 6379
# cache = Cache(app)

GOOGLE_MAPS_API_KEY = "AIzaSyCdc5N7AzzvPiWddsegRCRmna3LxG5HCmk"
razorpay_client = razorpay.Client(auth=("rzp_test_7TJCqucHMY4JS2", "489v1D9RIMDuqzWH8JmeWMZr"))

Cashfree.XClientId = "879351867ef3119b9f8f6ffa21153978"
Cashfree.XClientSecret = "cfsk_ma_prod_fe15187663924595a6fa8413775d4d34_682b88cc"
Cashfree.XEnvironment = Cashfree.PRODUCTION
x_api_version = "2023-08-01"


# Upload folder configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
executor = ThreadPoolExecutor()


# @app.route('/')
# def home():
#     username = request.cookies.get('username')
#     if username:
#         session['username'] = username
#         return redirect(url_for('main'))
#     else:
#         return render_template('index.html')


@app.route("/register_token", methods=['GET', 'POST'])
def register_token():
    if request.method == "GET":
        token = request.args.get("token")  # From URL
        public_ip = request.remote_addr     # From request header
    else:
        data = request.json
        token = data.get("token")
        public_ip = data.get("public_ip")

    # Save in session (optional use)
    session['token'] = token
    session['public_ip'] = public_ip

    print("Stored Token in Session:", session.get("token"))
    print("Stored Public IP:", session.get("public_ip"))

    # 🔁 Run update in background to reduce latency
    executor.submit(api.updatetoken, "None", token, public_ip)

    return jsonify({
        "message": "Token stored successfully",
        "token": token,
        "public_ip": public_ip
    })



@app.route('/')
def home():
    username = request.cookies.get('username')
    
    if username:
        session['username'] = username

        return redirect(url_for('main'))
        
    else:
        return render_template('main_without_login.html')
    

@app.route('/chat')
def chat():
    return render_template('chat.html')


messages = []
@socketio.on("send_message")
def handle_message(data):
    raw_username = data.get("username", "Anonymous")
    user_cookie = request.cookies.get('username')  # Get user from cookie
    message = data.get("message", "").strip()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def get_full_name():
        try:
            profile = api.fetch_profile(user_cookie)
            if profile and len(profile[0]) >= 2:
                return f"{profile[0][0]} {profile[0][1]}"
        except Exception as e:
            print("[⚠️] Error fetching profile:", e)
        return raw_username

    # 🧠 Fetch name in background thread
    future_name = executor.submit(get_full_name)
    username = future_name.result()

    if message:
        messages.append((username, message, timestamp))

        # 🚀 Immediately broadcast to all connected clients
        socketio.emit("receive_message", (username, message, timestamp))

        # 💾 Save message in background
        def save_message_background():
            try:
                result = api.save_message(username, message, timestamp)
                print("[💾] Message saved:", result)
            except Exception as e:
                print("[❌] Failed to save message:", e)

        executor.submit(save_message_background)
        

@socketio.on("connect")
def handle_connect():
    sid = request.sid  # Unique socket session ID
    print(f"[🔗] Client connected: {sid}")

    def fetch_and_send():
        try:
            messages = api.get_recent_messages()
            print("[🧾] Recent messages:", messages)
            socketio.emit("load_messages", messages, to=sid)  # Send only to the connecting client
        except Exception as e:
            print("[❌] Error fetching messages:", e)

    # Fetch and emit messages in the background
    executor.submit(fetch_and_send)


# @cache.cached(timeout=60 * 60 * 24 * 7)
@app.route('/login', methods=['GET', 'POST'])
def login():
    username_cookie = request.cookies.get('username')

    # Optional: auto-login from cookie
    # if username_cookie:
    #     session['username'] = username_cookie
    #     return redirect(url_for('main'))

    if request.method == 'POST':
        username = request.form['number']
        password = request.form['password']

        print(f"[🔐] Login attempt: {username}")

        # 🧠 Validate login in a thread
        future_login = executor.submit(api.login, username, password)
        checklogin = future_login.result()

        print(f"[✅] Login result: {checklogin}")

        if checklogin:
            session.clear()
            session['username'] = username
            expire_date = datetime.datetime.now() + datetime.timedelta(days=30)
            resp = make_response(redirect(url_for('main')))
            resp.set_cookie('username', username, expires=expire_date)
            return resp
        else:
            error = "Invalid login credentials!"
            return render_template('login.html', error=error)
        
    return render_template('login.html')

    

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email'].strip()
        print(f"[📨] Signup email entered: {email}")

        # ✅ Run email check in a background thread
        future_check = executor.submit(api.checkemail, email)
        checkemail = future_check.result()

        print(f"[✔️] Email availability: {checkemail}")

        if checkemail == False:
            error = "This email address is already being used by another account!"
            return render_template('signup.html', error=error)

        # Store email for next step
        session['email'] = email
        return redirect(url_for('signup_name'))
    
    return render_template('signup.html')


@app.route('/signup_name', methods=['GET', 'POST'])
def signup_name():
    if request.method == 'POST':
        firstname = request.form['firstname']
        lastname = request.form['lastname']

        print(firstname)
        print(lastname)

        # Store the name in session to carry it to the next page
        session['firstname'] = firstname
        session['lastname'] = lastname
        return redirect(url_for('signup_dob'))
    return render_template('signup_name.html')


@app.route('/signup_dob', methods=['GET', 'POST'])
def signup_dob():
    if request.method == 'POST':
        dob = request.form['dateofbirth']

        print(dob)
        
        # Store the name in session to carry it to the next page
        session['dateofbirth'] = dob
        return redirect(url_for('signup_password'))
    return render_template('signup_dob.html')


@app.route('/signup_password', methods=['GET', 'POST'])
def signup_password():
    if request.method == 'POST':
        password = request.form['password']

        print(password)
        
        # Store the name in session to carry it to the next page
        session['password'] = password
        return redirect(url_for('signup_mobile'))
    return render_template('signup_password.html')


@app.route('/signup_mobile', methods=['GET', 'POST'])
def signup_mobile():
    if request.method == 'POST':
        mobilenumber = request.form['mobilenumber'].strip()
        print("📱 Mobile number received:", mobilenumber)

        # 🔁 Fetch profile in a background thread
        future_check = executor.submit(api.fetch_profile, mobilenumber)
        checkenumber = future_check.result()

        print("🔍 fetch_profile result:", checkenumber)

        if checkenumber:
            return jsonify({'error': 'Mobile number already in use'}), 400

        # ✅ Mobile number is new
        email = session.get('email')
        generateotp = random.randint(1000, 9999)
        print("🔐 Generated OTP:", generateotp)

        # 🔁 Send OTP in a background thread (but we wait for result)
        future_send = executor.submit(api.send_mail, email, generateotp)
        sendotp = future_send.result()

        if not sendotp:
            return "Failed to send OTP."

        # ✅ Store in session
        session['mobilenumber'] = mobilenumber
        session['otp'] = generateotp
        print("🚀 Redirecting to OTP input page...")

        return jsonify({'success': True, 'redirect_url': url_for('signup_mobile_code')})

    return render_template('signup_mobile.html')


@app.route('/signup_mobile_code', methods=['GET', 'POST'])
def signup_mobile_code():
    if request.method == 'POST':
        otpcode = request.form['otpcode']
        public_ip = request.form.get('public_ip', "Unknown")  # Get IP from form data

        sessionotp = session.get('otp')

        session['public_ip'] = public_ip

        print("Session OTP:", sessionotp)
        print("public_ip:", public_ip)

        # Ensure otpcode is compared as a string or integer consistently
        if str(otpcode) != str(sessionotp):  # Compare as string
            error = "Enter valid OTP!"
            return render_template('signup_mobile_code.html', error=error)
        else:
            # Redirect to the 'main' route
            checksignup = signup_done()
            if checksignup == True:
                return redirect(url_for('login'))
            else:
                error = "Something went wrong!"
                return render_template('signup_mobile_code.html', error=error)
        

    # Render the signup_mobile_code.html template for GET requests
    return render_template('signup_mobile_code.html')


@app.route('/signup_done')
def signup_done():
    user_data = {
        'email': session.get('email'),
        'mobilenumber': session.get('mobilenumber'),
        'firstname': session.get('firstname'),
        'lastname': session.get('lastname'),
        'dateofbirth': session.get('dateofbirth'),
        'password': session.get('password'),
        'public_ip': session.get('public_ip'),
    }

    print("user_data: ", user_data)

    userid = str(user_data.get("firstname"))[:3]+str(user_data.get("mobilenumber"))[:3]

    check = api.signup(user_data.get("firstname"), user_data.get("lastname"), user_data.get("email"), user_data.get("mobilenumber"), user_data.get("dateofbirth"), user_data.get("password"), userid, user_data.get("public_ip")) 

    if check:
        return True
    else:
        return False


@app.route('/main', methods=['GET', 'POST'])
def main():
    username = request.cookies.get('username')

    print("Username:", username)


    if request.method == 'POST':
        leaving_text = request.form.get('leaving_text', 'Default Leaving Text')
        going_text = request.form.get('going_text', 'Default Going Text')
        calendar_date = request.form.get('calendar', '')
        person_count = request.form.get('person', '')

        # Save the data to session or process it as needed
        session['leaving_text'] = leaving_text
        session['going_text'] = going_text
        session['calendar_date'] = calendar_date
        session['person_count'] = person_count

        if leaving_text:
            geocode_url = f"https://maps.googleapis.com/maps/api/geocode/json?address={leaving_text}&key={GOOGLE_MAPS_API_KEY}"
            response = requests.get(geocode_url)
            geocode_data = response.json()

            if geocode_data['status'] == 'OK':
                coordinates = geocode_data['results'][0]['geometry']['location']
                latitude = coordinates['lat']
                longitude = coordinates['lng']
                
                session['ridepickupcoordinates'] = f"{latitude},{longitude}"

                # For traditional form submissions
                print(session['leaving_text'])
                print(session['ridepickupcoordinates'])

                session['came_from_going'] = True
                # return redirect(url_for('going'))


        if going_text:
            geocode_url = f"https://maps.googleapis.com/maps/api/geocode/json?address={going_text}&key={GOOGLE_MAPS_API_KEY}"
            response = requests.get(geocode_url)
            geocode_data = response.json()

            if geocode_data['status'] == 'OK':
                coordinates = geocode_data['results'][0]['geometry']['location']
                latitude = coordinates['lat']
                longitude = coordinates['lng']
                
                session['ridedropcoordinates'] = f"{latitude},{longitude}"

                # For traditional form submissions
                print(session['going_text'])
                print(session['ridedropcoordinates'])

                session['came_from_going'] = True
                # return redirect(url_for('main'))

                # return jsonify({
                #     'message': 'Coordinates fetched successfully',
                #     'location': droplocation,
                #     'coordinates': {'lat': latitude, 'lng': longitude},
                # })

        # Redirect or render the next page
        return redirect(url_for('search_ride'))

    # GET request handling (renders main page)
    # ridepickuplocation = session.get('ridepickuplocation', 'Pickup Location')
    # ridedroplocation = session.get('ridedroplocation', 'Drop Location')
    # came_from_going = session.get('came_from_going', False)
    # print("came_from_going ", came_from_going)
    # print("ridepickuplocation ", ridepickuplocation)
    # print("ridedroplocation ", ridedroplocation)
    # # print("Full session content:", dict(session))
    # leaving_text = str(ridepickuplocation) if came_from_going else "Leaving from"
    # going_text = str(ridedroplocation) if came_from_going else "Going from"

    # # Clear the flag after use
    # session.pop('came_from_going', None)

    return render_template(
        'main.html',
        # leaving_text=leaving_text,
        # going_text=going_text
    )


@app.route('/leaving', methods=['GET', 'POST'])
def leaving():
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            pickuplocation = data.get('pickuplocation', '')
        else:
            pickuplocation = request.form.get('pickuplocation', '')

        print('Pickup Location:', pickuplocation)
        session['ridepickuplocation'] = pickuplocation

        if pickuplocation:
            geocode_url = f"https://maps.googleapis.com/maps/api/geocode/json?address={pickuplocation}&key={GOOGLE_MAPS_API_KEY}"
            response = requests.get(geocode_url)
            geocode_data = response.json()

            if geocode_data['status'] == 'OK':
                coordinates = geocode_data['results'][0]['geometry']['location']
                latitude = coordinates['lat']
                longitude = coordinates['lng']
                
                session['ridepickupcoordinates'] = f"{latitude},{longitude}"

                # For traditional form submissions
                print(session['ridepickuplocation'])
                print(session['ridepickupcoordinates'])

                session['came_from_going'] = True
                return redirect(url_for('going'))

                # return jsonify({
                #     'message': 'Coordinates fetched successfully',
                #     'location': droplocation,
                #     'coordinates': {'lat': latitude, 'lng': longitude},
                # })
            else:
                return jsonify({'message': 'Failed to fetch coordinates', 'status': geocode_data['status']}), 400

    return render_template('leaving.html')



@app.route('/going', methods=['GET', 'POST'])
def going():
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            droplocation = data.get('droplocation', '')
        else:
            droplocation = request.form.get('droplocation', '')

        print('Drop-off Location:', droplocation)
        session['ridedroplocation'] = droplocation

        if droplocation:
            geocode_url = f"https://maps.googleapis.com/maps/api/geocode/json?address={droplocation}&key={GOOGLE_MAPS_API_KEY}"
            response = requests.get(geocode_url)
            geocode_data = response.json()

            if geocode_data['status'] == 'OK':
                coordinates = geocode_data['results'][0]['geometry']['location']
                latitude = coordinates['lat']
                longitude = coordinates['lng']
                
                session['ridedropcoordinates'] = f"{latitude},{longitude}"

                # For traditional form submissions
                print(session['ridedroplocation'])
                print(session['ridedropcoordinates'])

                session['came_from_going'] = True
                return redirect(url_for('main'))

                # return jsonify({
                #     'message': 'Coordinates fetched successfully',
                #     'location': droplocation,
                #     'coordinates': {'lat': latitude, 'lng': longitude},
                # })
            else:
                return jsonify({'message': 'Failed to fetch coordinates', 'status': geocode_data['status']}), 400

    return render_template('going.html')


@app.route('/search_ride')
def search_ride():
    # Get session values
    gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)
    ridepickuplocation = session.get('ridepickuplocation', '')
    ridedroplocation = session.get('ridedroplocation', '')
    calendar_date = session.get('calendar_date', '')
    person_count = session.get('person_count', '')
    ridepickupcoordinates = session.get('ridepickupcoordinates', '')
    ridedropcoordinates = session.get('ridedropcoordinates', '')

    ridepickupcoordinate_list = ridepickupcoordinates.split(",")
    ridedropcoordinate_list = ridedropcoordinates.split(",")

    print("🚗 Coordinates:", ridepickupcoordinate_list, ridedropcoordinate_list)

    # Run both city lookups in parallel
    future_pickup_city = executor.submit(api.find_city, GOOGLE_MAPS_API_KEY, ridepickupcoordinate_list[0], ridepickupcoordinate_list[1])
    future_drop_city = executor.submit(api.find_city, GOOGLE_MAPS_API_KEY, ridedropcoordinate_list[0], ridedropcoordinate_list[1])
    
    ridepickupcity = future_pickup_city.result()
    ridedropcity = future_drop_city.result()

    print("🌆 Cities:", ridepickupcity, ridedropcity)

    # Run find_ride in background
    future_rides = executor.submit(api.find_ride, ridepickupcity, ridedropcity, calendar_date)
    findride = future_rides.result()
    print("🎯 Found rides:", findride)

    if not findride:
        return render_template('search_ride.html')

    # Run host name lookup in background
    future_host = executor.submit(api.find_host_user, findride[0][15])
    name = future_host.result()
    print("👤 Host name:", name)

    keys = [
        "start_location", "start_coordinated", "pickupcity", "end_location", "end_coordinated", "dropcity", "date",
        "start_time", "end_time", "passengers", "passengerprice", "kgcount", "kgprice", "ride_type", "details",
        "userid", "uniqueid", "datetime", "ridepickuplocation", "ridedroplocation"
    ]

    rides = [dict(zip(keys, entry[:len(keys)])) for entry in findride]

    # 🔁 Add distance + duration in background (optional per-ride threading)
    def enrich_ride_with_distance(ride):
        try:
            result = gmaps.distance_matrix(
                origins=ride["start_coordinated"],
                destinations=ride["end_coordinated"],
                mode="driving",
                units="metric"
            )
            ride["distance"] = result["rows"][0]["elements"][0]["distance"]["text"]
            ride["duration"] = result["rows"][0]["elements"][0]["duration"]["text"]
        except Exception as e:
            print(f"[❌] Distance error for {ride['uniqueid']}: {e}")
            ride["distance"] = "N/A"
            ride["duration"] = "N/A"

    # Run all distance lookups in parallel
    futures = [executor.submit(enrich_ride_with_distance, ride) for ride in rides]
    for f in futures:
        f.result()

    return render_template('search_ride.html', rides=rides, name=name[0], calendar_date=calendar_date)


@app.route('/pickup', methods=['GET', 'POST'])
def pickup():
    return render_template('pickup.html')


@app.route('/submit-ride', methods=['POST'])
def submit_ride():
    data = request.get_json()
    gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)

    start_location = data.get('startLocation')
    end_location = data.get('endLocation')
    ride_date_time = data.get('rideDateTime')  # Format: 'YYYY-MM-DDTHH:MM'
    ride_type = data.get('rideType')
    passenger_count = data.get('passengerCount')
    passenger_price = data.get('passengerPrice')
    weight_capacity = data.get('weightCapacity')
    weight_price = data.get('weightPrice')
    ride_comments = data.get('rideComments')

    user = request.cookies.get('username')

    # 🧠 Parse ride datetime
    try:
        ride_datetime = datetime.datetime.strptime(ride_date_time, "%Y-%m-%dT%H:%M")
    except ValueError:
        return jsonify({'message': 'Invalid rideDateTime format'}), 400

    # Add buffer and get formatted values
    datetime_with_buffer = ride_datetime + datetime.timedelta(minutes=13)
    formatted_startdate = datetime_with_buffer.strftime("%Y-%m-%d %H:%M:%S")
    StartTime = datetime_with_buffer.strftime("%I:%M %p")

    # 🧠 Geocode both locations in parallel
    def geocode_address(address):
        geocode_url = f"https://maps.googleapis.com/maps/api/geocode/json?address={address}&key={GOOGLE_MAPS_API_KEY}"
        response = requests.get(geocode_url)
        result = response.json()
        if result['status'] == 'OK':
            coords = result['results'][0]['geometry']['location']
            return f"{coords['lat']},{coords['lng']}", coords['lat'], coords['lng']
        return None, None, None

    future_start = executor.submit(geocode_address, start_location)
    future_end = executor.submit(geocode_address, end_location)

    start_coord_str, start_lat, start_lng = future_start.result()
    end_coord_str, end_lat, end_lng = future_end.result()

    if not all([start_coord_str, end_coord_str]):
        return jsonify({'message': 'Failed to geocode location'}), 400

    session['pickupcoordinates'] = start_coord_str
    session['dropcoordinates'] = end_coord_str

    # 🔁 Distance Matrix
    result = gmaps.distance_matrix(
        origins=(start_lat, start_lng),
        destinations=(end_lat, end_lng),
        mode="driving",
        departure_time=datetime.datetime.now()
    )

    if result['status'] != 'OK':
        return jsonify({'message': 'Failed to fetch distance data'}), 400

    distance = result['rows'][0]['elements'][0]['distance']['text']
    duration_text = result['rows'][0]['elements'][0]['duration']['text']

    session['ride_distance'] = distance
    session['ride_duration'] = duration_text

    # 🧠 Calculate end time based on duration
    duration_minutes = 0
    h = re.search(r'(\d+)\s*hour', duration_text)
    m = re.search(r'(\d+)\s*min', duration_text)
    if h: duration_minutes += int(h.group(1)) * 60
    if m: duration_minutes += int(m.group(1))

    ride_end_time = ride_datetime + datetime.timedelta(minutes=duration_minutes)
    session['ride_end_time'] = ride_end_time.strftime('%Y-%m-%dT%H:%M')

    final_datetime = ride_end_time + datetime.timedelta(minutes=13)
    formatted_datetime = final_datetime.strftime("%Y-%m-%d %H:%M:%S")
    EndTime = final_datetime.strftime("%I:%M %p")

    # 🔁 Find pickup/drop cities in parallel
    future_pickup_city = executor.submit(api.find_city, GOOGLE_MAPS_API_KEY, start_lat, start_lng)
    future_drop_city = executor.submit(api.find_city, GOOGLE_MAPS_API_KEY, end_lat, end_lng)

    pickupcity = future_pickup_city.result()
    dropcity = future_drop_city.result()

    ride_start_date = datetime_with_buffer.strftime("%d %B %Y")

    # 🧠 Insert ride (threaded, but we need result)
    host_future = executor.submit(
        api.hostride,
        start_location, start_coord_str, pickupcity,
        end_location, end_coord_str, dropcity,
        ride_start_date, StartTime, EndTime,
        passenger_count, f"₹ {passenger_price}",
        weight_capacity, f"₹ {weight_price}",
        ride_type, ride_comments, user
    )
    host = host_future.result()
    session['came_from_going'] = False

    if not host:
        return jsonify({'success': False, 'message': 'Failed to host ride'}), 500

    # 🔁 Check KYC in background (must wait for result)
    future_kyc = executor.submit(api.check_kyc, user)
    checkkyc = future_kyc.result()

    if checkkyc == "no":
        redirect_url = url_for('uploadkyc')
    else:
        redirect_url = url_for('ride_published', pickuplocation=pickupcity, droplocation=dropcity, distance=quote(distance), price=quote(passenger_price))

    return jsonify({'success': True, 'redirect_url': redirect_url})


@app.route('/ride_details', methods=['GET', 'POST'])
def ride_details():
    if request.method == 'POST':
        details = request.form['details']
        print(details)

        session['details'] = details
        return redirect(url_for('ride_published'))
    
    return render_template('ride_details.html')


@app.route('/ride_published')
def ride_published():
    pickuplocation = request.args.get('pickuplocation', 'Unknown')
    droplocation = request.args.get('droplocation', 'Unknown')
    distance = request.args.get('distance', 'Unknown')
    price = request.args.get('price', 'Unknown')

    return render_template('ride_published.html', pickuplocation=pickuplocation, droplocation=droplocation, distance=distance, price=price)


@app.route('/uploadkyc')
def uploadkyc():    
    return render_template('uploadkyc.html')


@app.route('/my_hosted_rides')
def my_hosted_rides():
    user = request.cookies.get('username')
    gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)
    
    keys = [
        "start_location", "start_coordinated", "pickupcity", "end_location", "end_coordinated", "dropcity", 
        "date", "start_time", "end_time", "passengers", "passengerprice", "kgcount", "kgprice", 
        "ride_type", "details", "userid", "uniqueid", "datetime", "ridepickuplocation", "ridedroplocation"
    ]

    # 🔁 Fetch user's rides in background
    future_rides = executor.submit(api.fetch_your_rides, user)
    ride_data = future_rides.result()
    print("🎯 Ride data:", ride_data)

    name = None
    rides = None

    if ride_data:
        rides = [dict(zip(keys, entry[:len(keys)])) for entry in ride_data]

        # 🔁 Fetch host name (for first ride)
        userid = rides[0].get('userid')
        future_name = executor.submit(api.find_host_user, userid)
        name_data = future_name.result()

        if name_data:
            name = str(name_data[0] + " " + name_data[1])

        # 🔁 Enrich each ride with Google Maps distance/duration (parallel)
        def enrich_ride(ride):
            try:
                result = gmaps.distance_matrix(
                    origins=ride["start_coordinated"],
                    destinations=ride["end_coordinated"],
                    mode="driving",
                    units="metric"
                )
                ride["distance"] = result["rows"][0]["elements"][0]["distance"]["text"]
                ride["duration"] = result["rows"][0]["elements"][0]["duration"]["text"]
            except Exception as e:
                print(f"[❌] Failed distance for ride {ride['uniqueid']}: {e}")
                ride["distance"] = "N/A"
                ride["duration"] = "N/A"

        # Start all distance lookups in parallel
        futures = [executor.submit(enrich_ride, r) for r in rides]
        for f in futures:
            f.result()  # Wait for all to complete

    return render_template('my_hosted_rides.html', rides=rides, name=name)


@app.route('/hosted_rides_details')
def hosted_rides_details():
    ride_details = {
        "date": request.args.get('date'),
        "start_time": request.args.get('start_time'),
        "end_time": request.args.get('end_time'),
        "start_location": request.args.get('start_location'),
        "start_coordinated": request.args.get('start_coordinated'),
        "pickupcity": request.args.get('pickupcity'),
        "end_location": request.args.get('end_location'),
        "end_coordinated": request.args.get('end_coordinated'),
        "dropcity": request.args.get('dropcity'),
        "passengers": request.args.get('passengers'),
        "passengerprice": request.args.get('passengerprice'),
        "kgcount": request.args.get('kgcount'),
        "kgprice": request.args.get('kgprice'),
        "ride_type": request.args.get('ride_type'),
        "details": request.args.get('details'),
        "userid": request.args.get('userid'),
        "uniqueid": request.args.get('uniqueid'),
        "datetime": request.args.get('datetime'),
        "duration": request.args.get('duration'),
        "distance": request.args.get('distance'),
        "name": request.args.get('name'),
    }

    # 🔁 Fetch passenger list in background
    future_passengers = executor.submit(api.fetch_passengers, ride_details.get("uniqueid"))
    raw_passenger_data = future_passengers.result()

    keys = [
        "name", "number", "personcount", "kgcount", "uniqueid", "approval", "datetime"
    ]

    passengers = [dict(zip(keys, entry[:len(keys)])) for entry in raw_passenger_data] if raw_passenger_data else []

    print("[🚕] Passengers for ride:", passengers)

    return render_template('hosted_rides_details.html', ride=ride_details, passengers=passengers)


@app.route('/my_rides')
def my_rides():
    user = request.cookies.get('username')

    gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)


    keys = [
        "start_location", "start_coordinated", "pickupcity", "end_location", "end_coordinated", "dropcity",
        "date", "start_time", "end_time", "passengers", "passengerprice", "kgcount", "kgprice",
        "ride_type", "details", "userid", "uniqueid", "datetime", "ridepickuplocation", "ridedroplocation"
    ]

    # 🔁 Fetch user's booked rides in background
    future_ride_data = executor.submit(api.fetch_my_rides, user)
    ride_data = future_ride_data.result()
    print("🎯 My rides:", ride_data)

    rides = None
    name = None

    if ride_data:
        rides = [dict(zip(keys, entry[:len(keys)])) for entry in ride_data]

        # 🔁 Host name lookup in parallel
        future_host = executor.submit(api.find_host_user, rides[0].get('userid'))
        name_data = future_host.result()
        name = str(name_data[0] + " " + name_data[1]) if name_data else None

        # 🔁 Enrich each ride with Google Maps distance/duration (parallel)
        def enrich_ride(ride):
            try:
                result = gmaps.distance_matrix(
                    origins=ride["start_coordinated"],
                    destinations=ride["end_coordinated"],
                    mode="driving",
                    units="metric"
                )
                ride["distance"] = result["rows"][0]["elements"][0]["distance"]["text"]
                ride["duration"] = result["rows"][0]["elements"][0]["duration"]["text"]
            except Exception as e:
                print(f"[❌] Error in ride {ride['uniqueid']}: {e}")
                ride["distance"] = "N/A"
                ride["duration"] = "N/A"

        # Run all distance lookups in parallel
        futures = [executor.submit(enrich_ride, ride) for ride in rides]
        for f in futures:
            f.result()  # Wait for all threads

    return render_template('my_rides.html', rides=rides)


@app.route('/my_rides_details')
def my_rides_details():
    user = request.cookies.get('username')

    ride_details = {
        "date": request.args.get('date'),
        "start_time": request.args.get('start_time'),
        "end_time": request.args.get('end_time'),
        "start_location": request.args.get('start_location'),
        "start_coordinated": request.args.get('start_coordinated'),
        "pickupcity": request.args.get('pickupcity'),
        "end_location": request.args.get('end_location'),
        "end_coordinated": request.args.get('end_coordinated'),
        "dropcity": request.args.get('dropcity'),
        "passengers": request.args.get('passengers'),
        "passengerprice": request.args.get('passengerprice'),
        "kgcount": request.args.get('kgcount'),
        "kgprice": request.args.get('kgprice'),
        "ride_type": request.args.get('ride_type'),
        "details": request.args.get('details'),
        "userid": request.args.get('userid'),
        "uniqueid": request.args.get('uniqueid'),
        "datetime": request.args.get('datetime'),
        "duration": request.args.get('duration'),
        "distance": request.args.get('distance'),
        "name": request.args.get('name'),
    }

    # 🔁 Fetch passengers in background
    future_passengers = executor.submit(api.fetch_passengers, ride_details.get("uniqueid"))
    raw_passengers = future_passengers.result()

    keys = ["name", "number", "personcount", "kgcount", "uniqueid", "approval", "datetime"]
    passengers = [dict(zip(keys, entry[:len(keys)])) for entry in raw_passengers] if raw_passengers else []

    for p in passengers:
        try:
            p['total_count'] = int(p['personcount']) + int(p['kgcount'])
        except:
            p['total_count'] = 0

    # ✅ Filter current user's booking info
    selected_passenger = next((p for p in passengers if p["number"] == user), None)

    print("user:", user)
    print("selected_passenger:", selected_passenger)

    if selected_passenger:
        return render_template('my_rides_details.html', ride=ride_details, passengers=selected_passenger)
    else:
        return render_template('my_rides_details.html', ride=ride_details, passengers={})


@app.route('/book_ride')
def book_ride():
    return render_template('book_ride.html')  # Renders the HTML page directly


@app.route('/search_ride_details', methods=['GET', 'POST'])
def search_ride_details():
    if request.method == 'POST':
        try:
            data = request.json
            if not data:
                raise ValueError("No JSON data received.")

            uniqueid = data.get('uniqueid')
            price = data.get('price', 0)
            kgprice = data.get('kgprice', 0)
            start_location = data.get('start_location', "Unknown")
            end_location = data.get('end_location', "Unknown")

            user = request.cookies.get('username')
            if not user:
                raise ValueError("User not authenticated.")

            # 🔁 Use multithreading to fetch profile
            future_profile = executor.submit(api.fetch_profile, user)
            profile = future_profile.result()

            if not profile:
                raise ValueError("Unable to fetch user profile.")

            name = f"{profile[0][0]} {profile[0][1]}"
            number = profile[0][2]
            email = profile[0][3]

            if uniqueid is None or price is None or kgprice is None:
                raise ValueError("Invalid data provided. All fields are required.")

            return jsonify({
                'redirect': url_for(
                    'book_ride',
                    uniqueid=uniqueid,
                    price=price,
                    kgprice=kgprice,
                    start_location=start_location,
                    end_location=end_location,
                    name=name,
                    number=number,
                    email=email
                )
            }), 200

        except ValueError as e:
            print(f"Error: {str(e)}")
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            print(f"Unexpected Error: {str(e)}")
            return jsonify({"error": "An unexpected error occurred."}), 500

    else:
        try:
            ride_details = {
                "date": request.args.get('date'),
                "start_time": request.args.get('start_time'),
                "end_time": request.args.get('end_time'),
                "start_location": request.args.get('start_location'),
                "end_location": request.args.get('end_location'),
                "pickupcity": request.args.get('pickupcity'),
                "dropcity": request.args.get('dropcity'),
                "uniqueid": request.args.get('uniqueid'),
                "name": request.args.get('name'),
                "passengerprice": request.args.get('passengerprice'),
                "kgprice": request.args.get('kgprice'),
                "details": request.args.get('details'),
                "duration": request.args.get('duration'),
                "distance": request.args.get('distance'),
                "ride_type": request.args.get('ride_type'),
                "userid": request.args.get('userid'),
            }

            uniqueid = ride_details.get("uniqueid")
            user = request.cookies.get('username')

            # 🔁 Fetch passengers and vehicle data in parallel
            future_passengers = executor.submit(api.fetch_passengers, uniqueid)
            future_vehicle = executor.submit(api.fetch_vehicle, user)

            fetch_passengers = future_passengers.result()
            fetch_vehicle = future_vehicle.result()

            passenger_keys = ["name", "number", "personcount", "kgcount", "uniqueid", "approval", "datetime"]
            passengers = [dict(zip(passenger_keys, entry[:len(passenger_keys)])) for entry in fetch_passengers]

            vehicle_keys = ["carcompany", "carnumber", "carmodel", "userid", "datetime"]
            carmodel = [dict(zip(vehicle_keys, entry[:len(vehicle_keys)])) for entry in fetch_vehicle]

            return render_template('search_ride_details.html', ride=ride_details, passengers=passengers, carmodel=carmodel)

        except Exception as e:
            print(f"Error during GET: {str(e)}")
            return jsonify({"error": "An unexpected error occurred while processing the GET request."}), 500


@app.route('/create_order', methods=['POST'])
def create_order():

    data = request.get_json()
    amount = data.get("amount")  # Amount in paise, sent from the frontend
    #amount = 1.0
    
    # order_data = {
    #     "amount": amount,  # Use the dynamic amount
    #     "currency": "INR",
    #     "payment_capture": 1
    # }
    # order = razorpay_client.order.create(data=order_data)
    # return jsonify({"order_id": order['id']})    
    customer_id = data.get("customer_id")
    customer_phone = data.get("customer_phone")
    customer_email = data.get("customer_email")
    price = data.get("price")
    kgprice = data.get("kgprice")
    uniqueid = data.get("uniqueid")

    session['price'] = price
    session['kgprice'] = kgprice
    session['uniqueid'] = uniqueid
    # amount = data.get("amount")

    if not customer_id or not customer_phone or not customer_email or not amount:
        return jsonify({"error": "Missing customer details or amount"}), 400

    order_id = str(uuid.uuid4())  # Generate a unique order ID
    
    customerDetails = CustomerDetails(
        customer_id=customer_id,
        customer_phone=customer_phone,
        customer_email=customer_email
    )
    
    createOrderRequest = CreateOrderRequest(
        order_id=order_id,
        order_amount=float(amount),  # Convert amount to float
        order_currency="INR",
        customer_details=customerDetails
    )
    
    orderMeta = OrderMeta()
    orderMeta.return_url = f"https://app.carrykar.co.in/capture_payment?order_id={order_id}"
    createOrderRequest.order_meta = orderMeta
    
    try:
        api_response = Cashfree().PGCreateOrder(x_api_version, createOrderRequest, None, None)
        print("Cashfree Response:", api_response.data)  # Debugging log
        
        if hasattr(api_response.data, "code") and api_response.data.code == "order_already_exists":
            return jsonify({"error": "Order already exists, please try again with a new order ID"}), 409
        
        if hasattr(api_response.data, "payment_session_id"):
            return jsonify({"paymentSessionId": api_response.data.payment_session_id})
        else:
            return jsonify({"error": "Invalid response from Cashfree"}), 400
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 400


@app.route('/capture_payment', methods=['GET', 'POST'])
def capture_payment():
    user = request.cookies.get('username')
    uniqueid = session.get('uniqueid')
    price = session.get('price')
    kgprice = session.get('kgprice')
    
    order_id = request.args.get("order_id")
    if not order_id:
        return jsonify({"error": "Missing order_id in request"}), 400

    # 🔁 Run Cashfree fetch in background
    future_payment = executor.submit(Cashfree().PGOrderFetchPayments, x_api_version, order_id, None)
    api_response = future_payment.result()

    if not api_response.data:
        return jsonify({"error": "No payment data found for this order"}), 404

    payment = api_response.data[0]

    payment_details = {
        "cf_payment_id": payment.cf_payment_id,
        "order_id": payment.order_id,
        "order_amount": payment.order_amount,
        "payment_currency": payment.payment_currency,
        "payment_amount": payment.payment_amount,
        "payment_time": payment.payment_time,
        "payment_completion_time": payment.payment_completion_time,
        "payment_status": payment.payment_status,
        "payment_message": payment.payment_message,
        "bank_reference": payment.bank_reference,
        "payment_group": payment.payment_group,
        "payment_method": {},
        "uniqueid": uniqueid,
        "contact": user
    }

    # Extract payment method
    instance = payment.payment_method.actual_instance
    if isinstance(instance, PaymentMethodAppInPaymentsEntity):
        payment_details["payment_method"] = {
            "type": "Wallet/App",
            "provider": instance.app.provider,
            "channel": instance.app.channel,
            "phone": instance.app.phone,
        }
    elif isinstance(instance, PaymentMethodUPIInPaymentsEntity):
        payment_details["payment_method"] = {
            "type": "UPI",
            "upi_id": getattr(instance.upi, "upi_id", "Unknown"),
            "upi_provider": getattr(instance.upi, "provider", "Unknown"),
        }
    elif isinstance(instance, PaymentMethodNetBankingInPaymentsEntity):
        payment_details["payment_method"] = {
            "type": "Net Banking",
            "bank_name": getattr(instance.netbanking, "bank_code", "Unknown"),
        }
    elif isinstance(instance, PaymentMethodCardInPaymentsEntity):
        payment_details["payment_method"] = {
            "type": "Card",
            "card_type": getattr(instance.card, "card_type", "Unknown"),
            "last4": getattr(instance.card, "card_number", "Unknown"),
            "network": getattr(instance.card, "card_brand", "Unknown"),
        }
    else:
        payment_details["payment_method"] = {
            "type": "Unknown"
        }

    print("Payment Details:", payment_details)

    # Insert payment async
    future_insert = executor.submit(api.insert_payment, payment_details)
    payment_insert = future_insert.result()

    if payment_details["payment_status"] == "SUCCESS" and payment_insert:
        # Fetch profile and book ride in parallel
        future_profile = executor.submit(api.fetch_profile, user)
        profile = future_profile.result()

        name = f"{profile[0][0]} {profile[0][1]}"
        number = profile[0][2]
        email = profile[0][3]

        future_book = executor.submit(api.book_ride, name, number, price, kgprice, uniqueid, "pending")
        book_result = future_book.result()

        print("Booking Result:", book_result)
        return redirect(url_for('payment_success'))

    return redirect(url_for('payment_failed'))


@app.route('/payment_success')
def payment_success():
    return render_template('payment_success.html')


@app.route('/payment_failed')
def payment_failed():
    return render_template('payment_failed.html')


@app.route('/delete_ride', methods=['POST'])
def delete_ride():
    data = request.get_json()
    uniqueid = data.get('uniqueid')

    if not uniqueid:
        return jsonify({'success': False, 'message': 'Unique ID is missing'}), 400

    # Run delete operation in a thread to avoid blocking
    future = executor.submit(api.delete_ride, uniqueid)
    deleteride = future.result()

    if deleteride:
        return jsonify({'success': True, 'message': 'Ride deleted successfully'})
    else:
        return jsonify({'success': False, 'message': 'Failed to delete ride'}), 500


@app.route('/delete_my_ride', methods=['POST'])
def delete_my_ride():
    data = request.get_json()
    uniqueid = data.get('uniqueid')
    user = request.cookies.get('username')  # Fetch the 'user' cookie

    if not uniqueid or not user:
        return jsonify({'success': False, 'message': 'Missing unique ID or user'}), 400

    # Offload to a background thread
    future = executor.submit(api.delete_my_ride, uniqueid, user)
    deleteride = future.result()

    if deleteride:
        return jsonify({'success': True, 'message': 'Ride deleted successfully'})
    else:
        return jsonify({'success': False, 'message': 'Failed to delete ride'}), 500


@app.route('/reject_passenger', methods=['POST'])
def reject_passenger():
    try:
        data = request.get_json()
        number = data.get('number')

        if not number:
            return jsonify({'success': False, 'message': 'Missing passenger number'}), 400

        # Run passenger activity in a separate thread
        future = executor.submit(api.passenger_activity, "rejected", number)
        passengeractivity = future.result()

        print("Passenger activity result:", passengeractivity)

        return jsonify({'success': True, 'message': 'Passenger rejected successfully!'})
    except Exception as e:
        print("Error:", e)
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/approve_passenger', methods=['POST'])
def approve_passenger():
    try:
        data = request.get_json()
        number = data.get('number')

        if not number:
            return jsonify({'success': False, 'message': 'Missing passenger number'}), 400

        print("Approving passenger number:", number)

        # Run the passenger activity in a background thread
        future = executor.submit(api.passenger_activity, "accepted", number)
        passengeractivity = future.result()  # Wait for result if you need the output

        print("Passenger activity result:", passengeractivity)

        return jsonify({'success': True, 'message': 'Passenger approved successfully!'})
    except Exception as e:
        print("Error:", e)
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/profile')
def profile():
    user = request.cookies.get('username')  # Fetch the 'user' cookie

    print("user ", user)

    if not user:
        return redirect(url_for('login'))

    print("Logged in user:", user)

    # Start all API calls concurrently
    future_profile = executor.submit(api.fetch_profile, user)
    future_vehicles = executor.submit(api.fetch_vehicle, user)
    future_banks = executor.submit(api.fetch_bank_account, user)

    # Wait for results
    profile = future_profile.result()
    vehicles = future_vehicles.result()
    banks = future_banks.result()

    # Process profile data
    profile_keys = [
        "firstname", "lastnumber", "number", "emailid", "dob", "ipaddress", 
        "uniqueid", "password", "emailverification", "kycverification", "datetime"
    ]
    # Validate and process profile
    passengers = []
    if isinstance(profile, (list, tuple)):
        # If it's a single tuple, wrap it in a list
        if isinstance(profile, tuple):
            profile = [profile]
        
        for entry in profile:
            if isinstance(entry, (list, tuple)) and len(entry) >= len(profile_keys):
                passengers.append(dict(zip(profile_keys, entry)))
            else:
                print("Invalid profile entry skipped:", entry)
    else:
        print("Profile is not list or tuple:", profile)


    print("Profile:", passengers)

    # Process vehicle data
    vehicle_keys = ["carcompany", "carnumber", "carmodel", "userid", "datetime"]
    vehicles = [dict(zip(vehicle_keys, entry[:len(vehicle_keys)])) for entry in vehicles]
    print("Vehicles:", vehicles)

    # Process bank data
    bank_keys = ["bankname", "accountnumber", "ifscode", "holder_name", "userid", "datetime"]
    banks_arrays = [dict(zip(bank_keys, entry[:len(bank_keys)])) for entry in banks]
    print("Banks:", banks_arrays)

    return render_template('profile.html', passengers=passengers, vehicles=vehicles, banks_arrays=banks_arrays)


@app.route('/profile_account')
def profile_account():
    return render_template('profile_account.html')


def generate_filename(original_filename, type, user):
    # Safely check for file extension presence
    if '.' in original_filename:
        file_extension = original_filename.rsplit('.', 1)[1].lower()
        unique_name = f"{user}_{uuid.uuid4().hex}_{type}.{file_extension}"
        return unique_name
    else:
        raise ValueError(f"Invalid filename: {original_filename}")


def allowed_file(filename):
    # Ensure filename is not empty and contains a valid extension
    if filename and '.' in filename:
        file_extension = filename.rsplit('.', 1)[1].lower()
        return file_extension in ALLOWED_EXTENSIONS
    return False


def process_kyc_upload(user, frontfile, backfile, front_path, back_path):
    try:
        # Save using Pillow
        front_img = Image.open(frontfile)
        front_img.save(front_path)

        back_img = Image.open(backfile)
        back_img.save(back_path)

        # Call KYC API in background
        print(f'Files uploaded successfully: {front_path}, {back_path}')
        update_kyc = api.update_kyc(user)
        print("KYC Update Status:", update_kyc)
    except Exception as e:
        print("Error in thread:", e)


@app.route('/add_kyc', methods=['GET', 'POST'])
def add_kyc():
    user = request.cookies.get('username')  # Fetch the 'user' cookie

    if request.method == 'POST':
        frontfile = request.files.get('frontfile')
        backfile = request.files.get('backfile')

        if not frontfile or not frontfile.filename:
            print('Front file is missing.')
            return redirect(request.url)
        if not backfile or not backfile.filename:
            print('Back file is missing.')
            return redirect(request.url)

        if not allowed_file(frontfile.filename) or not allowed_file(backfile.filename):
            print('Invalid file format.')
            return redirect(request.url)

        try:
            front_filename = generate_filename(frontfile.filename, 'front', user)
            back_filename = generate_filename(backfile.filename, 'back', user)

            front_path = os.path.join(app.config['UPLOAD_FOLDER'], front_filename)
            back_path = os.path.join(app.config['UPLOAD_FOLDER'], back_filename)

            # Copy file objects for threading (reset stream position)
            frontfile.stream.seek(0)
            backfile.stream.seek(0)
            front_copy = frontfile.read()
            back_copy = backfile.read()

            # Run image save and KYC update in background thread
            thread = Thread(target=process_kyc_upload, args=(user, BytesIO(front_copy), BytesIO(back_copy), front_path, back_path))
            thread.start()

            print("KYC submission in progress. You'll be updated shortly.")
            return redirect(url_for('profile'))

        except Exception as e:
            print('Error during processing:', e)
            return redirect(request.url)

    return render_template('add_kyc.html')


@app.route('/send_email_verification', methods=['POST'])
def send_email_verification():
    user = request.cookies.get('username')  # Fetch the 'user' cookie

    if not request.is_json:
        return jsonify({"error": "Request body must be JSON"}), 400

    data = request.get_json()
    email = data.get('email')

    print(email)

    if not email:
        return jsonify({"error": "Email is missing"}), 400

    # ✅ Background task function
    def send_verification_email(email, user):
        try:
            print(f"Sending verification email to {email}")
            sendmail = api.send_verification_mail(email, user)
            print("Mail API result:", sendmail)
        except Exception as e:
            print(f"Error while sending email in background thread: {e}")

    # ✅ Start email sending in background
    Thread(target=send_verification_email, args=(email, user)).start()

    return jsonify({"message": "Verification email is being sent!"}), 200


@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    user = request.cookies.get('username')  # Fetch the 'user' cookie

    if request.method == 'POST':
        password = request.form['password']
        print("Received password:", password)

        # ✅ Define background task
        def update_password():
            try:
                change = api.change_password(user, password)
                if change:
                    print("Password updated successfully in background")
                else:
                    print("Password update failed in background")
            except Exception as e:
                print("Error in background password update:", e)

        # ✅ Run in background thread
        Thread(target=update_password).start()

        return redirect(url_for('profile'))  # Respond immediately

    return render_template('change_password.html')


@app.route('/add_vehicle', methods=['GET', 'POST'])
def add_vehicle():
    user = request.cookies.get('username')  # Fetch the 'user' cookie

    if request.method == 'POST':
        company = request.form['company']
        carnumber = request.form['carnumber']
        carmodel = request.form['carmodel']
        print(company)
        print(carnumber)
        print(carmodel)

        # ✅ Define background function
        def add_vehicle_background():
            try:
                result = api.add_vehicle(user, company, carnumber, carmodel)
                print("Vehicle added (background):", result)
            except Exception as e:
                print("Error adding vehicle in background:", e)

        # ✅ Start background thread
        Thread(target=add_vehicle_background).start()

        # ✅ Redirect immediately
        return redirect(url_for('profile'))

    return render_template('add_vehicle.html')


@app.route('/add_bank_account', methods=['GET', 'POST'])
def add_bank_account():
    user = request.cookies.get('username')  # Fetch the 'user' cookie

    if request.method == 'POST':
        bankname = request.form['bankname']
        accountnumber = request.form['accountnumber']
        ifscode = request.form['ifscode']
        holdername = request.form['name']

        print(bankname, accountnumber, ifscode, holdername)

        # ✅ Background task definition
        def add_bank_background():
            try:
                result = api.add_bank_account(user, bankname, accountnumber, ifscode, holdername)
                print("Bank account added (background):", result)
            except Exception as e:
                print("Error adding bank account in background:", e)

        # ✅ Start background thread
        Thread(target=add_bank_background).start()

        # ✅ Redirect immediately
        return redirect(url_for('profile'))

    return render_template('add_bank_account.html')


@app.route('/logout')
def logout():
    session.clear()

    response = make_response(redirect(url_for('home')))

    # Clear cookies by setting them to expire
    response.set_cookie('username', '', expires=0)
    response.set_cookie('session_id', '', expires=0)

    return response


@app.route('/tnc')
def tnc():
    return render_template('tnc.html')


@app.route('/privacy_policy')
def privacy_policy():
    return render_template('privacy_policy.html')


@app.route('/help', methods=['GET', 'POST'])
def help():
    if request.method == 'POST':
        data = request.json  # Assuming the POST request sends JSON data
        name = data.get('name')
        number = data.get('number')
        message = data.get('message')

        if not name or not number or not message:
            return jsonify({'success': False, 'error': 'All fields are required'}), 400

        # Process the ticket (e.g., save to database or send an email)
        print(f"Ticket raised by {name}, Number: {number}, Message: {message}")

        # Return success response
        return jsonify({'success': True})

    return render_template('help.html')


@app.route('/refundpolicy')
def refundpolicy():
    return render_template('refundpolicy.html')


@app.route('/main_without_login')
def main_without_login():
    return render_template('main_without_login.html')


if __name__ == '__main__':
    # app.run(debug=True)
    # app = WsgiToAsgi(app)
    #app.run(port=8080, debug=True)
    #socketio.run(app, debug=True, port=6060, allow_unsafe_werkzeug=True)
    socketio.run(app, debug=True, port=6060, allow_unsafe_werkzeug=True)
