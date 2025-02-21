from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)

def get_car_data(make="", model="", year_from=None, year_to=None, price_from=None, price_to=None, mileage_from=None, mileage_to=None, keyword=""):
    base_url = "https://www.sbtjapan.com/used-cars/"
    
    # If a keyword search is provided, ignore other filters
    if keyword:
        params = {"keyword": keyword}
    else:
        params = {
            "make": make if make else "",
            "model": model if model else "",
            "year_f": year_from if year_from else "",
            "year_t": year_to if year_to else "",
            "price_f": price_from if price_from else "",
            "price_t": price_to if price_to else "",
            "mile_f": mileage_from if mileage_from else "",
            "mile_t": mileage_to if mileage_to else "",
            "search_box": 1,
            "sort": 46
        }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    response = requests.get(base_url, params=params, headers=headers)

    if response.status_code != 200:
        return [{"Error": f"Failed to fetch data. Status Code: {response.status_code}"}]

    soup = BeautifulSoup(response.text, 'html.parser')

    # Extract car details
    car_data = []

    car_images = [img["src"] for img in soup.find_all("img") if "dealercarphoto" in img.get("src", "")]
    
    car_prices = [span.get_text(strip=True) for span in soup.find_all("span") if "USD" in span.get_text()]
    
    car_titles = [h.get_text(strip=True) for h in soup.find_all(["h2", "h3"]) if "AUDI" in h.get_text(strip=True)]
    
    # Extract mileage correctly from car_info_right div
    car_mileages = []
    for car in soup.find_all("div", class_="car_info_right"):
        mileage_tag = car.find("h3", string="Mileage")
        if mileage_tag:
            mileage_p = mileage_tag.find_next("p")
            mileage = mileage_p.get_text(strip=True) if mileage_p else "N/A"
            car_mileages.append(mileage)
    
    while len(car_mileages) < len(car_titles):  
        car_mileages.append("N/A")  # Fill missing values

    # Extract features uniquely (removes duplicates)
    car_features = []
    for div in soup.find_all("div"):
        text = div.get_text(strip=True)
        features_list = list(set(re.findall(r"(Air Conditioner|Cruise Control|Navigation System|ABS|Alloy Wheels|Back Camera|Leather Seat|Sun Roof)", text)))

        if features_list:
            car_features.append(", ".join(features_list))
    
    while len(car_features) < len(car_titles):  
        car_features.append("N/A")  # Fill missing values

    # Ensure correct matching of extracted data
    total_cars = min(len(car_images), len(car_prices), len(car_titles), len(car_mileages), len(car_features))

    for i in range(total_cars):
        car_data.append({
            "Image": car_images[i],
            "Title": car_titles[i],
            "Price": car_prices[i],
            "Mileage": car_mileages[i],
            "Features": car_features[i]
        })

    return car_data if car_data else [{"Error": "No cars found"}]

@app.route('/', methods=['GET', 'POST'])
def index():
    cars = []
    search_performed = False

    if request.method == 'POST':
        search_performed = True
        keyword = request.form.get("keyword", "").strip()
        make = request.form.get("make", "")
        model = request.form.get("model", "")
        year_from = request.form.get("year_from", None)
        year_to = request.form.get("year_to", None)
        price_from = request.form.get("price_from", None)
        price_to = request.form.get("price_to", None)
        mileage_from = request.form.get("mileage_from", None)
        mileage_to = request.form.get("mileage_to", None)

        # Convert numeric fields properly
        year_from = int(year_from) if year_from else None
        year_to = int(year_to) if year_to else None
        price_from = int(price_from) if price_from else None
        price_to = int(price_to) if price_to else None
        mileage_from = int(mileage_from) if mileage_from else None
        mileage_to = int(mileage_to) if mileage_to else None

        cars = get_car_data(make, model, year_from, year_to, price_from, price_to, mileage_from, mileage_to, keyword)

    return render_template("index.html", cars=cars, search_performed=search_performed)

if __name__ == '__main__':
    app.run(debug=True)
