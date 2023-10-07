import streamlit as st
from datetime import datetime
from google.oauth2 import service_account
from gsheetsdb import connect
from streamlit_option_menu import option_menu
import pandas as pd
import numpy as np
import hydralit_components as hc
import gspread
import base64
import hydralit_components as hc
import plotly.express as px
import joblib

def pre_processing(diagnosiscode_list,icu_counter,resp_counter,los,lab_list):
    diagnosis_variables = ["V5861", "486", "49121", "27651", "41400", "28529", "V4581", "4019","51881","72400","49390"]
    availability_list = [0] * len(diagnosis_variables)

    for i, value in enumerate(diagnosis_variables):
        if value in diagnosiscode_list:
            availability_list[i] = 1
    
    costcenter_icu=icu_counter/(icu_counter+resp_counter)
    costcenter_resp=resp_counter/(icu_counter+resp_counter)
    

    # normalization
    norm_los=(float(los)-8.775193798449612)/12.69734243237384

    availability_list.append(costcenter_icu)
    availability_list.append(costcenter_resp)
    availability_list.append(norm_los)

    # lab test

    # Convert all elements in fluid_category_flag_list to lowercase
    fluid_category_flag_list = [[element.lower() for element in sublist] for sublist in lab_list]

    # Initialize the dictionary with category keys and initial values of 0
    category_values = {
        "blood_blood gas_normal":0,
        "blood_hematology_normal": 0,
        "blood_hematology_abnormal": 0,
        "urine_chemistry_0": 0,
    }

    # Iterate through the fluid_category_flag_list
    for item in fluid_category_flag_list:
        fluid, category, flag = item

        # Generate the category key
        category_key = f"{fluid}_{category}_{flag}"

        # Check if the category key exists in the dictionary, and set it to 1 if found
        if category_key in category_values:
            category_values[category_key] = 1

    # Set values for categories that should be 1 if no matching combination was found
    category_values["urine_chemistry_0"] = 1  # Set to 1 if no matching urine/chemistry combination

    # Convert dictionary values to a list
    category_list = list(category_values.values())

    # final list
    final_list= availability_list + category_list

    return final_list

def prediction(input_data):
    rf_model = joblib.load("best_model.pkl")
    
    input_numpy_array=np.array(input_data)

    input_reshaped=input_numpy_array.reshape(1,-1)

    prediction = rf_model.predict(input_reshaped)

    return prediction[0]

# Create a connection object.
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
    ],
)
conn = connect(credentials=credentials)
client=gspread.authorize(credentials)

