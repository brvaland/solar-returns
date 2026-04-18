import pandas as pd
from datetime import datetime
from config.settings import BASELINE_RATE
from openpyxl.utils import get_column_letter

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
        
        # Find the column positions for headers
        actual_cost_col = None
        no_solar_cost_col = None
        header_positions = {}
        for col_idx, cell in enumerate(worksheet[1], 1):
            header_positions[cell.value] = col_idx
            if cell.value == "self use savings":
                actual_cost_col = col_idx + 1  # Insert after this column

        # Insert Actual_Cost column if we found the right position
        if actual_cost_col:
            worksheet.insert_cols(actual_cost_col)
            # Add header
            worksheet.cell(row=1, column=actual_cost_col).value = "Actual_Cost"
            worksheet.cell(row=1, column=actual_cost_col).fill = orange_fill
            worksheet.cell(row=1, column=actual_cost_col).font = header_font
            
            # Add formulas for data rows (import cost - export income)
            for row in range(2, worksheet.max_row + 1):
                formula = f"=C{row}-E{row}"
                worksheet.cell(row=row, column=actual_cost_col).value = formula
                worksheet.cell(row=row, column=actual_cost_col).number_format = '£#,##0.00'

            # Update header positions after inserting Actual_Cost
            header_positions = {worksheet.cell(1, idx).value: idx for idx in range(1, worksheet.max_column + 1)}
            no_solar_cost_col = header_positions.get("Actual_Cost", actual_cost_col) + 1

            # Insert No_Solar_Cost column after Actual_Cost
            worksheet.insert_cols(no_solar_cost_col)
            worksheet.cell(row=1, column=no_solar_cost_col).value = "No_Solar_Cost"
            worksheet.cell(row=1, column=no_solar_cost_col).fill = orange_fill
            worksheet.cell(row=1, column=no_solar_cost_col).font = header_font

            # Build formula columns by header names so the formula stays aligned
            positions = {worksheet.cell(1, idx).value: idx for idx in range(1, worksheet.max_column + 1)}
            import_col = positions.get("import (kwh)")
            pv_col = positions.get("PV_to_home_Kwh")
            battery_col = positions.get("Grid_to_Battery_kwh") or positions.get("Grid_to_battery_kwh")
            actual_cost_col = positions.get("Actual_Cost")
            no_solar_cost_col = positions.get("No_Solar_Cost")

            if import_col and pv_col and battery_col and no_solar_cost_col:
                import_col_letter = get_column_letter(import_col)
                pv_col_letter = get_column_letter(pv_col)
                battery_col_letter = get_column_letter(battery_col)
                for row in range(2, worksheet.max_row + 1):
                    formula = f"=(({import_col_letter}{row}+{pv_col_letter}{row})-{battery_col_letter}{row})*{BASELINE_RATE}"
                    worksheet.cell(row=row, column=no_solar_cost_col).value = formula
                    worksheet.cell(row=row, column=no_solar_cost_col).number_format = '£#,##0.00'

            if actual_cost_col and no_solar_cost_col:
                roi_col = no_solar_cost_col + 1
                worksheet.insert_cols(roi_col)
                worksheet.cell(row=1, column=roi_col).value = "ROI"
                worksheet.cell(row=1, column=roi_col).fill = orange_fill
                worksheet.cell(row=1, column=roi_col).font = header_font
                
                no_solar_cost_letter = get_column_letter(no_solar_cost_col)
                actual_cost_letter = get_column_letter(actual_cost_col)
                for row in range(2, worksheet.max_row + 1):
                    formula = f"={no_solar_cost_letter}{row}-{actual_cost_letter}{row}"
                    worksheet.cell(row=row, column=roi_col).value = formula
                    worksheet.cell(row=row, column=roi_col).number_format = '£#,##0.00'

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
                                     or "savings" in col_header.lower() or "return" in col_header.lower() 
                                     or col_header == "ROI"):
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