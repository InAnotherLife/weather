import os
from datetime import datetime
from typing import Optional, Tuple

import requests
from dotenv import load_dotenv
from flask import (Flask, jsonify, redirect, render_template, request, session,
                   url_for)
from flask_sqlalchemy import SQLAlchemy
from geopy.geocoders import Nominatim
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.types import PickleType

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///weather.db'
app.secret_key = os.getenv('SECRET_KEY')

db = SQLAlchemy(app)


# Модель города
class Сity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    added = db.Column(MutableList.as_mutable(PickleType), default=[])


# Получение координат города по названию
def get_coordinates(city_name: str) -> Optional[Tuple[float, float]]:
    geolocator = Nominatim(user_agent='Weather')
    location = geolocator.geocode(city_name)
    if location:
        return location.latitude, location.longitude


# Эндпойнт выводит прогноз погоды
@app.route('/weather', methods=['POST'])
def get_weather():
    city_name = request.form['name'].title()
    coordinates = get_coordinates(city_name)
    if coordinates:
        last_cities = session.get('last_cities', [])
        if city_name not in last_cities:
            last_cities.append(city_name)
            session['last_cities'] = last_cities
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
                current_city.added.append(
                    datetime.utcnow().replace(microsecond=0))
            else:
                new_city = Сity(name=city_name, added=[
                                datetime.utcnow().replace(microsecond=0)])
                db.session.add(new_city)
            db.session.commit()
        return render_template('weather.html', city=city_name,
                               weather=data.get('daily'))
    return jsonify({'message': 'City with that name was not found'}), 400


# Эндпойнт удаляет историю запросов прогноза погоды
@app.route('/clear', methods=['POST'])
def clear_last_cities():
    session.pop('last_cities')
    return redirect(url_for('index'))


# Эндпойнт выводит статистику запросов прогноза погоды
@app.route('/history')
def get_history():
    cities = Сity.query.all()
    sorted_cities = sorted(
        cities, key=lambda city: len(city.added), reverse=True)
    return render_template('history.html', cities=sorted_cities)


# Главная страница
@app.route('/')
def index():
    last_cities = session.get('last_cities')
    return render_template('index.html', last_cities=last_cities)


with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=False)
