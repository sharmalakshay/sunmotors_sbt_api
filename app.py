from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup
import pandas as pd

app = Flask(__name__)

def get_car_data(make, model, year_from, year_to, price_from, price_to, mileage_from, mileage_to):
    base_url = "https://www.sbtjapan.com/used-cars/"
    params = {
        "make": make,
        "model": model,
        "year_f": year_from,
        "year_t": year_to,
        "price_f": price_from,
        "price_t": price_to,
        "mile_f": mileage_from,
        "mile_t": mileage_to,
        "search_box": 1,
        "sort": 46
    }
    
    response = requests.get(base_url, params=params)
    
    if response.status_code != 200:
        return []
    
    soup = BeautifulSoup(response.text, 'html.parser')
    car_list = soup.find_all("div", class_="car_listitem")
    
    car_data = []
    
    for car in car_list:
        image = car.find("img")["src"] if car.find("img") else "N/A"
        title = car.find("h2").text.strip() if car.find("h2") else "N/A"
        price = car.find("span", class_="price").text.strip() if car.find("span", class_="price") else "N/A"
        mileage = car.find("li", class_="mileage").text.strip() if car.find("li", class_="mileage") else "N/A"
        
        car_data.append({
            "Image": image,
            "Title": title,
            "Price": price,
            "Mileage": mileage
        })
    
    return car_data

@app.route('/', methods=['GET', 'POST'])
def index():
    cars = []
    if request.method == 'POST':
        make = request.form.get("make")
        model = request.form.get("model")
        year_from = request.form.get("year_from")
        year_to = request.form.get("year_to")
        price_from = request.form.get("price_from")
        price_to = request.form.get("price_to")
        mileage_from = request.form.get("mileage_from")
        mileage_to = request.form.get("mileage_to")
        
        cars = get_car_data(make, model, year_from, year_to, price_from, price_to, mileage_from, mileage_to)
    
    return render_template("index.html", cars=cars)

if __name__ == '__main__':
    app.run(debug=True)
