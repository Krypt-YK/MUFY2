import streamlit as st
import json
import os
import pandas as pd
import numpy as np
from passlib.context import CryptContext  # Added for password hashing

# --- SECURITY: Initialize Password Hashing ---
# This is a critical security fix to avoid storing plain-text passwords.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- Class to handle NumPy types during JSON serialization ---
class SafeEncoder(json.JSONEncoder):
    """
    A JSON encoder that can handle NumPy integer and float types,
    which are not standard JSON serializable types.
    """
    def default(self, obj):
        if isinstance(obj, (np.integer, np.floating)):
            return obj.item()
        return super().default(obj)

# --- Constants ---
USERS_FILE = "users.json"
ORDERS_FILE = "orders.json"
RATINGS_FILE = "ratings.json"
ROLES = ["Customer", "Driver"]

# --- Helper functions to load/save data ---
def load_data(file):
    if os.path.exists(file):
        try:
            with open(file, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}  # Return empty dict if file is empty or corrupted
    return {}

def save_data(file, data):
    with open(file, "w") as f:
        # Use the SafeEncoder to prevent errors with NumPy types
        json.dump(data, f, indent=4, cls=SafeEncoder)

# --- Phone formatting helper ---
def format_phone_number(phone):
    digits = ''.join(filter(str.isdigit, phone))
    if len(digits) < 4:
        return phone
    return f"{digits[:3]}-{digits[3:]}"

# --- Load data from files ---
users = load_data(USERS_FILE)
orders = load_data(ORDERS_FILE)
ratings = load_data(RATINGS_FILE)

# Initialize ratings structure if it doesn't exist
if "restaurants" not in ratings:
    ratings["restaurants"] = {}
if "drivers" not in ratings:
    ratings["drivers"] = {}

# --- User Authentication Functions ---
def verify_password(plain_password, hashed_password):
    """Verifies a plain password against a hashed one."""
    return pwd_context.verify(plain_password, hashed_password)

def hash_password(password):
    """Hashes a password for storing."""
    return pwd_context.hash(password)

def login(username, password, role):
    """Handles user login."""
    if username in users and verify_password(password, users[username]["password"]):
        if users[username].get("role") == role:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.role = role
            st.success(f"Logged in as {username} ({role})")
            st.rerun() # Rerun to update the page view
        else:
            st.error(f"User '{username}' is not registered as a {role}.")
    else:
        st.error("Invalid username or password.")

def register(username, password, phone, role):
    """Handles new user registration."""
    if not username or not password or not phone:
        st.error("All fields are required.")
        return
    if username in users:
        st.error("Username already exists.")
        return
    
    # Hash the password before storing
    hashed_pwd = hash_password(password)
    users[username] = {"password": hashed_pwd, "phone": phone, "role": role}
    save_data(USERS_FILE, users)
    st.success("User registered successfully! Please log in.")

# --- Sidebar for Login/Registration ---
st.sidebar.title("User Authentication")

# Initialize session state variables
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""

if not st.session_state.logged_in:
    mode = st.sidebar.selectbox("Choose Mode", ["Login", "Register"])
    if mode == "Login":
        with st.sidebar.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            role_login = st.selectbox("Login as", ROLES)
            if st.form_submit_button("Login"):
                login(username, password, role_login)
    else: # Register
        with st.sidebar.form("register_form"):
            username = st.text_input("Choose Username")
            password = st.text_input("Choose Password", type="password")
            phone = st.text_input("Phone Number (digits only)")
            role_reg = st.selectbox("Register as", ROLES)
            if st.form_submit_button("Register"):
                register(username, password, phone, role_reg)
else:
    st.sidebar.write(f"Logged in as **{st.session_state.username}** ({st.session_state.role})")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.role = ""
        st.rerun()

# Stop app execution if user is not logged in
if not st.session_state.logged_in:
    st.info("Please log in or register using the sidebar to continue.")
    st.stop()

