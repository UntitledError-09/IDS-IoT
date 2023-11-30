# Device Manager Web Application

This is a simple Flask web application for managing devices and users using SQLite as the database.

## Installation

1. Clone the Repository
    ```bash
    git clone https://github.com/your-username/device-manager.git
    cd device-manager
    ```
2. Create and Activate a Conda Environment
    ```bash
    Copy code
    conda create --name device-manager-env python=3.8
    conda activate device-manager-env
    ```
3. Install Dependencies
    ```bash
    Copy code
    pip install Flask Flask-SQLAlchemy
    ```
4. Run the Application
    ```bash
    Copy code
    python app.py
    ```
The application will be accessible at http://127.0.0.1:5000/ in your web browser.

## Usage
* Visit http://127.0.0.1:5000/ in your web browser to access the home page.
* Register a new user by clicking on the "Register" link.
* Login with the registered user on the "Login" page.
* Access the dashboard to manage users and devices.
## Folder Structure
* `templates/`: Contains HTML templates used by the Flask application.
* `app.py`: The main Flask application script.
* `devices.db`: SQLite database file.
## Dependencies
* Flask
* Flask-SQLAlchemy
* Werkzeug