def add_patient():
    # Perform SQL query on the Google Sheet.
    # Uses st.cache_data to only rerun when the query changes or after 10 min.
    @st.cache_resource()
    def run_query(query):
        rows = conn.execute(query, headers=1)
        rows = rows.fetchall()
        return rows

    sheet_url = st.secrets["patients_gsheets_url"]

    rows = run_query(f'SELECT subject_id FROM "{sheet_url}"')
    subject_ids = [int(row[0]) for row in rows]


    # Add New Patient 
    st.title("Add New Patient")
    st.markdown("---")
    st.subheader("Personal Details")
    st.write("Please input the patient's complete personal details!")
    st.write("\n")



    #### PLACEHOLDER ####
    data = {'subject_id': subject_ids}
    df = pd.DataFrame(data)

    # Subject ID input
    # Determine the latest subject_id if the DataFrame is not empty
    if not df.empty:
        latest_id = df['subject_id'].max()
    else:
        # If the DataFrame is empty, start from a default value (e.g., 1000)
        latest_id = 1000

    # Create a new subject_id as +1 of the latest ID
    subject_id = latest_id + 1
    st.write("Subject id:", subject_id)

    # Input Full Name
    full_name= st.text_input("Full Name:")

    # Input gender
    gender = st.radio("Gender:", ["M", "F"])

    # date of birth
    # Set the minimum and maximum date values
    min_date = datetime(1900, 1, 1)
    max_date = datetime.now()

    # Create a date input with date range
    dob = st.date_input("Date of Birth:", min_value=min_date, max_value=max_date)

    dod=""
    # date of death
    death_applicable = st.checkbox("Is Date of Death Applicable?")

    if death_applicable:
        dod = st.date_input("Date of Death:")

    #Insurance
    insurance = st.radio("Insurance:", ["Medicare", "Private"])

    # Marital Status
    marital_status = st.selectbox("Marital Status:", ["Single", "Married", "Divorced", "Widowed"])

    # Ethnicity
    ethnicity = st.text_input("Ethnicity:")

    st.markdown("---")

    # take diagnosis
    diagnoses_sheet_url = st.secrets["diagnosis_url"]
    rows_diagnosis = run_query(f'SELECT icd9_code, long_title FROM "{diagnoses_sheet_url}"')
    diagnoses = [[row[0], row[1]] for row in rows_diagnosis]

    # take admission
    admission_sheet_url = st.secrets["admissions_gsheets_url"]
    rows_admissions = run_query(f'SELECT admission_id FROM "{admission_sheet_url}"')
    admission_ids = [int(row[0]) for row in rows_admissions]


    @st.cache_resource()
    def get_existing_admissions():
        return []

    @st.cache_resource()
    def get_dcode():
        return []

    st.subheader("Admission History")
    st.write("Please input all of the patient's admission history and details of the admissions.")
    st.write("\n")

    # Get existing admissions
    existing_admissions = get_existing_admissions()
    diagnosiscode_list=get_dcode()

    # admission id
    #### PLACEHOLDER ####
    data_admission = {'admission_id': admission_ids}
    df_admission = pd.DataFrame(data_admission)

    # Admission ID input
    # Determine the latest subject_id if the DataFrame is not empty
    if not df_admission.empty:
        latest_aid = df_admission['admission_id'].max()
    else:
        # If the DataFrame is empty, start from a default value (e.g., 1000)
        latest_aid = 100

    # Create a new subject_id as +1 of the latest ID
    # Initialize the counter in session state
    if 'admission_counter' not in st.session_state:
        st.session_state.admission_counter = latest_aid+1

    if 'icu_counter' not in st.session_state:
        st.session_state.icu_counter = 0

    if 'resp_counter' not in st.session_state:
        st.session_state.resp_counter = 0

    # Collect admission details
    min_date = datetime(1900, 1, 1)
    max_date = datetime.now()
    
    admission_time = st.date_input("Admission Date:", min_value=min_date, max_value=max_date)
    discharge_time = st.date_input("Discharge Date:", min_value=min_date, max_value=max_date)
    admission_type = st.radio("Admission Type", ["Emergency", "Elective"])
    admission_location = st.selectbox("Admission Location:", ["CLINIC REFERRAL/PREMATURE", "EMERGENCY ROOM ADMIT", "PHYS REFERRAL/NORMAL DELI", "TRANSFER FROM HOSP/ESTRAM", "TRANSFER FROM SKILLED NUR"])
    discharge_location = st.selectbox("Discharge Location:", ["DEAD/EXPIRED", "DISCH-TRAN TO PSYCH HOSP", "HOME", "HOME HEALTH CARE", "HOME WITH HOME IV PROVIDR", "HOSPICE-HOME", "ICF", "LONG TERM CARE HOSPITAL", "REHAB/DISTINCT PART HOSP", "SNF"])
    selected_diagnosis = st.selectbox("Diagnosis Code:", [f"{icd_code} {long_desc}" for icd_code, long_desc in diagnoses])
    icd_code, long_desc = selected_diagnosis.split(" ",1)
    cost_center = st.radio('Select Cost Center', ['ICU', 'Respiratory'])
    los=int((discharge_time - admission_time).days)
    add_admission_button = st.button("Add Admission")


    # Save admission details to the DataFrame when "Add Admission" button is clicked
    if add_admission_button:
    
        new_admission = {"Admission ID": st.session_state.admission_counter,
                        "Subject ID":subject_id,
                        "Admission Time": admission_time,
                        "Discharge Time": discharge_time,
                        "LOS":(discharge_time - admission_time).days,
                        "Admission Type": admission_type,
                        "Admission Location": admission_location,
                        "Discharge Location": discharge_location,
                        "Diagnosis Code": icd_code,
                        "Diagnosis Description": long_desc,
                        "Center": cost_center}
        existing_admissions.append(new_admission)
        diagnosiscode_list.append(new_admission["Diagnosis Code"])

        if(new_admission["Center"]=="Respiratory"):
            st.session_state.resp_counter += 1
        else:
            st.session_state.icu_counter += 1

        st.session_state.admission_counter += 1
        
        st.success("Admission details added successfully!")

    # Display the list of admissions
    if existing_admissions:
        
        df = pd.DataFrame(existing_admissions)
        st.dataframe(df)



    #get lab test
    lab_sheet_url = st.secrets["lab_events_url"]
    rows_lab = run_query(f'SELECT lab_id FROM "{lab_sheet_url}"')
    lab_ids = [int(row[0]) for row in rows_lab]

    @st.cache_resource()
    def get_existing_lab_events():
        return []

    @st.cache_resource()
    def get_labreq():
        return []

    # lab id

    # lab id
    #### PLACEHOLDER ####
    data_lab = {'lab_id': lab_ids}
    df_lab = pd.DataFrame(data_lab)

    # Lab ID input
    # Determine the latest lab_id if the DataFrame is not empty
    if not df_lab.empty:
        latest_lid = df_lab['lab_id'].max()
    else:
        # If the DataFrame is empty, start from a default value (e.g., 1000)
        latest_lid = 0



    # Get existing lab events
    existing_lab_events = get_existing_lab_events()
    labreq_list=get_labreq()

    # Define a dictionary mapping categories to their corresponding fluids
    category_to_fluid = {
        "Blood_Gas": ["Blood", "Other Bodily Fluid"],
        "Chemistry": ["Ascites", "Blood", "Cerebrospinal Fluid (CSF)", "Joint Fluid","Other Body Fluid","Pleural","Stool","Urine"],
        "Hematology": ["Ascites", "Blood", "Cerebrospinal Fluid (CSF)", "Joint Fluid","Other Body Fluid","Pleural","Stool","Urine"],
    }

    st.markdown("---")

    st.subheader("Lab History")
    st.write("Please input a complete lab testing history of the patient.")
    st.write("\n")


    col1, col2 = st.columns(2)

    with col1:
        category = st.selectbox("Category:", list(category_to_fluid.keys()))

    with col2:
        fluid = st.selectbox("Fluid:", category_to_fluid[category])
    label=st.text_input("Label:")
    flag = st.selectbox("Flag:", ["normal", "abnormal", "delta"])
    add_lab_event_button = st.button("Add Lab Event")

    # Initialize the counter in session state
    if 'lab_event_counter' not in st.session_state:
        st.session_state.lab_event_counter = latest_lid+1

    # Save lab event details to the DataFrame when "Add Lab Event" button is clicked
    if add_lab_event_button:
        new_lab_event = {
            "Lab Events ID": st.session_state.lab_event_counter,
            "Subject ID": subject_id,
            "Category": category,
            "Fluid": fluid,
            "Label": label,
            "Flag": flag,
        }
        existing_lab_events.append(new_lab_event)
        labreq_list.append([new_lab_event["Fluid"],new_lab_event["Category"],new_lab_event["Flag"]])
        st.session_state.lab_event_counter += 1
        st.success("Lab Event details added successfully!")

    # Display the list of lab events
    if existing_lab_events:
        df = pd.DataFrame(existing_lab_events)
        st.dataframe(df)


    st.write("\n")
    st.write("Add Patient into the database.")
    final_submit_button = st.button("Add Patient")



    st.text("Re-admission Risk for patient "+ str(subject_id)+" :")
    # Display the list of lab events
    if final_submit_button:
        

        # Predict

        the_result=pre_processing(diagnosiscode_list,st.session_state.icu_counter,st.session_state.resp_counter,los,labreq_list)
        
        pred_result=prediction(the_result)

        if(pred_result==0):
            st.text("Low")
        else:
            st.text("High")

        # Append patients
        
        open_patient = client.open_by_url(sheet_url).sheet1
        new_prow = [int(subject_id),full_name,str(dob),str(dod),gender,marital_status,ethnicity,insurance,pred_result]
    
        open_patient.append_row(new_prow)  
        
        # Append admissions

        admission_nested_list = [[d[key] for key in d.keys()] for d in existing_admissions]

        open_admission=client.open_by_url(sheet_url).worksheet('Admissions')

        for adm in admission_nested_list:
            adm1=[int(adm[0]),int(adm[1]),str(adm[2]), str(adm[3]), int(adm[4]),adm[5],adm[6],adm[7],str(adm[8]),adm[9],adm[10]]
            open_admission.append_row(adm1)
        
        # Append lab tests

        lab_nested_list = [[d[key] for key in d.keys()] for d in existing_lab_events]

        open_lab=client.open_by_url(sheet_url).worksheet('Lab Events')

        for lab in lab_nested_list:
            lab1=[int(lab[0]),int(lab[1]),lab[2], lab[3], lab[4],lab[5]]
            open_lab.append_row(lab1)
        
        st.cache_resource.clear()
        st.session_state.clear()
        st.success("Patients details added successfully!")


