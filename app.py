import streamlit as st
import pandas as pd

# ✅ GitHub Raw 路徑
EMPLOYEE_CSV_URL = "https://raw.githubusercontent.com/wwwcxwhywhy/Scheduling/main/employees.csv"
SCHEDULE_CSV_URL = "https://raw.githubusercontent.com/wwwcxwhywhy/Scheduling/main/schedule.csv"
DEMAND_CSV_URL = "https://raw.githubusercontent.com/wwwcxwhywhy/Scheduling/main/shift_demand.csv"

st.title("SmartScheduler 2.0 - 員工排班查詢")

menu = st.sidebar.selectbox("選擇功能", ["查詢班表", "申請換班", "輸入員工資料", "產生班表"])

@st.cache_data
def load_schedule():
    df = pd.read_csv(SCHEDULE_CSV_URL, encoding="utf-8-sig")
    df.columns = df.columns.str.replace('\ufeff', '')  # 清除 BOM
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
            st.write(f"找到 {len(filtered)} 筆班表")
            st.dataframe(filtered)
        else:
            st.warning("找不到此員工的排班資料")

elif menu == "申請換班":
    st.header("換班申請表單")
    with st.form("shift_form"):
        emp_id = st.text_input("員工ID")
        date = st.date_input("想換的日期")
        shift = st.radio("班別", ["早班", "晚班"])
        reason = st.text_area("換班原因")
        submitted = st.form_submit_button("送出申請")
        if submitted:
            with open("swap_requests.csv", "a", encoding="utf-8") as f:
                f.write(f"{emp_id},{date},{shift},{reason}\n")
            st.success("已送出換班申請")

elif menu == "輸入員工資料":
    st.header("新增員工")
    with st.form("add_emp_form"):
        emp_id = st.text_input("員工ID（例如 E001）")
        name = st.text_input("員工姓名")
        work_days = st.multiselect("可上班日", options=["1", "2", "3", "4", "5", "6", "7"])
        shifts = st.multiselect("可上班班別", options=["早", "晚"])
        submitted = st.form_submit_button("新增員工")
        if submitted:
            new_row = pd.DataFrame([[emp_id.strip().upper(), name.strip(), ",".join(work_days), ",".join(shifts)]],
                                   columns=["員工ID", "員工姓名", "可上班日（1～7）", "可上班班別（早/晚）"])
            try:
                df = pd.read_csv(EMPLOYEE_CSV_URL, encoding="utf-8-sig")
                df = pd.concat([df, new_row], ignore_index=True)
            except Exception:
                df = new_row
            df.to_csv("employees.csv", index=False, encoding="utf-8-sig")
            st.success("已成功新增員工")

elif menu == "產生班表":
    st.header("自動產生班表")
    if st.button("點我排班！"):
        try:
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
            result_df["Date"] = pd.to_datetime(result_df["Date"]).dt.strftime("%Y-%m-%d")
            result_df.to_csv("schedule.csv", index=False, encoding="utf-8-sig")

            st.success("班表已產生！")
            st.dataframe(result_df)

            with open("schedule.csv", "rb") as f:
                st.download_button("下載班表 CSV", f, file_name="schedule.csv", mime="text/csv")

        except Exception as e:
            st.error(f"發生錯誤：{e}")
