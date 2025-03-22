import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, timezone

st.set_page_config(layout="wide")

# API_URL = "http://localhost:8000" # local
# API_URL = "/api"  # local docker
API_URL = "https://hse-apy-short-url.onrender.com/api/"  # render.com
EXTERNAL_API_URL = "http://localhost:8000"

if "token" not in st.session_state:
    st.session_state.token = None
if "username" not in st.session_state:
    st.session_state.username = None
if "role" not in st.session_state:
    st.session_state.role = None
if "page" not in st.session_state:
    st.session_state.page = "Dashboard"

def login(username, password):
    resp = requests.post(
        f"{API_URL}/users/token",
        data={"username": username, "password": password}
    )
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
            st.rerun()
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

def quick_create_link():
    st.header("Быстро создать ссылку (без регистрации)")
    original_url = st.text_input("Оригинальный URL", key="quick_original_url")
    custom_alias = st.text_input("Кастомный алиас (опционально)", key="quick_custom_alias")
    project = st.text_input("Проект (опционально)", key="quick_project")
    expires_at = st.text_input("Дата истечения (YYYY-MM-DD HH:MM, опционально)", key="quick_expires_at")
    auto_renew = st.checkbox("Автоматическое продление", value=False, key="quick_auto_renew")
    if st.button("Создать ссылку (быстро)", key="btn_quick_create"):
        payload = {
            "original_url": original_url,
            "custom_alias": custom_alias if custom_alias else None,
            "project": project if project else None,
            "expires_at": expires_at if expires_at else None,
            "auto_renew": auto_renew
        }
        resp = requests.post(f"{API_URL}/links/shorten", json=payload)
        if resp.status_code == 200:
            st.success("Ссылка успешно создана!")
            st.write(resp.json())
        else:
            st.error(resp.json().get("detail", "Ошибка при создании ссылки"))

if st.session_state.token is None:
    st.sidebar.header("Логин / Регистрация")
    auth_option = st.sidebar.radio("Выберите действие:", ["Логин", "Регистрация"], key="auth_option")
    if auth_option == "Логин":
        login_username = st.sidebar.text_input("Имя пользователя", key="login_username")
        login_password = st.sidebar.text_input("Пароль", type="password", key="login_password")
        if st.sidebar.button("Войти", key="btn_sidebar_login"):
            login(login_username, login_password)
    else:
        reg_username = st.sidebar.text_input("Новое имя пользователя", key="reg_username")
        reg_email = st.sidebar.text_input("Электронная почта", key="reg_email")
        reg_password = st.sidebar.text_input("Новый пароль", type="password", key="reg_password")
        if st.sidebar.button("Зарегистрироваться", key="btn_sidebar_register"):
            register(reg_username, reg_email, reg_password)
else:
    st.sidebar.write(f"Вы вошли как: {st.session_state.username}")
    if st.sidebar.button("Выйти", key="btn_sidebar_logout"):
        st.session_state.token = None
        st.session_state.username = None
        st.session_state.role = None
        st.session_state.page = "Dashboard"
        st.rerun()
    st.sidebar.markdown("### Навигация")
    if st.sidebar.button("Обзор сервиса", key="btn_nav_dashboard"):
        st.session_state.page = "Dashboard"
    if st.sidebar.button("Создать ссылку", key="btn_nav_create"):
        st.session_state.page = "CreateLink"
    if st.sidebar.button("Мои ссылки", key="btn_nav_my"):
        st.session_state.page = "MyLinks"
    if st.sidebar.button("Аналитика", key="btn_nav_analytics"):
        st.session_state.page = "Analytics"
    if st.session_state.role == "admin":
        if st.sidebar.button("Админ-панель", key="btn_nav_admin"):
            st.session_state.page = "AdminPanel"

