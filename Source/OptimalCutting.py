import time
import tracemalloc
from amplpy import AMPL, ampl_notebook
import pandas as pd
import matplotlib.pyplot as plt

# Bắt đầu đo thời gian và bộ nhớ
start_time = time.time()
tracemalloc.start()

# Khởi tạo đối tượng AMPL
SOLVER_MILO = "highs"
SOLVER_MINLO = "ipopt"

ampl = ampl_notebook(
    modules=["coin", "highs"],  # Các module cần cài đặt
    license_uuid="default",     # Giấy phép sử dụng
)  # Khởi tạo đối tượng AMPL và đăng ký các magic functions

def make_patterns(stocks, finish):
    """
    Tạo các mẫu cắt có thể thực hiện từ các chiều dài của kho đến các chiều dài hoàn thiện yêu cầu.

    Parameters:
    stocks (dict): Từ điển với các khóa là định danh kho và giá trị là từ điển chứa
                   chiều dài của từng kho.
    finish (dict): Từ điển với các khóa là định danh hoàn thiện và giá trị là từ điển chứa
                   chiều dài yêu cầu của từng hoàn thiện.

    Returns:
    patterns (list): Danh sách các từ điển, mỗi từ điển đại diện cho một mẫu cắt.
    """

    patterns = []
    for f in finish:
        feasible = False
        for s in stocks:
            # Tính số lượng cắt có thể thực hiện từ kho s để đáp ứng yêu cầu của f
            num_cuts = int(stocks[s]["length"] / finish[f]["length"])

            if num_cuts > 0:
                feasible = True
                cuts_dict = {key: 0 for key in finish.keys()}
                cuts_dict[f] = num_cuts
                patterns.append({"stock": s, "cuts": cuts_dict})

        if not feasible:
            print(f"No feasible pattern was found for {f}")
            return []

    return patterns

def plot_patterns(stocks, finish, patterns):
    """
    Vẽ đồ thị các mẫu cắt.

    Parameters:
    stocks (dict): Từ điển với các khóa là định danh kho và giá trị là từ điển chứa
                   chiều dài của từng kho.
    finish (dict): Từ điển với các khóa là định danh hoàn thiện và giá trị là từ điển chứa
                   chiều dài yêu cầu của từng hoàn thiện.
    patterns (list): Danh sách các mẫu cắt cần vẽ.

    Returns:
    ax (matplotlib.axes.Axes): Đối tượng trục của đồ thị.
    """

    lw = 0.6
    cmap = plt.get_cmap("tab10")
    colors = {f: cmap(k % 10) for k, f in enumerate(finish.keys())}
    fig, ax = plt.subplots(1, 1, figsize=(8, 0.05 + 0.4 * len(patterns)))

    for k, pattern in enumerate(patterns):
        s = pattern["stock"]
        y_lo = (-k - lw / 2, -k - lw / 2)
        y_hi = (-k + lw / 2, -k + lw / 2)
        ax.fill_between((0, stocks[s]["length"]), y_lo, y_hi, color="k", alpha=0.1)

        xa = 0
        for f, n in pattern["cuts"].items():
            for j in range(n):
                xb = xa + finish[f]["length"]
                ax.fill_between((xa, xb), y_lo, y_hi, alpha=1.0, color=colors[f])
                ax.plot((xb, xb), (y_lo[0], y_hi[0]), "w", lw=1, solid_capstyle="butt")
                ax.text(
                    (xa + xb) / 2,
                    -k,
                    f,
                    ha="center",
                    va="center",
                    fontsize=6,
                    color="w",
                    weight="bold",
                )
                xa = xb

    ax.spines[["top", "right", "left", "bottom"]].set_visible(False)
    ax.set_yticks(
        range(0, -len(patterns), -1),
        [pattern["stock"] for pattern in patterns],
        fontsize=8,
    )

    return ax

def cut_patterns(stocks, finish, patterns):
    """
    Tìm lựa chọn mẫu cắt tối thiểu để đáp ứng nhu cầu hoàn thiện.

    Parameters:
    stocks (dict): Từ điển với các khóa là định danh kho và giá trị là từ điển chứa
                   chiều dài của từng kho.
    finish (dict): Từ điển với các khóa là định danh hoàn thiện và giá trị là từ điển chứa
                   chiều dài yêu cầu của từng hoàn thiện.
    patterns (list): Danh sách các mẫu cắt.

    Returns:
    x (list): Danh sách số lượng mỗi mẫu cắt được chọn.
    cost (float): Chi phí tổng cộng.
    """

    m = AMPL()
    m.eval(
        """
        set S;
        set F;
        set P;

        param c{P};
        param a{F, P};
        param demand_finish{F};

        var x{P} integer >= 0;

        minimize cost:
            sum{p in P} c[p]*x[p];

        subject to demand{f in F}:
            sum{p in P} a[f,p]*x[p] >= demand_finish[f];
        """
    )

    m.set["S"] = list(stocks.keys())
    m.set["F"] = list(finish.keys())
    m.set["P"] = list(range(len(patterns)))

    s = {p: patterns[p]["stock"] for p in range(len(patterns))}
    c = {p: stocks[s[p]]["cost"] for p in range(len(patterns))}
    m.param["c"] = c
    a = {
        (f, p): patterns[p]["cuts"][f]
        for p in range(len(patterns))
        for f in finish.keys()
    }
    m.param["a"] = a
    m.param["demand_finish"] = {
        f_part: finish[f_part]["demand"] for f_part in finish.keys()
    }

    m.option["solver"] = SOLVER_MILO
    m.get_output("solve;")

    return [m.var["x"][p].value() for p in range(len(patterns))], m.obj["cost"].value()

