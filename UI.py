import streamlit as st
import requests
from streamlit_lottie import st_lottie
from streamlit_option_menu import option_menu
import datetime
from google.oauth2 import service_account
from gsheetsdb import connect
from streamlit_option_menu import option_menu
import pandas as pd
import numpy as np
import hydralit_components as hc
import gspread
import pickle
import base64
from Function import *
from streamlit_extras.switch_page_button import switch_page


st.set_page_config(page_title="PatientRePro", layout="wide", initial_sidebar_state="collapsed")
st.markdown(""" <style> [data-testid="collapsedControl"] ... </style> """, unsafe_allow_html=True)


rf_model=pickle.load(open("best_model.pkl","rb"))

def load_lottieurl(url):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

#Animation
lottie_coding = load_lottieurl("https://lottie.host/562faaed-117a-4970-bbe4-6af071b287d7/JaKo9Vrsvk.json")

# Apply CSS style to add padding and move the button to the right
st.markdown(
    """
    <style>
    .custom-button {
        padding-left: 30px; /* Adjust the number of pixels to move the button to the right */
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Function to navigate to a new page
def navigate_to_new_page():
    st.write("This is the new page.")
    # Add content for the new page here

def main_page():
    st.title("Main Page")
    st.write("Welcome to the main page!")

# Header
def start_page():

    with st.container():
        st.markdown("<br><br>", unsafe_allow_html=True)
        left_column , right_column = st.columns(2)
        with left_column:
            st.markdown("<br><br><br><br>", unsafe_allow_html=True)
            st.title("&nbsp;&nbsp;Welcome to PatientRePro")
            st.markdown("<h style='color: #7895CB; font-size: 26px;'>&nbsp;&nbsp;&nbsp;&nbsp;Empowering Care with Insight</h>", unsafe_allow_html=True)
            st.markdown("""
                <style>
                    .stButton:last-child {
                        margin-left: 1em !important;
                    }
                </style>
            """, unsafe_allow_html=True)
            gs = st.button("Get started")
            
            if gs:
                switch_page("Details")
                
        with right_column:
            st_lottie(lottie_coding, height = 500, key = "coding")


def main():

    start_page()
    st.markdown("<br><br><br><br><br>", unsafe_allow_html=True)


if __name__ == '__main__':
    main()




