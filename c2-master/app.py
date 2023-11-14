from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///devices.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'secret_key'
db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mac_address = db.Column(db.String(17), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)


class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mac_address = db.Column(db.String(17), unique=True, nullable=False)
    uri = db.Column(db.String(255), nullable=False)


# Create tables
with app.app_context():
    db.create_all()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        mac_address = request.form['mac_address']
        password = request.form['password']
        hashed_password = generate_password_hash(password)

        new_user = User(mac_address=mac_address, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash('User registered successfully!', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        mac_address = request.form['mac_address']
        password = request.form['password']

        user = User.query.filter_by(mac_address=mac_address).first()

        if user and check_password_hash(user.password, password):
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Login failed. Check your credentials and try again.', 'danger')

    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    users = User.query.all()
    devices = Device.query.all()
    return render_template('dashboard.html', users=users, devices=devices)


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
