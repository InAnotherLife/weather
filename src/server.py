import requests
from flask import Flask, jsonify, render_template, request
from flask_sqlalchemy import SQLAlchemy
from geopy.geocoders import Nominatim

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///weather.db'

db = SQLAlchemy(app)


# Модель города
class Сity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    count = db.Column(db.Integer, default=0)


# Получение координат города по названию
def get_coordinates(city_name):
    geolocator = Nominatim(user_agent='Weather')
    location = geolocator.geocode(city_name)
    if location:
        return location.latitude, location.longitude


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/weather', methods=['POST'])
def get_weather():
    city_name = request.form['name']
    coordinates = get_coordinates(city_name)
    if coordinates:
        url = ('https://api.open-meteo.com/v1/forecast?' +
               f'latitude={coordinates[0]}&longitude={coordinates[1]}' +
               '&daily=temperature_2m_max,temperature_2m_min&forecast_days=14')
        headers = {
                'Accept': 'text/html',
                'Accept-Encoding': 'gzip, deflate, sdch',
                'Accept-Language': 'en-US,en;q=0.8',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 12_3_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.4 Safari/605.1.15'  # noqa: E501
            }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            current_city = Сity.query.filter_by(name=city_name).first()
            if current_city:
                current_city.count += 1
            else:
                new_city = Сity(name=city_name, count=1)
                db.session.add(new_city)
            db.session.commit()
        return jsonify({'city': city_name, 'weather': data}), 200
    return jsonify({'message': 'City with that name was not found'}), 400


with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