# --- Sample Restaurant Data ---
restaurants = {
    "Pizza Place": {
        "Pizza": {"Margherita": 12.0, "Pepperoni": 14.0, "Hawaiian": 13.5},
        "Sides": {"Garlic Bread": 5.0, "Wings": 7.0}
    },
    "Sushi Bar": {
        "Sushi Rolls": {"California Roll": 10.0, "Spicy Tuna": 11.5, "Dragon Roll": 12.5},
        "Drinks": {"Green Tea": 3.0, "Sake": 8.0}
    },
    "Yo Mama's Kitchen": {
        "Comfort Food": {"Fried Chicken": 15.0, "Mac and Cheese": 9.0, "Cornbread": 4.0},
        "Desserts": {"Peach Cobbler": 6.5, "Chocolate Cake": 7.0}
    },
    "Darren's Skibidi Restaurant": {
        "Meme Meals": {
            "Skibidi Burger": 13.0,
            "Toilet Tacos": 11.0,
            "Sigma Soda": 4.5
        },
        "Sides": {
            "French Fries": 5.0,
            "Onion Rings": 5.5
        }
    },
    "The Hungry Coder": {
        "Wraps": {
            "Chicken Shawarma": 10.0,
            "Beef Kebab": 12.0
        },
        "Energy Drinks": {
            "Red Bull": 6.0,
            "Monster": 6.5
        }
    }
}

