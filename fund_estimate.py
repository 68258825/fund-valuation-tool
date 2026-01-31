import streamlit as st
import akshare as ak
import pandas as pd
import json
import os
import shutil
from typing import List, Optional

# ===================== 全局配置（重点：移动端适配） =====================
st.set_page_config(
    page_title="基金估值查询（手机版）",
    page_icon="📊",
    layout="centered",  # 适配手机窄屏
    initial_sidebar_state="collapsed"  # 隐藏侧边栏，节省空间
)

# 新增：移动端样式优化
st.markdown("""
<style>
/* 适配手机字体大小 */
html, body, [class*="css"] {
    font-size: 14px !important;
}
/* 按钮适配手机 */
.stButton>button {
    width: 100%;
    padding: 8px 0;
}
/* 输入框适配 */
.stTextInput>div>div>input, .stNumberInput>div>div>input {
    padding: 8px;
}
/* 表格适配手机横向滚动 */
.dataframe {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch; /* iOS顺滑滚动 */
}
</style>
""", unsafe_allow_html=True)

# ===================== 以下代码和「多人共享版」完全一致（省略，直接复用） =====================
# 1. 多用户持仓配置
ROOT_HOLDINGS_DIR = os.path.join(os.path.expanduser("~"), "fund_holdings_shared")
os.makedirs(ROOT_HOLDINGS_DIR, exist_ok=True)

# 2. 样式函数（红涨绿跌）
def format_increase(val: Optional[float]) -> str:
    val_float = float(val) if pd.notna(val) else 0.0
    if val_float > 0:
        return "color: #ef4444; font-weight: 500;"
    elif val_float < 0:
        return "color: #10b981; font-weight: 500;"
    else:
        return "color: #6b7280; font-weight: 400;"

def format_summary_table(styler):
    return styler.set_table_styles([
        {"selector": "table", "props": [("border-collapse", "collapse"), ("width", "100%")]},
        {"selector": "th, td", "props": [("border", "1px solid #e5e7eb"), ("padding", "6px 8px"), ("text-align", "center")]},
        {"selector": "th", "props": [("background-color", "#1f77b4"), ("color", "white"), ("font-weight", "600")]}
    ])

# 3. 持仓管理函数（复用）
def get_user_holdings_file(user_name: str) -> str:
    safe_user_name = "".join([c for c in user_name if c.isalnum() or c in "_-"]).strip() or "default_user"
    return os.path.join(ROOT_HOLDINGS_DIR, f"{safe_user_name}_holdings.json")

