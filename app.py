import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy_financial as npf
import io
import google.generativeai as genai

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Phân tích FS & Dòng Tiền", page_icon="🏢", layout="wide")

# --- HÀM FORMAT CHUẨN KẾ TOÁN ---
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

# --- HÀM TÔ MÀU BẢNG (PANDAS STYLING) ---
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
    
    # --- KHU VỰC AI TRỢ LÝ ---
    with st.expander("🤖 AI Trợ Lý Khảo Sát Giá (Gemini)", expanded=False):
        st.markdown("*Nhập vị trí để AI đề xuất mức giá bán hợp lý dựa trên dữ liệu thị trường.*")
        api_key = st.text_input("Nhập Google Gemini API Key:", type="password", key="ai_key")
        location = st.text_input("Vị trí dự án:", value="Phường An Lạc, Bình Tân", key="ai_loc")
        proj_type = st.selectbox("Loại hình SP:", ["Căn hộ trung cấp", "Căn hộ cao cấp", "Nhà phố liền kề", "Biệt thự"], key="ai_type")
        
        if st.button("🔍 Yêu cầu AI Khảo sát", type="primary", key="btn_ai"):
            if api_key == "":
                st.warning("Vui lòng nhập API Key trước!")
            else:
                with st.spinner("AI đang tổng hợp dữ liệu thị trường..."):
                    try:
genai.configure(api_key=api_key)
                        
                        # Tự động quét các model mà API Key của bạn được cấp quyền
                        valid_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                        
                        if not valid_models:
                            st.error("API Key của bạn chưa được cấp quyền dùng AI tạo văn bản. Hãy thử tạo Key mới nhé!")
                        else:
                            # Tự động chọn model phù hợp nhất (ưu tiên dòng flash hoặc pro)
                            best_model = valid_models[0]
                            for m_name in valid_models:
                                if 'flash' in m_name or 'pro' in m_name:
                                    best_model = m_name
                                    break
                            
                            model = genai.GenerativeModel(best_model)
                            
                            prompt = f"""
                            Bạn là một Giám đốc Nghiên cứu Thị trường Bất động sản tại Việt Nam.
                            Hãy phân tích ngắn gọn thị trường {proj_type} tại khu vực {location}.
                            Yêu cầu trả lời:
                            1. Phân tích ưu/nhược điểm vị trí này.
                            2. Kể tên 2-3 dự án đối thủ cạnh tranh lân cận và mức giá của họ (Triệu VND/m2).
                            3. Đề xuất mức giá bán dự kiến (Min - Max) cho dự án mới tại đây (Triệu VND/m2).
                            """
                            response = model.generate_content(prompt)
                            st.success(f"Khảo sát hoàn tất! (Sử dụng AI: {best_model})")
                            st.markdown(response.text)
                    except Exception as e:
                        st.error(f"Có lỗi xảy ra: Xin kiểm tra lại API Key. (Chi tiết: {e})")
    
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
        st.markdown("**Vay M&A (Mua đất)** - *Lãi không được khấu trừ thuế*")
        ma_loan_ratio = st.slider("Tỷ lệ Vay M&A (%)", min_value=0.0, max_value=1.0, value=0.70, step=0.05, key='inp_ma_r')
        ma_int_rate = st.number_input("Lãi suất M&A/năm (%)", value=0.12, step=0.01, key='inp_ma_i')
        
        st.markdown("**Vay Xây dựng & Phát triển** - *Giải ngân khi thiếu tiền*")
        dev_loan_ratio = st.slider("Tỷ lệ Vay XD tối đa (%)", min_value=0.0, max_value=1.0, value=0.70, step=0.05, key='inp_dev_r')
        dev_int_rate = st.number_input("Lãi suất Vay XD/năm (%)", value=0.10, step=0.01, key='inp_dev_i')

    st.subheader("4. Ma trận Tiến độ Thu / Chi (%)")
    
    default_schedule = pd.DataFrame({
        "Hạng mục": [
            "1. Tiến độ Bán hàng (Ký HĐMB)",
            "2. Tiến độ Thu tiền Khách hàng", 
            "3. Chi tiền Đất (M&A) & Pháp lý", 
            "4. Chi tiền Xây dựng & QLDA", 
            "5. Chi Bán hàng & Marketing",
            "6. Chi phí Hoạt động (OPEX)"
        ],
        "Năm 1": [50.0, 20.0, 100.0, 10.0, 50.0, 20.0],
        "Năm 2": [30.0, 20.0,   0.0, 30.0, 30.0, 20.0],
        "Năm 3": [20.0, 25.0,   0.0, 30.0, 20.0, 25.0],
        "Năm 4": [ 0.0, 15.0,   0.0, 15.0,  0.0, 15.0],
        "Năm 5": [ 0.0, 10.0,   0.0, 10.0,  0.0, 10.0],
        "Năm 6": [ 0.0,  5.0,   0.0,  5.0,  0.0,  5.0],
        "Năm 7": [ 0.0,  5.0,   0.0,  0.0,  0.0,  5.0],
        "Năm 8": [ 0.0,  0.0,   0.0,  0.0,  0.0,  0.0]
    })
    
    edited_schedule = st.data_editor(
        default_schedule, hide_index=True, use_container_width=True,
        column_config={
            "Hạng mục": st.column_config.Column(disabled=True, width="medium"),
            "Năm 1": st.column_config.NumberColumn(format="%.0f%%"), "Năm 2": st.column_config.NumberColumn(format="%.0f%%"),
            "Năm 3": st.column_config.NumberColumn(format="%.0f%%"), "Năm 4": st.column_config.NumberColumn(format="%.0f%%"),
            "Năm 5": st.column_config.NumberColumn(format="%.0f%%"), "Năm 6": st.column_config.NumberColumn(format="%.0f%%"),
            "Năm 7": st.column_config.NumberColumn(format="%.0f%%"), "Năm 8": st.column_config.NumberColumn(format="%.0f%%"),
        }
    )
    
    sums = edited_schedule.iloc[:, 1:].sum(axis=1)
    is_valid_schedule = all(abs(s - 100.0) < 0.1 for s in sums)

