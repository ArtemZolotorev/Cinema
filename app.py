from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cinema.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class Film(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    duration = db.Column(db.Integer)
    genre = db.Column(db.String(50))
    age = db.Column(db.String(3))
    country = db.Column(db.String(20))
    d = db.Column(db.String(2))
    poster_url = db.Column(db.String(200))
    screenings = db.relationship('Screening', backref='film', lazy=True)


class Hall(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    rows = db.Column(db.Integer, nullable=False)
    seats = db.Column(db.Integer, nullable=False)
    screenings = db.relationship('Screening', backref='hall', lazy=True)


class Screening(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.DateTime, nullable=False)
    price = db.Column(db.String(4), nullable=False)
    film_id = db.Column(db.Integer, db.ForeignKey('film.id'), nullable=False)
    hall_id = db.Column(db.Integer, db.ForeignKey('hall.id'), nullable=False)
    bookings = db.relationship('Booking', backref='screening', lazy=True)


class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.Integer, nullable=False)
    booking_time = db.Column(db.DateTime, default=datetime.utcnow)
    total_price = db.Column(db.Float)
    booked_seats = db.relationship('BookedSeat', backref='booking', lazy=True)
    screening_id = db.Column(db.Integer, db.ForeignKey('screening.id'))


class BookedSeat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'))
    row_number = db.Column(db.Integer, nullable=False)
    seat_number = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)


with app.app_context():
    db.create_all()


def get_russian_weekday(date):
    weekdays = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
    return weekdays[date.weekday()]


app.jinja_env.globals.update(get_russian_weekday=get_russian_weekday)


@app.route('/')
def home():
    films = Film.query.all()
    today = datetime.now().date()
    dates = [today + timedelta(days=i) for i in range(7)]

    for film in films:
        film.schedule_by_date = {}
        for screening in film.screenings:
            if screening.start_time > datetime.now():
                date = screening.start_time.date()
                if date not in film.schedule_by_date:
                    film.schedule_by_date[date] = []
                film.schedule_by_date[date].append(screening)

    return render_template('main.html', films=films, dates=dates, today=today)


@app.route('/booking/<int:screening_id>')
def booking_page(screening_id):
    screening = Screening.query.get_or_404(screening_id)
    occupied_seats = []
    for booking in screening.bookings:
        for seat in booking.booked_seats:
            occupied_seats.append((seat.row_number, seat.seat_number))
    return render_template('booking.html', screening=screening, occupied_seats=occupied_seats)


@app.route('/book', methods=['POST'])
def book_tickets():
    try:
        screening_id = request.form['screening_id']
        selected_seats = request.form['selected_seats'].split(',')
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']

        if not selected_seats or selected_seats[0] == '':
            return "Ошибка: не выбраны места"

        screening = Screening.query.get(screening_id)
        total_price = len(selected_seats) * float(screening.price)

        booking = Booking(
            name=name, email=email, phone=phone,
            screening_id=screening_id, total_price=total_price
        )
        db.session.add(booking)
        db.session.flush()

        for seat_str in selected_seats:
            row, seat = map(int, seat_str.split('-'))
            booked_seat = BookedSeat(
                booking_id=booking.id, row_number=row,
                seat_number=seat, price=float(screening.price)
            )
            db.session.add(booked_seat)

        db.session.commit()
        return redirect(url_for('booking_confirmation', booking_id=booking.id))

    except Exception as e:
        return f"Ошибка: {str(e)}"


@app.route('/booking/confirm/<int:booking_id>')
def booking_confirmation(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    return render_template('confirmation.html', booking=booking)


if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False
    )
