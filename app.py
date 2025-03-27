import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px
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
        try:
            # Fallback to local file for development
            credentials = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
        except FileNotFoundError:
            st.error("credentials.json file not found. Please add your Google service account credentials to Streamlit secrets.")
            st.stop()
    
    client = gspread.authorize(credentials)
    return client

# Function to get data from Google Sheets
@st.cache_data(ttl=300)
def get_sheet_data(sheet_url):
    client = connect_to_sheets()
    spreadsheet = client.open_by_url(sheet_url)
    sheet = spreadsheet.get_worksheet(1)
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

# Title and description
st.title("#shine-little-star ⭐")
st.markdown("Confira o envio de suas Estrelas do canal #shine-little-star.")

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
        # Get data
        df = get_sheet_data(sheet_url)
        
        # Filter by month and year
        filtered_df = df[(df['month'] == selected_month) & (df['year'] == selected_year)]
        
        if filtered_df.empty:
            st.warning(f"Não há dados para {months[selected_month]} de {selected_year}")
        else:
            # Calculate metrics
            all_users = sorted(list(set(filtered_df['receiver'].unique()) | set(filtered_df['sender'].unique())))
            
            # Create summary dataframe
            summary_data = []
            for user in all_users:
                stars_sent = filtered_df[filtered_df['sender'] == user]['stars'].sum()
                stars_receiverd = filtered_df[filtered_df['receiver'] == user]['stars'].sum()
                summary_data.append({
                    'Pessoa': user,
                    'Estrelas Recebidas': int(stars_receiverd),
                    'Estrelas Enviadas': int(stars_sent)
                    
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
                            lambda x: ['background-color: rgba(255, 215, 0, 0.2)' if x.name == user_name else '' for _ in x],
                            axis=1
                        ),
                        use_container_width=True, 
                        height=400
                    )
                else:
                    st.dataframe(summary_df, use_container_width=True, height=400)
            
            # with col2:
            #     # Calculate metrics for charts
            #     total_stars = filtered_df['stars'].sum()
            #     total_users = len(all_users)
            #     active_receivers = len(filtered_df['receiver'].unique())
            #     participation_rate = (active_receivers / total_users) * 100 if total_users > 0 else 0
                
            #     # Chart 1: Stars distribution
            #     st.subheader("Distribuição de Estrelas Enviadas")
            #     stars_by_user = filtered_df.groupby('receiver')['stars'].sum().reset_index()
            #     stars_by_user = stars_by_user.sort_values('stars', ascending=False)
                
            #     fig1 = px.pie(
            #         stars_by_user, 
            #         values='stars', 
            #         names='receiver',
            #         title=f'Total de Estrelas: {int(total_stars)}',
            #         hole=0.4
            #     )
            #     st.plotly_chart(fig1, use_container_width=True)
                
            #     # Chart 2: Participation rate
            #     st.subheader("Taxa de Participação")
            #     participation_data = pd.DataFrame([
            #         {'Status': 'Enviaram Estrelas', 'Contagem': active_receivers},
            #         {'Status': 'Não Enviaram Estrelas', 'Contagem': total_users - active_receivers}
            #     ])
                
            #     fig2 = px.pie(
            #         participation_data,
            #         values='Contagem',
            #         names='Status',
            #         title=f'Taxa de Participação: {participation_rate:.1f}%',
            #         hole=0.4,
            #         color_discrete_sequence=['#1f77b4', '#d3d3d3']
            #     )
            #     st.plotly_chart(fig2, use_container_width=True)
                
            # # Additional insights
            # st.subheader("Insights")
            # col1, col2, col3 = st.columns(3)
            
            # with col1:
            #     top_receiver = stars_by_user.iloc[0] if not stars_by_user.empty else None
            #     if top_receiver is not None:
            #         st.metric("Maior Doador de Estrelas", 
            #                  f"{top_receiver['receiver']}", 
            #                  f"{int(top_receiver['stars'])} ⭐")
            
            # with col2:
            #     top_sender = summary_df.sort_values('Estrelas Recebidas', ascending=False).iloc[0] if not summary_df.empty else None
            #     if top_sender is not None:
            #         st.metric("Maior Receptor de Estrelas", 
            #                  f"{top_sender['Pessoa']}", 
            #                  f"{int(top_sender['Estrelas Recebidas'])} ⭐")
            
            # with col3:
            #     if slack_name:
            #         user_row = summary_df[summary_df['Pessoa'] == slack_name]
            #         if not user_row.empty:
            #             user_sent = user_row['Estrelas Enviadas'].values[0]
            #             user_receiverd = user_row['Estrelas Recebidas'].values[0]
            #             st.metric("Suas Estrelas", 
            #                      f"Enviadas: {user_sent} | Recebidas: {user_receiverd}", 
            #                      f"Saldo: {user_receiverd - user_sent}")
            #         else:
            #             st.info(f"Não encontramos dados para {slack_name}")
            #     else:
            #         st.info("Insira seu nome no Slack para ver suas estatísticas")
except Exception as e:
    st.error(f"Ocorreu um erro ao processar os dados: {e}")
    st.info("Verifique se a URL da planilha está correta e se você compartilhou a planilha com a conta de serviço.")
