import requests

def register(username, display_name, role):
    res = requests.post("http://0.0.0.0:3000/api/auth/register", json={
        "username": username,
        "pin": "1234",
        "displayName": display_name,
        "role": role
    })
    print(f"Register {username}: {res.status_code}")

print("Testing registration...")
register("gm_user", "GM User", "GM")
register("player1", "Player User", "PLAYER")
register("gm_user", "Duplicate User", "PLAYER")