def plot_nonzero_patterns(stocks, finish, patterns, x, cost):
    """
    Vẽ đồ thị các mẫu cắt không bằng không.

    Parameters:
    stocks (dict): Từ điển với các khóa là định danh kho và giá trị là từ điển chứa
                   chiều dài của từng kho.
    finish (dict): Từ điển với các khóa là định danh hoàn thiện và giá trị là từ điển chứa
                   chiều dài yêu cầu của từng hoàn thiện.
    patterns (list): Danh sách các mẫu cắt.
    x (list): Danh sách số lượng mỗi mẫu cắt được chọn.
    cost (float): Chi phí tổng cộng.

    Returns:
    ax (matplotlib.axes.Axes): Đối tượng trục của đồ thị.
    """

    k = [j for j, _ in enumerate(x) if _ > 0]
    ax = plot_patterns(stocks, finish, [patterns[j] for j in k])
    ticks = [
        f"{x[k]} x {pattern['stock']}" for k, pattern in enumerate(patterns) if x[k] > 0
    ]
    ax.set_yticks(range(0, -len(k), -1), ticks, fontsize=8)
    ax.set_title(f"Cost = {round(cost,2)}", fontsize=10)
    return ax

def display(df):
    """
    Hiển thị DataFrame theo định dạng đẹp mắt.

    Parameters:
    df (pandas.DataFrame): DataFrame cần hiển thị
    """
    with pd.option_context('display.max_rows', None, 'display.max_columns', None):
        print(df.to_string(index=False))
    print()

def displayP(patterns):
    """
    Hiển thị các mẫu cắt dưới dạng bảng.

    Parameters:
    patterns (list): Danh sách các mẫu cắt.
    """
    if not patterns:
        print("No patterns found.")
        return

    # In tiêu đề
    print("| Stock | Cuts |")
    print("| ----- | ---- |")

    # In từng mẫu cắt
    for pattern in patterns:
        stock = pattern["stock"]
        cuts_str = " | ".join(f"{finish_id}: {num_cuts}" for finish_id, num_cuts in pattern["cuts"].items())
        print(f"| {stock} | {cuts_str} |")

def read_google_sheet(sheet_id, sheet_name):
    """
    Đọc dữ liệu từ Google Sheet và trả về pandas DataFrame.

    Parameters:
    sheet_id (str): ID của Google Sheet.
    sheet_name (str): Tên của sheet cần đọc.

    Returns:
    df (pd.DataFrame): Pandas DataFrame chứa dữ liệu từ Google Sheet.
    """
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    df = pd.read_csv(url)
    df.columns = map(str.lower, df.columns)
    return df

# Google Sheet ID
sheet_id = "1JsjTA12Oq-GGrfBYDMAsTo_XPLtX-Fg7obCe-WP0UmE"

# Đọc dữ liệu từ Google Sheets
finish_df = read_google_sheet(sheet_id, "finish")
print("\nFinish")
display(finish_df)

stocks_df = read_google_sheet(sheet_id, "stocks")
if "price" not in stocks_df.columns:
    stocks_df["price"] = stocks_df["length"]
print("\nStocks")
display(stocks_df)

# Chuyển đổi dữ liệu từ DataFrame sang dict
tempfinish = dict()
for column in ["length", "quantity", "label"]:
    tempfinish[column] = finish_df[column].tolist()

finish = {}
for i in range(len(tempfinish["label"])):
    finish[tempfinish["label"][i]] = {
        "length": tempfinish["length"][i],
        "demand": tempfinish["quantity"][i],
    }

tempstocks = dict()
for column in ["length", "price"]:
    tempstocks[column] = stocks_df[column].tolist()
stocks = {}
for i in range(len(tempstocks["length"])):
    stocks[tempstocks["length"][i]] = {
        "length": tempstocks["length"][i],
        "cost": tempstocks["price"][i],
    }

patterns = make_patterns(stocks, finish)
print("\nPatterns")
displayP(patterns)

# Lấy snapshot bộ nhớ trước khi thực hiện cắt
snapshot1 = tracemalloc.take_snapshot()

x, cost = cut_patterns(stocks, finish, patterns)

# Lấy snapshot bộ nhớ sau khi thực hiện cắt
snapshot2 = tracemalloc.take_snapshot()
top_stats = snapshot2.compare_to(snapshot1, 'lineno')

print("\nTop 10 memory usage lines")
for stat in top_stats[:10]:
    print(stat)

# Vẽ đồ thị mẫu cắt
end_time = time.time()
execution_time = end_time - start_time
print(f"\nExecution time: {execution_time:.6f} seconds")

ax = plot_patterns(stocks, finish, patterns)
ax = plot_nonzero_patterns(stocks, finish, patterns, x, cost)
plt.show()

# Đo thời gian thực thi

