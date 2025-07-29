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



app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Ensure you use a secure key for session

# # Configure Flask-Caching with Redis
# app.config['CACHE_TYPE'] = 'redis'
# app.config['CACHE_REDIS_HOST'] = 'localhost'
# app.config['CACHE_REDIS_PORT'] = 6379
# cache = Cache(app)

GOOGLE_MAPS_API_KEY = "AIzaSyCdc5N7AzzvPiWddsegRCRmna3LxG5HCmk"

# Upload folder configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)



@app.route('/')
def home():
    username = request.cookies.get('username')
    if username:
        session['username'] = username
        return redirect(url_for('main'))
    else:
        return render_template('index.html')


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

        # Check if the user credentials are correct
        if checklogin == True:
            session['username'] = username  # Save to session
            expire_date = datetime.datetime.now() + datetime.timedelta(days=30)
            resp = make_response(redirect(url_for('main')))
            resp.set_cookie('username', username, expires=expire_date)

            return resp
            
        else:
            error = "This email address is already being used by another account!"
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
            email = "kirtip2673@gmail.com"

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
        sessionotp = session.get('otp')
        print("Session OTP:", sessionotp)

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
    }

    print(user_data)

    userid = str(user_data.get("firstname"))[:3]+str(user_data.get("mobilenumber"))[:3]

    check = api.signup(user_data.get("firstname"), user_data.get("lastname"), user_data.get("email"), user_data.get("mobilenumber"), user_data.get("dateofbirth"), user_data.get("password"), userid) 

    if check:
        return True
    else:
        return False
    
    # return render_template('signup_mobile_code.html')


@app.route('/main', methods=['GET', 'POST'])
def main():
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

        # Redirect or render the next page
        return redirect(url_for('search_ride'))

    # GET request handling (renders main page)
    ridepickuplocation = session.get('ridepickuplocation', 'Pickup Location')
    ridedroplocation = session.get('ridedroplocation', 'Drop Location')
    came_from_going = session.get('came_from_going', False)
    print("came_from_going ", came_from_going)
    # print("Full session content:", dict(session))
    leaving_text = str(ridepickuplocation) if came_from_going else "Leaving from"
    going_text = str(ridedroplocation) if came_from_going else "Going from"

    # Clear the flag after use
    session.pop('came_from_going', None)

    return render_template(
        'main.html',
        leaving_text=leaving_text,
        going_text=going_text
    )


@app.route('/leaving', methods=['GET', 'POST'])
def leaving():
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            pickuplocation = data.get('pickuplocation', '')
            print('Pickup Location:', pickuplocation)

            # Save the value in the session (optional)
            session['ridepickuplocation'] = pickuplocation

            # Get coordinates from Google Maps API
            geocode_url = f"https://maps.googleapis.com/maps/api/geocode/json?address={pickuplocation}&key={GOOGLE_MAPS_API_KEY}"
            response = requests.get(geocode_url)
            geocode_data = response.json()

            if geocode_data['status'] == 'OK':
                coordinates = geocode_data['results'][0]['geometry']['location']
                latitude = coordinates['lat']
                longitude = coordinates['lng']

                print(latitude)
                print(longitude)
                session['ridepickupcoordinates'] = str(latitude) + "," + str(longitude)

                # Return coordinates to frontend
                return jsonify({
                    'message': 'Coordinates fetched successfully',
                    'location': pickuplocation,
                    'coordinates': {'lat': latitude, 'lng': longitude}
                })
            else:
                return jsonify({'message': 'Failed to fetch coordinates', 'status': geocode_data['status']}), 400

        # For traditional form submissions
        session['came_from_going'] = True
        pickuplocation = request.form.get('pickuplocation', '')
        session['ridepickuplocation'] = pickuplocation
        print(session['ridepickuplocation'])
        print(session['ridepickupcoordinates'])
        return redirect(url_for('going'))

    return render_template('leaving.html')



@app.route('/going', methods=['GET', 'POST'])
def going():
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            droplocation = data.get('droplocation', '')
            print('drop Location:', droplocation)

            # Save the value in the session (optional)
            session['ridedroplocation'] = droplocation

            # Get coordinates from Google Maps API
            geocode_url = f"https://maps.googleapis.com/maps/api/geocode/json?address={droplocation}&key={GOOGLE_MAPS_API_KEY}"
            response = requests.get(geocode_url)
            geocode_data = response.json()

            if geocode_data['status'] == 'OK':
                coordinates = geocode_data['results'][0]['geometry']['location']
                latitude = coordinates['lat']
                longitude = coordinates['lng']

                print(latitude)
                print(longitude)
                session['ridedropcoordinates'] = str(latitude)+","+str(longitude)
                # Return coordinates to frontend
                return jsonify({
                    'message': 'Coordinates fetched successfully',
                    'location': droplocation,
                    'coordinates': {'lat': latitude, 'lng': longitude}
                })
            else:
                return jsonify({'message': 'Failed to fetch coordinates', 'status': geocode_data['status']}), 400

        # For traditional form submissions
        droplocation = request.form.get('droplocation', '')
        session['ridedroplocation'] = droplocation
        print(session['ridedroplocation'])
        print(session['ridedropcoordinates'])
        session['came_from_going'] = True
        return redirect(url_for('main'))

    return render_template('going.html')


