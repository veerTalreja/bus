"""Smart Bus Ticket Booking & Reservation System - single-file Streamlit app.

Run with:  python -m streamlit run streamlit_app.py

Part 1 holds the business rules (PRD BR-01 to BR-15) in plain Python.
Part 2 is the Streamlit interface. Only Streamlit is used: no HTML, no CSS.
Data lives in st.session_state (in memory only; lost when the session ends).
"""

import streamlit as st

# =====================================================================
# PART 1 - BUSINESS LOGIC
# =====================================================================

# Tuple of supported cities (PRD Feature 2)
CITIES = ("Karachi", "Hyderabad", "Sukkur", "Mirpur Khas", "Lahore")

CONFIRMED = "Confirmed"
CANCELLED = "Cancelled"


def create_initial_state():
    """Return a fresh in-memory state with the five starter routes."""
    routes = [
        {"route_id": "R101", "departure_city": "Karachi", "destination_city": "Hyderabad",
         "departure_time": "08:00 AM", "ticket_price": 1200, "total_seats": 40, "available_seats": 40},
        {"route_id": "R102", "departure_city": "Karachi", "destination_city": "Sukkur",
         "departure_time": "09:30 AM", "ticket_price": 2000, "total_seats": 36, "available_seats": 36},
        {"route_id": "R103", "departure_city": "Hyderabad", "destination_city": "Mirpur Khas",
         "departure_time": "11:00 AM", "ticket_price": 800, "total_seats": 32, "available_seats": 32},
        {"route_id": "R104", "departure_city": "Karachi", "destination_city": "Lahore",
         "departure_time": "07:00 PM", "ticket_price": 5000, "total_seats": 45, "available_seats": 45},
        {"route_id": "R105", "departure_city": "Sukkur", "destination_city": "Hyderabad",
         "departure_time": "02:00 PM", "ticket_price": 1500, "total_seats": 30, "available_seats": 30},
    ]
    return {
        "routes": routes,
        "bookings": [],
        "issued_ids": set(),   # set of booking IDs already issued (BR-06)
        "next_number": 1001,
    }


# ---------------------------------------------------------------- helpers

def seat_status(route):
    """Available / Partially Booked / Fully Booked (Feature 8)."""
    if route["available_seats"] == 0:
        return "Fully Booked"
    if route["available_seats"] == route["total_seats"]:
        return "Available"
    return "Partially Booked"


def find_route(state, route_id):
    """Return the route dict for route_id (case-insensitive) or None."""
    wanted = str(route_id).strip().upper()
    for route in state["routes"]:
        if route["route_id"] == wanted:
            return route
    return None


def find_booking(state, booking_id):
    """Return the booking dict for booking_id (case-insensitive) or None."""
    wanted = str(booking_id).strip().upper()
    for booking in state["bookings"]:
        if booking["booking_id"] == wanted:
            return booking
    return None