# --- CUSTOMER PAGE ---
def customer_page():
    st.header("Place Your Order")

    # Initialize session state for customer flow
    if "step" not in st.session_state:
        st.session_state.step = 1
    if "cart" not in st.session_state:
        st.session_state.cart = []

    # Step 1: Ordering
    if st.session_state.step == 1:
        restaurant = st.selectbox("Choose Restaurant", list(restaurants.keys()))
        
        # Display average rating for the restaurant
        r_rating = ratings["restaurants"].get(restaurant)
        if r_rating and r_rating["rating_count"] > 0:
            avg_rating = r_rating["rating_sum"] / r_rating["rating_count"]
            st.write(f"⭐ Average Food Rating: {avg_rating:.2f} / 5")

        category = st.selectbox("Choose Category", list(restaurants[restaurant].keys()))
        food = st.selectbox("Choose Food Item", list(restaurants[restaurant][category].keys()))
        price = restaurants[restaurant][category][food]
        st.write(f"Price: RM {price:.2f}")

        if st.button("Add to Cart"):
            found = False
            for item in st.session_state.cart:
                if item["food"] == food and item["restaurant"] == restaurant:
                    item["quantity"] += 1
                    found = True
                    break
            if not found:
                st.session_state.cart.append({
                    "restaurant": restaurant, "category": category, "food": food,
                    "price": price, "quantity": 1
                })
            st.rerun()

        if st.session_state.cart:
            st.subheader("Your Cart")
            subtotal = 0.0
            # Use a copy of the list to allow safe removal while iterating
            for idx, item in enumerate(st.session_state.cart[:]):
                col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 2, 1])
                with col1:
                    st.write(f"{item['food']} from {item['restaurant']}")
                with col2:
                    if st.button("-", key=f"minus_{idx}"):
                        if item["quantity"] > 1:
                            item["quantity"] -= 1
                            st.rerun()
                with col3:
                    st.write(f"x{item['quantity']}")
                with col4:
                    if st.button("+", key=f"plus_{idx}"):
                        item["quantity"] += 1
                        st.rerun()
                with col5:
                    if st.button("Remove", key=f"remove_{idx}"):
                        st.session_state.cart.pop(idx)
                        st.rerun()
                
                subtotal += item['price'] * item['quantity']

            service_tax = subtotal * 0.10
            delivery_charge = subtotal * 0.06
            total = subtotal + service_tax + delivery_charge

            st.markdown(f"<div style='text-align:right'><strong>Subtotal:</strong> RM {subtotal:.2f}</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='text-align:right'><strong>Service Tax (10%):</strong> RM {service_tax:.2f}</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='text-align:right'><strong>Delivery Charge (6%):</strong> RM {delivery_charge:.2f}</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='text-align:right'><strong>Total:</strong> RM {total:.2f}</div>", unsafe_allow_html=True)

            if st.button("Proceed to Checkout"):
                st.session_state.total = total
                st.session_state.step = 2
                st.rerun()

    # Step 2: Checkout
    elif st.session_state.step == 2:
        st.subheader("Checkout")
        with st.form("checkout_form"):
            dropoff = st.text_input("Enter Dropoff Location")
            map_location = st.text_input("Optional: Type location for map display (e.g., Kuala Lumpur)")
            payment = st.selectbox("Payment Method", ["Cash"])
            tip = st.number_input("Tip for the Driver (RM)", min_value=0.0, value=2.0, step=0.5)
            
            if st.form_submit_button("Place Order"):
                if not dropoff:
                    st.error("Please enter a dropoff location.")
                else:
                    user_phone = users[st.session_state.username]["phone"]
                    # FIX: Generate a robust new order ID
                    # Find the highest existing ID and add 1. Handles empty dicts and ensures uniqueness.
                    last_id = max([int(k) for k in orders.keys()] or [0])
                    
                    for item in st.session_state.cart:
                        last_id += 1
                        order_id = str(last_id)
                        orders[order_id] = {
                            "customer": st.session_state.username, "phone": user_phone,
                            "restaurant": item["restaurant"], "category": item["category"],
                            "food": item["food"], "price": item["price"],
                            "quantity": item["quantity"], "dropoff": dropoff,
                            "payment": payment, "tip": float(tip), "status": "pending",
                            "driver": None, "rating_food": None, "rating_speed": None,
                            "rating_service": None
                        }
                    
                    save_data(ORDERS_FILE, orders)
                    st.success("Order placed successfully!")
                    st.session_state.step = 1
                    st.session_state.cart = []
                    st.rerun()
        if st.button("Back to Menu"):
            st.session_state.step = 1
            st.rerun()

    # --- Display User Orders and Rating Section ---
    st.subheader("Your Orders & Ratings")
    user_orders = {oid: o for oid, o in orders.items() if o["customer"] == st.session_state.username}

    if not user_orders:
        st.write("You have not placed any orders yet.")
    else:
        # BUG FIX: This section was heavily bugged with duplicate code and incorrect loops.
        # It's now corrected into a single, logical block.
        for oid, o in sorted(user_orders.items(), key=lambda item: item[0], reverse=True):
            with st.expander(f"Order #{oid} - {o['food']} ({o['status']})"):
                st.markdown(f"**Restaurant:** {o['restaurant']}")
                st.markdown(f"**Quantity:** {o['quantity']}")
                st.markdown(f"**Total Paid:** RM {(o['price']*o['quantity']):.2f} (excluding fees/tip)")
                st.markdown(f"**Driver:** {o.get('driver', 'Not assigned')}")
                st.markdown(f"**Status:** {o['status']}")

                # Show rating form ONLY if the order is complete and has not been rated yet.
                if o["status"] == "completed" and o.get("rating_food") is None:
                    st.markdown("---")
                    st.markdown("#### Rate this order:")
                    with st.form(key=f"rating_form_{oid}"):
                        rating_food = st.slider("Food Quality", 1, 5, 3, key=f"food_{oid}")
                        rating_speed = st.slider("Delivery Speed", 1, 5, 3, key=f"speed_{oid}")
                        rating_service = st.slider("Driver Service", 1, 5, 3, key=f"service_{oid}")

                        if st.form_submit_button("Submit Rating"):
                            # Save ratings
                            orders[oid]["rating_food"] = rating_food
                            orders[oid]["rating_speed"] = rating_speed
                            orders[oid]["rating_service"] = rating_service

                            # Update restaurant rating summary
                            r = ratings["restaurants"].setdefault(o["restaurant"], {"rating_sum": 0, "rating_count": 0})
                            r["rating_sum"] += rating_food
                            r["rating_count"] += 1

                            # Update driver rating summary
                            if o["driver"]:
                                d = ratings["drivers"].setdefault(o["driver"], {
                                    "rating_sum": 0, "rating_count": 0,
                                    "speed_sum": 0, "service_sum": 0
                                })
                                d["rating_sum"] += rating_food
                                d["speed_sum"] += rating_speed
                                d["service_sum"] += rating_service
                                d["rating_count"] += 1

                            save_data(RATINGS_FILE, ratings)
                            save_data(ORDERS_FILE, orders)
                            st.success("Thank you for your feedback!")
                            st.rerun()
                # Show existing rating if it exists
                elif o.get("rating_food") is not None:
                    st.markdown("---")
                    st.markdown("Your rating:")
                    st.markdown(f"**Food:** {'⭐'*o['rating_food']} | **Speed:** {'⭐'*o['rating_speed']} | **Service:** {'⭐'*o['rating_service']}")


