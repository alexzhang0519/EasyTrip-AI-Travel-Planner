from flask import Blueprint, render_template
pages = Blueprint('pages', __name__)

@pages.get('/')
def home():
    return render_template('index.html', page='home')

@pages.get('/planner')
def planner():
    return render_template('planner.html', page='planner')

@pages.get('/trips')
def trips():
    return render_template('trips.html', page='trips')

@pages.get('/restaurants')
def restaurants():
    return render_template('restaurants.html', page='restaurants')