def parse_positive_int(value):
    """Return int(value) if it is a positive whole number, else None (BR-02, BR-04)."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        number = value
    else:
        text = str(value).strip()
        try:
            number = int(text)
        except ValueError:
            return None
    return number if number > 0 else None


def generate_booking_id(state):
    """Issue a booking ID that is not already in the issued set (BR-06)."""
    while True:
        candidate = "B" + str(state["next_number"])
        state["next_number"] += 1
        if candidate not in state["issued_ids"]:
            state["issued_ids"].add(candidate)
            return candidate


# ---------------------------------------------------------------- routes

def list_routes(state, available_only=False):
    """Numbered route rows. Uses enumerate(); `continue` skips full routes on filter."""
    rows = []
    for number, route in enumerate(state["routes"], start=1):
        if available_only and route["available_seats"] == 0:
            continue
        rows.append({
            "No.": number,
            "Route": route["route_id"],
            "Journey": f'{route["departure_city"]} -> {route["destination_city"]}',
            "Depart": route["departure_time"],
            "Fare (Rs.)": route["ticket_price"],
            "Seats": f'{route["available_seats"]}/{route["total_seats"]}',
            "Status": seat_status(route),
        })
    return rows


def search_routes(state, term):
    """Search by route ID, departure city or destination city.

    Returns (matches, message). A unique route ID match stops with `break`;
    for-else produces the no-match result when no break happened.
    """
    term = str(term).strip().lower()
    if not term:
        return [], "Enter a route ID or a city name to search."

    matches = []
    for route in state["routes"]:
        if route["route_id"].lower() == term:
            matches = [route]          # route IDs are unique, so stop here
            break
        if term in (route["departure_city"].lower(), route["destination_city"].lower()):
            matches.append(route)
    else:
        if not matches:
            return [], f'No routes match "{term}".'
    return matches, ""


# ---------------------------------------------------------------- booking

def book_ticket(state, name, age, route_id, seats):
    """Validate everything first; change state only if every check passes.

    Returns (ok, message, booking_or_None).
    """
    # BR-01 name
    clean_name = str(name).strip()
    if not clean_name:
        return False, "Passenger name cannot be empty.", None

    # BR-02 age
    age_value = parse_positive_int(age)
    if age_value is None:
        return False, "Age must be a positive whole number.", None

    # BR-03 route exists
    route = find_route(state, route_id)
    if route is None:
        return False, f'Route "{str(route_id).strip()}" does not exist.', None

    # BR-04 seat quantity
    seat_count = parse_positive_int(seats)
    if seat_count is None:
        return False, "Number of seats must be a positive whole number.", None

    # BR-05 availability
    if seat_count > route["available_seats"]:
        return (False,
                f'Only {route["available_seats"]} seat(s) left on {route["route_id"]}; '
                f"you asked for {seat_count}.",
                None)

    # All checks passed: create ID, calculate fare (BR-07), store, then decrement (BR-08).
    booking = {
        "booking_id": generate_booking_id(state),
        "passenger_name": clean_name,
        "passenger_age": age_value,
        "route_id": route["route_id"],
        "seats": seat_count,
        "total_fare": route["ticket_price"] * seat_count,
        "status": CONFIRMED,
    }
    state["bookings"].append(booking)
    route["available_seats"] -= seat_count
    return True, "Booking confirmed!", booking


def list_bookings(state):
    """Numbered booking rows including cancelled records (BR-11)."""
    rows = []
    for number, booking in enumerate(state["bookings"], start=1):
        route = find_route(state, booking["route_id"])
        journey = f'{route["departure_city"]} -> {route["destination_city"]}' if route else "-"
        rows.append({
            "No.": number,
            "Booking ID": booking["booking_id"],
            "Passenger": booking["passenger_name"],
            "Age": booking["passenger_age"],
            "Route": f'{booking["route_id"]} ({journey})',
            "Seats": booking["seats"],
            "Total fare (Rs.)": booking["total_fare"],
            "Status": booking["status"],
        })
    return rows


# ---------------------------------------------------------------- cancellation

def cancel_booking(state, booking_id):
    """Cancel a Confirmed booking and restore its seats exactly once.

    Returns (ok, message, details_or_None).
    """
    booking = find_booking(state, booking_id)
    if booking is None:
        return False, f'Booking "{str(booking_id).strip()}" was not found.', None

    if booking["status"] != CONFIRMED:                       # BR-09, BR-10
        return False, f'Booking {booking["booking_id"]} is already cancelled. No seats were changed.', None

    route = find_route(state, booking["route_id"])
    # Status change and seat restore happen together as one logical step.
    booking["status"] = CANCELLED
    route["available_seats"] = min(route["total_seats"],     # BR-13 safety cap
                                   route["available_seats"] + booking["seats"])
    details = {
        "booking_id": booking["booking_id"],
        "seats_restored": booking["seats"],
        "route_id": route["route_id"],
        "route_available": route["available_seats"],
    }
    return True, f'Booking {booking["booking_id"]} has been cancelled.', details


# ---------------------------------------------------------------- availability

def availability_rows(state, available_only=False):
    """Seat availability per route; optional filter for routes with seats left."""
    rows = []
    for route in state["routes"]:
        if available_only and route["available_seats"] == 0:
            continue
        rows.append({
            "Route": route["route_id"],
            "Journey": f'{route["departure_city"]} -> {route["destination_city"]}',
            "Available": route["available_seats"],
            "Capacity": route["total_seats"],
            "Status": seat_status(route),
        })
    return rows


# ---------------------------------------------------------------- report

def generate_report(state):
    """Totals for Feature 9. Confirmed records only count towards seats and revenue."""
    total = len(state["bookings"])
    confirmed_count = 0
    cancelled_count = 0
    for booking in state["bookings"]:
        if booking["status"] == CONFIRMED:
            confirmed_count += 1
        elif booking["status"] == CANCELLED:
            cancelled_count += 1

    reserved_seats = 0
    revenue = 0
    fully_booked = 0
    per_route = []
    # Nested loops: outer visits routes, inner checks matching confirmed bookings.
    for route in state["routes"]:
        route_seats = 0
        route_revenue = 0
        for booking in state["bookings"]:
            if booking["route_id"] == route["route_id"] and booking["status"] == CONFIRMED:
                route_seats += booking["seats"]
                route_revenue += booking["total_fare"]
        reserved_seats += route_seats
        revenue += route_revenue
        if route["available_seats"] == 0:
            fully_booked += 1
        per_route.append({
            "Route": route["route_id"],
            "Journey": f'{route["departure_city"]} -> {route["destination_city"]}',
            "Confirmed seats": route_seats,
            "Confirmed revenue (Rs.)": route_revenue,
        })

    return {
        "total_bookings": total,
        "confirmed": confirmed_count,
        "cancelled": cancelled_count,
        "reserved_seats": reserved_seats,
        "revenue": revenue,
        "fully_booked_routes": fully_booked,
        "per_route": per_route,
    }


# ---------------------------------------------------------------- schedule

def schedule_by_city(state):
    """{city: [route, ...]} using an outer loop over cities and inner loop over routes."""
    schedule = {}
    for city in CITIES:
        departures = []
        for route in state["routes"]:
            if route["departure_city"] == city:
                departures.append(route)
        schedule[city] = departures
    return schedule


# ---------------------------------------------------------------- consistency check

def state_is_consistent(state):
    """True when seats, bookings and revenue reconcile (used by tests)."""
    for route in state["routes"]:
        if not 0 <= route["available_seats"] <= route["total_seats"]:
            return False
        booked = sum(b["seats"] for b in state["bookings"]
                     if b["route_id"] == route["route_id"] and b["status"] == CONFIRMED)
        if route["total_seats"] - route["available_seats"] != booked:
            return False
    return True


# =====================================================================
# PART 2 - STREAMLIT INTERFACE
# =====================================================================

st.set_page_config(page_title="Smart Bus Reservations", page_icon="🚌", layout="wide")

# ------------------------------------------------------------------ state

if "bus_state" not in st.session_state:
    st.session_state.bus_state = create_initial_state()
if "last_ticket" not in st.session_state:
    st.session_state.last_ticket = None

state = st.session_state.bus_state


def show_table(rows):
    """Show a list of dicts as a table made of Streamlit columns."""
    if not rows:
        return
    columns = list(rows[0].keys())
    header = st.columns(len(columns))
    for box, name in zip(header, columns):
        box.markdown("**" + name + "**")
    st.divider()
    for row in rows:
        cells = st.columns(len(columns))
        for box, name in zip(cells, columns):
            box.text(str(row[name]))


def money(amount):
    return f"Rs. {amount:,}"


def render_ticket(booking):
    route = find_route(state, booking["route_id"])
    with st.container(border=True):
        st.subheader("Booking confirmed")
        left, right = st.columns(2)
        left.metric("Booking ID", booking["booking_id"])
        right.metric("Total fare", money(booking["total_fare"]))
        st.text(f'Passenger: {booking["passenger_name"]}')
        st.text(f'Route: {route["route_id"]} ({route["departure_city"]} -> {route["destination_city"]})')
        st.text(f'Departs: {route["departure_time"]}')
        st.text(f'Seats booked: {booking["seats"]}')
        st.text(f'Fare per seat: {money(route["ticket_price"])}')
        st.text(f'Status: {booking["status"]}')


# ------------------------------------------------------------------ pages

def page_routes():
    st.header("Available routes")
    only_open = st.checkbox("Hide fully booked routes", value=False)
    rows = list_routes(state, available_only=only_open)
    if rows:
        show_table(rows)
    else:
        st.info("Every route is fully booked right now.")


def page_search():
    st.header("Search for a route")
    term = st.text_input("Route ID or city", placeholder="R101, Hyderabad, lahore ...")
    if not term:
        st.caption("City search is not case-sensitive and matches departure or destination.")
        return
    matches, message = search_routes(state, term)
    if not matches:
        st.warning(message)
        return
    st.write(f"{len(matches)} match(es)")
    rows = []
    for route in matches:
        rows.append({
            "Route": route["route_id"],
            "Journey": f'{route["departure_city"]} -> {route["destination_city"]}',
            "Depart": route["departure_time"],
            "Fare (Rs.)": route["ticket_price"],
            "Seats available": route["available_seats"],
        })
    show_table(rows)


def page_book():
    st.header("Book a ticket")

    def route_label(route_id):
        route = find_route(state, route_id)
        return (f'{route["route_id"]}: {route["departure_city"]} -> {route["destination_city"]}, '
                f'{route["departure_time"]}, Rs. {route["ticket_price"]:,}, '
                f'{route["available_seats"]} seats left')

    with st.form("booking_form"):
        name = st.text_input("Passenger name")
        age = st.number_input("Passenger age", min_value=0, max_value=120, value=0, step=1)
        route_id = st.selectbox("Route", [r["route_id"] for r in state["routes"]],
                                format_func=route_label)
        seats = st.number_input("Number of seats", min_value=0, max_value=100, value=1, step=1)
        submitted = st.form_submit_button("Book ticket", type="primary")

    if submitted:
        ok, message, booking = book_ticket(state, name, age, route_id, seats)
        if ok:
            st.session_state.last_ticket = booking["booking_id"]
            st.rerun()  # refresh so seat counts in the route list are current
        else:
            st.session_state.last_ticket = None
            st.error(message)

    if st.session_state.last_ticket:
        booking = find_booking(state, st.session_state.last_ticket)
        if booking:
            render_ticket(booking)


def page_bookings():
    st.header("My bookings")
    rows = list_bookings(state)
    if not rows:
        st.info("No bookings found.")
        return
    show_table(rows)
    st.caption("Cancelled bookings stay in this list so the history is complete.")


def page_cancel():
    st.header("Cancel a booking")
    confirmed_ids = [b["booking_id"] for b in state["bookings"] if b["status"] == CONFIRMED]
    if confirmed_ids:
        st.caption("Confirmed bookings: " + ", ".join(confirmed_ids))
    else:
        st.caption("There are no confirmed bookings to cancel.")

    with st.form("cancel_form"):
        booking_id = st.text_input("Booking ID", placeholder="B1001")
        submitted = st.form_submit_button("Cancel booking", type="primary")

    if submitted:
        ok, message, details = cancel_booking(state, booking_id)
        if ok:
            st.success(message)
            st.write(f'Seats restored: {details["seats_restored"]}')
            st.write(f'Route {details["route_id"]} available seats: {details["route_available"]}')
        else:
            st.error(message)


def page_availability():
    st.header("Seat availability")
    only_open = st.checkbox("Only routes with seats left", value=False)
    rows = availability_rows(state, available_only=only_open)
    if not rows:
        st.info("No routes have seats left.")
        return
    for row in rows:
        left, middle, right = st.columns([2, 3, 1])
        left.text(row["Route"] + "  " + row["Journey"])
        middle.progress(row["Available"] / row["Capacity"] if row["Capacity"] else 0.0)
        right.text(f'{row["Available"]}/{row["Capacity"]}  {row["Status"]}')


def page_report():
    st.header("Booking report")
    report = generate_report(state)

    first = st.columns(3)
    first[0].metric("Total bookings created", report["total_bookings"])
    first[1].metric("Confirmed bookings", report["confirmed"])
    first[2].metric("Cancelled bookings", report["cancelled"])

    second = st.columns(3)
    second[0].metric("Seats currently reserved", report["reserved_seats"])
    second[1].metric("Confirmed revenue", money(report["revenue"]))
    second[2].metric("Fully booked routes", report["fully_booked_routes"])

    st.subheader("Confirmed bookings by route")
    show_table(report["per_route"])
    st.caption("Cancelled bookings are counted in totals but excluded from seats and revenue.")


def page_schedule():
    st.header("Route schedule by departure city")
    schedule = schedule_by_city(state)
    for city, departures in schedule.items():
        st.subheader(city)
        if not departures:
            st.caption("No scheduled departures.")
            continue
        for route in departures:
            st.text(f'{route["route_id"]} -> {route["destination_city"]} | {route["departure_time"]}')


PAGES = {
    "View Available Routes": page_routes,
    "Search for a Route": page_search,
    "Book a Ticket": page_book,
    "View My Bookings": page_bookings,
    "Cancel a Booking": page_cancel,
    "View Seat Availability": page_availability,
    "Generate Booking Report": page_report,
    "Route Schedule": page_schedule,
}

# ------------------------------------------------------------------ layout

with st.sidebar:
    st.title("Smart Bus")
    st.caption("Ticket booking and reservations")
    choice = st.radio("Menu", list(PAGES.keys()), label_visibility="collapsed")
    st.divider()
    st.caption("Data is kept in memory for this browser session only. "
               "It is lost when the session ends.")
    if st.button("Reset all data"):
        st.session_state.bus_state = create_initial_state()
        st.session_state.last_ticket = None
        st.rerun()

if choice != "Book a Ticket":
    st.session_state.last_ticket = None  # clear the confirmation when leaving the page

PAGES[choice]()
