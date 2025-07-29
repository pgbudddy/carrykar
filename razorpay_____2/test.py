from flask import Flask, render_template, request, jsonify
import razorpay

app = Flask(__name__)

# Initialize Razorpay client with API keys
razorpay_client = razorpay.Client(auth=("rzp_test_7TJCqucHMY4JS2", "489v1D9RIMDuqzWH8JmeWMZr"))

@app.route('/book_ride_popup')
def book_ride_popup():
    return render_template('book_ride_popup.html')


@app.route('/create_order', methods=['POST'])
def create_order():
    order_data = {
        "amount": 10000,  # Amount in paise
        "currency": "INR",
        "payment_capture": 1
    }
    order = razorpay_client.order.create(data=order_data)
    return jsonify({"order_id": order['id']})


@app.route('/capture_payment', methods=['POST'])
def capture_payment():
    payment_id = request.json.get('payment_id')
    order_id = request.json.get('order_id')
    amount = request.json.get('amount')

    print("payment_id ", payment_id)
    print("amount ", amount)
    print("order_id ", order_id)

    # Capture the payment
    payment = razorpay_client.payment.fetch(payment_id)

    print("payment ", payment)

    if payment['status'] == 'captured':
        return jsonify({"message": "Payment successful!"})
    else:
        return jsonify({"message": "Payment failed or pending."}), 400

if __name__ == '__main__':
    app.run(debug=True)
