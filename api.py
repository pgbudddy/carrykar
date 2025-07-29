from conn import *
import datetime
import requests
import googlemaps
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def login(number, password):
    try:
        # Get a connection from the pool
        mydb = get_db_connection()

        # Create a cursor from the connection
        mycursor = mydb.cursor(buffered=True)
        
        # Use BINARY to enforce case sensitivity for the password
        query = 'SELECT * FROM signup WHERE number=%s AND BINARY password=%s'
        mycursor.execute(query, (number, password))  # Use parameterized query to prevent SQL injection
        
        # Fetch the result
        myresult = mycursor.fetchone()

        # Check if the user exists
        if myresult is None:
            return False
        else:
            return True

    except Exception as e:
        print("Error:", e)  # Log the error for debugging
        return False

    finally:
        # Ensure that the cursor and connection are closed
        close_connection(mydb, mycursor)

    

def fetch_userid(number):
    try:
        # Get a connection from the pool
        mydb = get_db_connection()

        # Create a cursor from the connection
        mycursor = mydb.cursor(buffered=True)
        
        query = 'SELECT * FROM signup where number="'+str(number)+'"'
        mycursor.execute(query)
        myresult = mycursor.fetchone()
        
        if myresult == None:  
            return False
        else:
            return myresult[0], myresult[1], myresult[6]

    except:
        return False

    finally:
        # Ensure that the cursor and connection are closed
        close_connection(mydb, mycursor)


def check_kyc(number):
    try:
        # Get a connection from the pool
        mydb = get_db_connection()

        # Create a cursor from the connection
        mycursor = mydb.cursor(buffered=True)
        
        query = 'SELECT kycverification FROM signup where number="'+str(number)+'"'
        mycursor.execute(query)
        myresult = mycursor.fetchone()
        
        if myresult == None:  
            return False
        else:
            return myresult[0]

    except:
        return False
    
    finally:
        # Ensure that the cursor and connection are closed
        close_connection(mydb, mycursor)


def get_recent_messages():
    try:
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=7)
        mydb = get_db_connection()
        mycursor = mydb.cursor(buffered=True)
        mycursor.execute("SELECT username, message, timestamp FROM messages WHERE timestamp >= %s ORDER BY timestamp ASC", (cutoff_date,))
        myresult = mycursor.fetchall()

        if myresult == None:
            return False
        else:
            return myresult
    
    except:
        return False
    
    finally:
        close_connection(mydb, mycursor)


def save_message(username, message, timestamp):
    print("save_message")
    try:
        # Get a connection from the pool
        mydb = get_db_connection()

        # Create a cursor from the connection
        mycursor = mydb.cursor(buffered=True)
        
        date = datetime.datetime.now()
        print(username, message, timestamp)
        trade = "INSERT INTO messages (username, message, timestamp) VALUES (%s, %s, %s)"
        mycursor.execute(trade, (username, message, timestamp))
        mydb.commit()
        
        # Check if insertion was successful
        if mycursor.rowcount > 0:
            print("Data inserted successfully.")
            return True
        else:
            print("Data insertion failed.")
            return False
        
    except Exception as e:
        print(e)
        return False

    finally:
        # Ensure that the cursor and connection are closed
        close_connection(mydb, mycursor)


