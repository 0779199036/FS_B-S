import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy_financial as npf
import io
import google.generativeai as genai

# --- CẤU HÌNH TRANG & SESSION STATE ---
st.set_page_config(page_title="Phân tích FS & Dòng Tiền", page_icon="🏢", layout="wide")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "executive_summary" not in st.session_state:
    st.session_state.executive_summary = ""

# --- HÀM FORMAT ---
def format_acc(val):
    if pd.isna(val) or val == "": return ""
    if isinstance(val, str): return val
    if abs(val) < 0.1: return "-" 
    s = f"{abs(val):,.0f}".replace(",", ".")
    return f"({s})" if val < 0 else s

def format_unit(val):
    if pd.isna(val) or val == "": return ""
    if isinstance(val, str): return val
    s = f"{abs(val):,.1f}".replace(",", ".")
    return f"({s})" if val < 0 else s

def style_pl(row):
    styles = [''] * len(row)
    idx = str(row.iloc[0]).upper()
    if "LỢI NHUẬN SAU THUẾ" in idx or "DOANH THU" in idx:
        styles = ['background-color: #d4edda; font-weight: bold; color: #155724'] * len(row)
    elif "TỔNG CHI PHÍ" in idx or "LỢI NHUẬN TRƯỚC" in idx:
        styles = ['font-weight: bold'] * len(row)
    return styles

def style_cf(row):
    styles = [''] * len(row)
    idx = str(row.iloc[0]).upper()
    if "DÒNG TIỀN THUẦN (SAU TÀI CHÍNH)" in idx or "LŨY KẾ" in idx:
        styles = ['background-color: #d4edda; font-weight: bold; color: #155724'] * len(row)
    elif "DÒNG TIỀN VÀO" in idx or "DÒNG TIỀN RA" in idx or "DÒNG TIỀN THUẦN (TRƯỚC TÀI CHÍNH)" in idx or "DÒNG TIỀN TÀI CHÍNH" in idx or "TỔNG CỘNG" in idx:
        styles = ['background-color: #f8f9fa; font-weight: bold'] * len(row)
    return styles

st.title("📊 Hệ Thống Phân Tích FS & Dòng Tiền Dự Án (8 Năm)")

# --- KHU VỰC NHẬP LIỆU (BÊN TRÁI) ---
col_input, col_result = st.columns([1.2, 2.6])

