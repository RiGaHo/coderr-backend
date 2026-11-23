"""Exercise authenticated workflows over real HTTP using disposable data."""

import json
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from http_server import live_server


class HTTPClient:
    """Small JSON HTTP client that checks each expected response status."""

    def __init__(self, base):
        """Store the isolated server address and initial anonymous state."""
        self.base = base
        self.token = None
        self.checks = 0

    def request(self, method, path, expected, data=None):
        """Send a real request and decode its JSON or empty response."""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Token {self.token}"
        body = json.dumps(data).encode() if data is not None else None
        request = Request(self.base + path, data=body, headers=headers, method=method)
        try:
            response = urlopen(request, timeout=10)
        except HTTPError as error:
            response = error
        with response:
            return self.decode(response, expected)

    def decode(self, response, expected):
        """Check status and body before returning decoded JSON."""
        content = response.read()
        assert response.status == expected, (response.status, expected, content)
        self.checks += 1
        return json.loads(content) if content else None


def register(client, name, role):
    """Register a fresh account and check the required identity fields."""
    data = {
        "username": name,
        "email": f"{name}@example.invalid",
        "type": role,
        "password": "HTTPSmokePassword42!",
        "repeated_password": "HTTPSmokePassword42!",
    }
    result = client.request("POST", "registration/", 201, data)
    assert set(result) == {"token", "username", "email", "user_id"}
    return result


def offer_data():
    """Create a three-tier service request independent of API test fixtures."""
    tiers = [
        {
            "title": name,
            "offer_type": name,
            "price": 10 * index,
            "revisions": -1,
            "features": ["Service"],
            "delivery_time_in_days": index,
        }
        for index, name in enumerate(["basic", "standard", "premium"], 1)
    ]
    return {"title": "HTTP service", "description": "Disposable test", "details": tiers}


def authentication_checks(client, business):
    """Verify login and account/profile updates over the network."""
    bad = {"username": "httpbusiness", "password": "wrong"}
    client.request("POST", "login/", 400, bad)
    credentials = bad | {"password": "HTTPSmokePassword42!"}
    login = client.request("POST", "login/", 200, credentials)
    assert login["user_id"] == business["user_id"]
    client.token = login["token"]
    profile_checks(client, business["user_id"])


def profile_checks(client, user_id):
    """Verify own-profile edits and rejection of role changes."""
    path = f"profile/{user_id}/"
    profile = client.request("GET", path, 200)
    assert profile["location"] == ""
    updated = client.request("PATCH", path, 200, {"location": "Test"})
    assert updated["location"] == "Test"
    client.request("PATCH", path, 400, {"type": "customer"})
    client.request("GET", "profile/999999/", 404)


def offer_checks(client):
    """Create, resolve and partially edit a three-tier offer."""
    offer = client.request("POST", "offers/", 201, offer_data())
    path = f"offers/{offer['id']}/"
    read = client.request("GET", path, 200)
    assert read["min_price"] == 10 and len(read["details"]) == 3
    detail = client.request("GET", f"offerdetails/{offer['details'][0]['id']}/", 200)
    assert detail["revisions"] == -1
    changed = client.request("PATCH", path, 200, {"title": "Updated HTTP service"})
    assert changed["details"] == offer["details"]
    client.request("GET", "offers/999999/", 404)
    return offer


def customer_checks(client, customer, business, offer):
    """Exercise customer purchases and protected fields."""
    client.token = customer["token"]
    client.request("POST", "offers/", 403, offer_data())
    client.request("PATCH", f"profile/{business['user_id']}/", 403, {"location": "No"})
    client.request("DELETE", f"offers/{offer['id']}/", 403)
    order = client.request(
        "POST", "orders/", 201, {"offer_detail_id": offer["details"][0]["id"]}
    )
    assert order["customer_user"] == customer["user_id"]
    client.request("PATCH", f"orders/{order['id']}/", 403, {"status": "completed"})
    client.request("POST", "orders/", 404, {"offer_detail_id": 999999})
    review = review_checks(client, business)
    return order, review


def review_checks(client, business):
    """Create, edit and reject duplicate customer reviews."""
    data = {
        "business_user": business["user_id"],
        "rating": 4,
        "description": "HTTP review",
    }
    review = client.request("POST", "reviews/", 201, data)
    client.request("POST", "reviews/", 400, data)
    changed = client.request("PATCH", f"reviews/{review['id']}/", 200, {"rating": 5})
    assert changed["rating"] == 5 and changed["reviewer"] == review["reviewer"]
    return review


def completion_checks(client, business, offer, order, review):
    """Complete an order and verify the snapshot after deleting its offer."""
    client.token = business["token"]
    client.request("DELETE", f"reviews/{review['id']}/", 403)
    client.request("PATCH", f"orders/{order['id']}/", 200, {"status": "completed"})
    counts = client.request("GET", f"completed-order-count/{business['user_id']}/", 200)
    assert counts == {"order_count": 1, "completed_order_count": 1}
    assert client.request("DELETE", f"offers/{offer['id']}/", 204) is None
    stored = client.request("GET", "orders/", 200)[0]
    assert stored["price"] == order["price"] and stored["status"] == "completed"


def run_workflows(client):
    """Run all workflows within one disposable server/database lifecycle."""
    client.request("GET", "orders/", 401)
    client.request("GET", "offers/", 200)
    business = register(client, "httpbusiness", "business")
    customer = register(client, "httpcustomer", "customer")
    authentication_checks(client, business)
    offer = offer_checks(client)
    order, review = customer_checks(client, customer, business, offer)
    completion_checks(client, business, offer, order, review)
    client.token = customer["token"]
    client.request("DELETE", f"reviews/{review['id']}/", 204)
    assert client.request("GET", "base-info/", 200)["review_count"] == 0


def main():
    """Report actual HTTP checks; propagate errors rather than simulating success."""
    with live_server() as base:
        client = HTTPClient(base)
        run_workflows(client)
        sys.stdout.write(f"HTTP smoke passed: {client.checks} requests.\n")


if __name__ == "__main__":
    main()
