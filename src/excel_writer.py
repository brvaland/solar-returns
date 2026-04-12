import pandas as pd
from datetime import datetime

def update_excel(data, file_path="data/solar_return.xlsx", month=None):
    if month is None:
        month = datetime.now().strftime("%Y-%m")
    
    df = pd.DataFrame([{
        "month": month,
        **data
    }])

    try:
        existing = pd.read_excel(file_path)
        df = pd.concat([existing, df], ignore_index=True)
    except FileNotFoundError:
        pass

    df.to_excel(file_path, index=False)