@app.route('/search_ride')
def search_ride():
    # Retrieve session data
    ridepickuplocation = session.get('ridepickuplocation', '')
    ridedroplocation = session.get('ridedroplocation', '')
    calendar_date = session.get('calendar_date', '')
    person_count = session.get('person_count', '')


    ridepickupcoordinates = session.get('ridepickupcoordinates')
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
        name = api.find_host_user(findride[0][13])

        keys = [
        "start_location", "start_coordinated", "pickupcity", "end_location", "end_coordinated", "dropcity", "date", "start_time", "end_time", "passengers", "passengerprice", "kgprice", "details", "userid", "uniqueid", "datetime"
        ]

        rides = [dict(zip(keys, entry[:len(keys)])) for entry in findride]

        print("findride arrays ",rides)
        print("name ", name[0])

        return render_template('search_ride.html', rides=rides, name=name[0])

    else:
        return render_template('search_ride.html')


@app.route('/pickup', methods=['GET', 'POST'])
def pickup():
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            pickuplocation = data.get('pickuplocation', '')
            print('Pickup Location:', pickuplocation)

            # Save the value in the session (optional)
            session['pickuplocation'] = pickuplocation
            

            # Get coordinates from Google Maps API
            geocode_url = f"https://maps.googleapis.com/maps/api/geocode/json?address={pickuplocation}&key={GOOGLE_MAPS_API_KEY}"
            response = requests.get(geocode_url)
            geocode_data = response.json()

            if geocode_data['status'] == 'OK':
                coordinates = geocode_data['results'][0]['geometry']['location']
                latitude = coordinates['lat']
                longitude = coordinates['lng']

                print(latitude)
                print(longitude)
                session['pickupcoordinates'] = str(latitude)+","+str(longitude)

                # Return coordinates to frontend
                return jsonify({
                    'message': 'Coordinates fetched successfully',
                    'location': pickuplocation,
                    'coordinates': {'lat': latitude, 'lng': longitude}
                })
            else:
                return jsonify({'message': 'Failed to fetch coordinates', 'status': geocode_data['status']}), 400

        # For traditional form submissions
        pickuplocation = request.form.get('pickuplocation', '')
        session['pickuplocation'] = pickuplocation
        print(session['pickuplocation'])
        print(session['pickupcoordinates'])
        return redirect(url_for('dropoff'))

    return render_template('pickup.html')


@app.route('/dropoff', methods=['GET', 'POST'])
def dropoff():
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            droplocation = data.get('droplocation', '')
            print('drop Location:', droplocation)

            # Save the value in the session (optional)
            session['droplocation'] = droplocation

            # Get coordinates from Google Maps API
            geocode_url = f"https://maps.googleapis.com/maps/api/geocode/json?address={droplocation}&key={GOOGLE_MAPS_API_KEY}"
            response = requests.get(geocode_url)
            geocode_data = response.json()

            if geocode_data['status'] == 'OK':
                coordinates = geocode_data['results'][0]['geometry']['location']
                latitude = coordinates['lat']
                longitude = coordinates['lng']

                print(latitude)
                print(longitude)
                session['dropcoordinates'] = str(latitude)+","+str(longitude)
                # Return coordinates to frontend
                return jsonify({
                    'message': 'Coordinates fetched successfully',
                    'location': droplocation,
                    'coordinates': {'lat': latitude, 'lng': longitude}
                })
            else:
                return jsonify({'message': 'Failed to fetch coordinates', 'status': geocode_data['status']}), 400

        # For traditional form submissions
        droplocation = request.form.get('droplocation', '')
        session['droplocation'] = droplocation
        print(session['droplocation'])
        print(session['dropcoordinates'])
        return redirect(url_for('when_publish'))

    return render_template('dropoff.html')




@app.route('/when_publish', methods=['GET', 'POST'])
def when_publish():
    if request.method == 'POST':
        riderdate = request.form['ridedate']
        print(riderdate)

        session['riderdate'] = riderdate
        return redirect(url_for('what_time'))

    return render_template('when_publish.html')


@app.route('/what_time', methods=['GET', 'POST'])
def what_time():
    if request.method == 'POST':
        starttime = request.form['starttime']
        endtime = request.form['endtime']
        
        print(starttime)
        print(endtime)

        session['starttime'] = starttime
        session['endtime'] = endtime
        return redirect(url_for('no_of_passengers'))

    return render_template('what_time.html')


@app.route('/no_of_passengers', methods=['GET', 'POST'])
def no_of_passengers():
    if request.method == 'POST':
        passengers = request.form['passengers']
        print(passengers)

        session['passengers'] = passengers
        return redirect(url_for('set_price'))

    return render_template('no_of_passengers.html')