with col_input:
    st.header("📝 Nhập Thông Số")
    
    # Kéo API Key ra ngoài để dùng chung cho cả Khảo sát và Phân tích FS
    api_key = st.text_input("🔑 Nhập Google Gemini API Key (Bắt buộc cho AI):", type="password", key="ai_key")
    
    with st.expander("🤖 AI Trợ Lý Khảo Sát Giá", expanded=False):
        location = st.text_input("Vị trí dự án:", value="Phường An Lạc, Bình Tân", key="ai_loc")
        proj_type = st.selectbox("Loại hình SP:", ["Căn hộ trung cấp", "Căn hộ cao cấp", "Nhà phố liền kề", "Biệt thự"], key="ai_type")
        
        if st.button("🔍 Yêu cầu AI Khảo sát", type="primary", key="btn_ai_survey"):
            if api_key == "":
                st.warning("Vui lòng nhập API Key ở trên!")
            else:
                with st.spinner("Đang tổng hợp dữ liệu..."):
                    try:
                        genai.configure(api_key=api_key)
                        valid_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                        best_model = next((m for m in valid_models if 'flash' in m or 'pro' in m), valid_models[0]) if valid_models else None
                        
                        if best_model:
                            model = genai.GenerativeModel(best_model)
                            prompt = f"Phân tích ngắn gọn thị trường {proj_type} tại {location}. 1. Ưu/nhược điểm. 2. Đối thủ (giá Tr/m2). 3. Đề xuất giá bán (Min-Max Tr/m2)."
                            st.markdown(model.generate_content(prompt).text)
                        else: st.error("Lỗi API Key.")
                    except Exception as e: st.error(f"Lỗi: {e}")

    with st.expander("1. Quy hoạch & Giá bán", expanded=False):
        gfa = st.number_input("Tổng GFA (m2)", value=81976, step=1000, key="inp_gfa")
        ct_nfa = st.number_input("NFA Cao tầng (m2)", value=63942, step=1000, key="inp_ct_nfa")
        ct_price = st.number_input("Giá bán Cao tầng (Tr/m2)", value=65.0, step=1.0, key="inp_ct_price")
        tt_nfa = st.number_input("NFA Thấp tầng (m2)", value=4824, step=100, key="inp_tt_nfa")
        tt_price = st.number_input("Giá bán Thấp tầng (Tr/m2)", value=80.0, step=1.0, key="inp_tt_price")
    
    with st.expander("2. Chi phí Phát triển (Triệu VND)", expanded=False):
        land_cost = st.number_input("Chi phí mua đất (M&A)", value=670000, step=10000, key="inp_land")
        legal_cost = st.number_input("Chi phí SDĐ & Pháp lý", value=588338, step=10000, key="inp_legal")
        infra_cost = st.number_input("Chi phí Hạ tầng & Cảnh quan", value=62277, step=1000, key="inp_infra")
        build_cost = st.number_input("Chi phí Xây dựng & Dự phòng", value=1359987, step=10000, key="inp_build")
    
    with st.expander("3. Giả định Tài chính (Vay vốn)", expanded=False):
        ma_loan_ratio = st.slider("Tỷ lệ Vay M&A (%)", min_value=0.0, max_value=1.0, value=0.70, step=0.05, key='inp_ma_r')
        ma_int_rate = st.number_input("Lãi suất M&A/năm (%)", value=0.12, step=0.01, key='inp_ma_i')
        dev_loan_ratio = st.slider("Tỷ lệ Vay XD tối đa (%)", min_value=0.0, max_value=1.0, value=0.70, step=0.05, key='inp_dev_r')
        dev_int_rate = st.number_input("Lãi suất Vay XD/năm (%)", value=0.10, step=0.01, key='inp_dev_i')

    st.subheader("4. Ma trận Tiến độ Thu / Chi (%)")
    default_schedule = pd.DataFrame({
        "Hạng mục": ["1. Tiến độ Bán hàng", "2. Tiến độ Thu tiền", "3. Chi tiền Đất & PL", "4. Chi tiền Xây dựng", "5. Chi Bán hàng & MKT", "6. Chi phí Hoạt động"],
        "Năm 1": [50.0, 20.0, 100.0, 10.0, 50.0, 20.0], "Năm 2": [30.0, 20.0, 0.0, 30.0, 30.0, 20.0],
        "Năm 3": [20.0, 25.0, 0.0, 30.0, 20.0, 25.0], "Năm 4": [0.0, 15.0, 0.0, 15.0, 0.0, 15.0],
        "Năm 5": [0.0, 10.0, 0.0, 10.0, 0.0, 10.0], "Năm 6": [0.0, 5.0, 0.0, 5.0, 0.0, 5.0],
        "Năm 7": [0.0, 5.0, 0.0, 0.0, 0.0, 5.0], "Năm 8": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    })
    
    edited_schedule = st.data_editor(default_schedule, hide_index=True, use_container_width=True)
    sums = edited_schedule.iloc[:, 1:].sum(axis=1)
    is_valid_schedule = all(abs(s - 100.0) < 0.1 for s in sums)