#Patient profile
def patient_profile(selected_subject):
    @st.cache_resource()
    def run_query1(query):
        try:
            rows = conn.execute(query, headers=1)
            rows = rows.fetchall()
            return rows
        except Exception as e:
            print(f"Error executing query: {e}")
            return None
    st.subheader("Patient Profile")
    sheet_url = st.secrets["patients_gsheets_url"]
    
    # Retrieve and display the full_name for the selected subject_id
    rows_name = run_query1(f'SELECT full_name FROM "{sheet_url}" WHERE subject_id = {selected_subject}')
    if len(rows_name) > 0:
        full_name = rows_name[0][0]
        st.write("Full Name:", full_name)
    
    rows_gender = run_query1(f'SELECT gender FROM "{sheet_url}" WHERE subject_id = {selected_subject}')
    if len(rows_gender) > 0:
        gender = rows_gender[0][0]
        if gender == 'F':
            st.write("Gender: Female")
        else:
            st.write("Gender: Male")

    rows_dob = run_query1(f'SELECT dob FROM "{sheet_url}" WHERE subject_id = {selected_subject}')
    if rows_dob is not None:
        if len(rows_dob) > 0:
            dob = rows_dob[0][0]

            # Convert datetime.date object to a string and remove single quotation marks
            dob_str = str(dob).strip("'")

            # Format the date of birth
            dob_datetime = datetime.strptime(dob_str, "%Y-%m-%d")
            formatted_dob = dob_datetime.strftime("%B %d, %Y")

            st.write("Date of Birth:", formatted_dob)
        else:
            st.write("No date of birth information available for the specified subject.")
    else:
        st.write("Error: Unable to retrieve date of birth information for the specified subject.")

    rows_dod = run_query1(f'SELECT dod FROM "{sheet_url}" WHERE subject_id = {selected_subject}')
    if rows_dod is not None:
        if len(rows_dod) > 0:
            dod = rows_dod[0][0]
            if dod is not None:
                # Convert datetime.date object to a string
                dod_str = str(dod).strip("'")

                # Format the date of death
                dod_datetime = datetime.datetime.strptime(dod_str, "%Y-%m-%d")
                formatted_dod = dod_datetime.strftime("%B %d, %Y")

                st.write("Date of Death:", formatted_dod)
            else:
                st.success("Status: Alive")
        else:
            st.success("Status: Error")
    else:
        st.success("Status: Alive")

    rows_insurance = run_query1(f'SELECT insurance FROM "{sheet_url}" WHERE subject_id = {selected_subject}')
    if len(rows_insurance) > 0:
        insurance = rows_insurance[0][0] 
        st.write("Type of Insurance:", insurance)

    rows_marital_status = run_query1(f'SELECT marital_status FROM "{sheet_url}" WHERE subject_id = {selected_subject}')
    if len(rows_marital_status) > 0:
        marital_status = rows_marital_status[0][0] 
        st.write("Marital Status:", marital_status)

    rows_ethnicity = run_query1(f'SELECT ethnicity FROM "{sheet_url}" WHERE subject_id = {selected_subject}')
    if len(rows_ethnicity) > 0:
        ethnicity = rows_ethnicity[0][0] 
        st.write("Ethnicity:", ethnicity)

