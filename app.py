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

app = Flask(__name__)
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
        token = request.args.get("token")  # Get token from URL
        public_ip = request.remote_addr  # Get client's IP from request
    else:
        data = request.json
        token = data.get("token")
        public_ip = data.get("public_ip")  # Public IP sent by Android

    session['token'] = token
    session['public_ip'] = public_ip

    print("Stored Token in Session:", session.get("token"))
    print("Stored Public IP:", session.get("public_ip"))

    print("updatetoken: ", api.updatetoken("None", token, public_ip))

    #return redirect(url_for('home'))
    return jsonify({
        "message": "Token stored successfully",
        "token": token,
        "public_ip": public_ip
    })  # ✅ No Redirect (JSON Response)


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
    username = data.get("username", "Anonymous")
    user = request.cookies.get('username')  # Fetch the 'user' cookie
    print("user ", user)
    checkenumber = api.fetch_profile(user)

    print("checkenumber ", checkenumber)
    username = checkenumber[0][0]+" "+checkenumber[0][1]
    print("name ", username)

    message = data.get("message", "")
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if message.strip():
        messages.append((username, message, timestamp))
        socketio.emit("receive_message", (username, message, timestamp), to=None)  # Broadcast to all
        insert = api.save_message(username, message, timestamp)
        

@socketio.on("connect")
def handle_connect():
    messages= api.get_recent_messages()

    print("messages ", messages)
    socketio.emit("load_messages", messages)


# @cache.cached(timeout=60 * 60 * 24 * 7)
@app.route('/login', methods=['GET', 'POST'])
def login():
    username = request.cookies.get('username')
    # print(username)
    # if username:
    #     session['username'] = username
    #     return redirect(url_for('main'))

    if request.method == 'POST':
        username = request.form['number']
        password = request.form['password']

        print(username, password)

        checklogin = api.login(username, password)
        print(checklogin)

        if checklogin:
            session.clear()  # Clear previous session data
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
        email = request.form['email']
        print(email)

        checkemail = api.checkemail(email)

        print(checkemail)

        if checkemail == False:
            error = "This email address is already being used by another account!"
            return render_template('signup.html', error=error)
        else:
            pass

        # Store the email in session to carry it to the next page
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
        mobilenumber = request.form['mobilenumber']
        print("mobilenumber ", mobilenumber)

        checkenumber = api.fetch_profile(mobilenumber)

        print(checkenumber)

        if checkenumber != []:
            return jsonify({'error': 'Mobile number already in use'}), 400
            
        else:
            print(mobilenumber)

            # email = session.get('email')
            # email = "kirtip2673@gmail.com"
            email = session.get('email')

            generateotp = random.randint(1000, 9999)
            print("Generated OTP:", generateotp)

            sendotp = api.send_mail(email, generateotp)

            if not sendotp:
                return "Failed to send OTP."

            # Store the name in session to carry it to the next page
            session['mobilenumber'] = mobilenumber
            session['otp'] = generateotp
            print("redirecting to")
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
    
    # return render_template('signup_mobile_code.html')


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
    # Retrieve session data
    ridepickuplocation = session.get('ridepickuplocation', '')
    ridedroplocation = session.get('ridedroplocation', '')
    calendar_date = session.get('calendar_date', '')
    person_count = session.get('person_count', '')

    ridepickupcoordinates = session.get('ridepickupcoordinates')
    print("ridepickupcoordinates ", ridepickupcoordinates)
    ridepickupcoordinate_list = ridepickupcoordinates.split(",")
    ridedropcoordinates = session.get('ridedropcoordinates')
    ridedropcoordinate_list = ridedropcoordinates.split(",")

    print("ridepickuplocation ", ridepickuplocation)    
    print("ridedroplocation ", ridedroplocation)
    print("ridepickupcoordinates ", ridepickupcoordinates)    
    print("ridedropcoordinates ", ridedropcoordinates)
    print("calendar_date ", calendar_date)
    print("person_count ", person_count)

    ridepickupcity = api.find_city(GOOGLE_MAPS_API_KEY, ridepickupcoordinate_list[0], ridepickupcoordinate_list[1])
    ridedropcity = api.find_city(GOOGLE_MAPS_API_KEY, ridedropcoordinate_list[0], ridedropcoordinate_list[1])
    
    print("ridepickupcity ", ridepickupcity)
    print("ridedropcity ", ridedropcity)

    findride = api.find_ride(ridepickupcity, ridedropcity, calendar_date)
    print("findride ", findride)
    if findride != False:
        name = api.find_host_user(findride[0][15])

        print("name ", name)

        keys = [
        "start_location", "start_coordinated", "pickupcity", "end_location", "end_coordinated", "dropcity", "date", "start_time", "end_time", "passengers", "passengerprice", "kgcount", "kgprice", "ride_type", "details", "userid", "uniqueid", "datetime", "ridepickuplocation", "ridedroplocation"
        ]

        rides = [dict(zip(keys, entry[:len(keys)])) for entry in findride]

        print("findride arrays ",rides)
        print("name ", name[0])

        gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)

        for ride in rides:
            start_coords = ride["start_coordinated"]
            end_coords = ride["end_coordinated"]
            
            # Use Google Maps Distance Matrix API
            try:
                result = gmaps.distance_matrix(
                    origins=start_coords,
                    destinations=end_coords,
                    mode="driving",  # Options: driving, walking, bicycling, transit
                    units="metric"
                )
                distance = result["rows"][0]["elements"][0]["distance"]["text"]
                duration = result["rows"][0]["elements"][0]["duration"]["text"]

                # Add distance and duration to the ride dictionary
                ride["distance"] = distance
                ride["duration"] = duration

            except Exception as e:
                print(f"Error fetching data for ride {ride['uniqueid']}: {e}")
                ride["distance"] = "N/A"
                ride["duration"] = "N/A"

        # print("Updated rides with distance and duration:", rides)

        return render_template('search_ride.html', rides=rides, name=name[0], calendar_date=calendar_date)

    else:
        return render_template('search_ride.html')