# --- DRIVER PAGE ---
def driver_page():
    st.header("Driver Dashboard")

    # Show driver's average rating summary
    d_rating = ratings["drivers"].get(st.session_state.username)
    if d_rating and d_rating["rating_count"] > 0:
        avg_food = d_rating["rating_sum"] / d_rating["rating_count"]
        avg_speed = d_rating["speed_sum"] / d_rating["rating_count"]
        avg_service = d_rating["service_sum"] / d_rating["rating_count"]
        st.write(f"Your Average Ratings: Food: {avg_food:.2f} ⭐ | Speed: {avg_speed:.2f} ⭐ | Service: {avg_service:.2f} ⭐")

    # Section for driver's currently active orders
    st.subheader("Your Claimed Orders")
    driver_orders = {oid: o for oid, o in orders.items() if o.get("driver") == st.session_state.username and o["status"] == "claimed"}
    
    if not driver_orders:
        st.write("You have no active orders.")
    else:
        for oid, o in driver_orders.items():
            st.markdown(f"**Order ID {oid}:** {o['quantity']}x {o['food']} for {o['customer']}")
            st.markdown(f"**Dropoff:** {o['dropoff']} | **Customer Phone:** {format_phone_number(o['phone'])}")
            if st.button(f"Mark Order {oid} as Completed", key=f"deliver_{oid}"):
                orders[oid]["status"] = "completed"
                save_data(ORDERS_FILE, orders)
                st.success(f"Order {oid} marked as completed!")
                st.rerun()
    
    st.markdown("---")

    # Section for available orders
    st.header("Available Orders to Claim")
    pending_orders = {oid: o for oid, o in orders.items() if o["status"] == "pending"}

    if not pending_orders:
        st.write("No available orders at the moment.")
    else:
        for oid, order in pending_orders.items():
            with st.container():
                st.markdown(f"**Order ID {oid}:** {order['quantity']}x {order['food']} from {order['restaurant']}")
                st.markdown(f"**Dropoff:** {order['dropoff']} | **Payment:** {order['payment']} | **Tip:** RM {order['tip']:.2f}")
                if st.button(f"Claim Order {oid}", key=f"claim_{oid}"):
                    orders[oid]["driver"] = st.session_state.username
                    orders[oid]["status"] = "claimed"
                    save_data(ORDERS_FILE, orders)
                    st.success(f"Order {oid} claimed! It has been moved to 'Your Claimed Orders'.")
                    st.rerun()
                st.markdown("---")

# --- Main app logic ---
if __name__ == "__main__":
    if st.session_state.role == "Customer":
        customer_page()
    elif st.session_state.role == "Driver":
        driver_page()