# House Price Prediction System

A modern Python desktop application for predicting house prices based on area, rooms, bathrooms, floors, age, plot type, and Dehradun city/location market rates.

## Features

- User login and signup system
- Forgot password and profile update options
- House price prediction using market-rate logic and ML model support
- Residential and Industrial plot type prediction
- City-wise price rate table for Dehradun locations
- Prediction history for each user
- Search and filter history by city, plot type, and price range
- Graphical price analysis using Matplotlib
- Save property prediction reports
- Light and dark mode support
- Custom dashboard and login artwork
- PyInstaller spec file included for building an executable

### Login / Dashboard Artwork
![Login Art](login_property_art.png)

### Dashboard Preview
![Dashboard](dashboard_auto.png)

## Tech Stack

- Python
- CustomTkinter
- Tkinter
- Matplotlib
- Pillow
- Pickle
- PyInstaller

## Project Files

```text
main.py                 Main application file
main.spec               PyInstaller build configuration
model.pkl               Trained/serialized ML model
model_ml.pkl            Lightweight ML model data
dashboard_auto.png      Dashboard image asset
login_property_art.png  Login screen image asset

Installation
Clone the repository:
git clone https://github.com/your-username/House-Price-Prediction-System.git
cd House-Price-Prediction-System
Install required packages:
pip install customtkinter matplotlib pillow
If your model.pkl depends on scikit-learn, also install:
pip install scikit-learn
Run the application:
python main.py
Build Executable
To build a Windows executable using PyInstaller:
pip install pyinstaller
pyinstaller main.spec
The executable will be created inside the dist folder.

Important Note
This project stores users and prediction history locally using text files. Do not upload private user data such as users.txt, generated history files, or generated reports to a public repository.


Author
Created by Aditya.


**Recommended `.gitignore`**
```gitignore
__pycache__/
*.pyc
dist/
build/
*.spec.bak

users.txt
history.txt
history_*.txt
reports_*/
*.log

.env
.venv/
venv/
Files You Should Upload
Upload these:

main.py
main.spec
model.pkl
model_ml.pkl
dashboard_auto.png
login_property_art.png
README.md
.gitignore
Avoid uploading these publicly:

users.txt
history.txt
history_*.txt
reports_*
model.pkl.txt
GitHub About Section
Description:
Python desktop app for house price prediction with login, city-wise market rates, ML model support, graphs, history, and reports.

Topics:
python customtkinter machine-learning real-estate matplotlib desktop-application house-price-prediction
