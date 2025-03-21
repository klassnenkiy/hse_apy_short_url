import streamlit as st
import requests
import pandas as pd

API_URL = "http://localhost:8000"


if "token" not in st.session_state:
    st.session_state.token = None
if "username" not in st.session_state:
    st.session_state.username = None
if "role" not in st.session_state:
    st.session_state.role = None


def login(username, password):
    resp = requests.post(f"{API_URL}/users/token", data={"username": username, "password": password})
    if resp.status_code == 200:
        token = resp.json()["access_token"]
        st.session_state.token = token
        st.session_state.username = username
        headers = {"Authorization": f"Bearer {token}"}
        user_resp = requests.get(f"{API_URL}/users/me", headers=headers)
        if user_resp.status_code == 200:
            user = user_resp.json()
            st.session_state.role = user.get("role", "user")
            st.success(f"Добро пожаловать, {user['username']}!")
        else:
            st.error("Не удалось получить данные пользователя.")
    else:
        st.error("Неверный логин/пароль.")


def register(username, email, password):
    payload = {"username": username, "email": email, "password": password}
    resp = requests.post(f"{API_URL}/users/register", json=payload)
    if resp.status_code == 200:
        st.success("Регистрация прошла успешно! Теперь выполните логин.")
    else:
        st.error(resp.json().get("detail", "Ошибка регистрации"))


st.sidebar.title("Link Shortener")
if st.session_state.token is None:
    st.sidebar.header("Login / Register")
    auth_option = st.sidebar.radio("Выберите действие:", ["Login", "Register"])
    if auth_option == "Login":
        login_username = st.sidebar.text_input("Username", key="login_username")
        login_password = st.sidebar.text_input("Password", type="password", key="login_password")
        if st.sidebar.button("Login"):
            login(login_username, login_password)
    else:
        reg_username = st.sidebar.text_input("New Username", key="reg_username")
        reg_email = st.sidebar.text_input("Email", key="reg_email")
        reg_password = st.sidebar.text_input("New Password", type="password", key="reg_password")
        if st.sidebar.button("Register"):
            register(reg_username, reg_email, reg_password)
else:
    st.sidebar.write(f"Logged in as: {st.session_state.username}")
    if st.sidebar.button("Logout"):
        st.session_state.token = None
        st.session_state.username = None
        st.session_state.role = None
        st.experimental_rerun()

