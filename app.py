from flask import Flask, render_template, request, send_file, jsonify
import requests
from bs4 import BeautifulSoup
import re
import pdfkit
import io
import json
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.DEBUG)

def get_car_data(make="", model="", year_from=None, year_to=None, price_from=None, price_to=None, mileage_from=None, mileage_to=None, keyword=""):
    try:
        base_url = "https://www.sbtjapan.com/used-cars/"
        
        params = {
            "steering": "all",
            "type": 0,
            "sub_body_type": 0,
            "drive": 0,
            "price_t": price_to if price_to else "",
            "cc_f": 0,
            "cc_t": 0,
            "mile_f": mileage_from // 1000 if mileage_from else "",
            "mile_t": mileage_to // 1000 if mileage_to else "",
            "trans": 0,
            "fuel": 0,
            "color": 0,
            "loadClass": 0,
            "engineType": 0,
            "location": 0,
            "port": 0,
            "search_box": 1,
            "locationIds": 0,
            "d_country": 76,
            "d_port": 119,
            "ship_type": 0,
            "FreightChk": "yes",
            "currency": 2,
            "insurance": 1,
            "fav_currency": 2,
            "fav_d_country": 76,
            "fav_insurance": 2,
            "sort": 46
        }

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        response = requests.get(base_url, params=params, headers=headers)

        if response.status_code != 200:
            logging.error(f"Failed to fetch data. Status Code: {response.status_code}")
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

        # Extract additional details
        car_details = []
        for car in soup.find_all("div", class_="car_info_right"):
            details = {}
            for detail in car.find_all("p"):
                key_value = detail.get_text(strip=True).split(":")
                if len(key_value) == 2:
                    details[key_value[0].strip()] = key_value[1].strip()
            car_details.append(details)
        
        while len(car_details) < len(car_titles):  
            car_details.append({})  # Fill missing values

        # Extract JSON data
        script_tag = soup.find("script", text=re.compile("window.__INITIAL_STATE__"))
        if script_tag:
            json_text = re.search(r"window.__INITIAL_STATE__\s*=\s*(\{.*\})", script_tag.string)
            if json_text:
                json_data = json.loads(json_text.group(1))
                for i, car in enumerate(json_data.get("cars", [])):
                    if i < len(car_data):
                        car_data[i].update({
                            "Engine": car.get("engine", "N/A"),
                            "Transmission": car.get("transmission", "N/A"),
                            "Fuel": car.get("fuel", "N/A"),
                            "Color": car.get("color", "N/A")
                        })

        # Ensure correct matching of extracted data
        total_cars = min(len(car_images), len(car_prices), len(car_titles), len(car_mileages), len(car_features), len(car_details))

        for i in range(total_cars):
            car_data.append({
                "Image": car_images[i],
                "Title": car_titles[i],
                "Price": car_prices[i],
                "Mileage": car_mileages[i],
                "Features": car_features[i],
                "Details": car_details[i]
            })

        return car_data if car_data else [{"Error": "No cars found"}]
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return [{"Error": "An internal error occurred"}]

@app.route('/export', methods=['POST'])
def export():
    try:
        cars = request.json.get('cars', [])
        if not cars:
            return jsonify({"Error": "No cars to export"}), 400

        html = render_template('export_template.html', cars=cars)
        pdf = pdfkit.from_string(html, False)
        return send_file(io.BytesIO(pdf), mimetype='application/pdf', as_attachment=True, download_name='car_data.pdf')
    except Exception as e:
        logging.error(f"An error occurred during export: {e}")
        return jsonify({"Error": "An internal error occurred during export"}), 500

@app.route('/', methods=['GET', 'POST'])
def index():
    try:
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
    except Exception as e:
        logging.error(f"An error occurred on the index page: {e}")
        return render_template("index.html", cars=[], search_performed=False, error="An internal error occurred")

if __name__ == '__main__':
    app.run(debug=True)