#Patient History (admission, diagnosis, labtests)
def patient_history(selected_subject):
    st.subheader("Patient History")

    @st.cache_data()
    def run_query3(query):
        try:
            rows = conn.execute(query, headers=1)
            rows = rows.fetchall()
            # Convert rows to a serializable format (e.g., list of tuples)
            serializable_data = [(row[0],) for row in rows]
            return serializable_data
        except Exception as e:
            print(f"Error executing query: {e}")
            return None
    
    admission_sheet_url = st.secrets["admissions_gsheets_url"]
    diagnosis_sheet_url = st.secrets["diagnosis_url"]
    sheet_url = st.secrets["patients_gsheets_url"]
    labtests_sheet_url = st.secrets["lab_events_url"]
    
    def show_admission_history(admission_id):
        st.markdown("---")

        st.success("Patient Admission History")
        row_admission_date = run_query3(f'SELECT admission_date FROM "{admission_sheet_url}" WHERE subject_id = {selected_subject} AND admission_id = {admission_id}')
        if len(row_admission_date) > 0:
            admission_date = row_admission_date[0][0]
            st.write("Admission Date:", admission_date)

        row_discharged_date = run_query3(f'SELECT discharge_date FROM "{admission_sheet_url}" WHERE subject_id = {selected_subject} AND admission_id = {admission_id}')
        if len(row_discharged_date) > 0:
            discharged_date = row_discharged_date[0][0]
            st.write("Discharged Date:", discharged_date)

        row_los = run_query3(f'SELECT los FROM "{admission_sheet_url}" WHERE subject_id = {selected_subject} AND admission_id = {admission_id}')
        if len(row_los) > 0:
            los = int(row_los[0][0])
            st.write("Length of Stay:", los)

        row_admission_type = run_query3(f'SELECT admission_type FROM "{admission_sheet_url}" WHERE subject_id = {selected_subject} AND admission_id = {admission_id}')
        if len(row_admission_type) > 0:
            admission_type = row_admission_type[0][0]
            st.write("Admission Type:", admission_type)

        row_admission_location = run_query3(f'SELECT admission_location FROM "{admission_sheet_url}" WHERE subject_id = {selected_subject} AND admission_id = {admission_id}')
        if len(row_admission_location) > 0:
            admission_location = row_admission_location[0][0]
            st.write("Admission Location:", admission_location)

        row_discharged_location = run_query3(f'SELECT discharge_location FROM "{admission_sheet_url}" WHERE subject_id = {selected_subject} AND admission_id = {admission_id}')
        if len(row_discharged_location) > 0:
            discharged_location = row_discharged_location[0][0]
            st.write("Discharged Location:", discharged_location)
        
        row_center = run_query3(f'SELECT center FROM "{admission_sheet_url}" WHERE subject_id = {selected_subject} AND admission_id = {admission_id}')
        if len(row_center) > 0:
            center = row_center[0][0]
            st.write("Location Center:", center)
            
        rows_diagnoses = run_query3(f'SELECT long_title FROM "{admission_sheet_url}" WHERE subject_id = {selected_subject} AND admission_id = {admission_id}')
        if len(rows_diagnoses) > 0:
            diagnoses = rows_diagnoses[0][0] 
            rows_name = run_query3(f'SELECT full_name FROM "{sheet_url}" WHERE subject_id = {selected_subject}')
            if len(rows_name) > 0:
                full_name = rows_name[0][0]
            # Create a styled frame around the diagnoses text
            st.write("Patient", full_name, "had been diagnosed with:\n")

            # Create a styled frame around the diagnoses text with a background color
            highlighted_diagnoses = f'<div style="border: 2px solid #000; padding: 10px; border-radius: 5px; background-color: lightblue;">{diagnoses}</div>'
            
            st.markdown(highlighted_diagnoses, unsafe_allow_html=True)

    def show_lab_events_history():
        st.markdown("---")
        st.success("Patient Lab History")
        row_category = run_query3(f'SELECT category FROM "{labtests_sheet_url}" WHERE subject_id = {selected_subject} AND lab_id = {selected_lab_id}')
        if len(row_category) > 0:
            category = row_category[0][0]
            st.write("Lab Category:", category)

        row_fluid = run_query3(f'SELECT fluid FROM "{labtests_sheet_url}" WHERE subject_id = {selected_subject} AND lab_id = {selected_lab_id}')
        if len(row_fluid) > 0:
            fluid = row_fluid[0][0]
            st.write("Fluid:", fluid)
        
        row_label = run_query3(f'SELECT label FROM "{labtests_sheet_url}" WHERE subject_id = {selected_subject} AND lab_id = {selected_lab_id}')
        if len(row_label) > 0:
            label = row_label[0][0]
            st.write("Label:", label)

        row_flag = run_query3(f'SELECT flag FROM "{labtests_sheet_url}" WHERE subject_id = {selected_subject} AND lab_id = {selected_lab_id}')
        if len(row_flag) > 0:
            flag = row_flag[0][0]
            st.write("Lab Status:", flag)


    
    options_history = st.radio(
    "Select an option:",
    ('Patient Admission History', 'Patient Lab History'),
    horizontal=True)

    if options_history == "Patient Admission History":
        row_admission_id = run_query3(f'SELECT admission_id FROM "{admission_sheet_url}" WHERE subject_id = {selected_subject}')
        if len(row_admission_id) > 0:
            admission_ids = [int(row[0]) for row in row_admission_id]

            # Create a selectbox for Admission IDs
            selected_admission_id = st.selectbox("Patient's Admissions:", admission_ids)

            if selected_admission_id:
                # Add a button to show the history for the selected Admission ID
                if st.button("Show Admission History"):
                    show_admission_history(selected_admission_id)

        else: 
            st.error("No Patient Record Found!")
    elif options_history == "Patient Lab History":
        # Add a button to show the lab history
        lab_ids = run_query3(f'SELECT lab_id FROM "{labtests_sheet_url}" WHERE subject_id = {selected_subject}')
        if len(lab_ids) > 0:
            lab_id = [int(row[0]) for row in lab_ids]  # Convert to integer
            
            # Create a selectbox for lab IDs
            selected_lab_id = st.selectbox("Select Lab ID:", lab_id)
            
            if selected_lab_id:
                if st.button("Show Lab History"):
                    show_lab_events_history()
        
        else: 
            st.error("No Patient Record Found!")

