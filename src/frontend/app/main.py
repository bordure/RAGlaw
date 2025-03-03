import streamlit as st
import streamlit_authenticator as stauth
import requests
import os 

API_URI = 'http://rag-api.rag-api.svc.cluster.local:8000'
#API_URI = 'http://localhost:8000'

data = {
    'usernames': {
        os.getenv('frontend_user'): {
            'email': os.getenv('frontend_email'),
            'first_name': 'Jane',
            'last_name': 'Doe',
            'password': os.getenv('frontend_password')
        }
    }
}

cookies = {
    'name': os.getenv('cookies_name'),
    'key': os.getenv('cookies_key'),
    'expiry_days': os.getenv('cookies_expiry_days')
}

preauthorized = os.getenv('frontend_email')

authenticator = stauth.Authenticate(
    data,
    cookies['name'],
    cookies['key'],
    cookies['expiry_days'],
    preauthorized
)

try:
    authenticator.login()
except Exception as e:
    st.error(e)

if st.session_state.get('authentication_status'):
    authenticator.logout()
    st.title("Law RAG model")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Przeszukaj kodeks karny"):
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        API_response = requests.post(f"{API_URI}/v1/rag_chat_completion?prompt={prompt}")

        response = API_response.json()['response']
        
        with st.chat_message("assistant"):
            st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})
elif st.session_state.get('authentication_status') is False:
    st.error('Username/password is incorrect')
elif st.session_state.get('authentication_status') is None:
    st.warning('Please enter your username and password')
elif authentication_status == False:
    st.error('Username/password is incorrect')
elif authentication_status == None:
    st.warning('Please enter your username and password')