if st.session_state.token:
    headers = {"Authorization": f"Bearer {st.session_state.token}"}

    tabs = ["Dashboard", "Create Link", "My Links", "Analytics"]
    if st.session_state.role == "admin":
        tabs.append("Admin Panel")
    tab = st.sidebar.selectbox("Навигация", tabs)

    if tab == "Dashboard":
        st.header("Dashboard")
        st.write("Здесь можно добавить сводную статистику или обзор сервиса.")

    elif tab == "Create Link":
        st.header("Создать новую ссылку")
        original_url = st.text_input("Original URL")
        custom_alias = st.text_input("Custom Alias (опционально)")
        project = st.text_input("Project (опционально)")
        expires_at = st.text_input("Expires At (YYYY-MM-DD HH:MM, опционально)")
        auto_renew = st.checkbox("Auto Renew", value=False)
        if st.button("Create Link"):
            payload = {
                "original_url": original_url,
                "custom_alias": custom_alias if custom_alias else None,
                "project": project if project else None,
                "expires_at": expires_at if expires_at else None,
                "auto_renew": auto_renew
            }
            resp = requests.post(f"{API_URL}/links/shorten", json=payload, headers=headers)
            if resp.status_code == 200:
                st.success("Link created successfully!")
                st.write(resp.json())
            else:
                st.error(resp.json().get("detail", "Error creating link"))

    elif tab == "My Links":
        st.header("Мои ссылки")

        if st.button("Refresh My Links"):
            my_links_resp = requests.get(f"{API_URL}/links/my", headers=headers)
            if my_links_resp.status_code == 200:
                links = my_links_resp.json()
                if links:
                    df = pd.DataFrame(links)
                    st.dataframe(df)
                else:
                    st.info("У вас пока нет ссылок.")
            else:
                st.error(my_links_resp.text)

        st.subheader("Удалить ссылку")
        del_short_code = st.text_input("Введите Short Code для удаления")
        if st.button("Delete Link"):
            if del_short_code:
                delete_resp = requests.delete(f"{API_URL}/links/{del_short_code}", headers=headers)
                if delete_resp.status_code == 200:
                    st.success("Link deleted successfully!")
                else:
                    st.error(delete_resp.json().get("detail", "Error deleting link"))
            else:
                st.warning("Введите Short Code")

        st.subheader("Обновить ссылку")
        upd_short_code = st.text_input("Short Code для обновления")
        new_original = st.text_input("Новый Original URL (опционально)")
        new_expires = st.text_input("Новое время истечения (YYYY-MM-DD HH:MM, опционально)")
        new_project = st.text_input("Новый проект (опционально)")
        if st.button("Update Link"):
            payload = {}
            if new_original:
                payload["original_url"] = new_original
            if new_expires:
                payload["expires_at"] = new_expires
            if new_project:
                payload["project"] = new_project

            if upd_short_code and payload:
                update_resp = requests.put(f"{API_URL}/links/{upd_short_code}", json=payload, headers=headers)
                if update_resp.status_code == 200:
                    st.success("Link updated successfully!")
                    st.write(update_resp.json())
                else:
                    st.error(update_resp.json().get("detail", "Error updating link"))
            else:
                st.warning("Необходимо указать Short Code и хотя бы одно поле для обновления.")

    elif tab == "Analytics":
        st.header("Аналитика")
        short_code = st.text_input("Введите Short Code для аналитики")
        if st.button("Получить дневную аналитику"):
            daily_resp = requests.get(f"{API_URL}/links/{short_code}/analytics/daily", headers=headers)
            if daily_resp.status_code == 200:
                st.write("Daily Analytics:", daily_resp.json())
            else:
                st.error(daily_resp.text)
        if st.button("Получить почасовую аналитику"):
            hourly_resp = requests.get(f"{API_URL}/links/{short_code}/analytics/hourly", headers=headers)
            if hourly_resp.status_code == 200:
                st.write("Hourly Analytics:", hourly_resp.json())
            else:
                st.error(hourly_resp.text)
        if st.button("Получить аналитику по User-Agent"):
            agents_resp = requests.get(f"{API_URL}/links/{short_code}/analytics/agents", headers=headers)
            if agents_resp.status_code == 200:
                st.write("Agents Analytics:", agents_resp.json())
            else:
                st.error(agents_resp.text)

        project_name = st.text_input("Введите имя проекта для статистики")
        if st.button("Получить статистику по проекту"):
            proj_resp = requests.get(f"{API_URL}/links/project/{project_name}/stats", headers=headers)
            if proj_resp.status_code == 200:
                st.write("Project Stats:", proj_resp.json())
            else:
                st.error(proj_resp.text)

    elif tab == "Admin Panel" and st.session_state.role == "admin":
        st.header("Админ-панель")
        if st.button("Обновить список ссылок"):
            admin_links_resp = requests.get(f"{API_URL}/admin/links", headers=headers)
            if admin_links_resp.status_code == 200:
                st.write("Все ссылки:")
                df_all_links = pd.DataFrame(admin_links_resp.json())
                st.dataframe(df_all_links)
            else:
                st.error(admin_links_resp.text)

        if st.button("Обновить список пользователей"):
            admin_users_resp = requests.get(f"{API_URL}/admin/users", headers=headers)
            if admin_users_resp.status_code == 200:
                st.write("Все пользователи:")
                df_users = pd.DataFrame(admin_users_resp.json())
                st.dataframe(df_users)
            else:
                st.error(admin_users_resp.text)
