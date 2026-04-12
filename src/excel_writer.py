import pandas as pd
from datetime import datetime

def update_excel(data, file_path="data/solar_return.xlsx", month=None, sheet_name="Sheet1"):
    if month is None:
        month = datetime.now().strftime("%Y-%m")
    
    # Format data before writing to Excel
    formatted_data = {
        "month": month,
    }
    
    for key, value in data.items():
        if "kwh" in key.lower():
            # Format kWh to 1 decimal place
            formatted_data[key] = round(value, 1)
        elif "cost" in key.lower() or "income" in key.lower() or "savings" in key.lower() or "return" in key.lower():
            # Format currency to 2 decimal places
            formatted_data[key] = round(value, 2)
        else:
            formatted_data[key] = value
    
    df = pd.DataFrame([formatted_data])

    try:
        existing = pd.read_excel(file_path)
        df = pd.concat([existing, df], ignore_index=True)
    except FileNotFoundError:
        pass

    # Write to Excel with formatting
    with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
        
        # Apply formatting
        worksheet = writer.sheets[sheet_name]
        from openpyxl.styles import numbers, PatternFill, Font
        
        # Orange fill for header row
        orange_fill = PatternFill(start_color="FFA500", end_color="FFA500", fill_type="solid")
        header_font = Font(bold=True)  # Bold text with default black color
        
        # Format header row
        for cell in worksheet[1]:
            cell.fill = orange_fill
            cell.font = header_font
        
        # Format data rows
        for row in worksheet.iter_rows(min_row=2, max_row=worksheet.max_row):
            for cell in row:
                col_header = worksheet.cell(1, cell.column).value
                
                if col_header and "kwh" in col_header.lower():
                    # Format kWh to 1 decimal place
                    cell.number_format = '0.0'
                elif col_header and ("cost" in col_header.lower() or "income" in col_header.lower() 
                                     or "savings" in col_header.lower() or "return" in col_header.lower()):
                    # Format as British Pounds with 2 decimal places
                    cell.number_format = '£#,##0.00'
        
        # Auto-fit column widths
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            
            # Set width with some padding
            adjusted_width = min(max_length + 2, 50)  # Cap at 50 for very long content
            worksheet.column_dimensions[column_letter].width = adjusted_width