#Patient page
def patient_page():
    @st.cache_resource()
    def run_query2(query):
        try:
            rows = conn.execute(query, headers=1)
            rows = rows.fetchall()
            return rows
        except Exception as e:
            print(f"Error executing query: {e}")
            return None
    
    st.markdown("---")

    # Dictionary to store the checkbox state for each subject ID
    checkbox_states = {}    

    # Perform actions based on the selected radio button
    sheet_url = st.secrets["patients_gsheets_url"]
    rows = run_query2(f'SELECT subject_id, full_name FROM "{sheet_url}"')
    subject_ids = [int(row[0]) for row in rows]
    full_names = [row[1] for row in rows]

    # Create a selectbox for subject_ids
    selected_subject_name = st.selectbox("Select a Patient:", range(len(rows)), format_func=lambda i: f"{subject_ids[i]} - {full_names[i]}")

    # You can access the selected subject_id and full_name like this:
    selected_subject = subject_ids[selected_subject_name]
    selected_full_name = full_names[selected_subject_name]


    # Display the selected subject ID
    st.write("Selected Patient ID:", selected_subject)

    # Get the checkbox state for the selected subject ID
    checkbox_state = checkbox_states.get(selected_subject, False)

    # Add a checkbox to toggle the result visibility
    show_result = st.checkbox("Show Result", key=f"checkbox_{selected_subject}", value=checkbox_state)

    # Store the checkbox state for the selected subject ID
    checkbox_states[selected_subject] = show_result

    # Add a conditional statement based on the selected subject ID
    if selected_subject is not None:
        if show_result:
            st.markdown("---")
            # Menu for navigate
            st.markdown('<div class="option-menu-container">', unsafe_allow_html=True)
            selected = option_menu(
                menu_title=None,
                options=["Patient Profile", "Patient History"],
                icons=['person', 'clipboard-data'],
                menu_icon="cast",
                default_index=0,
                orientation="horizontal",
                key="menu"
            )
            st.markdown('</div>', unsafe_allow_html=True)

            if selected == "Patient Profile":
                patient_profile(selected_subject)
            if selected == "Patient History":
                patient_history(selected_subject)