# --- TIỀN XỬ LÝ DỮ LIỆU ---
if is_valid_schedule:
    total_nfa = ct_nfa + tt_nfa
    ct_ratio, tt_ratio = (ct_nfa / total_nfa, tt_nfa / total_nfa) if total_nfa > 0 else (0, 0)

    rev_ratios = edited_schedule.iloc[1, 1:].values / 100
    land_ratios = edited_schedule.iloc[2, 1:].values / 100
    build_ratios = edited_schedule.iloc[3, 1:].values / 100
    sales_mkt_ratios = edited_schedule.iloc[4, 1:].values / 100
    op_ratios = edited_schedule.iloc[5, 1:].values / 100

    settlement_year = 7
    cum_rev = 0
    for i in range(8):
        cum_rev += rev_ratios[i]
        if cum_rev >= 0.999:
            settlement_year = i; break

    def run_financial_model(price_multiplier=1.0, build_cost_multiplier=1.0):
        m_tot_rev = (ct_nfa * ct_price * price_multiplier) + (tt_nfa * tt_price * price_multiplier)
        m_build_cost = build_cost * build_cost_multiplier
        m_dev_cost = land_cost + legal_cost + infra_cost + m_build_cost + (m_build_cost * 0.05) + (m_tot_rev * 0.08)

        m_cash_in = m_tot_rev * rev_ratios
        m_cash_out_ops_total = ((land_cost + legal_cost) * land_ratios) + ((m_build_cost + infra_cost + m_build_cost * 0.05) * build_ratios) + ((m_tot_rev * 0.07) * sales_mkt_ratios) + ((m_tot_rev * 0.01) * op_ratios)

        m_ma_draws, m_ma_repays, m_ma_ints, m_dev_draws, m_dev_repays, m_dev_ints = [], [], [], [], [], []
        m_ma_bal, m_dev_bal, m_dev_drawn_tot = 0, 0, 0
        m_max_dev = (m_build_cost + infra_cost + m_build_cost * 0.05 + legal_cost) * dev_loan_ratio

        for i in range(8):
            ma_draw = ((land_cost + legal_cost) * land_ratios)[i] * ma_loan_ratio
            ma_int = m_ma_bal * ma_int_rate
            dev_int = m_dev_bal * dev_int_rate
            cads = m_cash_in[i] - m_cash_out_ops_total[i] + ma_draw - ma_int - dev_int
            
            dev_draw = min(abs(cads), max(0, m_max_dev - m_dev_drawn_tot)) if cads < 0 else 0
            dev_repay = min(cads, m_dev_bal) if cads > 0 else 0
            ma_repay = min(cads - dev_repay, m_ma_bal + ma_draw) if cads > 0 else 0
            
            m_ma_draws.append(ma_draw); m_ma_ints.append(ma_int); m_dev_ints.append(dev_int)
            m_dev_draws.append(dev_draw); m_dev_repays.append(dev_repay); m_ma_repays.append(ma_repay)
            
            m_ma_bal = m_ma_bal + ma_draw - ma_repay
            m_dev_bal = m_dev_bal + dev_draw - dev_repay
            m_dev_drawn_tot += dev_draw

        m_taxable = (m_tot_rev - m_dev_cost) - sum(m_dev_ints)
        m_tax_total = m_taxable * 0.20 if m_taxable > 0 else 0
        m_net_profit = (m_tot_rev - m_dev_cost) - sum(m_ma_ints) - sum(m_dev_ints) - m_tax_total

        m_cash_tax = [0] * 8; m_prepaid = 0
        for i in range(8):
            if i < settlement_year: m_cash_tax[i] = m_cash_in[i] * 0.01; m_prepaid += m_cash_tax[i]
            elif i == settlement_year: m_cash_tax[i] = (m_cash_in[i] * 0.01) + (m_tax_total - m_prepaid)

        m_fcff = m_cash_in - m_cash_out_ops_total - m_cash_tax 
        m_fcfe = [m_fcff[i] + m_ma_draws[i] - m_ma_repays[i] - m_ma_ints[i] + m_dev_draws[i] - m_dev_repays[i] - m_dev_ints[i] for i in range(8)]
            
        try:
            m_p_irr = npf.irr([-m_cash_out_ops_total[0]] + list(m_fcff[1:])) if m_fcff[0] > 0 else npf.irr(m_fcff)
            m_e_irr = npf.irr([-abs(m_fcfe[0])] + list(m_fcfe[1:])) if m_fcfe[0] > 0 else npf.irr(m_fcfe)
        except: m_p_irr, m_e_irr = None, None
            
        return {
            "tot_rev": m_tot_rev, "dev_cost": m_dev_cost, "profit_gross": m_tot_rev - m_dev_cost, "net_profit": m_net_profit,
            "fcfe": m_fcfe, "cum_fcfe": pd.Series(m_fcfe).cumsum().tolist(),
            "project_irr": m_p_irr, "equity_irr": m_e_irr,
            "max_negative_cashflow": min(m_fcfe)
        }

    base = run_financial_model(1.0, 1.0)
    irr_p_disp = f"{base['project_irr'] * 100:.1f}%" if base['project_irr'] else "N/A"
    irr_e_disp = f"{base['equity_irr'] * 100:.1f}%" if base['equity_irr'] else "N/A"