def insert_payment(payment):
    print("payment ", payment)
    mydb = None
    mycursor = None
    try:
        mydb = get_db_connection()
        mycursor = mydb.cursor(buffered=True)

        # Access attributes using dot notation
        cf_payment_id = payment["cf_payment_id"]
        order_id = payment["order_id"]
        order_amount = payment["order_amount"]
        payment_currency = payment["payment_currency"]
        payment_amount = payment["payment_amount"]
        payment_time = payment["payment_time"]
        payment_completion_time = payment["payment_completion_time"]
        payment_status = payment["payment_status"]
        payment_message = payment["payment_message"]
        bank_reference = payment["bank_reference"]
        payment_group = payment["payment_group"]
        payment_method = payment["payment_method"]  # Assuming this is already a string or valid data
        uniqueid = payment["uniqueid"]  # Use `getattr` to avoid AttributeError if email is missing
        contact = payment["contact"] 

        date = datetime.datetime.now()

        # Prepare the INSERT query
        trade = """
            INSERT INTO payments (
                cf_payment_id, order_id, order_amount, payment_currency, payment_amount, 
                payment_time, payment_completion_time, payment_status, payment_message, 
                bank_reference, payment_group, payment_method, uniqueid, contact, datetime
            ) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        # Execute the query
        mycursor.execute(trade, (
            str(cf_payment_id), str(order_id), str(order_amount), str(payment_currency), str(payment_amount), 
            str(payment_time), str(payment_completion_time), str(payment_status), str(payment_message), 
            str(bank_reference), str(payment_group), str(payment_method), str(uniqueid), str(contact), str(date)
        ))

        mydb.commit()

        if mycursor.rowcount > 0:
            print("Data inserted successfully.")
            return True
        else:
            print("Data insertion failed.")
            return False

    except Exception as e:
        print("Error:", e)
        return False

    finally:
        if mycursor:
            mycursor.close()
        if mydb:
            mydb.close()


    
def passenger_activity(approval, number):
    try:
        # Get a connection from the pool
        mydb = get_db_connection()

        # Create a cursor from the connection
        mycursor = mydb.cursor(buffered=True)
        
        trade = "UPDATE passengers SET approval='"+str(approval)+"' WHERE number='"+str(number)+"'"
        mycursor.execute(trade)
        mydb.commit()
        
        # Check if insertion was successful
        if mycursor.rowcount > 0:
            print("Data inserted successfully.")
            return True
        else:
            print("Data insertion failed.")
            return False
        
    except:
        return False

    finally:
        # Ensure that the cursor and connection are closed
        close_connection(mydb, mycursor)


def fetch_your_rides(number):
    try:
        # Get a connection from the pool
        mydb = get_db_connection()

        # Create a cursor from the connection
        mycursor = mydb.cursor(buffered=True)
        
        userid = fetch_userid(number)
        query = 'SELECT * FROM hosted_rides where userid="'+str(userid[2])+'"'
        mycursor.execute(query)
        myresult = mycursor.fetchall()

        # print(myresult)
        
        if myresult == None:  
            return False
        else:
            return myresult

    except:
        return False

    finally:
        # Ensure that the cursor and connection are closed
        close_connection(mydb, mycursor)


def fetch_my_rides(number):
    try:
        # Get a connection from the pool
        mydb = get_db_connection()

        # Create a cursor from the connection
        mycursor = mydb.cursor(buffered=True)

        # Query to get all unique IDs for the given number
        query = 'SELECT uniqueid FROM passengers WHERE number=%s'
        mycursor.execute(query, (number,))
        myresult = mycursor.fetchall()

        print("myresult ", myresult)


        if myresult == []:  
            return myresult
        else:
            # Extract unique IDs from the query result
            unique_ids = [row[0] for row in myresult if row[0] is not None]

            if not unique_ids:
                return False  # No valid unique IDs found

            # Query to fetch data from hosted_rides for all unique IDs
            query = 'SELECT * FROM hosted_rides WHERE uniqueid IN ({})'.format(
                ','.join(['%s'] * len(unique_ids))
            )
            mycursor.execute(query, unique_ids)
            hosted_rides = mycursor.fetchall()

            return hosted_rides if hosted_rides else False

    except Exception as e:
        print("Error:", e)
        return False



# print(fetch_my_rides("9137620445"))


def fetch_passengers(uniqueid):
    try:
        # Get a connection from the pool
        mydb = get_db_connection()

        # Create a cursor from the connection
        mycursor = mydb.cursor(buffered=True)
        
        query = 'SELECT * FROM passengers where uniqueid="'+str(uniqueid)+'"'
        mycursor.execute(query)
        myresult = mycursor.fetchall()

        # print(myresult)
        
        if myresult == None:  
            return False
        else:
            return myresult

    except:
        return False
    
    finally:
        # Ensure that the cursor and connection are closed
        close_connection(mydb, mycursor)


def book_ride(name, number, personcount, kgcount, uniqueid, approval):
    try:
        # Get a connection from the pool
        mydb = get_db_connection()

        # Create a cursor from the connection
        mycursor = mydb.cursor(buffered=True)
        
        date = datetime.datetime.now()
        print(name, number, personcount, kgcount, uniqueid, approval)
        trade = "INSERT INTO passengers (name, number, personcount, kgcount, uniqueid, approval, datetime) values ('"+str(name)+"', '"+str(number)+"', '"+str(personcount)+"', '"+str(kgcount)+"', '"+str(uniqueid)+"', '"+str(approval)+"', '"+str(date)+"')"
        mycursor.execute(trade)
        mydb.commit()
        
        # Check if insertion was successful
        if mycursor.rowcount > 0:
            print("Data inserted successfully.")
            return True
        else:
            print("Data insertion failed.")
            return False
        
    except Exception as e:
        print(e)
        return False

    finally:
        # Ensure that the cursor and connection are closed
        close_connection(mydb, mycursor)


def fetch_profile(uniqueid):
    try:
        # Get a connection from the pool
        mydb = get_db_connection()

        # Create a cursor from the connection
        mycursor = mydb.cursor(buffered=True)
        
        query = 'SELECT * FROM signup where number="'+str(uniqueid)+'"'
        mycursor.execute(query)
        myresult = mycursor.fetchall()

        # print(myresult)
        
        if myresult == None:  
            return False
        else:
            return myresult

    except:
        return False
    
    finally:
        # Ensure that the cursor and connection are closed
        close_connection(mydb, mycursor)


def delete_ride(uniqueid):
    try:
        # Get a connection from the pool
        mydb = get_db_connection()

        # Create a cursor from the connection
        mycursor = mydb.cursor(buffered=True)
        
        trade = "DELETE FROM hosted_rides WHERE uniqueid='"+str(uniqueid)+"'"
        mycursor.execute(trade)
        mydb.commit()

        # Check the number of affected rows
        if mycursor.rowcount > 0:
            return True
        else:
            return False
    except Exception as e:
        print(f"Error: {e}")  # Log the error for debugging
        return False
    
    finally:
        # Ensure that the cursor and connection are closed
        close_connection(mydb, mycursor)


def delete_my_ride(uniqueid, number):
    try:
        # Get a connection from the pool
        mydb = get_db_connection()

        # Create a cursor from the connection
        mycursor = mydb.cursor(buffered=True)
        
        trade = "DELETE FROM passengers WHERE uniqueid='"+str(uniqueid)+"' AND number='"+str(number)+"'"
        mycursor.execute(trade)
        mydb.commit()

        # Check the number of affected rows
        if mycursor.rowcount > 0:
            return True
        else:
            return False
    except Exception as e:
        print(f"Error: {e}")  # Log the error for debugging
        return False
    
    finally:
        # Ensure that the cursor and connection are closed
        close_connection(mydb, mycursor)


def signup(firstname, lastname, email, mobilenumber, dateofbirth, password, userid, public_ip):
    try:
        # Get a connection from the pool
        mydb = get_db_connection()

        # Create a cursor from the connection
        mycursor = mydb.cursor(buffered=True)
        
        date = datetime.datetime.now()
        # public_ip = get_public_ip()

        trade = "INSERT INTO signup (firstname, lastname, number, emailid, dob, ipaddress, uniqueid, password, emailverification, kycverification, datetime) values ('"+str(firstname)+"', '"+str(lastname)+"', '"+str(mobilenumber)+"', '"+str(email)+"', '"+str(dateofbirth)+"', '"+str(public_ip)+"', '"+str(userid)+"', '"+str(password)+"', 'no', 'no', '"+str(date)+"')"
        mycursor.execute(trade)
        mydb.commit()
        
        # Check if insertion was successful
        if mycursor.rowcount > 0:
            print("Data inserted successfully.")
            return True
        else:
            print("Data insertion failed.")
            return False
        
    except:
        return False
    
    finally:
        # Ensure that the cursor and connection are closed
        close_connection(mydb, mycursor)


def change_password(number, password):
    try:
        # Get a connection from the pool
        mydb = get_db_connection()

        # Create a cursor from the connection
        mycursor = mydb.cursor(buffered=True)
        
        print(number)
        trade = "update signup set password = '"+str(password)+"' where number = '"+str(number)+"'"
        mycursor.execute(trade)
        mydb.commit()
        
        # Check if insertion was successful
        if mycursor.rowcount > 0:
            print("Data inserted successfully.")
            return True
        else:
            print("Data insertion failed.")
            return False
        
    except:
        return False

    finally:
        # Ensure that the cursor and connection are closed
        close_connection(mydb, mycursor)


def fetch_vehicle(number):
    try:
        # Get a connection from the pool
        mydb = get_db_connection()

        # Create a cursor from the connection
        mycursor = mydb.cursor(buffered=True)
        
        userid = fetch_userid(number)
        query = 'SELECT * FROM vehicles where userid="'+str(userid[2])+'"'
        mycursor.execute(query)
        myresult = mycursor.fetchall()

        print(myresult)

        if myresult == None:  
            return False
        else:
            return myresult

    except:
        return False
    
    finally:
        # Ensure that the cursor and connection are closed
        close_connection(mydb, mycursor)


def fetch_bank_account(number):
    try:
        # Get a connection from the pool
        mydb = get_db_connection()

        # Create a cursor from the connection
        mycursor = mydb.cursor(buffered=True)
        
        userid = fetch_userid(number)
        query = 'SELECT * FROM bank_accounts where userid="'+str(userid[2])+'"'
        mycursor.execute(query)
        myresult = mycursor.fetchall()

        print(myresult)

        if myresult == None:  
            return False
        else:
            return myresult

    except:
        return False

    finally:
        # Ensure that the cursor and connection are closed
        close_connection(mydb, mycursor)


def update_kyc(number):
    try:
        # Get a connection from the pool
        mydb = get_db_connection()

        # Create a cursor from the connection
        mycursor = mydb.cursor(buffered=True)
        
        print(number)
        trade = "update signup set kycverification = 'yes' where number = '"+str(number)+"'"
        mycursor.execute(trade)
        mydb.commit()
        
        # Check if insertion was successful
        if mycursor.rowcount > 0:
            print("Data inserted successfully.")
            return True
        else:
            print("Data insertion failed.")
            return False
        
    except:
        return False
    
    finally:
        # Ensure that the cursor and connection are closed
        close_connection(mydb, mycursor)


def update_email_verification(number):
    try:
        # Get a connection from the pool
        mydb = get_db_connection()

        # Create a cursor from the connection
        mycursor = mydb.cursor(buffered=True)
        
        print(number)
        trade = "update signup set emailverification = 'yes' where number = '"+str(number)+"'"
        mycursor.execute(trade)
        mydb.commit()
        
        # Check if insertion was successful
        if mycursor.rowcount > 0:
            print("Data inserted successfully.")
            return True
        else:
            print("Data insertion failed.")
            return False
        
    except:
        return False
    
    finally:
        # Ensure that the cursor and connection are closed
        close_connection(mydb, mycursor)


def send_verification_mail(receiver_email, number):
    # Sender's Gmail credentials (login credentials of 'vivekparmar75@gmail.com')
    sender_email = "carrykar108@gmail.com"  # Your Gmail address
    sender_password = "dboe gmgj riue ohsd"  # Your Gmail app password

    # Sender's email alias (custom domain email created through Cloudflare)
    sender_alias = "noreply@carrykar.co.in"  # The email you're sending from
    receiver_email = receiver_email  # The recipient's email

    # Email subject and body
    subject = "Please confirm your email address"

    # HTML content for the email body
    html_body = """
    <html>
        <head>
            <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap" rel="stylesheet">
            <style>
                body {
                    font-family: 'Poppins', sans-serif; 
                    color: #333; 
                    background-color: #f4f4f4; 
                    padding: 20px;
                    display: flex; /* Use flexbox */
                    justify-content: center; /* Horizontally center the mainbox */
                    align-items: flex-start; /* Align to the top */
                    height: 100vh; /* Full viewport height for alignment */
                    margin: 0; /* Remove default body margin */
                }
                .mainbox{
                    border: 1px solid lightgrey;
                    border-radius: 10px;
                    padding: 50px 50px;
                    width: 40%;
                }
                h1 {
                    font-family: 'Poppins', sans-serif;
                    color: black;
                }
                p {
                    font-family: 'Poppins', sans-serif;
                    font-size: 16px;
                    font-style: normal;
                    color: black;
                }
                .button {
                    background-color: #0747A9;
                    color: white;
                    padding: 10px 20px;
                    text-align: center;
                    text-decoration: none;
                    display: inline-block;
                    border-radius: 5px;
                    font-style: normal;
                    text-decoration: none;
                }
                .line{
                    border-top: 1px solid lightgrey;
                }
            </style>
        </head>
        <body>
            <div class="mainbox">
            <img src="./static/images/logo.png" style="width: 50px;" alt="Logo">
            <p>Hello User,</p>
            <p>Welcome to CarryKar! In order to get started, you need to confirm your email address.</p>
            <a href="https://example.com" class="button">Confirm email</a>
            <br><br>
            <div class="line"></div>
            <img src="./static/images/logo.png" style="margin-top: 30px; width: 30px;" alt="Logo">
            <p style="font-size: 13px;">Regards,<br>CarryKar Team</p>
            </div>
        </p>
    </html>
    """

    # Setup the MIME
    message = MIMEMultipart()
    message["From"] = sender_alias  # Set the 'From' to your custom domain email
    message["To"] = receiver_email
    message["Subject"] = subject

    # Attach the HTML body to the MIME message
    message.attach(MIMEText(html_body, "html"))

    # Gmail SMTP server configuration
    smtp_server = "smtp.gmail.com"
    smtp_port = 587  # TLS port

    try:
        # Get a connection from the pool
        mydb = get_db_connection()

        # Create a cursor from the connection
        mycursor = mydb.cursor(buffered=True)
        
        # Connect to Gmail's SMTP server
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # Secure the connection using TLS

        # Login to your Gmail account
        server.login(sender_email, sender_password)

        # Send the email
        server.sendmail(sender_alias, receiver_email, message.as_string())
        print("Email sent successfully!")
        # updatekyc = update_email_verification(number)
        # print(updatekyc)

    except Exception as e:
        print(f"Error: {e}")

    finally:
        # Ensure that the cursor and connection are closed
        close_connection(mydb, mycursor)


def send_mail(receiver_email, otp):
    # Sender's Gmail credentials (login credentials of 'vivekparmar75@gmail.com')
    sender_email = "carrykar108@gmail.com"  # Your Gmail address
    sender_password = "dboe gmgj riue ohsd"  # Your Gmail app password

    # Sender's email alias (custom domain email created through Cloudflare)
    sender_alias = "noreply@carrykar.co.in"  # The email you're sending from
    receiver_email = receiver_email  # The recipient's email

    # Email subject and body
    subject = "Welcome to CarryKar"

    # HTML content for the email body
    html_body = """
    <html>
        <head>
            <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap" rel="stylesheet">
            <style>
                body {
                    font-family: 'Poppins', sans-serif; 
                    color: #333; 
                    background-color: #f4f4f4; 
                    padding: 20px;
                    display: flex; /* Use flexbox */
                    justify-content: center; /* Horizontally center the mainbox */
                    align-items: flex-start; /* Align to the top */
                    height: 100vh; /* Full viewport height for alignment */
                    margin: 0; /* Remove default body margin */
                }
                .mainbox{
                    border: 1px solid lightgrey;
                    border-radius: 10px;
                    padding: 50px 50px;
                    width: 40%;
                }
                h1 {
                    font-family: 'Poppins', sans-serif;
                    color: #0747A9;
                    font-style: normal;
                    font-size: 25px;
                }
                p {
                    font-family: 'Poppins', sans-serif;
                    font-size: 16px;
                    font-style: normal;
                    color: black;
                }
                .button {
                    background-color: #0747A9;
                    color: white;
                    padding: 10px 20px;
                    text-align: center;
                    text-decoration: none;
                    display: inline-block;
                    border-radius: 5px;
                    font-style: normal;
                    text-decoration: none;
                }
                .line{
                    border-top: 1px solid lightgrey;
                }
            </style>
        </head>
        <body>
            <div class="mainbox">
            <img src="./static/images/logo.png" style="width: 50px;" alt="Logo">
            <p>Hello User,</p>
            <p>Welcome to CarryKar! Your verificatoin code is:</p>
            <h1>"""+str(otp)+"""</h1>
            <br>
            <div class="line"></div>
            <img src="./static/images/logo.png" style="margin-top: 30px; width: 30px;" alt="Logo">
            <p style="font-size: 13px;">Regards,<br>CarryKar Team</p>
            </div>
        </p>
    </html>
    """

    # Setup the MIME
    message = MIMEMultipart()
    message["From"] = sender_alias  # Set the 'From' to your custom domain email
    message["To"] = receiver_email
    message["Subject"] = subject

    # Attach the HTML body to the MIME message
    message.attach(MIMEText(html_body, "html"))

    # Gmail SMTP server configuration
    smtp_server = "smtp.gmail.com"
    smtp_port = 587  # TLS port

    try:
        # Get a connection from the pool
        mydb = get_db_connection()

        # Create a cursor from the connection
        mycursor = mydb.cursor(buffered=True)
        
        # Connect to Gmail's SMTP server
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # Secure the connection using TLS

        # Login to your Gmail account
        server.login(sender_email, sender_password)

        # Send the email
        server.sendmail(sender_alias, receiver_email, message.as_string())
        print("Email sent successfully!")
        return True
        # print(updatekyc)

    except Exception as e:
        print(f"Error: {e}")

    finally:
        # Ensure that the cursor and connection are closed
        close_connection(mydb, mycursor)


def add_vehicle(number, company, carnumber, carmodel):
    try:
        # Get a connection from the pool
        mydb = get_db_connection()

        # Create a cursor from the connection
        mycursor = mydb.cursor(buffered=True)
        
        check = fetch_vehicle(number)
        date = datetime.datetime.now()
        userid = fetch_userid(number)


        if len(check) > 0:
            trade = "update vehicles set carcompany = '"+str(company)+"', carnumber = '"+str(carnumber)+"', carmodel = '"+str(carmodel)+"' where userid = '"+str(userid[2])+"'"
            mycursor.execute(trade)
            mydb.commit()
            
            # Check if insertion was successful
            if mycursor.rowcount > 0:
                print("Data inserted successfully.")
                return True
            else:
                print("Data insertion failed.")
                return False

        else:
            trade = "INSERT INTO vehicles (carcompany, carnumber, carmodel, userid, datetime) values ('"+str(company)+"', '"+str(carnumber)+"', '"+str(carmodel)+"', '"+str(userid[2])+"', '"+str(date)+"')"
            mycursor.execute(trade)
            mydb.commit()
            
            # Check if insertion was successful
            if mycursor.rowcount > 0:
                print("Data inserted successfully.")
                return True
            else:
                print("Data insertion failed.")
                return False
        
    except Exception as e:
        print(e)
        return False
    
    finally:
        # Ensure that the cursor and connection are closed
        close_connection(mydb, mycursor)


def add_bank_account(number, bankname, accountnumber, ifscode, holdername):
    try:
        # Get a connection from the pool
        mydb = get_db_connection()

        # Create a cursor from the connection
        mycursor = mydb.cursor(buffered=True)
        
        check = fetch_bank_account(number)
        date = datetime.datetime.now()
        userid = fetch_userid(number)


        if len(check) > 0:
            trade = "update bank_accounts set bankname = '"+str(bankname)+"', accountnumber = '"+str(accountnumber)+"', ifscode = '"+str(ifscode)+"', holder_name = '"+str(holdername)+"' where userid = '"+str(userid[2])+"'"
            mycursor.execute(trade)
            mydb.commit()
            
            # Check if insertion was successful
            if mycursor.rowcount > 0:
                print("Data inserted successfully.")
                return True
            else:
                print("Data insertion failed.")
                return False

        else:
            trade = "INSERT INTO bank_accounts (bankname, accountnumber, ifscode, holder_name, userid, datetime) values ('"+str(bankname)+"', '"+str(accountnumber)+"', '"+str(ifscode)+"', '"+str(holdername)+"', '"+str(userid[2])+"', '"+str(date)+"')"
            mycursor.execute(trade)
            mydb.commit()
            
            # Check if insertion was successful
            if mycursor.rowcount > 0:
                print("Data inserted successfully.")
                return True
            else:
                print("Data insertion failed.")
                return False
        
    except Exception as e:
        print(e)
        return False
    
    finally:
        # Ensure that the cursor and connection are closed
        close_connection(mydb, mycursor)



def hostride(pickuplocation, pickupcoordinates, pickupcity, droplocation, dropcoordinates, dropcity, riderdate, starttime, endtime, passengers, price, weight_capacity, kgprice, ride_type, details, number):
    try:
        # Get a connection from the pool
        mydb = get_db_connection()

        # Create a cursor from the connection
        mycursor = mydb.cursor(buffered=True)
        
        date = datetime.datetime.now()
        date_string = str(date)
        date_format = '%Y-%m-%d %H:%M:%S.%f'  # Format of the input date string
        # Convert the string to a datetime object
        date_obj = datetime.datetime.strptime(date_string, date_format)
        epoch_time = int(date_obj.timestamp())

        userid = fetch_userid(number)
        name = str(userid[0]+" "+userid[1])
        print(name)
        # upiurl = f"upi://pay?pn={str(name)}&pa={str(upi)}&cu=INR&am={str(price[1:])}"
        print(userid[2])

        trade = "INSERT INTO hosted_rides (pickuplocation, pickupcoordinates, pickupcity, droplocation, dropcoordinates, dropcity, riderdate, starttime, endtime, passengers, passengerprice, kgcount, kgprice, ride_type, details, userid, uniqueid, datetime) values ('"+pickuplocation+"', '"+str(pickupcoordinates)+"', '"+str(pickupcity)+"', '"+droplocation+"', '"+str(dropcoordinates)+"', '"+str(dropcity)+"', '"+riderdate+"', '"+str(starttime)+"', '"+str(endtime)+"', '"+passengers+"', '"+price+"', '"+str(weight_capacity)+"', '"+str(kgprice)+"', '"+str(ride_type)+"', '"+str(details.replace("'", ""))+"', '"+str(userid[2])+"', '"+str(epoch_time)+"', '"+str(date)+"')"
        mycursor.execute(trade)
        mydb.commit()
        
        # Check if insertion was successful
        if mycursor.rowcount > 0:
            print("Data inserted successfully.")
            return True
        else:
            print("Data insertion failed.")
            return False

    except Exception as e:
        print(e)
        return False

    finally:
        # Ensure that the cursor and connection are closed
        close_connection(mydb, mycursor)


def find_host_user(userid):
    try:
        # Get a connection from the pool
        mydb = get_db_connection()

        # Create a cursor from the connection
        mycursor = mydb.cursor(buffered=True)
        
        query = 'SELECT * FROM signup where uniqueid="'+str(userid)+'"'
        mycursor.execute(query)
        myresult = mycursor.fetchone()

        if myresult == None:  
            return False
        else:
            return myresult

    except:
        return False
    
    finally:
        # Ensure that the cursor and connection are closed
        close_connection(mydb, mycursor)


def find_ride(pickuplocation, droplocation, date):
    try:
        # Get a connection from the pool
        mydb = get_db_connection()

        # Create a cursor from the connection
        mycursor = mydb.cursor(buffered=True)
        
        date_obj = datetime.datetime.strptime(date, "%Y-%m-%d")
        formatted_date = date_obj.strftime("%d %B %Y")
        print("formatted_date ", formatted_date)
        query = 'SELECT * FROM hosted_rides where pickupcity LIKE "'+str(pickuplocation)+'" and dropcity LIKE "'+str(droplocation)+'" and riderdate LIKE "'+str(formatted_date)+'"'
        mycursor.execute(query)
        myresult = mycursor.fetchall()

        print(query)

        print(myresult)

        if myresult == []:  
            return False
        else:
            return myresult

    except:
        return False

    finally:
        # Ensure that the cursor and connection are closed
        close_connection(mydb, mycursor)


def find_city(api_key, lat, lng):
    try:
        # Initialize Google Maps client
        gmaps = googlemaps.Client(key=api_key)
        
        # Perform reverse geocoding
        results = gmaps.reverse_geocode((lat, lng))
        
        # Parse the results to find the city name
        if results:
            for component in results[0]['address_components']:
                if 'locality' in component['types']:  # 'locality' represents the city
                    return component['long_name']
                elif 'administrative_area_level_1' in component['types']:
                    return component['long_name']  # Fallback to state/province if city is unavailable
        return "City not found for these coordinates."
    
    except Exception as e:
        return f"An error occurred: {e}"


def calculate_distance(api_key, origin, destination):
    print("api_key: ", api_key, " origin: ", origin, " destination: ", destination)
    # Initialize the Google Maps client
    gmaps = googlemaps.Client(key=api_key)
    
    # Convert coordinates to strings
    origin_str = f"{origin[0]},{origin[1]}"
    destination_str = f"{destination[0]},{destination[1]}"
    
    # Fetch distance matrix
    result = gmaps.distance_matrix(origins=origin_str, destinations=destination_str, mode="driving")
    
    if result['status'] == 'OK':
        elements = result['rows'][0]['elements'][0]
        if elements['status'] == 'OK':
            distance = elements['distance']['value']  # Distance in meters
            return distance
        else:
            raise Exception(f"Error in element status: {elements['status']}")
    else:
        raise Exception(f"Error in API request: {result['status']}")


def checkemail(email):
    try:
        # Get a connection from the pool
        mydb = get_db_connection()

        # Create a cursor from the connection
        mycursor = mydb.cursor(buffered=True)
        
        query = 'SELECT * FROM signup where emailid="'+str(email)+'"'
        print(query)
        mycursor.execute(query)
        myresult = mycursor.fetchone()
        print(myresult)
        
        if myresult == None:  
            return True
        else:
            return False

    except:
        return False

    finally:
        # Ensure that the cursor and connection are closed
        close_connection(mydb, mycursor)


def get_public_ip():
    try:
        # Get a connection from the pool
        mydb = get_db_connection()

        # Create a cursor from the connection
        mycursor = mydb.cursor(buffered=True)
        
        response = requests.get("https://api.ipify.org?format=json")
        response.raise_for_status()
        ip_address = response.json()["ip"]
        return ip_address
    
    except requests.RequestException as e:
        print(f"Error fetching IP address: {e}")
        return None
    
    finally:
        # Ensure that the cursor and connection are closed
        close_connection(mydb, mycursor)


def updatetoken(user_id, token, public_ip):
    try:
        # Get a connection from the pool
        mydb = get_db_connection()

        # Create a cursor from the connection
        mycursor = mydb.cursor(buffered=True)

        date = datetime.datetime.now()
        
        query = 'SELECT * FROM fcm_token where public_ip="'+str(public_ip)+'"'
        mycursor.execute(query)
        myresult = mycursor.fetchone()
        print("myresult: ", myresult)
        
        if myresult == None:  
            trade = "INSERT INTO fcm_token (user_id, token, public_ip, datetime) values ('"+str(user_id)+"', '"+str(token)+"', '"+str(public_ip)+"', '"+str(date)+"')"
            mycursor.execute(trade)
            mydb.commit()
            return "Token Inserted"
        
        else:
            trade = "UPDATE fcm_token SET user_id='"+str(user_id)+"', token='"+str(token)+"' WHERE public_ip='"+str(public_ip)+"'"
            mycursor.execute(trade)
            mydb.commit()
            return "Token Updated"

    except requests.RequestException as e:
        print("Error: ", e)
        return False

    finally:
        # Ensure that the cursor and connection are closed
        close_connection(mydb, mycursor)