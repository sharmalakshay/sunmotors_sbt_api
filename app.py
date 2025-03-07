from flask import Flask, render_template, request, send_file
import requests
from bs4 import BeautifulSoup
import re
import pdfkit
import io
import json

app = Flask(__name__)

def get_car_data(make="", model="", year_from=None, year_to=None, price_from=None, price_to=None, mileage_from=None, mileage_to=None, keyword=""):
    base_url = "https://www.sbtjapan.com/used-cars/"
    
    # If a keyword search is provided, ignore other filters
    if keyword:
        params = {"keyword": keyword}
    else:
        params = {
            "search_box": 1,
            "sort": 46,
            "steering": "all",
            "type": 0,
            "sub_body_type": 0,
            "drive": 0,
            "cc_f": 0,
            "cc_t": 0,
            "trans": 0,
            "fuel": 0,
            "color": 0,
            "loadClass": 0,
            "engineType": 0,
            "location": 0,
            "port": 0,
            "locationIds": 0,
            "d_country": 76,
            "d_port": 119,
            "ship_type": 0,
            "FreightChk": "yes",
            "currency": 2,
            "insurance": 1,
            "fav_currency": 2,
            "fav_d_country": 76,
            "fav_insurance": 2
        }

        # Add filters only if they have values
        if make:
            params["make"] = make
        if model:
            params["model"] = model
        if year_from:
            params["year_f"] = year_from
        if year_to:
            params["year_t"] = year_to
        if price_from:
            params["price_f"] = price_from
        if price_to:
            params["price_t"] = price_to
        if mileage_from:
            params["mile_f"] = mileage_from / 1000
        if mileage_to:
            params["mile_t"] = mileage_to / 1000

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    response = requests.get(base_url, params=params, headers=headers)
    
    # Print the URL being visited for debugging
    print(response.url)

    if response.status_code != 200:
        return [], response.url

    soup = BeautifulSoup(response.text, 'html.parser')

    # Extract car details from HTML elements
    car_data = []
    car_images = [img["src"] for img in soup.find_all("img") if "dealercarphoto" in img.get("src", "")]
    car_prices = [span.get_text(strip=True) for span in soup.find_all("span") if "USD" in span.get_text()]
    car_titles = [h.get_text(strip=True) for h in soup.find_all(["h2", "h3"]) if "AUDI" in h.get_text(strip=True)]
    car_stock_ids = [p.get_text(strip=True).replace("Stock Id: ", "") for p in soup.find_all("p", class_="stock_num")]
    
    car_mileages = []
    for car in soup.find_all("div", class_="car_info_right"):
        mileage_tag = car.find("h3", string="Mileage")
        if mileage_tag:
            mileage_p = mileage_tag.find_next("p")
            mileage = mileage_p.get_text(strip=True) if mileage_p else "N/A"
            car_mileages.append(mileage)
    
    while len(car_mileages) < len(car_titles):  
        car_mileages.append("N/A")  # Fill missing values

    car_features = []
    for div in soup.find_all("div"):
        text = div.get_text(strip=True)
        features_list = list(set(re.findall(r"(Air Conditioner|Cruise Control|Navigation System|ABS|Alloy Wheels|Back Camera|Leather Seat|Sun Roof)", text)))
        if features_list:
            car_features.append(", ".join(features_list))
    
    while len(car_features) < len(car_titles):  
        car_features.append("N/A")  # Fill missing values

    total_cars = min(len(car_images), len(car_prices), len(car_titles), len(car_mileages), len(car_features), len(car_stock_ids))

    for i in range(total_cars):
        price_in_eur = float(car_prices[i].replace("USD", "").replace(",", "").strip()) * 4
        car_data.append({
            "Image": car_images[i],
            "Title": car_titles[i],
            "Price": f"{price_in_eur:.2f} EUR",
            "Mileage": car_mileages[i],
            "Features": car_features[i],
            "StockId": car_stock_ids[i]
        })

    # Fallback to JSON-LD script tag if no results found
    if not car_data:
        script_tag = soup.find("script", type="application/ld+json")
        if script_tag:
            json_data = json.loads(script_tag.string)
            if "itemListElement" in json_data:
                for item in json_data["itemListElement"]:
                    car = item["item"]
                    euro_price = next((offer["price"] for offer in car["offers"] if offer["priceCurrency"] == "EUR"), "N/A")
                    car_data.append({
                        "Image": car["image"],
                        "Title": car["name"],
                        "Price": f"{float(euro_price) * 3:.2f} EUR" if euro_price != "N/A" else "N/A",
                        "Mileage": "N/A",  # Mileage is not available in JSON-LD
                        "Features": car["description"],
                        "StockId": car["sku"]
                    })

    return car_data, response.url

@app.route('/export', methods=['POST'])
def export():
    cars = request.json.get('cars', [])
    if not cars:
        return {"Error": "No cars to export"}, 400

    html = render_template('export_template.html', cars=cars)
    pdf = pdfkit.from_string(html, False)
    return send_file(io.BytesIO(pdf), mimetype='application/pdf', as_attachment=True, download_name='car_data.pdf')

@app.route('/', methods=['GET', 'POST'])
def index():
    cars = []
    search_performed = False
    debug_url = None

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

        cars, debug_url = get_car_data(make, model, year_from, year_to, price_from, price_to, mileage_from, mileage_to, keyword)

    return render_template("index.html", cars=cars, search_performed=search_performed, debug_url=debug_url)

if __name__ == '__main__':
    app.run(debug=True)