if st.session_state.token:
    headers = {"Authorization": f"Bearer {st.session_state.token}"}
    page = st.session_state.page

    if page == "Dashboard":
        st.header("Обзор сервиса")
        st.write("Добро пожаловать в сервис сокращения ссылок! Зарегистрированные пользователи могут создавать, редактировать и просматривать аналитику по своим ссылкам. Используйте навигацию для перехода к нужной функции.")
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Создать ссылку", key="btn_dashboard_create"):
                st.session_state.page = "CreateLink"
                st.rerun()
        with col2:
            if st.button("Мои ссылки", key="btn_dashboard_my"):
                st.session_state.page = "MyLinks"
                st.rerun()
        with col3:
            if st.button("Аналитика", key="btn_dashboard_analytics"):
                st.session_state.page = "Analytics"
                st.rerun()

    elif page == "CreateLink":
        st.header("Создать новую ссылку")
        original_url = st.text_input("Оригинальный URL", key="create_original_url")
        custom_alias = st.text_input("Кастомный алиас (опционально)", key="create_custom_alias")
        project = st.text_input("Проект (опционально)", key="create_project")
        expires_at = st.text_input("Дата истечения (YYYY-MM-DD HH:MM, опционально)", key="create_expires_at")
        auto_renew = st.checkbox("Автоматическое продление", value=False, key="create_auto_renew")
        if st.button("Создать ссылку", key="btn_create_link_submit"):
            payload = {
                "original_url": original_url,
                "custom_alias": custom_alias if custom_alias else None,
                "project": project if project else None,
                "expires_at": expires_at if expires_at else None,
                "auto_renew": auto_renew
            }
            resp = requests.post(f"{API_URL}/links/shorten", json=payload, headers=headers)
            if resp.status_code == 200:
                st.success("Ссылка успешно создана!")
                st.write(resp.json())
            else:
                st.error(resp.json().get("detail", "Ошибка при создании ссылки"))

    elif page == "MyLinks":
        st.header("Мои ссылки")
        my_links_resp = requests.get(f"{API_URL}/links/my", headers=headers)
        if my_links_resp.status_code == 200:
            links = my_links_resp.json()
            if links:
                df_links = pd.DataFrame(links)
                for col in ["created_at", "expires_at", "last_visited"]:
                    if col in df_links.columns:
                        df_links[col] = pd.to_datetime(df_links[col], errors="coerce").dt.strftime('%Y-%m-%d %H:%M')
                df_links["Короткий код"] = df_links["short_code"].apply(
                    lambda sc: f'<a href="{EXTERNAL_API_URL}/links/{sc}" target="_blank">{sc}</a>'
                )
                df_links.rename(columns={
                    "original_url": "Оригинальный URL",
                    "created_at": "Дата создания",
                    "expires_at": "Дата истечения",
                    "project": "Проект",
                    "visits": "Количество переходов",
                    "last_visited": "Дата последнего перехода"
                }, inplace=True)
                df_links.drop("short_code", axis=1, inplace=True)
                df_final = df_links[["Короткий код", "Оригинальный URL", "Дата создания", "Дата истечения",
                                     "Проект", "Количество переходов", "Дата последнего перехода"]]
                html_table = df_final.to_html(escape=False, index=False)
                st.markdown(html_table, unsafe_allow_html=True)
            else:
                st.info("У вас пока нет ссылок.")
        else:
            st.error(my_links_resp.text)
        st.subheader("Удалить ссылку")
        del_short_code = st.text_input("Введите короткий код для удаления", key="delete_short_code")
        if st.button("Удалить ссылку", key="btn_delete_link"):
            if del_short_code:
                delete_resp = requests.delete(f"{API_URL}/links/{del_short_code}", headers=headers)
                if delete_resp.status_code == 200:
                    st.success("Ссылка удалена!")
                else:
                    st.error(delete_resp.json().get("detail", "Ошибка при удалении ссылки"))
            else:
                st.warning("Введите короткий код")
        st.subheader("Обновить ссылку")
        upd_short_code = st.text_input("Короткий код для обновления", key="update_short_code")
        new_original = st.text_input("Новый оригинальный URL (опционально)", key="update_original_url")
        new_expires = st.text_input("Новое время истечения (YYYY-MM-DD HH:MM, опционально)", key="update_expires")
        new_project = st.text_input("Новый проект (опционально)", key="update_project")
        if st.button("Обновить ссылку", key="btn_update_link"):
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
                    st.success("Ссылка обновлена!")
                    st.write(update_resp.json())
                else:
                    st.error(update_resp.json().get("detail", "Ошибка при обновлении ссылки"))
            else:
                st.warning("Укажите короткий код и хотя бы одно поле для обновления")

    elif page == "Analytics":
        st.header("Аналитика")
        my_links_resp = requests.get(f"{API_URL}/links/my", headers=headers)
        if my_links_resp.status_code == 200:
            links = my_links_resp.json()
            if links:
                df_links = pd.DataFrame(links)
                df_links["created_at"] = pd.to_datetime(df_links["created_at"], errors="coerce")
                df_sorted = df_links.sort_values(by="created_at", ascending=False)
                last_link = df_sorted.iloc[0]
                st.subheader("Почасовая аналитика для последней ссылки")
                st.write(f"Последняя ссылка: {last_link['short_code']} ({last_link['original_url']})")
                hourly_resp = requests.get(f"{API_URL}/links/{last_link['short_code']}/analytics/hourly", headers=headers)
                if hourly_resp.status_code == 200:
                    data = hourly_resp.json()
                    if data:
                        df_hourly = pd.DataFrame(data)
                        fig_hourly = px.line(df_hourly, x="hour", y="count", title="Почасовая аналитика (последняя ссылка)")
                        st.plotly_chart(fig_hourly, use_container_width=True)
                    else:
                        st.info("Нет данных для почасовой аналитики.")
                else:
                    st.error(hourly_resp.text)
                st.subheader("Дополнительная информация")
                created_at = pd.to_datetime(last_link["created_at"], errors="coerce")
                if pd.notna(created_at):
                    time_since_creation = datetime.now(timezone.utc) - created_at.to_pydatetime()
                    time_since_creation = str(time_since_creation).split('.')[0]
                    st.write(f"Время с момента создания: {time_since_creation}")
                st.write(f"Общее количество переходов: {last_link.get('visits', 0)}")
                if last_link.get("expires_at"):
                    expires_at = pd.to_datetime(last_link["expires_at"], errors="coerce")
                    if pd.notna(expires_at):
                        time_left = expires_at - pd.Timestamp.utcnow()
                        time_left = str(time_left).split('.')[0]
                        st.write(f"Время до истечения: {time_left}")
            else:
                st.info("У вас пока нет ссылок для автоматической аналитики.")
        else:
            st.error(my_links_resp.text)
        st.subheader("Ручной ввод аналитики")
        short_code = st.text_input("Введите короткий код для аналитики (ручной ввод)", key="analytics_manual")
        if st.button("Получить дневную аналитику", key="btn_daily_analytics"):
            daily_resp = requests.get(f"{API_URL}/links/{short_code}/analytics/daily", headers=headers)
            if daily_resp.status_code == 200:
                data = daily_resp.json()
                st.write("Дневная аналитика:", data)
                if data:
                    df_daily = pd.DataFrame(data)
                    fig_daily = px.line(df_daily, x="day", y="count", title="Дневная аналитика (ручной ввод)")
                    st.plotly_chart(fig_daily, use_container_width=True)
            else:
                st.error(daily_resp.text)
        if st.button("Получить почасовую аналитику", key="btn_hourly_analytics_manual"):
            hourly_resp = requests.get(f"{API_URL}/links/{short_code}/analytics/hourly", headers=headers)
            if hourly_resp.status_code == 200:
                data = hourly_resp.json()
                st.write("Почасовая аналитика:", data)
                if data:
                    df_hourly = pd.DataFrame(data)
                    fig_hourly = px.line(df_hourly, x="hour", y="count", title="Почасовая аналитика (ручной ввод)")
                    st.plotly_chart(fig_hourly, use_container_width=True)
            else:
                st.error(hourly_resp.text)
        if st.button("Получить аналитику по User-Agent", key="btn_agents_analytics"):
            agents_resp = requests.get(f"{API_URL}/links/{short_code}/analytics/agents", headers=headers)
            if agents_resp.status_code == 200:
                data = agents_resp.json()
                st.write("Аналитика по User-Agent:", data)
                if data:
                    df_agents = pd.DataFrame(data)
                    fig_agents = px.pie(df_agents, names="user_agent", values="count", title="Аналитика по User-Agent (ручной ввод)")
                    st.plotly_chart(fig_agents, use_container_width=True)
            else:
                st.error(agents_resp.text)
        project_name = st.text_input("Введите имя проекта для статистики", key="analytics_project")
        if st.button("Получить статистику по проекту", key="btn_project_stats"):
            proj_resp = requests.get(f"{API_URL}/links/project/{project_name}/stats", headers=headers)
            if proj_resp.status_code == 200:
                st.write("Статистика по проекту:", proj_resp.json())
            else:
                st.error(proj_resp.text)

    elif page == "AdminPanel" and st.session_state.role == "admin":
        st.header("Админ-панель")
        if st.button("Обновить список ссылок", key="btn_admin_links"):
            admin_links_resp = requests.get(f"{API_URL}/admin/links", headers=headers)
            if admin_links_resp.status_code == 200:
                df_all_links = pd.DataFrame(admin_links_resp.json())
                st.write("Все ссылки:")
                st.dataframe(df_all_links, use_container_width=True)
            else:
                st.error(admin_links_resp.text)
        if st.button("Обновить список пользователей", key="btn_admin_users"):
            admin_users_resp = requests.get(f"{API_URL}/admin/users", headers=headers)
            if admin_users_resp.status_code == 200:
                df_users = pd.DataFrame(admin_users_resp.json())
                st.write("Все пользователи:")
                st.dataframe(df_users, use_container_width=True)
            else:
                st.error(admin_users_resp.text)
else:
    st.header("Добро пожаловать в сервис сокращения ссылок!")
    st.write("""
        Этот сервис позволяет сокращать длинные URL, получать статистику переходов и управлять своими ссылками.
        Зарегистрированные пользователи могут создавать, обновлять и удалять свои ссылки, а также просматривать аналитику переходов.
        Даже если вы не зарегистрированы, вы можете быстро создать короткую ссылку, но возможности будут ограничены.
        Рекомендуем зарегистрироваться для получения полного доступа к функциям сервиса.
    """)
    st.markdown("---")
    quick_create_link()
