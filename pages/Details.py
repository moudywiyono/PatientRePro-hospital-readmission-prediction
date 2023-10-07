import streamlit as st
from streamlit_option_menu import option_menu
from Function import *
import base64
from streamlit_extras.colored_header import colored_header

st.set_page_config(layout="wide", initial_sidebar_state="collapsed")
st.markdown(""" <style> [data-testid="collapsedControl"] ... </style> """, unsafe_allow_html=True)

def image_to_base64(img_path):
    with open(img_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode('utf-8')

# Convert the image to base64
img_str = image_to_base64("public/img/new_logo.png")

st.markdown(
    f"""
    <div style="display: flex; align-items: center; justify-content: center; width: 100%;">
        <img src="data:image/png;base64,{img_str}" style="width:70px; height:70px;" />
        <h2 style="margin-left: 18px;">PatientRePro</h2>
    </div>
    """, 
    unsafe_allow_html=True
)

colored_header(
    label= " ",
    description="",
    color_name="light-blue-70",
)

selected = option_menu(
        menu_title=None,
        options=["Patient Details", "Add Patient", "Dashboard", "Report"],
        icons=["clipboard2-check-fill", "person-add", "bar-chart-line", "file-earmark-bar-graph"],
        orientation = "horizontal"
    )

if selected == "Patient Details":
     
    st.title(f"Patient Details")
    patient_page()
elif selected == "Add Patient":
    #st.title(f"Add Patient")
    add_patient()
elif selected == "Dashboard":
    st.title(f"Dashboard")
    
    viz()

elif selected == "Report":
    st.title(f"Report")

    @st.cache_resource()
    def run_query4(query):
        try:
            rows = conn.execute(query, headers=1)
            rows = rows.fetchall()
            return rows
        except Exception as e:
            print(f"Error executing query: {e}")
            return None

    sheet_url = st.secrets["patients_gsheets_url"]
    rows = run_query4(f'SELECT subject_id FROM "{sheet_url}"')
    if rows:
        subject_ids = [int(row[0]) for row in rows]

        # Create a selectbox for subject_ids
        selected_subject = st.selectbox("Select a Patient ID", subject_ids)
    else:
        st.error("No patient data found.")

    if selected_subject is not None:
        generate_report = st.button("Generate")
        if generate_report:
            get_patient_data(selected_subject)