# --- TIỀN XỬ LÝ DỮ LIỆU ---
if is_valid_schedule:
    total_nfa = ct_nfa + tt_nfa
    ct_ratio = ct_nfa / total_nfa if total_nfa > 0 else 0
    tt_ratio = tt_nfa / total_nfa if total_nfa > 0 else 0

    sales_ratios = edited_schedule.iloc[0, 1:].values / 100
    rev_ratios = edited_schedule.iloc[1, 1:].values / 100
    land_ratios = edited_schedule.iloc[2, 1:].values / 100
    build_ratios = edited_schedule.iloc[3, 1:].values / 100
    sales_mkt_ratios = edited_schedule.iloc[4, 1:].values / 100
    op_ratios = edited_schedule.iloc[5, 1:].values / 100

    # Tìm năm quyết toán thuế tự động
    cumulative_rev = 0
    settlement_year = 7
    for i in range(8):
        cumulative_rev += rev_ratios[i]
        if cumulative_rev >= 0.999:
            settlement_year = i
            break

    # --- HÀM MÔ PHỎNG TÀI CHÍNH ---
    def run_financial_model(price_multiplier=1.0, build_cost_multiplier=1.0):
        m_ct_rev = ct_nfa * (ct_price * price_multiplier)
        m_tt_rev = tt_nfa * (tt_price * price_multiplier)
        m_tot_rev = m_ct_rev + m_tt_rev

        m_build_cost = build_cost * build_cost_multiplier
        m_sales_cost = m_tot_rev * 0.04
        m_mkt_cost = m_tot_rev * 0.03
        m_op_cost = m_tot_rev * 0.01
        m_soft_cost = m_build_cost * 0.05
        m_dev_cost = land_cost + legal_cost + infra_cost + m_build_cost + m_soft_cost + m_sales_cost + m_mkt_cost + m_op_cost

        m_cash_in = m_tot_rev * rev_ratios
        m_cash_out_land = (land_cost + legal_cost) * land_ratios
        m_cash_out_build = (m_build_cost + infra_cost + m_soft_cost) * build_ratios
        m_cash_out_sales_mkt = (m_sales_cost + m_mkt_cost) * sales_mkt_ratios
        m_cash_out_op = m_op_cost * op_ratios
        m_cash_out_ops_total = m_cash_out_land + m_cash_out_build + m_cash_out_sales_mkt + m_cash_out_op

        m_ma_draws, m_ma_repays, m_ma_ints = [], [], []
        m_dev_draws, m_dev_repays, m_dev_ints = [], [], []
        m_ma_bal, m_dev_bal, m_dev_drawn_tot = 0, 0, 0
        m_max_dev = (m_build_cost + infra_cost + m_soft_cost + legal_cost) * dev_loan_ratio

        for i in range(8):
            ma_draw = m_cash_out_land[i] * ma_loan_ratio
            m_ma_draws.append(ma_draw)
            ma_int = m_ma_bal * ma_int_rate
            m_ma_ints.append(ma_int)
            dev_int = m_dev_bal * dev_int_rate
            m_dev_ints.append(dev_int)
            
            cads = m_cash_in[i] - m_cash_out_ops_total[i] + ma_draw - ma_int - dev_int
            dev_draw = 0; dev_repay = 0; ma_repay = 0
            
            if cads < 0:
                shortfall = abs(cads)
                avail_dev = max(0, m_max_dev - m_dev_drawn_tot)
                dev_draw = min(shortfall, avail_dev)
            elif cads > 0:
                dev_repay = min(cads, m_dev_bal)
                rem_cash = cads - dev_repay
                ma_repay = min(rem_cash, m_ma_bal + ma_draw) 
                
            m_dev_draws.append(dev_draw)
            m_dev_repays.append(dev_repay)
            m_ma_repays.append(ma_repay)
            
            m_ma_bal = m_ma_bal + ma_draw - ma_repay
            m_dev_bal = m_dev_bal + dev_draw - dev_repay
            m_dev_drawn_tot += dev_draw

        m_total_ma_int = sum(m_ma_ints)
        m_total_dev_int = sum(m_dev_ints)
        m_total_int = m_total_ma_int + m_total_dev_int
        
        m_profit_gross = m_tot_rev - m_dev_cost
        m_taxable = m_profit_gross - m_total_dev_int 
        m_tax_total = m_taxable * 0.20 if m_taxable > 0 else 0
        m_pbt_display = m_profit_gross - m_total_int
        m_net_profit = m_pbt_display - m_tax_total

        m_cash_tax = [0] * 8
        m_prepaid = 0
        for i in range(8):
            if i < settlement_year:
                t = m_cash_in[i] * 0.01
                m_cash_tax[i] = t
                m_prepaid += t
            elif i == settlement_year:
                m_cash_tax[i] = (m_cash_in[i] * 0.01) + (m_tax_total - m_prepaid)
            else:
                m_cash_tax[i] = 0

        m_fcff = m_cash_in - m_cash_out_ops_total - m_cash_tax 
        m_fcfe = []
        for i in range(8):
            cf = m_fcff[i] + m_ma_draws[i] - m_ma_repays[i] - m_ma_ints[i] + m_dev_draws[i] - m_dev_repays[i] - m_dev_ints[i]
            m_fcfe.append(cf)
            
        try:
            m_project_irr = npf.irr([-m_cash_out_ops_total[0]] + list(m_fcff[1:])) if m_fcff[0] > 0 else npf.irr(m_fcff)
            m_equity_irr = npf.irr([-abs(m_fcfe[0])] + list(m_fcfe[1:])) if m_fcfe[0] > 0 else npf.irr(m_fcfe)
        except:
            m_project_irr = None
            m_equity_irr = None
            
        return {
            "tot_rev": m_tot_rev, "ct_rev": m_ct_rev, "tt_rev": m_tt_rev, "dev_cost": m_dev_cost,
            "build_cost": m_build_cost, "soft_cost": m_soft_cost, "sales_cost": m_sales_cost, "mkt_cost": m_mkt_cost, "op_cost": m_op_cost,
            "cash_in": m_cash_in, "cash_out_land": m_cash_out_land, "cash_out_build": m_cash_out_build, "cash_out_sales_mkt": m_cash_out_sales_mkt,
            "cash_out_op": m_cash_out_op, "cash_out_ops_total": m_cash_out_ops_total,
            "ma_draws": m_ma_draws, "ma_repays": m_ma_repays, "ma_ints": m_ma_ints,
            "dev_draws": m_dev_draws, "dev_repays": m_dev_repays, "dev_ints": m_dev_ints,
            "total_int": m_total_int, "total_ma_int": m_total_ma_int, "total_dev_int": m_total_dev_int,
            "profit_gross": m_profit_gross, "tax_total": m_tax_total, "pbt_display": m_pbt_display, "net_profit": m_net_profit,
            "cash_tax": m_cash_tax, "fcff": m_fcff, "fcfe": m_fcfe, "cum_fcfe": pd.Series(m_fcfe).cumsum().tolist(),
            "project_irr": m_project_irr, "equity_irr": m_equity_irr
        }

    base = run_financial_model(1.0, 1.0)
    irr_p_disp = f"{base['project_irr'] * 100:.1f}%" if base['project_irr'] else "N/A"
    irr_e_disp = f"{base['equity_irr'] * 100:.1f}%" if base['equity_irr'] else "N/A"

