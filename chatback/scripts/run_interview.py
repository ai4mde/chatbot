#!/usr/bin/env python3
"""
Script to automate the interview process by first logging in to the API.
"""

import requests
import json
import sys
from termcolor import colored


def login():
    """
    Log in to the API and return the authentication token.
    """
    login_url = "http://localhost:8000/api/v1/auth/login"
    credentials = {"username": "kate", "password": "TestP@ssw0rd"}

    print(colored("Attempting to log in...", "blue"))

    try:
        response = requests.post(login_url, json=credentials)
        response.raise_for_status()  # Raise an exception for 4XX/5XX responses

        # Parse the response
        result = response.json()

        if response.status_code == 200:
            print(colored("Login successful!", "green"))
            print(colored(f"Response: {json.dumps(result, indent=2)}", "cyan"))
            return result.get("access_token")
        else:
            print(
                colored(f"Login failed with status code: {response.status_code}", "red")
            )
            print(colored(f"Response: {json.dumps(result, indent=2)}", "red"))
            return None

    except requests.exceptions.RequestException as e:
        print(colored(f"Error during login: {str(e)}", "red"))
        return None


def main():
    """
    Main function to run the interview process.
    """
    token = login()

    if token:
        print(colored("Successfully obtained authentication token.", "green"))
        print(colored(f"Token: {token}", "yellow"))
    else:
        print(colored("Failed to obtain authentication token. Exiting.", "red"))
        sys.exit(1)

    # Future steps will be added here


if __name__ == "__main__":
    main()
