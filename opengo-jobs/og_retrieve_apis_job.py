""" This script is the `opengo-jobs` component, responsible for performing the daily query and update of the OpenFinance API data. Main functionality: - Queries the OpenFinance Participants API (https://data.directory.openbankingbrasil.org.br/participants) and searches for information about loans (`opendata-loans`) and financing (`opendata-financings`) offered by the participating institutions - The collected data is stored in specific collections (`loans_rates` and `financings_rates`) in MongoDB Atlas. - The query job is scheduled to be performed daily at 3 am, ensuring that the data is always up to date Script structure: 1. Importing allowed libraries, including `requests` to make HTTP requests, `schedule` for scheduling jobs, and `pymongo` for interacting with MongoDB. 2. Configuring the connection to MongoDB Atlas using a provided URI.
3. Definition the `fetch_and_store_participants()` function, which performs the API data request, filters the relevant endpoints and stores the data in MongoDB.
4. Schedule the function execution daily at 3 am.
5. Continuous execution of the scheduler to ensure that the task is executed on the defined schedule.

The purpose of this component is to provide an updated database to be consumed by a frontend component, which will present the information to the end user in an organized and accessible way.
"""

# opengo-jobs: Component to search and update openfinance participants api daily


import requests
import os
import logging
from pymongo import MongoClient, UpdateOne
from datetime import datetime, timezone

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("opengo-jobs")

# Mongodb atlas connection configuration
MONGO_URI = os.getenv("MONGO_URI", None)
DATABASE_NAME = os.getenv("DATABASE_NAME")
ENVIRONMENT = os.getenv("ENVIRONMENT", "sandbox")
PARTICIPANTS_API_URI = os.getenv("PARTICIPANTS_API_URI",
                                 "https://data.sandbox.directory.openbankingbrasil.org.br/participants")

client = MongoClient(MONGO_URI)
db = client[DATABASE_NAME]


def fetch_and_store_participants():
    try:
        participants_response = requests.get(PARTICIPANTS_API_URI)
        participants_response.raise_for_status()
        participants = participants_response.json()

        loans_data = []
        financings_data = []

        for participant in participants:
            auth_servers = participant.get("AuthorisationServers", [])
            for auth_serer in auth_servers:
                apis = auth_serer.get("ApiResources", [])
                for api in apis:
                    discovery_endpoints = api.get("ApiDiscoveryEndpoints", [])
                    if discovery_endpoints and len(discovery_endpoints) > 0:
                        if "opendata-loans" in api["ApiDiscoveryEndpoints"][0]["ApiEndpoint"]:
                            loans_data.append(
                                UpdateOne(
                                    {"organisationId": participant.get("OrganisationId")},
                                    {"$set": {"data": api}},
                                    upsert=True
                                )
                            )
                        elif "opendata-financings" in api["ApiDiscoveryEndpoints"][0]["ApiEndpoint"]:
                            financings_data.append(
                                UpdateOne(
                                    {"organisationId": participant.get("OrganisationId")},
                                    {"$set": {"data": api}},
                                    upsert=True
                                )
                            )

        if loans_data:
            db[f"{ENVIRONMENT}.loans.rates"].bulk_write(loans_data)
        if financings_data:
            db[f"{ENVIRONMENT}.financings.rates"].bulk_write(financings_data)

        logger.info(f"{datetime.now(timezone.utc)} Job succeeded")
    except requests.exceptions.RequestException as e:
        logger.error(f"{datetime.now(timezone.utc)} Error while get dada from participants api: {e}")
    except ValueError as e:
        logger.error(f"Error interpreting JSON API response: {e}")
    except Exception as e:
        logger.error(f"{datetime.now(timezone.utc)} Error inserting data in database: {e}")
        print(e)


if __name__ == "__main__":
    fetch_and_store_participants()
