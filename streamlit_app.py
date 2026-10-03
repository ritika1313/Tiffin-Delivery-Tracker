"""
Tiffin Delivery Tracker - Streamlit Frontend
Talks to the existing FastAPI backend using only: /health, /orders/, /stats/daily
Run:  streamlit run streamlit_app.py
"""

import html
from datetime import date, datetime

import requests
import streamlit as st

# --------------------------------------------------------------------------
# CONFIGURATION (the only place the API URL is defined)
# --------------------------------------------------------------------------
API_URL = "http://127.0.0.1:8000"
REQUEST_TIMEOUT = 5  # seconds

# Backend status value -> (user-friendly label, emoji, text color, background color)
STATUS_INFO = {
    "preparing": ("Preparing", "🟠", "#B45309", "#FEF3C7"),
    "picked_up": ("Picked Up", "🔵", "#1D4ED8", "#DBEAFE"),
    "in_transit": ("In Transit", "🟣", "#6D28D9", "#EDE9FE"),
    "delivered": ("Delivered", "🟢", "#047857", "#D1FAE5"),
}
LABEL_TO_STATUS = {info[0]: key for key, info in STATUS_INFO.items()}

st.set_page_config(
    page_title="Tiffin Delivery Tracker",
    page_icon="🥘",
    layout="wide",
)

