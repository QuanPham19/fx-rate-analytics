import openpyxl
from openpyxl.utils import get_column_letter
from openpyxl.styles import Alignment

# Load the existing workbook
file_path = 'output.xlsx'
def excel_format(file_path):
    wb = openpyxl.load_workbook(file_path)

    # Iterate over all sheets
    for sheet in wb.worksheets:
        # Iterate over all columns in the sheet
        for col in sheet.columns:
            max_length = 0
            column = col[0].column_letter  # Get the column name
            for cell in col:
                try:
                    # Update the maximum length of the column
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = (max_length + 2)
            sheet.column_dimensions[column].width = adjusted_width

            # Set alignment for the entire column
            for cell in col:
                cell.alignment = Alignment(horizontal='center')

    # Save the modified workbook
    wb.save(file_path)
    
excel_format(file_path)