@app.route('/set_price', methods=['GET', 'POST'])
def set_price():
    if request.method == 'POST':
        price = request.form['price']
        kgprice = request.form['kgprice']
        # upi = request.form['upi']
        print(price)
        print(kgprice)

        session['price'] = price
        session['kgprice'] = kgprice
        return redirect(url_for('ride_details'))

    return render_template('set_price.html')


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
    user_data = {
        'pickuplocation': session.get('pickuplocation'),
        'droplocation': session.get('droplocation'),
        'riderdate': session.get('riderdate'),
        'starttime': session.get('starttime'),
        'endtime': session.get('endtime'),
        'passengers': session.get('passengers'),
        'price': session.get('price'),
        'kgprice': session.get('kgprice'),
        'details': session.get('details'),
        'pickupcoordinates': session.get('pickupcoordinates'),
        'dropcoordinates': session.get('dropcoordinates')
    }

    user = request.cookies.get('username')  # Fetch the 'user' cookie

    print(user_data)
    print(user)

    coordinates_list = [float(coord) for coord in user_data.get("pickupcoordinates").split(",")]
    pickupcity = api.find_city(GOOGLE_MAPS_API_KEY, coordinates_list[0], coordinates_list[1])

    dropcoordinates_list = [float(coord) for coord in user_data.get("dropcoordinates").split(",")]
    dropcity = api.find_city(GOOGLE_MAPS_API_KEY, dropcoordinates_list[0], dropcoordinates_list[1])
    

    host = api.hostride(user_data.get("pickuplocation"), user_data.get("pickupcoordinates"), pickupcity, user_data.get("droplocation"), user_data.get("dropcoordinates"), dropcity, user_data.get("riderdate"), user_data.get("starttime"), user_data.get("endtime"), user_data.get("passengers"), user_data.get("price"), user_data.get("kgprice"), user_data.get("details"), user)
    print(host)
    distance = api.calculate_distance(GOOGLE_MAPS_API_KEY, tuple(map(float, user_data.get("pickupcoordinates").split(','))), tuple(map(float, user_data.get("dropcoordinates").split(','))))
    if host:
        # return True
        user = request.cookies.get('username')  # Fetch the 'user' cookie
        checkkyc = api.check_kyc(user)

        distance = distance / 1000

        if checkkyc == "no":
            return render_template('uploadkyc.html')
        else: 
            return render_template('ride_published.html', pickuplocation = pickupcity, droplocation = dropcity, distance = distance, price = user_data.get("price"))



@app.route('/uploadkyc')
def uploadkyc():    
    return render_template('uploadkyc.html')


@app.route('/your_rides')
def your_rides():
    user = request.cookies.get('username')  # Fetch the 'user' cookie

    keys = [
    "start_location", "start_coordinated", "pickupcity", "end_location", "end_coordinated", "dropcity", "date", "start_time", "end_time", "passengers", "passengerprice", "kgprice", "details", "userid", "uniqueid", "datetime"
    ]

    ride = api.fetch_your_rides(user)
    # Convert to required format
    rides = [dict(zip(keys, entry[:len(keys)])) for entry in ride]

    # Output the resulting rides array
    print("rides ", rides)

    return render_template('your_rides.html', rides=rides)


@app.route('/your_rides_details')
def your_rides_details():
    ride_details = {
        "date": request.args.get('date'),
        "start_time": request.args.get('start_time'),
        "end_time": request.args.get('end_time'),
        "start_location": request.args.get('start_location'),
        "end_location": request.args.get('end_location'),
        "uniqueid": request.args.get('uniqueid'),
    }

    fetch_passengers = api.fetch_passengers(ride_details.get("uniqueid"))

    keys = [
    "name", "number", "personcount", "kgcount", "uniqueid", "approval", "datetime"
    ]

    passengers = [dict(zip(keys, entry[:len(keys)])) for entry in fetch_passengers]

    print(passengers)

    return render_template('your_rides_details.html', ride=ride_details, passengers=passengers)


@app.route('/search_ride_details')
def search_ride_details():
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
    }

    print("ride_details ", ride_details)

    fetch_passengers = api.fetch_passengers(ride_details.get("uniqueid"))

    keys = [
    "name", "number", "personcount", "kgcount", "uniqueid", "approval", "datetime"
    ]

    passengers = [dict(zip(keys, entry[:len(keys)])) for entry in fetch_passengers]

    print("passengers ", passengers)

    return render_template('search_ride_details.html', ride=ride_details, passengers=passengers)



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


def generate_filename(original_filename, type, user):
    # Safely check for file extension presence
    if '.' in original_filename:
        file_extension = original_filename.rsplit('.', 1)[1].lower()
        unique_name = f"{user}_{uuid.uuid4().hex}_{type}.{file_extension}"
        return unique_name
    else:
        raise ValueError(f"Invalid filename: {original_filename}")


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


if __name__ == '__main__':
    # app.run(debug=True)
    # app = WsgiToAsgi(app)
    app.run(host="0.0.0.0", port=8080)
