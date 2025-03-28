import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import calendar
from collections import defaultdict

# Set page configuration
st.set_page_config(
    page_title="#shine-little-star",
    page_icon="⭐",
    layout="wide"
)

# Function to connect to Google Sheets
@st.cache_resource
def connect_to_sheets():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    
    # Use Streamlit secrets for deployment
    if 'gcp_service_account' in st.secrets:
        credentials_dict = st.secrets["gcp_service_account"]
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
    else:
        # Fallback to local file for development
        credentials = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    
    client = gspread.authorize(credentials)
    return client

# Function to get feedback data from Google Sheets
@st.cache_data(ttl=300)
def get_feedback_data(sheet_url):
    client = connect_to_sheets()
    spreadsheet = client.open_by_url(sheet_url)
    sheet = spreadsheet.get_worksheet(1)  # Feedback sheet (index 1)
    data = sheet.get_all_values()
    headers = ['Time', 'receiver', 'stars', 'message', 'sender', 'timestamp']
    df = pd.DataFrame(data, columns=headers)
    
    # Convert timestamp to datetime
    df['timestamp'] = pd.to_numeric(df['timestamp'], errors='coerce')
    df['date'] = pd.to_datetime(df['timestamp'], unit='s')
    df['month'] = df['date'].dt.month
    df['year'] = df['date'].dt.year
    
    # Convert stars to numeric
    df['stars'] = pd.to_numeric(df['stars'], errors='coerce')
    
    return df

# Function to get quotas data from Google Sheets
@st.cache_data(ttl=300)
def get_quotas_data(sheet_url):
    client = connect_to_sheets()
    spreadsheet = client.open_by_url(sheet_url)
    sheet = spreadsheet.get_worksheet(2)  # Quotas sheet (index 2)
    data = sheet.get_all_values()
    headers = ['id', 'user', 'available_stars', 'last_update']
    df = pd.DataFrame(data, columns=headers)
    
    # Convert available_stars to numeric
    df['available_stars'] = pd.to_numeric(df['available_stars'], errors='coerce')
    df = df[df['available_stars'].notna()]
    return df

# Function to get slack data from Google Sheets
@st.cache_data(ttl=300)
def get_slack_data(sheet_url):
    client = connect_to_sheets()
    spreadsheet = client.open_by_url(sheet_url)
    sheet = spreadsheet.get_worksheet(3)  # Slack sheet (index 3)
    data = sheet.get_all_values()
    headers = ['update_date', 'total_users']
    df = pd.DataFrame(data, columns=headers)
    
    # Convert total_users to numeric
    df['total_users'] = pd.to_numeric(df['total_users'], errors='coerce')
    df = df[df['total_users'].notna()]
    
    return df

# Title and description
st.title("#shine-little-star ⭐")

# Add last updated timestamp in the upper right
col1, col2 = st.columns([6, 2])
with col1:
    st.markdown("Confira o envio de suas Estrelas do canal #shine-little-star.")
with col2:
    current_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    st.markdown(f"<div style='text-align: right; color: gray; font-size: 0.8em;'>Última atualização:<br>{current_time}</div>", unsafe_allow_html=True)

# Sidebar for inputs
with st.sidebar:
    st.header("Filtros")
    sheet_url = st.text_input("URL da planilha do Google Sheets", 
                             "https://docs.google.com/spreadsheets/d/1s75mY_hLlcsv0EVvyKFb7-DbXqPOdyw0mzcQ8L06f8Y/edit")
    
    slack_name = st.text_input("Nome no Slack", placeholder="seu_nome_no_slack")
    
    # Get current year and month
    current_year = datetime.now().year
    current_month = datetime.now().month
    
    # Create month and year selection
    months = {i: calendar.month_name[i] for i in range(1, 13)}
    selected_month = st.selectbox("Mês", options=list(months.keys()), 
                                 format_func=lambda x: months[x], index=current_month-1)
    
    years = list(range(2020, current_year + 1))
    selected_year = st.selectbox("Ano", options=years, index=len(years)-1)
    
    if st.button("Buscar"):
        if not sheet_url or "your-sheet-id" in sheet_url:
            st.error("Por favor, insira uma URL válida da planilha.")
        else:
            st.success("Dados carregados com sucesso!")