@app.route('/pickup', methods=['GET', 'POST'])
def pickup():
    return render_template('pickup.html')



@app.route('/submit-ride', methods=['POST'])
def submit_ride():
    # Get data from the request
    data = request.get_json()

    # Extract values from the JSON data
    start_location = data.get('startLocation')
    end_location = data.get('endLocation')
    ride_date_time = data.get('rideDateTime')  # Expected format: 'YYYY-MM-DDTHH:MM'
    ride_type = data.get('rideType')
    passenger_count = data.get('passengerCount')
    passenger_price = data.get('passengerPrice')
    weight_capacity = data.get('weightCapacity')
    weight_price = data.get('weightPrice')
    ride_comments = data.get('rideComments')

    print("start_location ", start_location)
    print("end_location ", end_location)
    print("ride_date_time ", ride_date_time)
    print("ride_type ", ride_type)
    print("passenger_count ", passenger_count)
    print("passenger_price ", passenger_price)
    print("weight_capacity ", weight_capacity)
    print("weight_price ", weight_price)
    print("ride_comments ", ride_comments)

    datetime_obj = datetime.datetime.strptime(ride_date_time, "%Y-%m-%dT%H:%M")

    new_datetime_obj = datetime_obj + datetime.timedelta(minutes=13)

    # Convert to the desired format
    formatted_startdate = new_datetime_obj.strftime("%Y-%m-%d %H:%M:%S")
    StartTime = new_datetime_obj.strftime("%I:%M %p")  # Fetch only time in AM/PM format

    # Output results
    print("Formatted DateTime:", formatted_startdate)
    print("Time in AM/PM:", StartTime)

    # Google Maps API client setup
    gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)

    # Fetch coordinates for the start location
    if start_location:
        geocode_url = f"https://maps.googleapis.com/maps/api/geocode/json?address={start_location}&key={GOOGLE_MAPS_API_KEY}"
        response = requests.get(geocode_url)
        geocode_data = response.json()

        if geocode_data['status'] == 'OK':
            coordinates = geocode_data['results'][0]['geometry']['location']
            start_latitude = coordinates['lat']
            start_longitude = coordinates['lng']
            session['pickupcoordinates'] = f"{start_latitude},{start_longitude}"
        else:
            return jsonify({'message': 'Failed to fetch start location coordinates', 'status': geocode_data['status']}), 400

    # Fetch coordinates for the end location
    if end_location:
        geocode_url = f"https://maps.googleapis.com/maps/api/geocode/json?address={end_location}&key={GOOGLE_MAPS_API_KEY}"
        response = requests.get(geocode_url)
        geocode_data = response.json()

        if geocode_data['status'] == 'OK':
            coordinates = geocode_data['results'][0]['geometry']['location']
            end_latitude = coordinates['lat']
            end_longitude = coordinates['lng']
            session['dropcoordinates'] = f"{end_latitude},{end_longitude}"
        else:
            return jsonify({'message': 'Failed to fetch end location coordinates', 'status': geocode_data['status']}), 400

    # Calculate distance and estimated time using Google Maps Distance Matrix API
    if start_latitude and start_longitude and end_latitude and end_longitude:
        # Request distance and time data
        result = gmaps.distance_matrix(
            origins=(start_latitude, start_longitude),
            destinations=(end_latitude, end_longitude),
            mode="driving",  # You can change this to "walking", "transit", etc.
            departure_time = datetime.datetime.now()  # Can be set to a specific time if needed
        )

        # Extract the distance and duration
        if result['status'] == 'OK':
            distance = result['rows'][0]['elements'][0]['distance']['text']
            duration_text = result['rows'][0]['elements'][0]['duration']['text']
            session['ride_distance'] = distance
            session['ride_duration'] = duration_text

            print("Distance: ", distance)
            print("Duration: ", duration_text)
        else:
            return jsonify({'message': 'Failed to calculate distance and duration', 'status': result['status']}), 400

    # Convert ride_date_time string (with 'T') to a datetime object
    try:
        ride_date_time_obj = datetime.datetime.strptime(ride_date_time, '%Y-%m-%dT%H:%M')
    except ValueError:
        return jsonify({'message': 'Invalid ride_date_time format. Expected format: YYYY-MM-DDTHH:MM'}), 400

    # Extract the duration from the duration text (e.g., "15 mins" or "1 hour 20 mins")
    duration_minutes = 0
    hours_match = re.search(r'(\d+)\s*hour', duration_text)
    minutes_match = re.search(r'(\d+)\s*min', duration_text)

    if hours_match:
        duration_minutes += int(hours_match.group(1)) * 60  # Convert hours to minutes
    if minutes_match:
        duration_minutes += int(minutes_match.group(1))

    # Add the duration to the ride_date_time
    ride_end_time = ride_date_time_obj + datetime.timedelta(minutes=duration_minutes)

    print("ride_end_time ", ride_end_time)

    # Format the ride_end_time to a string and add it to the session
    session['ride_end_time'] = ride_end_time.strftime('%Y-%m-%dT%H:%M')


    new_datetime_obj = ride_end_time + datetime.timedelta(minutes=13)

    # Convert to the desired format
    formatted_datetime = new_datetime_obj.strftime("%Y-%m-%d %H:%M:%S")
    EndTime = new_datetime_obj.strftime("%I:%M %p")  # Fetch only time in AM/PM format

    # Output results
    print("Formatted DateTime:", formatted_datetime)
    print("EndTime:", EndTime)
    print("Time in AM/PM:", StartTime)


    user = request.cookies.get('username')  # Fetch the 'user' cookie

    print(user)

    coordinates_list = [float(coord) for coord in session['pickupcoordinates'].split(",")]
    pickupcity = api.find_city(GOOGLE_MAPS_API_KEY, coordinates_list[0], coordinates_list[1])

    dropcoordinates_list = [float(coord) for coord in session["dropcoordinates"].split(",")]
    dropcity = api.find_city(GOOGLE_MAPS_API_KEY, dropcoordinates_list[0], dropcoordinates_list[1])
    
    datetime_obj = datetime.datetime.strptime(formatted_startdate, "%Y-%m-%d %H:%M:%S")

    # Convert to the desired format
    ride_start_date = datetime_obj.strftime("%d %B %Y")

    print("formatted_date ", ride_start_date)
    
    host = api.hostride(start_location, session['pickupcoordinates'], pickupcity, end_location, session['dropcoordinates'], dropcity, ride_start_date, StartTime, EndTime, passenger_count, "₹ "+passenger_price, weight_capacity, "₹ "+weight_price, ride_type, ride_comments, user)
    print(host)
    session['came_from_going'] = False


    redirect_url = url_for(
    'ride_published',
    pickuplocation=pickupcity,
    droplocation=dropcity,
    distance=quote(distance),
    price=quote(passenger_price)
    )
    

    if host:
        # return True
        user = request.cookies.get('username')  # Fetch the 'user' cookie
        checkkyc = api.check_kyc(user)

        if checkkyc == "no":
            redirect_url = url_for('uploadkyc')
            return jsonify({'success': True, 'redirect_url': redirect_url})
        else: 
            redirect_url = url_for('ride_published', pickuplocation=pickupcity, droplocation=dropcity, distance=distance, price=passenger_price)
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
    user = request.cookies.get('username')  # Fetch the 'user' cookie

    keys = [
        "start_location", "start_coordinated", "pickupcity", "end_location", "end_coordinated", "dropcity", 
        "date", "start_time", "end_time", "passengers", "passengerprice", "kgcount", "kgprice", 
        "ride_type", "details", "userid", "uniqueid", "datetime", "ridepickuplocation", "ridedroplocation"
    ]

    ride = api.fetch_your_rides(user)

    print("ride ", ride)

    name = None  # ✅ Initialize 'name' to avoid UnboundLocalError
    rides = None

    if ride:
        rides = [dict(zip(keys, entry[:len(keys)])) for entry in ride]
        name_data = api.find_host_user(rides[0].get('userid'))
        if name_data:  # ✅ Ensure 'name_data' is not None or empty
            name = str(name_data[0] + " " + name_data[1])

        gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)

        for ride in rides:
            start_coords = ride["start_coordinated"]
            end_coords = ride["end_coordinated"]
            
            try:
                result = gmaps.distance_matrix(
                    origins=start_coords,
                    destinations=end_coords,
                    mode="driving",
                    units="metric"
                )
                distance = result["rows"][0]["elements"][0]["distance"]["text"]
                duration = result["rows"][0]["elements"][0]["duration"]["text"]

                ride["distance"] = distance
                ride["duration"] = duration

            except Exception as e:
                print(f"Error fetching data for ride {ride['uniqueid']}: {e}")
                ride["distance"] = "N/A"
                ride["duration"] = "N/A"

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


    fetch_passengers = api.fetch_passengers(ride_details.get("uniqueid"))

    keys = [
    "name", "number", "personcount", "kgcount", "uniqueid", "approval", "datetime"
    ]

    passengers = [dict(zip(keys, entry[:len(keys)])) for entry in fetch_passengers]

    print(passengers)

    return render_template('hosted_rides_details.html', ride=ride_details, passengers=passengers)