def load_holdings(user_name: str) -> dict:
    holdings_file = get_user_holdings_file(user_name)
    if os.path.exists(holdings_file):
        try:
            with open(holdings_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {k.strip(): v.strip() for k, v in data.items() if k.strip() and v.strip()}
        except:
            st.warning("📝 持仓数据读取异常，已重置")
            save_holdings(user_name, {})
    return {}

def save_holdings(user_name: str, holdings: dict):
    holdings_file = get_user_holdings_file(user_name)
    try:
        temp_file = holdings_file + ".tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(holdings, f, ensure_ascii=False, indent=4)
        shutil.move(temp_file, holdings_file)
        if os.name == 'nt':
            os.system(f"attrib -R {holdings_file}")
    except Exception as e:
        st.error(f"❌ 保存失败：{e}")

def add_holding(user_name: str, fund_code: str, custom_name: str):
    holdings = load_holdings(user_name)
    fund_code, custom_name = fund_code.strip(), custom_name.strip()
    if fund_code and custom_name:
        holdings[fund_code] = custom_name
    elif fund_code and not custom_name and fund_code in holdings:
        del holdings[fund_code]
    save_holdings(user_name, {k: v for k, v in holdings.items() if v.strip()})
    st.rerun()

def clear_all_holdings(user_name: str):
    save_holdings(user_name, {})
    st.rerun()

# 4. 基金数据获取（复用）
def get_fund_data(fund_code: str, custom_name: str) -> Optional[pd.DataFrame]:
    try:
        df = ak.fund_open_fund_info_em(symbol=fund_code)
        if df.empty:
            st.warning(f"⚠️ 基金{fund_code}（{custom_name}）无数据")
            return None

        base_cols = ["净值日期", "实时估值", "日增长率", "单位净值"]
        df_filtered = df[[c for c in base_cols if c in df.columns]].copy()
        df_filtered.rename(columns={"净值日期": "时间", "实时估值": "当日预估值"}, inplace=True)
        df_filtered["基金代码/名称"] = f"{fund_code}（{custom_name}）"

        numeric_cols = ["当日预估值", "日增长率", "单位净值"]
        for col in numeric_cols:
            if col in df_filtered.columns:
                df_filtered[col] = pd.to_numeric(df_filtered[col], errors="coerce").fillna(0.0).round(4)
        
        target_cols = ["时间", "基金代码/名称", "当日预估值", "日增长率", "单位净值"]
        for col in target_cols:
            if col not in df_filtered.columns:
                df_filtered[col] = "-"
        df_filtered = df_filtered[target_cols]

        if "时间" in df_filtered.columns:
            df_filtered["时间_标准"] = pd.to_datetime(df_filtered["时间"], errors="coerce", format="mixed")
            df_filtered = df_filtered.sort_values(by="时间_标准", ascending=False).drop(columns=["时间_标准"]).reset_index(drop=True)

        return df_filtered
    except Exception as e:
        st.error(f"❌ 查询失败：{str(e)}")
        return None

# 5. 页面主逻辑（适配手机）
def main():
    st.title("📊 基金估值查询（手机版）")
    st.markdown("### 👤 你的昵称（区分用户）")
    user_name = st.text_input("", placeholder="输入昵称（如：张三）", label_visibility="collapsed")
    current_user = user_name.strip() or "默认用户"
    st.success(f"当前用户：{current_user}")

    st.divider()
    st.markdown("### 📝 持仓管理")
    col1, col2 = st.columns([2, 3])
    with col1:
        fund_code = st.text_input("基金代码", placeholder="6位代码")
    with col2:
        custom_name = st.text_input("自定义名称", placeholder="如：白酒基金")
    col1, col2 = st.columns([1, 1])
    with col1:
        st.button("✅ 保存持仓", type="primary", on_click=add_holding, args=(current_user, fund_code, custom_name))
    with col2:
        st.button("🗑️ 清空所有", type="secondary", on_click=clear_all_holdings, args=(current_user,))

    holdings = load_holdings(current_user)
    if holdings:
        st.markdown("### 📋 你的持仓")
        for code, name in holdings.items():
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"📌 {code}（{name}）")
            with col2:
                st.button(f"删", key=f"del_{code}", on_click=add_holding, args=(current_user, code, ""))
        
        selected_codes = st.multiselect("选择查询基金", holdings.keys(), format_func=lambda x: f"{x}（{holdings[x]}）", default=holdings.keys())
    else:
        st.info("暂无持仓，添加后即可查询")
        selected_codes = []

    st.divider()
    st.markdown("### 🔍 估值查询")
    fund_input = st.text_input("", value=",".join(selected_codes), placeholder="多只基金用英文逗号分隔", label_visibility="collapsed")
    if st.button("立即查询", type="primary"):
        fund_codes = [c.strip() for c in fund_input.split(",") if c.strip()]
        if not fund_codes:
            st.warning("请输入有效代码！")
            return

        summary_data = []
        all_fund_dfs = []
        for code in fund_codes:
            name = holdings.get(code, "未命名")
            df = get_fund_data(code, name)
            if df is not None:
                all_fund_dfs.append((code, name, df))
                summary_data.append({"基金代码/名称": df.iloc[0]["基金代码/名称"], "当日预估值": df.iloc[0]["当日预估值"]})

        if summary_data:
            st.markdown("### 📈 估值汇总")
            st.dataframe(pd.DataFrame(summary_data).style.pipe(format_summary_table), use_container_width=True, hide_index=True)
        
        if all_fund_dfs:
            st.markdown("### 📋 估值明细")
            for idx, (code, name, df) in enumerate(all_fund_dfs):
                st.markdown(f"#### 基金{idx+1}：{code}（{name}）")
                st.dataframe(df.style.applymap(format_increase, subset=["日增长率"]), use_container_width=True, hide_index=True)

    st.caption("💡 估值≠实际净值，交易日9:30-15:00实时更新")

if __name__ == "__main__":
    main()