def get_patient_data(selected_subject):
    st.markdown("---")
    @st.cache_resource()
    def run_query4(query):
        try:
            rows = conn.execute(query, headers=1)
            rows = rows.fetchall()
            return rows
        except Exception as e:
            print(f"Error executing query: {e}")
            return None
    
    # Retrieve patient information based on the selected subject ID
    sheet_url = st.secrets["patients_gsheets_url"]
    admissions_url = st.secrets["admissions_gsheets_url"]
    lab_url = st.secrets["lab_events_url"]

    rows = run_query4(f'SELECT * FROM "{sheet_url}" WHERE subject_id = {selected_subject}')
    rows2 = run_query4(f'SELECT * FROM "{admissions_url}" WHERE subject_id = {selected_subject}')
    rows3 = run_query4(f'SELECT * FROM "{lab_url}" WHERE subject_id = {selected_subject}')
    
    if len(rows) > 0:
        patient_data = {
            'subject_id': rows[0][0],
            'full_name': rows[0][1],
            'gender': 'Female' if rows[0][4] == 'F' else 'Male',
            'dob': str(rows[0][2]),
            'dod': str(rows[0][3]) if rows[0][3] else 'Not Applicable',
            'insurance': rows[0][7],
            'marital_status': rows[0][5],
            'ethnicity': rows[0][6],
            'readmission_risk': rows[0][8]
        }

    if len(rows2) > 0:
        patient_data_admission = {
            'admission_id': rows2[0][0],
            'admission_date': rows2[0][2],
            'discharge_date': rows2[0][3],
            'los': rows2[0][4],
            'admission_type': rows2[0][5],
            'admission_location': rows2[0][6],
            'discharge_location': rows2[0][7],
            'icd9_code': rows2[0][8],
            'long_title': rows2[0][9],
            'center': rows2[0][10]
        }
    
    else:
        patient_data_admission = {}  # Create an empty dictionary if no admission data


    if len(rows3) > 0:
        patient_data_lab = { 
            'lab_id': rows3[0][0],
            'category': rows3[0][2],
            'fluid': rows3[0][3],
            'label': rows3[0][4],
            'flag': rows3[0][5]
        }
    
    else:
        patient_data_lab = {}  # Create an empty dictionary if no lab data


    st.title("Patient Report")
    st.markdown("---")
    # Center the patient report using layout options
    col1, col2 = st.columns(2)  # Split the page into two columns
    with col1:
        # Display patient information
        st.subheader("\nPatient Profile Report")
        st.write("Full Name:", patient_data['full_name'])
        st.write("Gender:", patient_data['gender'])
        st.write("Date of Birth:", patient_data['dob'])
        st.write("Date of Death:", patient_data['dod'])
        st.write("Insurance:", patient_data['insurance'])
        st.write("Marital Status:", patient_data['marital_status'])
        st.write("Ethnicity:", patient_data['ethnicity'])
        if(patient_data['readmission_risk']==0):
            st.success("Prediction Result of patient being readmit is LOW")
        else:
            st.error("Prediction Result of patient being readmit is HIGH")
        

    with col2:
        # Display patient information
        st.subheader("\nPatient Admission")
        if patient_data_admission:
            st.write("Admission ID:", patient_data_admission['admission_id'])
            st.write("Admission Date:", patient_data_admission['admission_date'])
            st.write("Discharge Date:", patient_data_admission['discharge_date'])
            st.write("Length of Stay:", patient_data_admission['los'])
            st.write("Admission Type:", patient_data_admission['admission_type'])
            st.write("Admission Location:", patient_data_admission['admission_location'])
            st.write("Discharge Location:", patient_data_admission['discharge_location'])
            st.write("ICD9 Code:", patient_data_admission['icd9_code'])
            st.write("Diagnoses:", patient_data_admission['long_title'])
            st.write("Location Center:", patient_data_admission['center'])
        else:
            st.warning("No Admission Data available for this patient.")
        
        st.markdown("---")
        st.subheader("\nPatient Lab Report")
        if patient_data_lab:
            st.write("Lab ID:", patient_data_lab['lab_id'])
            st.write("Lab Category:", patient_data_lab['category'])
            st.write("Fluid:", patient_data_lab['fluid'])
            st.write("Label:", patient_data_lab['label'])
            st.write("Lab Result:", patient_data_lab['flag'])
        else:
            st.warning("No Lab Data available for this patient.")
        
        
        # Create a download button to download the report as a CSV file
        report_data = {
            'Patient Information': patient_data,
            'Patient Admission': patient_data_admission,
            'Patient Lab Report': patient_data_lab
        }

        # Convert the dictionary into a DataFrame
        report_df = pd.DataFrame(report_data)

        if st.download_button("Download Report", data=report_df.to_csv(index=False), 
                                file_name=f"patient_report_{selected_subject}.csv", 
                                key="download_report"):
            st.success(f"Report downloaded successfully as 'patient_report_{selected_subject}.csv'")