@app.route('/my_rides')
def my_rides():
    user = request.cookies.get('username')  # Fetch the 'user' cookie

    keys = [
    "start_location", "start_coordinated", "pickupcity", "end_location", "end_coordinated", "dropcity", "date", "start_time", "end_time", "passengers", "passengerprice", "kgcount", "kgprice", "ride_type", "details", "userid", "uniqueid", "datetime", "ridepickuplocation", "ridedroplocation"
    ]

    ride = api.fetch_my_rides(user)

    print("ride ", ride)
    # Convert to required format
    name = None  # ✅ Initialize 'name' to avoid UnboundLocalError
    rides = None

    if ride:
        rides = [dict(zip(keys, entry[:len(keys)])) for entry in ride]
        name = api.find_host_user(rides[0].get('userid'))
        name = str(name[0]+" "+name[1])

        gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)

        for ride in rides:
            start_coords = ride["start_coordinated"]
            end_coords = ride["end_coordinated"]
            
            # Use Google Maps Distance Matrix API
            try:
                result = gmaps.distance_matrix(
                    origins=start_coords,
                    destinations=end_coords,
                    mode="driving",  # Options: driving, walking, bicycling, transit
                    units="metric"
                )
                distance = result["rows"][0]["elements"][0]["distance"]["text"]
                duration = result["rows"][0]["elements"][0]["duration"]["text"]

                # Add distance and duration to the ride dictionary
                ride["distance"] = distance
                ride["duration"] = duration

            except Exception as e:
                print(f"Error fetching data for ride {ride['uniqueid']}: {e}")
                ride["distance"] = "N/A"
                ride["duration"] = "N/A"


    return render_template('my_rides.html', rides=rides)