# Main content
try:
    if "your-sheet-id" not in sheet_url:
        # Get data from all sheets
        with st.spinner("Carregando dados..."):
            feedback_df = get_feedback_data(sheet_url)
            quotas_df = get_quotas_data(sheet_url)
            slack_df = get_slack_data(sheet_url)

        # Filter feedback data by month and year
        filtered_df = feedback_df[(feedback_df['month'] == selected_month) & (feedback_df['year'] == selected_year)]

        if filtered_df.empty:
            st.warning(f"Não há dados para {months[selected_month]} de {selected_year}")
        else:
            # Get total users from slack data
            total_users_count = int(slack_df['total_users'].iloc[0]) if not slack_df.empty else 0
            
            # Get unique users who have sent stars
            active_senders = filtered_df['sender'].unique()
            active_senders_count = len(active_senders)
            
            # Get unique users who have received stars
            active_receivers = filtered_df['receiver'].unique()
            
            # Combine all unique users from feedback and quotas
            all_users_in_system = sorted(list(set(filtered_df['receiver'].unique()) | 
                                         set(filtered_df['sender'].unique()) | 
                                         set(quotas_df['user'].unique())))
            
            # Create summary dataframe
            summary_data = []
            for user in all_users_in_system:
                stars_sent = filtered_df[filtered_df['sender'] == user]['stars'].sum()
                stars_received = filtered_df[filtered_df['receiver'] == user]['stars'].sum()
                
                # Get available stars from quotas
                user_quota = quotas_df[quotas_df['user'] == user]
                available_stars = user_quota['available_stars'].values[0] if not user_quota.empty else 50
                
                summary_data.append({
                    'Pessoa': user,
                    'Estrelas Recebidas': int(stars_received) if not pd.isna(stars_received) else 0,
                    'Estrelas Enviadas': int(stars_sent) if not pd.isna(stars_sent) else 0,
                    'Estrelas Disponíveis': int(available_stars) if not pd.isna(available_stars) else 50
                })
            
            summary_df = pd.DataFrame(summary_data)
            summary_df = summary_df.sort_values('Pessoa')
            
            # Highlight user's row if slack_name is provided
            if slack_name:
                user_name = slack_name
                
            # Display main metrics
            col1, col2 = st.columns([3, 2])
            
            with col1:
                st.subheader("Resumo de Estrelas")
                
                # Highlight user's row if slack_name is provided
                if slack_name:
                    st.dataframe(
                        summary_df.style.apply(
                            lambda x: ['background-color: rgba(255, 215, 0, 0.2)' if x['Pessoa'] == user_name else '' for i in x],
                            axis=1
                        ),
                        use_container_width=True, 
                        height=400
                    )
                else:
                    st.dataframe(summary_df, use_container_width=True, height=400)
            
            with col2:
                # Calculate metrics for charts based on new data structure
                total_stars_sent = filtered_df['stars'].sum()
                
                # Calculate total available stars across all users (50 stars per user)
                total_possible_stars = total_users_count * 50
                
                # Chart 1: Participation Rate (Senders)
                st.subheader("Taxa de Participação")
                participation_rate = (active_senders_count / total_users_count) * 100 if total_users_count > 0 else 0
                
                fig1 = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=participation_rate,
                    title={'text': "Pessoas que enviaram estrelas (%)"},
                    domain={'x': [0, 1], 'y': [0, 1]},
                    gauge={
                        'axis': {'range': [0, 100]},
                        'bar': {'color': "#1f77b4"},
                        'steps': [
                            {'range': [0, 33], 'color': "lightgray"},
                            {'range': [33, 66], 'color': "gray"},
                            {'range': [66, 100], 'color': "darkgray"}
                        ],
                        'threshold': {
                            'line': {'color': "red", 'width': 4},
                            'thickness': 0.75,
                            'value': 100
                        }
                    }
                ))
                
                fig1.update_layout(height=250)
                st.plotly_chart(fig1, use_container_width=True)
                
                # Chart 2: Stars Usage Rate
                st.subheader("Utilização de Estrelas")
                stars_usage_rate = (total_stars_sent / total_possible_stars) * 100 if total_possible_stars > 0 else 0
                
                fig2 = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=stars_usage_rate,
                    title={'text': "Estrelas utilizadas (%)"},
                    domain={'x': [0, 1], 'y': [0, 1]},
                    gauge={
                        'axis': {'range': [0, 100]},
                        'bar': {'color': "#ff7f0e"},
                        'steps': [
                            {'range': [0, 33], 'color': "lightgray"},
                            {'range': [33, 66], 'color': "gray"},
                            {'range': [66, 100], 'color': "darkgray"}
                        ],
                        'threshold': {
                            'line': {'color': "red", 'width': 4},
                            'thickness': 0.75,
                            'value': 100
                        }
                    }
                ))
                
                fig2.update_layout(height=250)
                st.plotly_chart(fig2, use_container_width=True)
                
            
           
except Exception as e:
    st.error(f"Ocorreu um erro ao processar os dados: {e}")
    st.info("Verifique se a URL da planilha está correta e se você compartilhou a planilha com a conta de serviço.")