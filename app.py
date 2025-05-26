import streamlit as st
import pandas as pd
import base64
import requests

# GitHub repo info
REPO = "wwwcxwhywhy/Scheduling"
BRANCH = "main"

# 讀取 GitHub Token（需從 secrets.toml 或 Secrets Manager 設定）
GITHUB_TOKEN = st.secrets["github_token"]

# GitHub raw URLs（讀取資料）
EMPLOYEE_CSV_URL = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/employees.csv"
SCHEDULE_CSV_URL = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/schedule.csv"
DEMAND_CSV_URL = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/shift_demand.csv"

def upload_to_github(local_path, repo_path, commit_msg):
    with open(local_path, "rb") as f:
        content = f.read()
    b64 = base64.b64encode(content).decode()
    api_url = f"https://api.github.com/repos/{REPO}/contents/{repo_path}"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}

    # 檢查是否已有該檔案
    res = requests.get(api_url, headers=headers)
    sha = res.json().get("sha") if res.status_code == 200 else None

    data = {
        "message": commit_msg,
        "content": b64,
        "branch": BRANCH
    }
    if sha:
        data["sha"] = sha

    response = requests.put(api_url, headers=headers, json=data)
    if response.status_code in [200, 201]:
        st.success(f"GitHub 更新成功：{repo_path}")
    else:
        st.error(f"GitHub 更新失敗：{response.status_code}\n{response.text}")

st.title("SmartScheduler 2.0 - 安全版")

menu = st.sidebar.selectbox("選擇功能", ["查詢班表", "新增員工", "產生班表"])

@st.cache_data
def load_schedule():
    df = pd.read_csv(SCHEDULE_CSV_URL, encoding="utf-8-sig")
    df.columns = df.columns.str.replace('\ufeff', '')
    df["Date"] = pd.to_datetime(df["Date"])
    return df

if menu == "查詢班表":
    st.header("查詢排班")
    df = load_schedule()
    emp_id = st.text_input("請輸入員工ID（例如：E001）")
    if emp_id:
        emp_id = emp_id.strip().upper()
        df["員工ID"] = df["員工ID"].astype(str).str.strip().str.upper()
        filtered = df[df["員工ID"] == emp_id]
        if not filtered.empty:
            st.dataframe(filtered)
        else:
            st.warning("找不到此員工的排班資料")

elif menu == "新增員工":
    st.header("新增員工")
    with st.form("add_emp_form"):
        emp_id = st.text_input("員工ID（例如 E001）")
        name = st.text_input("員工姓名")
        work_days = st.multiselect("可上班日", ["1", "2", "3", "4", "5", "6", "7"])
        shifts = st.multiselect("可上班班別", ["早", "晚"])
        submitted = st.form_submit_button("新增員工")
        if submitted:
            new_row = pd.DataFrame([[emp_id.strip().upper(), name.strip(), ",".join(work_days), ",".join(shifts)]],
                                   columns=["員工ID", "員工姓名", "可上班日（1～7）", "可上班班別（早/晚）"])
            df = pd.read_csv(EMPLOYEE_CSV_URL, encoding="utf-8-sig")
            df = pd.concat([df, new_row], ignore_index=True)
            df.to_csv("employees.csv", index=False, encoding="utf-8-sig")
            upload_to_github("employees.csv", "employees.csv", "新增員工")

elif menu == "產生班表":
    st.header("自動產生班表")
    if st.button("點我排班！"):
        emp_df = pd.read_csv(EMPLOYEE_CSV_URL, encoding="utf-8-sig")
        demand_df = pd.read_csv(DEMAND_CSV_URL, encoding="utf-8")

        emp_df.columns = emp_df.columns.str.replace('\ufeff', '')
        emp_df["員工ID"] = emp_df["員工ID"].astype(str).str.strip().str.upper()
        emp_df["可上班日（1～7）"] = emp_df["可上班日（1～7）"].astype(str).str.split(",")
        emp_df["可上班班別（早/晚）"] = emp_df["可上班班別（早/晚）"].astype(str).str.split(",")

        schedule = []
        for i, row in demand_df.iterrows():
            date = pd.to_datetime(row["Date"]).strftime("%Y-%m-%d")
            weekday = str(i + 1)
            m_need = int(row["早班需求人數"])
            e_need = int(row["晚班需求人數"])

            m_cand = emp_df[emp_df["可上班日（1～7）"].apply(lambda x: weekday in x) &
                            emp_df["可上班班別（早/晚）"].apply(lambda x: "早" in x)]
            e_cand = emp_df[emp_df["可上班日（1～7）"].apply(lambda x: weekday in x) &
                            emp_df["可上班班別（早/晚）"].apply(lambda x: "晚" in x)]

            m_sel = m_cand.sample(n=min(len(m_cand), m_need), replace=False)
            e_sel = e_cand.sample(n=min(len(e_cand), e_need), replace=False)

            for _, emp in m_sel.iterrows():
                schedule.append({"Date": date, "班別": "早班", "員工ID": emp["員工ID"], "員工姓名": emp["員工姓名"]})
            for _, emp in e_sel.iterrows():
                schedule.append({"Date": date, "班別": "晚班", "員工ID": emp["員工ID"], "員工姓名": emp["員工姓名"]})

        result_df = pd.DataFrame(schedule, columns=["Date", "班別", "員工ID", "員工姓名"])
        result_df.to_csv("schedule.csv", index=False, encoding="utf-8-sig")
        upload_to_github("schedule.csv", "schedule.csv", "更新班表")
        st.dataframe(result_df)

