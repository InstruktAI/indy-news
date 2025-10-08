#!/usr/bin/env python3
"""
Cookie refresh cron script - triggers async cookie refresh via playwright service.
Results are delivered via webhook (configured separately).

Usage:
    python bin/refresh_cookies_cron.py

Required environment variables:
    SVC_USERNAME - X/Twitter username
    SVC_EMAIL - X/Twitter email
    SVC_PASSWORD - X/Twitter password
    EMAIL_PASSWORD - ProtonMail password

Optional environment variables:
    CACHE - Directory for cookie storage (default: {cwd}/cache)
    COOKIE_SERVICE_URL - Service URL (default: http://localhost:8000)
    COOKIE_SERVICE_CALLBACK_URL - Webhook callback URL (default: http://localhost:8088/webhook/cookies)
"""

import asyncio
import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()


async def trigger_cookie_refresh() -> str | None:
    """Trigger async cookie refresh and return request_id"""
    service_url = os.getenv("COOKIE_SERVICE_URL", "http://localhost:8000/get-cookies")
    callback_url = os.getenv(
        "COOKIE_SERVICE_CALLBACK_URL", "http://localhost:8088/webhook/cookies"
    )
    api_key = os.getenv("API_KEY")
    if "?" in service_url:
        callback_url += f"&apikey={api_key}"
    else:
        callback_url += f"?apikey={api_key}"

    service_api_key = os.getenv("COOKIE_SERVICE_API_KEY")
    if "?" in service_url:
        service_url += f"&apikey={service_api_key}"
    else:
        service_url += f"?apikey={service_api_key}"

    svc_username = os.getenv("SVC_USERNAME")
    svc_email = os.getenv("SVC_EMAIL")
    svc_password = os.getenv("SVC_PASSWORD")
    email_password = os.getenv("EMAIL_PASSWORD")

    if not all([svc_username, svc_email, svc_password, email_password]):
        print("Error: Missing required environment variables", file=sys.stderr)
        print(
            "Required: SVC_USERNAME, SVC_EMAIL, SVC_PASSWORD, EMAIL_PASSWORD",
            file=sys.stderr,
        )
        sys.exit(1)

    async with httpx.AsyncClient(timeout=180.0) as client:
        try:
            print("Triggering cookie refresh...")
            response = await client.post(
                service_url,
                json={
                    "login_url": "https://x.com/login",
                    "svc_username": svc_username,
                    "svc_email": svc_email,
                    "svc_password": svc_password,
                    "email_password": email_password,
                    "callback_url": callback_url,
                },
            )
            response.raise_for_status()

            data = response.json()

            # Expect TaskStatusResponse format
            if data.get("request_id"):
                print(f"✓ Task accepted. Request ID: {data.get('request_id')}")
                return data.get("request_id")
            else:
                print(f"Unexpected response: {data}", file=sys.stderr)
                sys.exit(1)

        except httpx.HTTPError as e:
            print(f"HTTP error during cookie refresh: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error during cookie refresh: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(trigger_cookie_refresh())