@app.route('/my_rides_details')
def my_rides_details():
    user = request.cookies.get('username')  # Fetch the 'user' cookie
    
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

    fetch_passengers = api.fetch_passengers(ride_details.get("uniqueid"))

    keys = [
    "name", "number", "personcount", "kgcount", "uniqueid", "approval", "datetime"
    ]

    passengers = [dict(zip(keys, entry[:len(keys)])) for entry in fetch_passengers]

    for passenger in passengers:
        passenger['total_count'] = int(passenger['personcount']) + int(passenger['kgcount'])

    print("user ", passengers)

    selected_passenger = [p for p in passengers if p["number"] == user]

    print("selected_passenger ", selected_passenger)

    return render_template('my_rides_details.html', ride=ride_details, passengers=selected_passenger[0])


@app.route('/book_ride')
def book_ride():
    return render_template('book_ride.html')  # Renders the HTML page directly


@app.route('/search_ride_details', methods=['GET', 'POST'])
def search_ride_details():
    if request.method == 'POST':
        try:
            # Parse incoming JSON data
            data = request.json
            if not data:
                raise ValueError("No JSON data received.")

            # Extract data from the request
            uniqueid = data.get('uniqueid')
            price = data.get('price', 0)  # Default to 0 if not provided
            kgprice = data.get('kgprice', 0)
            start_location = data.get('start_location', "Unknown")
            end_location = data.get('end_location', "Unknown")

            # Fetch user details from cookies
            user = request.cookies.get('username')
            if not user:
                raise ValueError("User not authenticated.")

            print("User: ", user)

            # Fetch user profile details (simulate API call)
            profile = api.fetch_profile(user)
            if not profile:
                raise ValueError("Unable to fetch user profile.")

            print("Profile: ", profile)
            name = f"{profile[0][0]} {profile[0][1]}"
            number = profile[0][2]
            email = profile[0][3]

            print("Name: ", name)
            print("Number: ", number)
            print("Email: ", email)

            # Print received data for debugging
            print(f"Received: uniqueid={uniqueid}, price={price}, kgprice={kgprice}, start_location={start_location}, end_location={end_location}")

            # Validate required fields
            if uniqueid is None or price is None or kgprice is None:
                raise ValueError("Invalid data provided. All fields are required.")

            # Simulate booking the ride (replace with actual API call)
            # book_ride_result = api.book_ride(name, number, price, kgprice, uniqueid, "pending")
            # print("Booking Result: ", book_ride_result)

            # Respond with success and redirect URL
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

    else:  # Handle GET request
        try:
            # Extract ride details from query parameters
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

            print("Ride Details: ", ride_details)

            # Simulate fetching passengers (replace with actual API call)
            fetch_passengers = api.fetch_passengers(ride_details.get("uniqueid"))
            keys = ["name", "number", "personcount", "kgcount", "uniqueid", "approval", "datetime"]
            passengers = [dict(zip(keys, entry[:len(keys)])) for entry in fetch_passengers]

            print("Passengers: ", passengers)

            user = request.cookies.get('username')
            
            fetch_vehicle = api.fetch_vehicle(user)
            keys = ["carcompany", "carnumber", "carmodel", "userid", "datetime"]
            carmodel = [dict(zip(keys, entry[:len(keys)])) for entry in fetch_vehicle]

            print("carmodel: ", carmodel)

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
    uniqueid = session.get('uniqueid', None)
    price = session.get('price', None)
    kgprice = session.get('kgprice', None)
    
    order_id = request.args.get("order_id")  # Get order_id from URL
    
    if not order_id:
        return jsonify({"error": "Missing order_id in request"}), 400
    
    api_response = Cashfree().PGOrderFetchPayments(x_api_version, order_id, None)
    
    if not api_response.data:
        return jsonify({"error": "No payment data found for this order"}), 404
    
    # Extract payment details
    payment = api_response.data[0]  # Assuming only one payment entity
    
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
    
    # Detect and extract payment method details
    if isinstance(payment.payment_method.actual_instance, PaymentMethodAppInPaymentsEntity):
        payment_details["payment_method"] = {
            "type": "Wallet/App",
            "provider": payment.payment_method.actual_instance.app.provider,
            "channel": payment.payment_method.actual_instance.app.channel,
            "phone": payment.payment_method.actual_instance.app.phone,
        }
    elif isinstance(payment.payment_method.actual_instance, PaymentMethodUPIInPaymentsEntity):
        payment_details["payment_method"] = {
            "type": "UPI",
            "upi_id": getattr(payment.payment_method.actual_instance.upi, "upi_id", "Unknown"),  # Adjust as per debug output
            "upi_provider": getattr(payment.payment_method.actual_instance.upi, "provider", "Unknown"),
        }
    elif isinstance(payment.payment_method.actual_instance, PaymentMethodNetBankingInPaymentsEntity):
        payment_details["payment_method"] = {
            "type": "Net Banking",
            "bank_name": getattr(payment.payment_method.actual_instance.netbanking, "bank_code", "Unknown"),  # Adjust as per debug output
        }
    elif isinstance(payment.payment_method.actual_instance, PaymentMethodCardInPaymentsEntity):
        payment_details["payment_method"] = {
            "type": "Card",
            "card_type": getattr(payment.payment_method.actual_instance.card, "card_type", "Unknown"),
            "last4": payment.payment_method.actual_instance.card.card_number if hasattr(payment.payment_method.actual_instance.card, "card_number") else "Unknown",
            "network": getattr(payment.payment_method.actual_instance.card, "card_brand", "Unknown"),  # Adjusted key name
        }
    else:
        payment_details["payment_method"] = {
            "type": "Unknown"
        }
    
    print("Payment Details:", payment_details)

    if payment_details["payment_status"] == "SUCCESS":
        print("SUCCESS")
        payment_insert = api.insert_payment(payment_details)
        if payment_insert == True:
            # Attempt to book the ride (simulated API call here)
            user = request.cookies.get('username')  # Fetch the 'user' cookie
            profile = api.fetch_profile(user)
            print("Profile: ", profile)
            name = f"{profile[0][0]} {profile[0][1]}"
            number = profile[0][2]
            email = profile[0][3]
            book_ride_result = api.book_ride(name, number, price, kgprice, uniqueid, "pending")
            print("Booking Result: ", book_ride_result)
            return redirect(url_for('payment_success'))
        else:
            return redirect(url_for('payment_failed'))
    else:
        payment_insert = api.insert_payment(payment_details)
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

    deletereide = api.delete_ride(uniqueid)

    if deletereide == True:
        return jsonify({'success': True, 'message': 'Ride deleted successfully'})
    else:
        return jsonify({'success': False, 'message': 'Unique ID is missing'})