# --- HIỂN THỊ KẾT QUẢ ---
with col_result:
    if not is_valid_schedule: st.error("Vui lòng sửa bảng Tiến độ bên trái sao cho tổng mỗi hàng bằng 100%.")
    else:
        tab1, tab2, tab3, tab4 = st.tabs(["📊 P&L", "🗓️ Dòng Tiền", "📉 Độ Nhạy", "🤖 AI Nhận Định & Chat"])
        
        with tab1:
            st.subheader("Dự Phóng Kết Quả Kinh Doanh (P&L)")
            # (Rút gọn hiển thị để tập trung tab AI, bạn có thể bổ sung lại các hàm row_pl chi tiết nếu muốn)
            st.metric("Lợi Nhuận Sau Thuế (NPAT)", f"{base['net_profit']:,.0f} Tr")
            st.metric("Tỷ suất LNST / Doanh Thu", f"{(base['net_profit']/base['tot_rev'])*100:.1f} %")

        with tab2:
            st.subheader("Biểu đồ Dòng Tiền Lũy Kế (FCFE)")
            c1, c2 = st.columns(2)
            c1.info(f"🎯 **Project IRR: {irr_p_disp}**")
            c2.success(f"💰 **Equity IRR: {irr_e_disp}**")
            
            years = [f"Năm {i+1}" for i in range(8)]
            fig = go.Figure()
            fig.add_trace(go.Bar(x=years, y=base['fcfe'], name="Dòng Tiền Thực tế Từng Năm", marker_color="#2ECC71"))
            fig.add_trace(go.Scatter(x=years, y=base['cum_fcfe'], name="Dòng Tiền Lũy Kế", line=dict(color="#E74C3C", width=3), mode="lines+markers"))
            st.plotly_chart(fig, use_container_width=True)

        with tab3:
            st.info("Tính năng mô phỏng đang chạy ngầm...")

        # ================= TAB 4: AI FINANCIAL ANALYST =================
        with tab4:
            st.subheader("🤖 Trợ lý AI Phân Tích Báo Cáo Tài Chính")
            st.markdown("Hệ thống sẽ tổng hợp số liệu P&L và Dòng tiền để viết **Executive Summary** cho Ban Lãnh đạo.")
            
            # Khối dữ liệu Context gửi cho AI
            financial_context = f"""
            DỮ LIỆU TÀI CHÍNH DỰ ÁN BĐS 8 NĂM:
            - Tổng doanh thu: {base['tot_rev']:,.0f} Triệu VND
            - Tổng chi phí: {base['dev_cost']:,.0f} Triệu VND
            - Lợi nhuận sau thuế (NPAT): {base['net_profit']:,.0f} Triệu VND
            - Project IRR (Trước vay): {irr_p_disp}
            - Equity IRR (Sau vay): {irr_e_disp}
            - Điểm trũng dòng tiền sâu nhất: {base['max_negative_cashflow']:,.0f} Triệu VND
            - Dòng tiền các năm 1 đến 8: {[f"{v:,.0f}" for v in base['fcfe']]}
            """

            if st.button("📝 Viết Executive Summary", type="primary"):
                if api_key == "":
                    st.error("Vui lòng nhập API Key ở cột bên trái trước!")
                else:
                    with st.spinner("AI đang viết báo cáo..."):
                        try:
                            genai.configure(api_key=api_key)
                            valid_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                            best_model = next((m for m in valid_models if 'flash' in m or 'pro' in m), valid_models[0]) if valid_models else None
                            
                            model = genai.GenerativeModel(best_model)
                            prompt = f"""
                            Bạn là một Giám đốc Tài chính (CFO) xuất sắc. Hãy dựa vào dữ liệu sau để viết Executive Summary ngắn gọn (khoảng 150-200 chữ):
                            {financial_context}
                            Yêu cầu:
                            1. Nêu rõ mức độ hiệu quả (IRR, Biên lợi nhuận).
                            2. Nhận định rủi ro dòng tiền (năm nào âm nặng nhất, điểm hòa vốn năm thứ mấy).
                            3. Đưa ra 1 khuyến nghị tối ưu (ví dụ: cần bán hàng nhanh hơn, hoặc đẩy mạnh thu tiền...).
                            """
                            response = model.generate_content(prompt)
                            st.session_state.executive_summary = response.text
                        except Exception as e:
                            st.error(f"Lỗi kết nối API: {e}")

            if st.session_state.executive_summary != "":
                st.info(st.session_state.executive_summary)
            
            st.divider()
            st.markdown("#### 💬 Chat trực tiếp với Số liệu Dự án")
            
            # Hiển thị lịch sử chat
            for message in st.session_state.chat_history:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

            # Khung nhập chat
            if user_q := st.chat_input("Hỏi AI (VD: Tại sao dòng tiền năm 2 lại âm?)"):
                if api_key == "":
                    st.error("Vui lòng nhập API Key!")
                else:
                    # Lưu câu hỏi của người dùng
                    st.session_state.chat_history.append({"role": "user", "content": user_q})
                    with st.chat_message("user"): st.markdown(user_q)

                    # Gửi câu hỏi + Context cho AI
                    with st.chat_message("assistant"):
                        with st.spinner("Đang phân tích..."):
                            try:
                                genai.configure(api_key=api_key)
                                valid_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                                best_model = next((m for m in valid_models if 'flash' in m or 'pro' in m), valid_models[0])
                                
                                model = genai.GenerativeModel(best_model)
                                chat_prompt = f"Ngữ cảnh số liệu dự án:\n{financial_context}\nCâu hỏi của Giám đốc: {user_q}\nHãy trả lời chuyên nghiệp, đi thẳng vào số liệu."
                                
                                answer = model.generate_content(chat_prompt).text
                                st.markdown(answer)
                                st.session_state.chat_history.append({"role": "assistant", "content": answer})
                            except Exception as e:
                                st.error(f"Lỗi: {e}")