def image_to_base64(img_path):
    with open(img_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode('utf-8')
    
#Dashboard

def viz():
    # Create a connection object.
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
        ],
    )
    conn = connect(credentials=credentials)
    client=gspread.authorize(credentials)

    # Create a container with a grey background    
        
    @st.cache_resource()
    def run_query(query):
        try:
            rows = conn.execute(query, headers=1)
            rows = rows.fetchall()
            return rows
        except Exception as e:
            print(f"Error executing query: {e}")
            return None

    # Retrieve patient information based on the selected subject ID
    sheet_url = st.secrets["patients_gsheets_url"]
    admission_sheet_url = st.secrets["admissions_gsheets_url"]
    lab_sheet_url = st.secrets["lab_events_url"]

    rows= run_query(f'SELECT * FROM "{sheet_url}"')
    admission_rows= run_query(f'SELECT * FROM "{admission_sheet_url}"')
    lab_rows=run_query(f'SELECT * FROM "{lab_sheet_url}"')
    # Define column names
    columns = ["ID", "Name", "Birthdate", "DateOfDeath", "Gender", "MaritalStatus", "Ethnicity", "Insurance", "Flag"]

    # Create a DataFrame
    df_profile = pd.DataFrame(rows, columns=columns)
    df_admission=pd.DataFrame(admission_rows)
    df_labs=pd.DataFrame(lab_rows)

    st.markdown("## Patient List")

    # Create a dictionary to map values to labels
    flag_labels = {1: "High Risk", 0: "Low Risk", -1: "No Filter"}

    # Create a radio button for choosing High Risk, Low Risk, or No Filter
    selected_flag = st.radio("Select patient risk levels you want to view:", [-1, 1, 0], format_func=lambda x: flag_labels[x])

    # Apply the filter or turn it off based on the selected flag
    filtered_df=df_profile

    if selected_flag != -1:
        filtered_df = df_profile[df_profile['Flag'] == selected_flag]

    filtered_df['ID'] = filtered_df['ID'].astype(str).str.replace(',', '').astype(int)

    # Display the filtered DataFrame
    st.write(filtered_df)


    filtered_subjectid=filtered_df["ID"].tolist()

    filtered_admission=df_admission[df_admission["subject_id"].isin(filtered_subjectid)]
    filtered_lab=df_labs[df_labs["subject_id"].isin(filtered_subjectid)]


    st.markdown("-----")
    st.markdown("## Dashboard")

    st.markdown("### Demographic Analytics")
    container=st.container()


    # Group the DataFrame by 'country' and count the number of rows in each category
    gender_counts = filtered_df['Gender'].value_counts().reset_index()
    gender_counts.columns = ['Gender', 'count']

    ethnicity_counts = filtered_df['Ethnicity'].value_counts().reset_index()
    ethnicity_counts.columns = ['Ethnicity', 'count']
    # Create a pie chart using the 'count' column as values


        
    with container:
        col1, col2 = st.columns(2)
        with col1:
            # Gender
            fig_gender = px.pie(gender_counts, values='count', names='Gender', title='Gender')
            fig_gender.update_layout(
                height=450,  # You can adjust the size as needed
                width=400,   # Set both height and width to the same value to make it square
            )
            fig_gender.update_layout(legend=dict(orientation="h", y=0, x=0))
            st.write(fig_gender)
        with col2:
            # Ethnicity
            fig_ethnicity=px.bar(ethnicity_counts, x="count", y="Ethnicity", orientation='h',color='Ethnicity',title='Ethnicity')
            st.write(fig_ethnicity)
        # Age
        filtered_df['Birthdate'] = filtered_df['Birthdate'].str.replace("'", '')
        filtered_df['Birthdate'] = pd.to_datetime(filtered_df['Birthdate'])
        filtered_df['Birthdate'] = filtered_df['Birthdate'].dt.date
        current_date=datetime.datetime.now().date()
        filtered_df['Age'] = ((current_date - filtered_df['Birthdate']) / pd.Timedelta(days=365.25)).astype(int)
        # Define age groups (adjust as needed)
        age_bins = [0, 20, 30, 40, 50, 60, float('inf')]
        age_labels = ['0-20', '21-30', '31-40', '41-50', '51-60', '61+']
        # Create age groups and count the number of occurrences in each group
        filtered_df['AgeGroup'] = pd.cut(filtered_df['Age'], bins=age_bins, labels=age_labels)
        # Count the occurrences of each age group
        age_counts = filtered_df['AgeGroup'].value_counts().reset_index()
        age_counts.columns = ['AgeGroup', 'Count']
        # Create a bar chart using Plotly Express
        fig_age = px.bar(age_counts, x='AgeGroup', y='Count', color='AgeGroup',
                    labels={'AgeGroup': 'Age Group', 'Count': 'Count'},
                    title='Age Distribution',
                    category_orders={"AgeGroup": age_labels})
        st.write(fig_age)



    average_length_of_stay = filtered_admission['los'].mean()
    max_length_of_stay = filtered_admission['los'].max()
    # Define the CSS style for alignment
    style = """
    <style>
        .highlight-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            margin-bottom: 50px;
        }
        .caption {
            font-size: 20px;
            color: white;
            margin-top: 25px;
            /* Adjust the margin to make the gap closer */
        }
        .value {
            font-size: 80px;
            font-weight: bold;
            /* Make the value bold */
        }
    </style>
    """
    st.markdown("---")
            
    # Display the highlighted text with caption and value
    st.markdown("### Admission Analytics")
    container2=st.container()

    st.markdown(style, unsafe_allow_html=True)

    with container2:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"<div class='highlight-container'><div class='caption'>Average Length of Stay</div><div class='value'>{average_length_of_stay}</div></div>", unsafe_allow_html=True)
            st.markdown(f"<div class='highlight-container'><div class='caption'>Max Length of Stay</div><div class='value'>{max_length_of_stay}</div></div>", unsafe_allow_html=True)

            # Calculate the counts based on the number of rows for each admission type
            admission_type_counts = filtered_admission['admission_type'].value_counts().reset_index()
            admission_type_counts.columns = ['admission_type', 'Count']

            # Create a pie chart for Admission Type
            fig_admission_type = px.pie(admission_type_counts, values='Count', names='admission_type', title='Admission Type')
            fig_admission_type.update_layout(legend=dict(orientation="h", y=0, x=0))

            fig_admission_type.update_layout(
                height=450, 
                width=400,  
            )
            st.write(fig_admission_type)

        with col2:
            # Group by "Diagnosis" and calculate the average length of stay for each diagnosis
            diagnosis_average_length_of_stay = filtered_admission.groupby('long_title')['los'].mean().reset_index()
            
            max_label_width = 20  # Characters
            diagnosis_average_length_of_stay['truncated_title'] = diagnosis_average_length_of_stay['long_title'].apply(lambda x: x[:max_label_width] + ('...' if len(x) > max_label_width else ''))

            # Create a bar chart using Plotly Express
            fig_diag = px.bar(diagnosis_average_length_of_stay, y='truncated_title', x='los', orientation="h",
                labels={'truncated_title': 'Diagnosis', 'los': 'Average Length of Stay'},
                title='Average Length of Stay by Diagnosis',
                color="truncated_title")

            # Display the bar chart
            st.write(fig_diag)


            # Calculate the counts based on the number of rows for each admission type
            center_type_counts = filtered_admission['center'].value_counts().reset_index()
            center_type_counts.columns = ['center', 'Count']

            # Create a pie chart for Admission Type
            fig_center_type = px.pie(center_type_counts, values='Count', names='center', title='Center Type')
            fig_center_type.update_layout(legend=dict(orientation="h", y=0, x=0))

            # Update the layout to add margin to the right
            fig_center_type.update_layout(
                legend=dict(orientation="h", y=0, x=0),
                height=450,  
                margin=dict(l=100)
            )

            st.write(fig_center_type)

    st.markdown("### Lab Analytics")

    # Create a filter for Category
    selected_category = st.selectbox("Select a Category", filtered_lab['category'].unique())

    # Filter data by category
    filtered_data = filtered_lab[filtered_lab['category'] == selected_category]

    # Create a grouped bar chart
    lab_fig = px.bar(
        filtered_data,
        x='flag',
        y='fluid',
        color='flag',
        barmode='group',
        title=f'Lab Test Flags for Category: {selected_category}'
    )

    st.write(lab_fig)