@app.route('/delete_my_ride', methods=['POST'])
def delete_my_ride():
    data = request.get_json()
    uniqueid = data.get('uniqueid')
    user = request.cookies.get('username')  # Fetch the 'user' cookie

    deletereide = api.delete_my_ride(uniqueid, user)

    if deletereide == True:
        return jsonify({'success': True, 'message': 'Ride deleted successfully'})
    else:
        return jsonify({'success': False, 'message': 'Unique ID is missing'})


@app.route('/reject_passenger', methods=['POST'])
def reject_passenger():
    try:
        data = request.get_json()
        number = data.get('number')

        print(number)
        
        passengeractivity = api.passenger_activity("rejected", number)

        print(passengeractivity)

        return jsonify({'success': True, 'message': 'Passenger rejected successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/approve_passenger', methods=['POST'])
def approve_passenger():
    try:
        data = request.get_json()
        number = data.get('number')

        print(number)

        passengeractivity = api.passenger_activity("accepted", number)

        print(passengeractivity)

        # Perform your logic here (e.g., database operations)
        # For example:
        # approve_passenger_in_db(number)

        return jsonify({'success': True, 'message': 'Passenger approved successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/profile')
def profile():
    user = request.cookies.get('username')  # Fetch the 'user' cookie

    print(user)

    profile = api.fetch_profile(user)
    # print(profile)

    keys = [
    "firstname", "lastnumber", "number", "emailid", "dob", "ipaddress", "uniqueid", "password", "emailverification", "kycverification", "datetime"
    ]

    passengers = [dict(zip(keys, entry[:len(keys)])) for entry in profile]

    print(passengers)

    vehicles = api.fetch_vehicle(user)
    print(vehicles)

    vehicles_keys = [
    "carcompany", "carnumber", "carmodel", "userid", "datetime"
    ]

    vehicles = [dict(zip(vehicles_keys, entry[:len(vehicles_keys)])) for entry in vehicles]

    banks = api.fetch_bank_account(user)
    print(banks)

    bank_keys = [
    "bankname", "accountnumber", "ifscode", "holder_name", "userid", "datetime"
    ]

    banks_arrays = [dict(zip(bank_keys, entry[:len(bank_keys)])) for entry in banks]

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


@app.route('/add_kyc', methods=['GET', 'POST'])
def add_kyc():
    user = request.cookies.get('username')  # Fetch the 'user' cookie
    if request.method == 'POST':
        # Get files from the form
        frontfile = request.files.get('frontfile')
        backfile = request.files.get('backfile')

        # Validate presence of files
        if not frontfile or not frontfile.filename:
            print('Front file is missing or has no filename.')
            return redirect(request.url)

        if not backfile or not backfile.filename:
            print('Back file is missing or has no filename.')
            return redirect(request.url)

        # Validate file types
        if not allowed_file(frontfile.filename):
            print('Front file type is not allowed. Only PNG, JPG, and JPEG are supported.')
            return redirect(request.url)

        if not allowed_file(backfile.filename):
            print('Back file type is not allowed. Only PNG, JPG, and JPEG are supported.')
            return redirect(request.url)

        try:
            # Extract extensions safely
            front_extension = frontfile.filename.rsplit('.', 1)[-1].lower()
            back_extension = backfile.filename.rsplit('.', 1)[-1].lower()

            print("front_extension ", front_extension)
            print("back_extension ", back_extension)

            # Generate unique filenames
            front_filename = generate_filename(frontfile.filename, 'front', user)
            back_filename = generate_filename(backfile.filename, 'back', user)

            print("front_filename ", front_filename)
            print("back_filename ", back_filename)

            # Save paths
            front_path = os.path.join(app.config['UPLOAD_FOLDER'], front_filename)
            back_path = os.path.join(app.config['UPLOAD_FOLDER'], back_filename)

            print("front_path ", front_path)
            print("back_path ", back_path)

            # Save files using Pillow for image validation
            try:
                front_img = Image.open(frontfile)
                front_img.save(front_path)
            except UnidentifiedImageError:
                print('Front file is not a valid image.')
                return redirect(request.url)

            try:
                back_img = Image.open(backfile)
                back_img.save(back_path)
            except UnidentifiedImageError:
                print('Back file is not a valid image.')
                return redirect(request.url)

            # Success
            print(f'Files uploaded successfully: {front_filename}, {back_filename}')
            update_kyc = api.update_kyc(user)
            print(update_kyc)
            return redirect(url_for('profile'))

        except Exception as e:
            print(f'An error occurred while processing the images: {e}')
            return redirect(request.url)

    return render_template('add_kyc.html')


@app.route('/send_email_verification', methods=['POST'])
def send_email_verification():
    user = request.cookies.get('username')  # Fetch the 'user' cookie
    # Check if request body contains JSON
    if not request.is_json:
        return jsonify({"error": "Request body must be JSON"}), 400
    # Extract the email from the request body
    data = request.get_json()
    email = data.get('email')

    print(email)

    if not email:
        return jsonify({"error": "Email is missing"}), 400

    # Simulate email sending logic (replace this with your actual logic)
    try:
        print(f"Sending verification email to {email}")
        sendmail = api.send_verification_mail(email, user)
        print(sendmail)
        return jsonify({"message": "Verification email sent successfully!"}), 200
    except Exception as e:
        print(f"Error while sending email: {e}")
        return jsonify({"error": "Failed to send verification email"}), 500


@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    user = request.cookies.get('username')  # Fetch the 'user' cookie

    if request.method == 'POST':
        password = request.form['password']
        print(password)
        change = api.change_password(user, password)
        
        if change == True:
            print("working")
            return redirect(url_for('profile'))
        
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

        add = api.add_vehicle(user, company, carnumber, carmodel)

        print("add ", add)

        if add is True:
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
        print(bankname)
        print(accountnumber)
        print(ifscode)
        print(holdername)

        add = api.add_bank_account(user, bankname, accountnumber, ifscode, holdername)

        print("add ", add)

        if add is True:
            return redirect(url_for('profile'))
    
    return render_template('add_bank_account.html')


@app.route('/logout')
def logout():
    session.clear()
    response = make_response(redirect(url_for('home')))
    
    response.set_cookie('username', '', expires=0)

    session.clear()
    
    # Delete cookies by setting the expiration to a past date
    response.set_cookie('username', '', expires=0)
    response.set_cookie('session_id', '', expires=0)  # Example of deleting a session cookie
  
    return render_template('index.html')


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
    socketio.run(app, debug=True, port=8080, allow_unsafe_werkzeug=True)

