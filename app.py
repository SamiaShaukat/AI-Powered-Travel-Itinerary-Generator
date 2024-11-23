import os
import gradio as gr
import requests
from datetime import datetime
from groq import Groq

client = Groq(api_key="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")


# Function to validate date format
def validate_date(date_text):
    try:
        datetime.strptime(date_text, "%Y-%m-%d")
        return True
    except ValueError:
        return False

# Function to get hotels and attractions, then use Claude AI to generate an itinerary
def generate_itinerary(destination, num_people, budget, arrival_date, departure_date):
    # Validate dates
    if not validate_date(arrival_date) or not validate_date(departure_date):
        return "Error: Please enter dates in the format YYYY-MM-DD."

    # Set up variables for results
    hotel_results = "Hotel Recommendations:\n"
    attraction_results = "Attractions:\n"

    # First API: Fetch locationId based on the destination
    def get_location_id(city_name):
        url = "https://hotels-com6.p.rapidapi.com/hotels/auto-complete"
        querystring = {"query": city_name}
        headers = {
            "x-rapidapi-key": "7396fc6936msh4665e696fedb15dp13e5cfjsne6abaccb7d9a",
            "x-rapidapi-host": "hotels-com6.p.rapidapi.com"
        }

        response = requests.get(url, headers=headers, params=querystring)
        data = response.json()

        if data and "data" in data and "sr" in data["data"]:
            # Extracting locationId from the first result in "sr"
            first_location = data["data"]["sr"][0]
            location_id = first_location.get("locationId")
            return location_id
        return None

    location_id = get_location_id(destination)
    if not location_id:
        return "Error: Could not find location ID for the destination."

    # Second API: Search hotels based on the locationId
    def search_hotels(location_id, checkin_date, checkout_date, num_people):
        url = "https://hotels-com6.p.rapidapi.com/hotels/search"
        querystring = {
            "locationId": location_id,
            "checkinDate": checkin_date,
            "checkoutDate": checkout_date,
            "adults1": num_people
        }
        headers = {
            "x-rapidapi-key": "7396fc6936msh4665e696fedb15dp13e5cfjsne6abaccb7d9a",
            "x-rapidapi-host": "hotels-com6.p.rapidapi.com"
        }

        response = requests.get(url, headers=headers, params=querystring)
        return response.json()

    hotel_data = search_hotels(location_id, arrival_date, departure_date, num_people)

    # Extract hotel names from the API response
    try:
        hotel_listings = hotel_data.get("data", {}).get("propertySearchListings", [])
        for hotel in hotel_listings:
            hotel_name = hotel.get("headingSection", {}).get("heading")
            if hotel_name:
                hotel_results += f"- {hotel_name}\n"
        if not hotel_listings:
            hotel_results += "No hotels found for the given criteria.\n"
    except KeyError as e:
        hotel_results += f"Error accessing hotel listings: {e}\n"

    # Foursquare API setup for attractions
    fsq_url = "https://api.foursquare.com/v3/places/search"
    fsq_headers = {
        "Accept": "application/json",
        "Authorization": "fsq3RCx/OsydP/GesA8RJrwATydRCjX5zp+kpsq2CFPmHPM="
    }
    fsq_params = {
        "query": "attractions",
        "near": destination,
        "limit": 5
    }

    # Fetch attractions
    try:
        fsq_response = requests.get(fsq_url, headers=fsq_headers, params=fsq_params)
        fsq_response.raise_for_status()
        fsq_data = fsq_response.json()

        if 'results' in fsq_data:
            for place in fsq_data['results']:
                place_info = f"{place['name']} - {place['location']['address']}"
                attraction_results += f"{place_info}\n"
        else:
            attraction_results += "No attractions found for the given criteria.\n"
    except requests.exceptions.RequestException as e:
        attraction_results += f"Error fetching attractions: {e}\n"

    # Initiating groq for itinerary generation
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": f"Generate an efficient travel itinerary for a trip to {destination}. "
                           f"The trip includes {num_people} people with a budget of ${budget} from {arrival_date} to {departure_date}. "
                           f"Here are some hotel options:\n{hotel_results}\n"
                           f"And here are top attractions to visit:\n{attraction_results}\n"
                           f"Create a day-by-day plan with time allocations, dining suggestions, and budget-friendly tips."
            }
        ],
        model="llama3-8b-8192",
    )

    itinerary = chat_completion.choices[0].message.content

    # Return separated results
    return f"{hotel_results}\n\n{attraction_results}", itinerary

# Gradio interface setup
interface = gr.Interface(
    fn=generate_itinerary,
    inputs=[
        gr.Textbox(label="Destination (City)"),
        gr.Number(label="Number of People"),
        gr.Number(label="Budget (USD)"),
        gr.Textbox(label="Arrival Date (YYYY-MM-DD)"),
        gr.Textbox(label="Departure Date (YYYY-MM-DD)")
    ],
    outputs=[
        gr.Textbox(label="Hotel and Attraction Recommendations"),
        gr.Textbox(label="Generated Itinerary")
    ],
    title="AI-Powered Travel Itinerary Generator",
    description="Enter your travel details to generate a customized itinerary with hotel and attraction recommendations, plus a day-by-day plan."
)

# Launch the Gradio interface
interface.launch(debug = 'True')
