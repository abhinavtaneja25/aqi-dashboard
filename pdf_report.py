from fpdf import FPDF
import matplotlib.pyplot as plt
import tempfile
import os


def get_aqi_color(aqi):
    if aqi <= 50:
        return (0, 153, 0), "Good"
    elif aqi <= 100:
        return (255, 204, 0), "Satisfactory"
    elif aqi <= 200:
        return (255, 140, 0), "Moderate"
    elif aqi <= 300:
        return (255, 0, 0), "Poor"
    else:
        return (139, 0, 0), "Very Poor"


def get_worst_day(data):
    return data.loc[data["AQI"].idxmax()]


# Create graph and save as file (FIXED)
def create_aqi_graph_file(data):
    fig, ax = plt.subplots()
    ax.plot(data["Date"], data["AQI"], color="red")
    ax.set_title("AQI Trend")
    ax.set_xlabel("Date")
    ax.set_ylabel("AQI")

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    plt.savefig(tmp.name, bbox_inches="tight")
    plt.close()

    return tmp.name


def generate_pdf(data):
    pdf = FPDF()
    pdf.add_page()

    # Title
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, "AQI REPORT", ln=True, align="C")

    # Worst day info
    worst = get_worst_day(data)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(200, 10, "Worst Pollution Day", ln=True)

    pdf.set_font("Arial", size=11)
    pdf.cell(
        200,
        8,
        f"{worst['Date'].date()} | {worst['City']} | AQI {worst['AQI']}",
        ln=True
    )

    # Graph
    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(200, 10, "AQI Trend", ln=True)

    img_path = create_aqi_graph_file(data)
    pdf.image(img_path, x=10, w=180)

    # Cleanup temp file
    if os.path.exists(img_path):
        os.remove(img_path)

    file_path = "AQI_Report.pdf"
    pdf.output(file_path)

    return file_path