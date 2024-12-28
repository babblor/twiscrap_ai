import streamlit as st
from apify_client import ApifyClient
import pandas as pd
from pymongo import MongoClient
from datetime import datetime
import requests
from time import sleep
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Set your Apify API token and MongoDB URI from environment variables
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
PROXY = os.getenv("PROXY")
PORT = os.getenv("PORT")
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

def init_selenium():
    """Simulate a dummy task using Selenium."""
    # Setting up a dummy WebDriver (in this case, not really used for scraping)
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Run in headless mode (without opening a window)
    driver = webdriver.Chrome(options=options)
    
    try:
        driver.get("https://twitter.com/login")  # Navigate to Twitter login page
        time.sleep(2)  # Simulate waiting for the page to load
        
        # Simulate interaction with the page (entering username and password)
        username_box = driver.find_element(By.NAME, "text")  # Find the username input
        username_box.send_keys("dummy_username")  # Simulate typing the username
        username_box.send_keys(Keys.RETURN)  # Press Enter
        
        time.sleep(2)  # Wait for the password field to appear
        
        password_box = driver.find_element(By.NAME, "password")  # Find the password input
        password_box.send_keys("dummy_password")  # Simulate typing the password
        password_box.send_keys(Keys.RETURN)  # Press Enter
        
        time.sleep(3)  # Simulate waiting for the page to load after login attempt
        
        # Do something dummy with the results (not actually logging in)
        print("Simulated Twitter login task completed successfully.")
        
    except Exception as e:
        print(f"Error during Selenium task: {e}")
    
    finally:
        driver.quit()  # Close the WebDriver

# Run the function
# init_selenium()


def fetch_data_with_retry(url, proxy_ip, proxy_port, retries=3, delay=5):
    """Fetch data with retry logic and delay between requests using dynamic proxy."""
    proxies = {
        "http": f"http://{proxy_ip}:{proxy_port}",
        "https": f"https://{proxy_ip}:{proxy_port}",
    }
    try:
        response = requests.get(url, proxies=proxies)
        response.raise_for_status()  # Raises HTTPError for bad responses (4xx, 5xx)
        return response
    except requests.exceptions.ConnectionError as e:
        # Catch connection errors (server refuses connection)
        print(f"Connection error occurred: {e}")
        if retries > 0:
            print(f"Retrying in {delay} seconds...")
            sleep(delay)
            return fetch_data_with_retry(url, proxy_ip, proxy_port, retries-1, delay)  # Retry the request
        else:
            print("Max retries reached. Could not establish a connection.")
            return None
    except requests.exceptions.Timeout:
        # Catch timeout errors (if the server takes too long to respond)
        print("Request timed out. Retrying...")
        if retries > 0:
            sleep(delay)
            return fetch_data_with_retry(url, proxy_ip, proxy_port, retries-1, delay)
        else:
            print("Max retries reached. Timeout error.")
            return None
    except requests.exceptions.RequestException as e:
        # Catch other request-related exceptions
        print(f"Request error occurred: {e}")
        return None

def fetch_latest_topics(proxy_ip, proxy_port):
    """Fetch trending topics from Apify using dynamic proxy."""
    client = ApifyClient(APIFY_API_TOKEN)

    run_input = {
        "country": "2",
        "live": True,
        "hour1": False,
        "hour3": False,
        "hour6": False,
        "hour12": False,
        "day2": False,
        "day3": False,
        "proxyOptions": {
            "useApifyProxy": False, 
            "proxyUrl": proxy_ip, 
            "proxyPort": proxy_port, 
        }
    }

    try:
        run = client.actor("oCAEibQtPGKXcF5MM").call(run_input=run_input)
        results = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        return results
    except Exception as e:
        st.error(f"Error fetching topics: {e}")
        return []

def save_to_mongodb(data, ip_address, proxy_ip, proxy_port):
    """Save scraped data to MongoDB."""
    try:
        client = MongoClient(MONGO_URI)
        db = client["igrosine"]  # MongoDB will create the database if it doesn't exist
        collection = db["topics"]  # MongoDB will create the collection if it doesn't exist

        # Get the current date and time
        now = datetime.now()

        # Prepare documents to insert
        for i, topic in enumerate(data[:5], start=1):  # Limit to top 5 trends
            document = {
                "unique_id": f"{now.strftime('%Y%m%d%H%M%S')}_{i}",
                "name_of_trend": topic.get("trend"),
                "date_time_of_script_completion": now.strftime("%Y-%m-%d %H:%M:%S"),
                "ip_address_used": proxy_ip+":"+proxy_port
            }
            collection.insert_one(document)

        st.success("Results successfully saved to MongoDB!")
    except Exception as e:
        st.error(f"Error saving to MongoDB: {e}")

# Streamlit app

# Set page metadata title
st.set_page_config(
    page_title="Latest Twitter(X) Trending Topics Scraper",  # Title of the page (metadata title)
    page_icon="📰",  # Icon that appears in the browser tab (optional)
    layout="wide"  # Layout type (optional, "centered" or "wide")
)

st.image("logo.webp", width=200)  # Display image with specific width and height
st.title("Latest Twitter(X) Trending Topics Scraper")

# Add fields for the user to input proxy IP and port
proxy_ip = st.text_input("Enter your Proxy IP address:", PROXY)  # Default IP from environment
proxy_port = st.text_input("Enter your Proxy Port:", PORT)  # Default port from environment

# Check if proxy IP and port are valid (optional validation can be added)
if proxy_ip and proxy_port:
    st.write(f"Your current proxy IP address is: **{proxy_ip}**")
    st.write(f"Your current proxy port is: **{proxy_port}**")

if st.button("Scrape and Save"):
    with st.spinner("Fetching latest topics..."):
        topics = fetch_latest_topics(proxy_ip, proxy_port)
        
        if topics:
            # Limit to top 5 topics and format data
            top_5_topics = topics[:5]
            now = datetime.now()

            print(top_5_topics)
            
            # Prepare data for display
            data_for_display = []
            for i, topic in enumerate(top_5_topics, start=1):
                data_for_display.append({
                    "ID": f"{now.strftime('%Y%m%d%H%M%S')}_{i}",
                    "NAME": topic.get("trend"),
                    "DATE": now.strftime("%Y-%m-%d %H:%M:%S"),
                    "PROXY": proxy_ip+":"+proxy_port,
                })
            
            # Convert to DataFrame for displaying in Streamlit
            df = pd.DataFrame(data_for_display)
            st.write("Here are the top 5 latest trending topics: ")
            st.dataframe(df)

            # Save to MongoDB with the dynamic proxy IP and port
            save_to_mongodb(top_5_topics, "N/A", proxy_ip, proxy_port)
        else:
            st.warning("No topics found.")
