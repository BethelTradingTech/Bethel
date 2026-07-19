"""
Bethel Trading Technologies
System Health Verification
"""

import requests


API = "http://127.0.0.1:8000"



def check(endpoint):

    try:

        response = requests.get(
            API + endpoint
        )


        print("\n====================")
        print("ENDPOINT:", endpoint)
        print("STATUS:", response.status_code)


        try:

            print(
                response.json()
            )

        except:

            print(
                response.text
            )


    except Exception as error:

        print("\nFAILED")
        print(endpoint)
        print(error)



print(
    "\nBETHEL TRADING TECHNOLOGIES SYSTEM CHECK"
)



check("/health")

check("/dashboard/data")

check("/analytics/performance")

check("/analytics/equity")

check("/risk/status")