# --------------------------------------------------------------------------
# CUSTOM CSS (used only where it improves the look)
# --------------------------------------------------------------------------
CUSTOM_CSS = """
<style>
    #MainMenu, footer {visibility: hidden;}
    .block-container {padding-top: 1.5rem; padding-bottom: 2rem; max-width: 1200px;}

    .app-header {
        background: linear-gradient(135deg, #FF6B35 0%, #F7931E 100%);
        border-radius: 16px; padding: 1.4rem 1.8rem; color: white;
        display: flex; justify-content: space-between; align-items: center;
        flex-wrap: wrap; gap: 1rem; margin-bottom: 1.5rem;
        box-shadow: 0 6px 18px rgba(255, 107, 53, 0.25);
    }
    .app-header h1 {margin: 0; font-size: 2rem; color: white; padding: 0;}
    .app-header p {margin: 0.2rem 0 0 0; opacity: 0.95; font-size: 1rem;}
    .conn-badge {
        background: rgba(255,255,255,0.95); border-radius: 999px;
        padding: 0.4rem 1rem; font-weight: 600; font-size: 0.9rem;
    }

    .metric-card {
        background: white; border-radius: 14px; padding: 1.1rem 1.2rem;
        border: 1px solid #F1F1F1; border-top: 5px solid var(--accent);
        box-shadow: 0 2px 10px rgba(0,0,0,0.06);
    }
    .metric-label {color: #6B7280; font-size: 0.85rem; font-weight: 600;}
    .metric-value {color: #111827; font-size: 2.1rem; font-weight: 700; line-height: 1.2;}

    .badge {
        display: inline-block; padding: 0.2rem 0.8rem; border-radius: 999px;
        font-size: 0.85rem; font-weight: 600;
    }
    .detail-card {
        background: white; border: 1px solid #F1F1F1; border-radius: 14px;
        padding: 1.2rem 1.4rem; box-shadow: 0 2px 10px rgba(0,0,0,0.06);
    }
    .detail-label {color: #6B7280; font-size: 0.78rem; font-weight: 600; text-transform: uppercase;}
    .detail-value {color: #111827; font-size: 1.05rem; margin-bottom: 0.9rem;}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# --------------------------------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------------------------------
def extract_error_message(response):
    """Pull a readable message out of a FastAPI error response."""
    try:
        detail = response.json().get("detail")
    except (ValueError, AttributeError):
        return response.reason or "Unknown error"

    # FastAPI validation errors (422) come as a list of dicts
    if isinstance(detail, list):
        parts = []
        for err in detail:
            field = err.get("loc", ["?"])[-1]
            parts.append(f"{field}: {err.get('msg', 'invalid value')}")
        return "; ".join(parts)
    return str(detail) if detail else (response.reason or "Unknown error")


def api_request(method, path, **kwargs):
    """
    Single place where every HTTP call is made.
    Returns (data, error_message). Exactly one of them is None.
    """
    url = f"{API_URL}{path}"
    try:
        response = requests.request(method, url, timeout=REQUEST_TIMEOUT, **kwargs)
    except requests.exceptions.ConnectionError:
        return None, ("Cannot connect to the FastAPI server. "
                      "Start it with: uvicorn main:app --reload")
    except requests.exceptions.Timeout:
        return None, "The server took too long to respond. Please try again."
    except requests.exceptions.RequestException:
        return None, "Something went wrong while contacting the server."

    if 400 <= response.status_code < 500:
        return None, f"Request error ({response.status_code}): {extract_error_message(response)}"
    if response.status_code >= 500:
        return None, f"Server error ({response.status_code}). Please check the backend logs."

    try:
        return response.json(), None
    except ValueError:
        return None, "The server returned an invalid (non-JSON) response."


def format_datetime(value):
    """Turn an ISO timestamp into a friendly format; fall back to the raw value."""
    if not value:
        return "—"
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).strftime("%d %b %Y, %I:%M %p")
    except ValueError:
        return str(value)


def status_label(status):
    """Plain text label with emoji, used inside tables."""
    info = STATUS_INFO.get(status)
    return f"{info[1]} {info[0]}" if info else str(status)


def status_badge(status):
    """Colored HTML badge for a status."""
    info = STATUS_INFO.get(status)
    if not info:
        return f'<span class="badge" style="background:#E5E7EB;color:#374151;">{html.escape(str(status))}</span>'
    label, _, color, bg = info
    return f'<span class="badge" style="background:{bg};color:{color};">{label}</span>'


# --------------------------------------------------------------------------
# API FUNCTIONS (one per backend endpoint)
# --------------------------------------------------------------------------
def get_health():
    """GET /health -> (is_online, error_message)"""
    _, error = api_request("GET", "/health")
    return error is None, error


def get_daily_summary(summary_date):
    """GET /stats/daily?summary_date=YYYY-MM-DD"""
    data, error = api_request("GET", "/stats/daily", params={"summary_date": summary_date.isoformat()})
    if error:
        return None, error
    if not isinstance(data, dict) or "total_orders" not in data or "by_status" not in data:
        return None, "The statistics response had an unexpected format."
    return data, None


def create_order(customer_name, delivery_address, items):
    """POST /orders/"""
    payload = {
        "customer_name": customer_name,
        "delivery_address": delivery_address,
        "items": items,
    }
    return api_request("POST", "/orders/", json=payload)


def get_orders(status=None, created_date=None, skip=0, limit=10):
    """GET /orders/ with optional filters and pagination."""
    params = {"skip": skip, "limit": limit}
    if status:
        params["status"] = status
    if created_date:
        params["created_date"] = created_date.isoformat()

    data, error = api_request("GET", "/orders/", params=params)
    if error:
        return None, error
    if not isinstance(data, list):
        return None, "The orders response had an unexpected format."
    return data, None


# --------------------------------------------------------------------------
# UI SECTIONS
# --------------------------------------------------------------------------
def render_header(is_online):
    """Top banner with title, subtitle and live connection status."""
    badge_text = "🟢 API Connected" if is_online else "🔴 API Offline"
    st.markdown(
        f"""
        <div class="app-header">
            <div>
                <h1>🥘 Tiffin Delivery Tracker</h1>
                <p>Track, manage and monitor daily tiffin deliveries.</p>
            </div>
            <div class="conn-badge" style="color:{'#047857' if is_online else '#B91C1C'};">{badge_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar(is_online):
    """Sidebar: navigation, order filters (only on Orders page) and API status."""
    with st.sidebar:
        st.markdown("## 🥘 Tiffin Tracker")
        page = st.radio(
            "Navigation",
            ["📊 Dashboard", "➕ Create Order", "📋 Orders"],
            label_visibility="collapsed",
        )

        filters = None
        if page == "📋 Orders":
            st.divider()
            st.markdown("### 🔎 Filters")
            status_choice = st.selectbox("Status", ["All"] + list(LABEL_TO_STATUS.keys()))
            use_date = st.checkbox("Filter by created date")
            chosen_date = st.date_input("Created date", value=date.today(), disabled=not use_date)
            limit = st.selectbox("Records per page", [5, 10, 20, 50], index=1)
            filters = {
                "status": LABEL_TO_STATUS.get(status_choice),
                "created_date": chosen_date if use_date else None,
                "limit": limit,
            }

        st.divider()
        st.caption("Backend status")
        if is_online:
            st.success("FastAPI is online")
        else:
            st.error("FastAPI is offline")
        st.caption(f"API: {API_URL}")
    return page, filters


def render_dashboard():
    """Summary cards for a selected date (uses /stats/daily)."""
    left, right = st.columns([3, 1])
    left.subheader("📊 Daily Dashboard")
    selected_date = right.date_input("Select date", value=date.today(), key="dashboard_date")

    summary, error = get_daily_summary(selected_date)
    if error:
        st.error(error)
        return

    by_status = summary.get("by_status", {})
    total = summary.get("total_orders", 0)

    cards = [
        ("Total Orders", total, "#FF6B35", "🧾"),
        ("Preparing", by_status.get("preparing", 0), "#F59E0B", "🟠"),
        ("Picked Up", by_status.get("picked_up", 0), "#3B82F6", "🔵"),
        ("In Transit", by_status.get("in_transit", 0), "#8B5CF6", "🟣"),
        ("Delivered", by_status.get("delivered", 0), "#10B981", "🟢"),
    ]
    columns = st.columns(5)
    for col, (label, value, color, icon) in zip(columns, cards):
        col.markdown(
            f"""
            <div class="metric-card" style="--accent:{color};">
                <div class="metric-label">{icon} {label}</div>
                <div class="metric-value">{value}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.write("")
    if total == 0:
        st.info(f"No orders were created on {selected_date.strftime('%d %b %Y')}.")
    else:
        delivered = by_status.get("delivered", 0)
        st.markdown(f"**Delivery progress:** {delivered} of {total} orders delivered")
        st.progress(min(delivered / total, 1.0))


def render_create_order():
    """Order form with validation (uses POST /orders/)."""
    st.subheader("➕ Create New Order")
    st.caption("Fill in the details below to register a new tiffin order.")

    with st.form("create_order_form"):
        customer_name = st.text_input("Customer Name", placeholder="e.g. Ritika")
        delivery_address = st.text_area("Delivery Address", placeholder="e.g. Model Town, Jalandhar", height=90)
        items = st.text_input("Tiffin Items", placeholder="e.g. Dal, Rice, 4 Roti")
        submitted = st.form_submit_button("🍱 Create Order", type="primary")

    if not submitted:
        return

    # Validation: no empty (or whitespace-only) fields
    name, address, tiffin_items = customer_name.strip(), delivery_address.strip(), items.strip()
    missing = [label for label, value in [("Customer Name", name),
                                          ("Delivery Address", address),
                                          ("Tiffin Items", tiffin_items)] if not value]
    if missing:
        st.warning("Please fill in: " + ", ".join(missing))
        return

    with st.spinner("Creating order..."):
        created, error = create_order(name, address, tiffin_items)

    if error:
        st.error(f"Could not create the order. {error}")
    else:
        order_id = created.get("id") if isinstance(created, dict) else None
        suffix = f" (Order ID: {order_id})" if order_id else ""
        st.success(f"✅ Order created successfully{suffix}.")


def render_order_details(orders):
    """Show all fields of one order picked from the current page."""
    st.markdown("### 🔍 Order Details")
    orders_by_id = {o.get("id"): o for o in orders}
    selected_id = st.selectbox(
        "Select an order to inspect",
        options=list(orders_by_id.keys()),
        format_func=lambda oid: f"#{oid} — {orders_by_id[oid].get('customer_name', 'Unknown')}",
    )
    order = orders_by_id[selected_id]

    def field(label, value):
        return (f'<div class="detail-label">{label}</div>'
                f'<div class="detail-value">{html.escape(str(value))}</div>')

    col1, col2 = st.columns(2)
    col1.markdown(
        '<div class="detail-card">'
        + field("Order ID", f"#{order.get('id', '—')}")
        + field("Customer Name", order.get("customer_name", "—"))
        + field("Delivery Address", order.get("delivery_address", "—"))
        + field("Items", order.get("items", "—"))
        + "</div>",
        unsafe_allow_html=True,
    )
    col2.markdown(
        '<div class="detail-card">'
        '<div class="detail-label">Status</div>'
        f'<div class="detail-value">{status_badge(order.get("status"))}</div>'
        + field("Created At", format_datetime(order.get("created_at")))
        + field("Updated At", format_datetime(order.get("updated_at")))
        + "</div>",
        unsafe_allow_html=True,
    )


def render_orders(filters):
    """Filtered, paginated order table (uses GET /orders/)."""
    st.subheader("📋 Orders")

    # Reset to page 1 whenever the filters change
    signature = (filters["status"], filters["created_date"], filters["limit"])
    if st.session_state.get("filter_signature") != signature:
        st.session_state.filter_signature = signature
        st.session_state.page = 0
    page = st.session_state.get("page", 0)
    limit = filters["limit"]
    skip = page * limit  # pagination uses the backend's skip/limit

    orders, error = get_orders(filters["status"], filters["created_date"], skip, limit)
    if error:
        st.error(error)
        return

    if not orders:
        if page > 0:
            st.info("No more orders on this page.")
        else:
            st.info("No orders found for the selected filters.")
    else:
        rows = [
            {
                "Order ID": o.get("id"),
                "Customer": o.get("customer_name", "—"),
                "Address": o.get("delivery_address", "—"),
                "Items": o.get("items", "—"),
                "Status": status_label(o.get("status")),
                "Created At": format_datetime(o.get("created_at")),
            }
            for o in orders
        ]
        st.dataframe(rows, hide_index=True)

    # Pagination controls (backend gives no total count, so a full page
    # suggests there may be a next page)
    prev_col, info_col, next_col = st.columns([1, 2, 1])
    if prev_col.button("⬅️ Previous", disabled=page == 0):
        st.session_state.page = page - 1
        st.rerun()
    info_col.markdown(
        f"<div style='text-align:center;padding-top:0.4rem;'>Page <b>{page + 1}</b> "
        f"· Showing <b>{len(orders)}</b> record(s)</div>",
        unsafe_allow_html=True,
    )
    if next_col.button("Next ➡️", disabled=len(orders) < limit):
        st.session_state.page = page + 1
        st.rerun()

    if orders:
        st.divider()
        render_order_details(orders)


# --------------------------------------------------------------------------
# MAIN APP
# --------------------------------------------------------------------------
def main():
    is_online, health_error = get_health()
    render_header(is_online)
    page, filters = render_sidebar(is_online)

    # If the backend is down, stop early with a friendly message
    if not is_online:
        st.error(health_error)
        st.info("Once the backend is running, refresh this page.")
        return

    if page == "📊 Dashboard":
        render_dashboard()
    elif page == "➕ Create Order":
        render_create_order()
    else:
        render_orders(filters)


main()