# --- HIỂN THỊ KẾT QUẢ ---
with col_result:
    if not is_valid_schedule:
        st.error("Vui lòng sửa bảng Tiến độ bên trái sao cho tổng mỗi hàng bằng 100%.")
    else:
        tab1, tab2, tab3 = st.tabs(["📊 P&L Chi Tiết", "🗓️ Dòng Tiền & Vay Vốn", "📉 Phân Tích Độ Nhạy"])
        
        with tab1:
            st.subheader("Dự Phóng Kết Quả Kinh Doanh (P&L)")
            
            def row_pl(name, tot, ct=None, tt=None, is_pct=False):
                if is_pct: return [name, f"{tot:.1f}%", "", "", f"{ct:.1f}%" if ct else "", "", f"{tt:.1f}%" if tt else "", ""]
                return [name, tot, tot/gfa if gfa else 0, tot/total_nfa if total_nfa else 0, ct, ct/ct_nfa if ct and ct_nfa else "", tt, tt/tt_nfa if tt and tt_nfa else ""]

            data_pl = [
                row_pl("DOANH THU THUẦN", base['tot_rev'], base['ct_rev'], base['tt_rev']),
                row_pl("TỔNG CHI PHÍ PHÁT TRIỂN", -base['dev_cost'], -base['dev_cost']*ct_ratio, -base['dev_cost']*tt_ratio),
                row_pl("  - CP mua đất (M&A)", -land_cost, -land_cost*ct_ratio, -land_cost*tt_ratio),
                row_pl("  - CP tiền SDĐ + pháp lý", -legal_cost, -legal_cost*ct_ratio, -legal_cost*tt_ratio),
                row_pl("  - CP hạ tầng + cảnh quan", -infra_cost, -infra_cost*ct_ratio, -infra_cost*tt_ratio),
                row_pl("  - CP xây dựng + dự phòng", -base['build_cost'], -base['build_cost']*ct_ratio, -base['build_cost']*tt_ratio),
                row_pl("  - CP thiết kế, QLDA", -base['soft_cost'], -base['soft_cost']*ct_ratio, -base['soft_cost']*tt_ratio),
                row_pl("  - CP bán hàng", -base['sales_cost'], -base['sales_cost']*ct_ratio, -base['sales_cost']*tt_ratio),
                row_pl("  - CP marketing", -base['mkt_cost'], -base['mkt_cost']*ct_ratio, -base['mkt_cost']*tt_ratio),
                row_pl("  - CP hoạt động", -base['op_cost'], -base['op_cost']*ct_ratio, -base['op_cost']*tt_ratio),
                row_pl("LỢI NHUẬN GỘP (EBITDA)", base['profit_gross'], base['profit_gross']*ct_ratio, base['profit_gross']*tt_ratio),
                row_pl("Chi phí Lãi vay (M&A + XD)", -base['total_int'], -base['total_int']*ct_ratio, -base['total_int']*tt_ratio),
                row_pl("LỢI NHUẬN TRƯỚC THUẾ (PBT)", base['pbt_display'], base['pbt_display']*ct_ratio, base['pbt_display']*tt_ratio),
                row_pl("Thuế CIT", -base['tax_total'], -base['tax_total']*ct_ratio, -base['tax_total']*tt_ratio),
                row_pl("LỢI NHUẬN SAU THUẾ (NPAT)", base['net_profit'], base['net_profit']*ct_ratio, base['net_profit']*tt_ratio),
                row_pl("% LNST / Doanh thu", (base['net_profit']/base['tot_rev'])*100 if base['tot_rev'] else 0, is_pct=True)
            ]
            
            df_pl = pd.DataFrame(data_pl, columns=["Hạng mục", "Toàn DA (Tổng)", "Toàn DA (/m2 GFA)", "Toàn DA (/m2 NFA)", "Cao tầng (Tổng)", "Cao tầng (/m2 NFA)", "Thấp tầng (Tổng)", "Thấp tầng (/m2 NFA)"])
            for c in ["Toàn DA (Tổng)", "Cao tầng (Tổng)", "Thấp tầng (Tổng)"]: df_pl[c] = df_pl[c].apply(format_acc)
            for c in ["Toàn DA (/m2 GFA)", "Toàn DA (/m2 NFA)", "Cao tầng (/m2 NFA)", "Thấp tầng (/m2 NFA)"]: df_pl[c] = df_pl[c].apply(format_unit)
            st.dataframe(df_pl.style.apply(style_pl, axis=1), use_container_width=True, hide_index=True)

        with tab2:
            st.subheader("Bảng Lưu chuyển Tiền tệ & Lịch trả nợ (8 Năm)")
            c1, c2 = st.columns(2)
            c1.info(f"🎯 **Project IRR (Trước vay): {irr_p_disp}**")
            c2.success(f"💰 **Equity IRR (Sau vay): {irr_e_disp}**")
            
            years = [f"Năm {i+1}" for i in range(8)]
            data_cf = {"Hạng mục": [
                "I. DÒNG TIỀN VÀO (Thu bán hàng)", 
                "II. DÒNG TIỀN RA (HĐKD)", 
                "  - Tiền Đất & Pháp lý", "  - Chi phí Xây dựng", "  - Chi phí Vận hành & Bán hàng", "  - Thuế TNDN (Cash Tax)",
                "III. DÒNG TIỀN THUẦN (TRƯỚC TÀI CHÍNH)",
                "IV. DÒNG TIỀN TÀI CHÍNH (VAY & TRẢ NỢ)",
                "  + Giải ngân Vay M&A", "  - Trả gốc Vay M&A", "  - Trả lãi Vay M&A",
                "  + Giải ngân Vay Xây dựng", "  - Trả gốc Vay Xây dựng", "  - Trả lãi Vay Xây dựng",
                "V. DÒNG TIỀN THUẦN (SAU TÀI CHÍNH)",
                "VI. DÒNG TIỀN LŨY KẾ (FCFE)"
            ]}
            
            for i, year in enumerate(years):
                data_cf[year] = [
                    base['cash_in'][i],
                    -(base['cash_out_ops_total'][i] + base['cash_tax'][i]),
                    -base['cash_out_land'][i], -base['cash_out_build'][i], -(base['cash_out_sales_mkt'][i] + base['cash_out_op'][i]), -base['cash_tax'][i],
                    base['fcff'][i],
                    base['ma_draws'][i] - base['ma_repays'][i] - base['ma_ints'][i] + base['dev_draws'][i] - base['dev_repays'][i] - base['dev_ints'][i],
                    base['ma_draws'][i], -base['ma_repays'][i], -base['ma_ints'][i],
                    base['dev_draws'][i], -base['dev_repays'][i], -base['dev_ints'][i],
                    base['fcfe'][i],
                    base['cum_fcfe'][i]
                ]
            
            data_cf["TỔNG CỘNG"] = [sum(data_cf[y][i] for y in years) for i in range(len(data_cf["Hạng mục"]))]
            data_cf["TỔNG CỘNG"][-1] = data_cf["Năm 8"][-1] 
            
            df_cf = pd.DataFrame(data_cf)
            for col in years + ["TỔNG CỘNG"]: df_cf[col] = df_cf[col].apply(format_acc)
            st.dataframe(df_cf.style.apply(style_cf, axis=1), use_container_width=True, hide_index=True)
            
            fig = go.Figure()
            fig.add_trace(go.Bar(x=years, y=base['fcfe'], name="Dòng Tiền Thực tế Từng Năm", marker_color="#2ECC71"))
            fig.add_trace(go.Scatter(x=years, y=base['cum_fcfe'], name="Dòng Tiền Lũy Kế", line=dict(color="#E74C3C", width=3), mode="lines+markers"))
            fig.update_layout(title="Biểu Đồ Lũy Kế Dòng Tiền Vốn Chủ (Sau Vay)", barmode='group')
            st.plotly_chart(fig, use_container_width=True)

        with tab3:
            st.subheader("Bảng Ma trận Phân tích Độ nhạy (Sensitivity Analysis)")
            st.markdown("Đánh giá sự biến thiên của **Project IRR** và **Lợi nhuận ròng** khi **Giá bán** và **Chi phí Xây dựng** thay đổi.")
            
            variations = [0.9, 0.95, 1.0, 1.05, 1.1]
            col_labels = [f"Giá bán {'+' if v>1 else ''}{int((v-1)*100)}%" if v!=1 else "Giá bán (Gốc)" for v in variations]
            row_labels = [f"Chi phí XD {'+' if v>1 else ''}{int((v-1)*100)}%" if v!=1 else "Chi phí XD (Gốc)" for v in variations]
            
            irr_matrix = []
            npat_matrix = []
            
            for cost_adj in variations:
                irr_row = []
                npat_row = []
                for price_adj in variations:
                    sim_result = run_financial_model(price_multiplier=price_adj, build_cost_multiplier=cost_adj)
                    irr_row.append(sim_result['project_irr'])
                    npat_row.append(sim_result['net_profit'])
                irr_matrix.append(irr_row)
                npat_matrix.append(npat_row)
                
            st.markdown("#### Kịch bản 1: Tác động lên tỷ suất sinh lời Project IRR")
            df_sens_irr = pd.DataFrame(irr_matrix, index=row_labels, columns=col_labels)
            st.dataframe(
                df_sens_irr.style.format("{:.1%}", na_rep="N/A")
                                 .background_gradient(cmap='RdYlGn', axis=None),
                use_container_width=True
            )
            
            st.markdown("#### Kịch bản 2: Tác động lên Lợi nhuận sau thuế - NPAT (Triệu VND)")
            df_sens_npat = pd.DataFrame(npat_matrix, index=row_labels, columns=col_labels)
            st.dataframe(
                df_sens_npat.style.format("{:,.0f}")
                                  .background_gradient(cmap='RdYlGn', axis=None),
                use_container_width=True
            )


