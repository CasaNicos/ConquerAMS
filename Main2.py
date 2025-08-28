# Reinstall pysimplegui for license
# & "C:\Program Files (x86)\Microsoft Visual Studio\Shared\Python39_64\python.exe" 
# ` -m pip install --force-reinstall --extra-index-url https://PySimpleGUI.net/install PySimpleGUI

# Run program bc enviorment issues
# & "C:\Program Files (x86)\Microsoft Visual Studio\Shared\Python39_64\python.exe" "C:\Users\MrUnr\Documents\AssetManagementProj\ConquerAssetManagementSystem\Main2.py"

import PySimpleGUI as psg
from db import (initialize_schema,get_assets, get_next_asset_tag, insert_asset, update_asset, delete_asset,get_users, 
                insert_user, update_user, delete_user,get_locations, insert_location, update_location, delete_location,
                log_transaction, get_transactions, get_warranties_within)
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import csv
from collections import Counter
import datetime

########################### MAIN TABS ###############################################################################
# Need visuals
def make_dashboard_tab():
    assets = get_assets()
    total_devices = len(assets) # Total Devices display
    expired_warranties = len(get_warranties_within(0)) # Expired Warranties Display

    # Canvas creates placeholders for charts. Need separate list for horizontal visuals
    chart_row = [
        psg.Canvas(key='Canvas_Bar_Graph',     background_color='white', size=(200, 200), expand_x=True, expand_y=True),
        psg.Canvas(key='Canvas_Pie_Chart',     background_color='white', size=(400, 400), expand_x=True, expand_y=True),
        psg.Canvas(key='Canvas_Line_Graph',  background_color='white', size=(200, 200), expand_x=True, expand_y=True)
    ]

    # Layout list, switched from plain calls, displays objects in order
    layout = [
        [psg.Text(f"Total Assets: {total_devices}", font=('Any', 14), key='Total_Devices')], # Text on top
        [psg.Text(f"Expired Warranties: {expired_warranties}", font=('Any', 12), text_color='red', key='Expired_Warranties')],
        chart_row
    ]

    # Changed to column for scroll bars
    tab = [[psg.Column(layout, scrollable=True, vertical_scroll_only=False, expand_x=True, expand_y=True)]]

    # Whole tab with 2 text then charts
    return tab

# Assets w/ buttons
def make_assets_tab():
    layout = [
        [psg.Button('Add Asset'), psg.Button('Export as CSV', key='Export Assets')], # Top row of event buttons
        [psg.Table(values=[], headings=['Tag','Make','Model','Purchase Date', 'Warranty Expiry', 'Status','Location'], key='Asset_Table', enable_events=True, select_mode=psg.TABLE_SELECT_MODE_EXTENDED, auto_size_columns=True, num_rows=10, expand_x=True, expand_y=True)],
        [psg.Button('Check Out'), psg.Button('Check In'), psg.Button('Update Selected Asset'), psg.Button('Delete Selected Assets')] # Bottom row of event buttons
    ]
    return layout

# Users w/ buttons
def make_users_tab():
    layout = [
        [psg.Button('Add User'), psg.Button('Export as CSV', key='Export Users')], # Top row of event buttons
        [psg.Table(values=[], headings=['Full Name','Dept','Job Title','Location','Email','Username'], key='User_Table', enable_events=True, select_mode=psg.TABLE_SELECT_MODE_EXTENDED, auto_size_columns=True, num_rows=10, expand_x=True, expand_y=True)],
        [psg.Button('Update Selected User'), psg.Button('Delete Selected Users')] # Bottom row of event buttons
    ]
    return layout

# Locations w/ buttons
def make_locations_tab():
    layout = [
        [psg.Button('Add Location')], # Top row of event buttons
        [psg.Table(values=[], headings=['Name','Address'], key='Location_Table', enable_events=True, select_mode=psg.TABLE_SELECT_MODE_EXTENDED, auto_size_columns=True, num_rows=10, expand_x=True, expand_y=True)],
        [psg.Button('Update Selected Location'), psg.Button('Delete Selected Locations')] # Bottom row of event buttons
    ]
    return layout

# Warranties w/ dropdown & buttons
def make_warranties_tab():
    layout = [
        [psg.Text('Expiring in:'), psg.Combo(['<30 days','<90 days','<180 days'], default_value='<30 days', key='Warranty_Filter'), psg.Button('Refresh Warranties')], # Top row of dropdown (combo) with Refresh
        [psg.Table(values=[], headings=['Tag','Model','Expiry','Status'], key='Warranty_Table', auto_size_columns=True, num_rows=10, expand_x=True, expand_y=True)]
    ]
    return layout

# Logs w/ dropdown & buttons
def make_logs_tab():
    layout = [
        [psg.Text('Filter by Asset:'), psg.Combo(values=['All'], default_value='All', key='Log_Filter', enable_events=True), psg.Button('Export as CSV', key='Export Logs')], # Top row of dropdown (combo) with Export
        [psg.Table(values=[], headings=['Timestamp','Tag','Model','User','Action','Notes','From Loc','To Loc'], key='Log_Table', auto_size_columns=True, num_rows=10, expand_x=True, expand_y=True)]
    ]
    return layout

########################### CCORE GUI ###############################################################################
def make_gui():
    initialize_schema()

    tab_group = psg.TabGroup([[
        psg.Tab('Dashboard', make_dashboard_tab()),
        psg.Tab('Assets', make_assets_tab()),
        psg.Tab('Users', make_users_tab()),
        psg.Tab('Locations', make_locations_tab()),
        psg.Tab('Warranties', make_warranties_tab()),
        psg.Tab('Logs', make_logs_tab())
    ]], expand_x=True, expand_y=True) # Allow stretch

    layout = [
        [psg.Push(), psg.Button('Refresh All', key='Refresh All')], # Refresh ALL button
        [tab_group]
    ]

    # Actual GUI Window
    window = psg.Window('Asset Management System', layout, background_color = None , resizable=True, finalize=True, size=(1125, 500))

    # Populate tabs
    draw_dashboard_charts(window)
    load_assets(window)
    load_users(window)
    load_locations(window)

    # Set default filters so these next two actually load something
    window['Warranty_Filter'].update('<30 days')
    load_warranties(window, days=30)
    window['Log_Filter'].update('All')
    load_logs(window)

    return window

########################### POP UP TABS ###############################################################################
def add_asset_popup(loc_names):
    # Create Asset Entries
    layout = [
        [psg.Text('Make', size=(12,1)), psg.Input(key='Make')],
        [psg.Text('Model', size=(12,1)), psg.Input(key='Model')],
        [psg.Text('Purchase Date', size=(12,1)), psg.Input(key='Purchase_Date'), psg.CalendarButton('Pick Date', target='Purchase_Date', format='%Y-%m-%d')],
        [psg.Text('Warranty Expiry', size=(12,1)), psg.Input(key='Warranty_Date'), psg.CalendarButton('Pick Date', target='Warranty_Date', format='%Y-%m-%d')],
        [psg.Text('Status', size=(12,1)), psg.Combo(['Checked_In','Checked_Out','Retired','In_Repair','Damaged'],default_value='Checked_In', key='Status')],
        [psg.Text('Location', size=(12,1)), psg.Combo(loc_names, key='Location')],
        [psg.Button('Save'), psg.Button('Cancel')]
    ]
    # Window
    return psg.Window('Add Asset', layout, modal=True, finalize=True)

def update_asset_popup(current_vals, loc_names):
    # Current_vals list: [tag, make, model, purchase_date, warranty_expiry, status, location]
    layout = [
        [psg.Text('Tag', size=(12,1)), psg.Text(current_vals[0])],
        [psg.Text('Make', size=(12,1)), psg.Input(current_vals[1], key='Make')],
        [psg.Text('Model', size=(12,1)), psg.Input(current_vals[2], key='Model')],
        [psg.Text('Purchase Date', size=(12,1)), psg.Input(current_vals[3], key='Purchase_Date'), psg.CalendarButton('Pick Date', target='Purchase_Date', format='%Y-%m-%d')],
        [psg.Text('Warranty Expiry', size=(12,1)), psg.Input(current_vals[4], key='Warranty_Date'), psg.CalendarButton('Pick Date', target='Warranty_Date', format='%Y-%m-%d')],
        [psg.Text('Status', size=(12,1)), psg.Combo(['Checked_In','Checked_Out','Retired','In_Repair','Damaged'],default_value=current_vals[5],key='Status')],
        [psg.Text('Location', size=(12,1)), psg.Combo(loc_names, default_value=current_vals[6], key='Location')],
        [psg.Button('Save'), psg.Button('Cancel')]
    ]
    return psg.Window('Update Asset', layout, modal=True, finalize=True)

def add_location_popup():
    # Create Location Entries
    layout = [
        [psg.Text('Location Name', size=(15,1)), psg.Input(key='Location_Name')],
        [psg.Text('Address',       size=(15,1)), psg.Input(key='Location_Address')],
        [psg.Button('Save'), psg.Button('Cancel')]
    ]
    # Window
    return psg.Window('Add Location', layout, modal=True, finalize=True)

def edit_location_popup(loc_id, name, address):
    # Edit Location Entries
    layout = [
        [psg.Text('ID', size=(12,1)), psg.Text(str(loc_id))],
        [psg.Text('Location Name', size=(15,1)), psg.Input(name, key='Location_Name')],
        [psg.Text('Address', size=(15,1)), psg.Input(address, key='Location_Address')],
        [psg.Button('Save'), psg.Button('Cancel')]
    ]
    # Window
    return psg.Window('Update Location', layout, modal=True, finalize=True)

def add_user_popup(loc_names):
    # Add User Entries
    layout = [
        [psg.Text('Full Name', size=(12,1)), psg.Input(key='Full_Name')],
        [psg.Text('Department', size=(12,1)), psg.Input(key='Department')],
        [psg.Text('Job Title', size=(12,1)), psg.Input(key='Job_Title')],
        [psg.Text('Email', size=(12,1)), psg.Input(key='Email')],
        [psg.Text('Username', size=(12,1)), psg.Input(key='UserName')],
        [psg.Text('Location', size=(12,1)),
         psg.Combo(loc_names, key='Location')],
        [psg.Button('Save'), psg.Button('Cancel')]
    ]
    # Window
    return psg.Window('Add User', layout, modal=True, finalize=True)

def edit_user_popup(current_vals, loc_names):
    # Edit User Entries
    # current_vals = [id, full_name, dept, job_title, loc_name, email, username]
    layout = [
        [psg.Text('ID', size=(12,1)), psg.Text(str(current_vals[0]))],
        [psg.Text('Full Name', size=(12,1)), psg.Input(current_vals[1], key='Full_Name')],
        [psg.Text('Department', size=(12,1)), psg.Input(current_vals[2], key='Department')],
        [psg.Text('Job Title', size=(12,1)), psg.Input(current_vals[3], key='Job_Title')],
        [psg.Text('Location', size=(12,1)), psg.Combo(loc_names, default_value=current_vals[4], key='Location')],
        [psg.Text('Email', size=(12,1)), psg.Input(current_vals[5], key='Email')],
        [psg.Text('Username', size=(12,1)), psg.Input(current_vals[6], key='UserName')],
        [psg.Button('Save'), psg.Button('Cancel')]
    ]
    # Window
    return psg.Window('Update User', layout, modal=True, finalize=True)

# Window that records transaction data post asset update
def transaction_popup(user_names, loc_names, default_user=None, default_from=None, default_to=None, default_notes=''):
    layout = [
        [psg.Text('User', size=(12,1)), psg.Combo(user_names, default_value=default_user, key='Transaction_User', readonly=True)], # User dropdown selection
        [psg.Text('From Location', size=(12,1)), psg.Combo(loc_names, default_value=default_from, key='Transaction_From_Loc', readonly=True)], # From Location drop down selection
        [psg.Text('To Location', size=(12,1)), psg.Combo(loc_names, default_value=default_to, key='Transaction_To_Loc',   readonly=True)], # To Location drop down selection
        [psg.Text('Notes', size=(12,1)), psg.Multiline(default_notes, key='Transaction_Notes', size=(40,4))], # Notes multiline entry box
        [psg.Button('Save'), psg.Button('Cancel')]
    ]
    win = psg.Window('Transaction Details', layout, modal=True, finalize=True)

    while True:
        event , vals = win.read() # Read selections

        # Canceled 
        if event in (psg.WIN_CLOSED, 'Cancel'): 
            win.close()
            return None
        
        # Saved
        if event == 'Save':
            # Record Entries
            user_selection = vals['Transaction_User']
            from_selection = vals['Transaction_From_Loc']
            to_selection = vals['Transaction_To_Loc']
            notes = vals['Transaction_Notes'].rstrip()

            # Handle missing locs or user
            if not (from_selection and to_selection and user_selection):
                psg.popup_error('User, From Location and To Location are required.')
                continue
            
            win.close()
            return {
                'user': user_selection,
                'from_loc':from_selection,
                'to_loc': to_selection,
                'notes': notes
            }

# SaveAs popup with windows file explorer system dialog
def export_csv_popup(default_filename, file_types=(('CSV Files','*.csv'),)):
    layout = [
        [psg.Text('Please select "Browse" and enter destination.')],
        # Filename box with FileSaveAs windows system popup .csv extension
        [psg.Input(default_filename, key='Path', size=(40,1), readonly=True), psg.FileSaveAs(button_text='Browse…', key='-BROWSE-', file_types=file_types, default_extension='.csv')],
        [psg.Push(), psg.Button('Save'), psg.Button('Cancel')]
    ]
    
    # Create Window
    window = psg.Window('Save As CSV', layout, modal=True, finalize=True)

    path = None
    while True:
        event, vals = window.read()

        # Closed
        if event in (psg.WIN_CLOSED, 'Cancel'):
            break

        # Saved
        if event == 'Save':
            location = vals['Path']

            # Empty handler
            if not location:
                psg.popup_error('Please choose a file location first.')
                continue

            path = location
            break

    window.close()
    return path

########################### HELPER FUNCTIONS ###############################################################################
def _embed_figure(window, canvas_key, figure):
    canvas_elem = window[canvas_key] # Full Canvas Element for processing
    tk_canvas   = canvas_elem.TKCanvas

    # Destroy existing widgets (fix refreesh duplication bug)
    for child in tk_canvas.winfo_children():
        child.destroy()

    # Embed the new figures
    fig_canvas = FigureCanvasTkAgg(figure, tk_canvas)
    fig_canvas.draw()
    fig_canvas.get_tk_widget().pack(fill='both', expand=True)

# Return action change
def _determine_action(old_status, new_status):
    if old_status == new_status:
        return 'UPDATE_ASSET'
    
    # Status changed, return the action 
    if new_status == 'Checked_Out':
        return 'CHECK_OUT'
    elif new_status == 'Checked_In':
        return 'CHECK_IN'
    elif new_status == 'In_Repair':
        return 'UPDATE_ASSET_REPAIR'
    elif new_status == 'Retired':
        return 'UPDATE_ASSET_RETIRED'
    elif new_status == 'Damaged':
        return 'UPDATE_ASSET_DAMAGED'
    else:
        # Edge cases
        return 'UPDATE_ASSET'

############################ LOAD FUNCTIONS ###############################################################################
def load_assets(win):
    rows = get_assets()

    # Store AssetIDs
    win.asset_ids = []
    for row in rows:
        win.asset_ids.append(row[0]) # Row[0] = assetID

    table_data = []
    for row in rows:
        asset_row = list(row[1:])  # Skip the first column and take the rest
        table_data.append(asset_row)
    
    win['Asset_Table'].update(values=table_data)

def load_users(win):
    rows = get_users()

    # Store UserIDs
    win.user_ids = []
    for row in rows:
        win.user_ids.append(row[0])  # Save userID

    table_data = []
    for row in rows:
        user_row = list(row[1:])  # Skip the first column and take the rest
        table_data.append(user_row)

    win['User_Table'].update(values=table_data)

def load_locations(win):
    rows = get_locations()

    # Store LocationIDs
    win.loc_ids = []
    for row in rows:
        win.loc_ids.append(row[0])  # Store location ID

    table_data = []
    for row in rows:
        loc_row = list(row[1:])  # Skip the first column and take the rest
        table_data.append(loc_row)

    win['Location_Table'].update(values=table_data)

def load_warranties(win, days):
    data = get_warranties_within(days)
    win['Warranty_Table'].update(values=data)

def load_logs(win, asset_tag=None):
    data = get_transactions(asset_tag)
    win['Log_Table'].update(values=data)

########################### CHART FUNCTIONS ###############################################################################
def draw_dashboard_charts(window):

    # Update top dashboard labels
    assets = get_assets() # Refresh Assets
    total_devices = len(assets) 
    window['Total_Devices'].update(f"Total Assets: {total_devices}") # Refresh Total Asset Count
    expired_warranties = len(get_warranties_within(0))
    window['Expired_Warranties'].update(f"Expired Warranties: {expired_warranties}") # Refresh Expired Warranties

    ############ Devices per Location (bar) ############
    # Get all location names from the database
    locations = get_locations()  # [id, name, address]

    # Lisst of name
    location_names = []
    for loc in locations:
        location_names.append(loc[1])  # loc[1] == name

    # Count how many assets are in each location
    location_counts = []
    for name in location_names:
        count = 0
        for asset in assets:
            if asset[7] == name:  # asset[7] == location name
                count += 1
        location_counts.append(count)

    # Create bar chart figure
    fig_bar, ax_bar = plt.subplots(figsize=(3, 3)) 

    if location_names:
        ax_bar.bar(location_names, location_counts) # (x,y)
        ax_bar.yaxis.set_major_locator(MaxNLocator(integer=True))  # Show ints on y axis
        ax_bar.set_xticklabels(location_names, rotation=45, ha='right')  # or rotation=90 for vertical
    else:
        ax_bar.bar(['No locations'], [1], color='#dddddd')  # Placeholder if no locations

    ax_bar.set_title('Assets per Location') # Title
    fig_bar.tight_layout()
    _embed_figure(window, 'Canvas_Bar_Graph', fig_bar) # Embed into figure w/ key

    ############ Category Breakdown (pie) ############
     # Pull all statuses 
    statuses = []
    for asset in assets:
        if len(asset) > 6:
            statuses.append(asset[6])  # asset[6] == status

    if statuses:
        # List each status type
        status_type = list(set(statuses))

        # Count times each category appears
        status_counts = []
        for status in status_type:
            count = statuses.count(status)
            status_counts.append(count)
    else:
        status_type = ['No categories']
        status_counts = [1]

    # Create pie chart figure
    fig_cat, ax_cat = plt.subplots(figsize=(3, 3))
    ax_cat.pie(status_counts, labels=status_type, autopct='%1.1f%%')
    ax_cat.set_title('Asset Statuses by Percent') # Title
    fig_cat.tight_layout()
    _embed_figure(window, 'Canvas_Pie_Chart', fig_cat)

    ############ Warranty Expirations Over Time (line) ############
    # Get warranty expiry dates from assets
    expiry_dates = []
    for asset in assets:
        expiry_str = asset[5]  # asset[5] == warranty_expiry
        if expiry_str:
            expiry_date = datetime.datetime.strptime(expiry_str, '%Y-%m-%d') # Format str > date - time
            # Add formatted dates to lsit
            expiry_dates.append(expiry_date)

    # Convert each date into month  eg 2025-07-23 > '2025-07'
    month_labels = []
    for date in expiry_dates:
        month_str = date.strftime('%Y-%m')
        month_labels.append(month_str)

    # Count warranty expirations in each month
    month_counter = Counter(month_labels)

    # Sort months
    sorted_months = sorted(month_counter.keys())
    month_counts = []
    for month in sorted_months:
        month_counts.append(month_counter[month])

    # Create line chart 
    fig_line, ax_line = plt.subplots(figsize=(4, 3))
    if sorted_months:
        ax_line.plot(sorted_months, month_counts, marker='o') # (x,y)
        ax_line.set_title('Warranty Expirations by Month') # Title
        ax_line.set_ylabel('Expiring Assets') # y title
        ax_line.set_xlabel('Month') # x title
        ax_line.set_xticklabels(sorted_months, rotation=45, ha='right') # Slight rotation to fit, not vert
        ax_line.yaxis.set_major_locator(MaxNLocator(integer=True))  # Whole numbers only
    else:
        # For no data 
        ax_line.text(0.5, 0.5, 'No warranty data', ha='center', va='center')

    fig_line.tight_layout()
    _embed_figure(window, 'Canvas_Line_Graph', fig_line)

########################### MAIN ###############################################################################
def main():
    # Let the dogs out
    window = make_gui()

    # Event loop
    while True:
        event, vals = window.read()

        if event in (psg.WIN_CLOSED,): #Exitted window
            break
        ######## GUI EVENTS ############################################
        # Refresh Button
        if event == 'Refresh All':
            # Redraw charts
            draw_dashboard_charts(window)

            # REload Assets, Users, Locations
            load_assets(window)
            load_users(window)
            load_locations(window)

            # Reload Warranties (use whatever filter is currently set)
            warranty_selection = window['Warranty_Filter'].get()
            try:
                days = int(warranty_selection.strip('< days')) # Format selection
            except:
                days = 30 # Default
            load_warranties(window, days)

            # Reload Logs (filter is already in the combo)
            load_logs(window)    

        ######## ASSET EVENTS ############################################
        # Deleted Selected Assets button on Assets Tab
        if event == 'Delete Selected Assets':
            selection = vals['Asset_Table'] # Selected Asset
            if not selection:
                psg.popup_error('Please select at least one asset to delete.') # Throw if no selection
            else:
                if psg.popup_yes_no('Delete selected assets?')=='Yes': # If yes (no auto closes)
                    for i in selection:
                        # Delete each, error if failed
                        try:
                            delete_asset(window.asset_ids[i])
                        except ValueError as ve:
                            psg.popup_error(str(ve))
                    # Reload
                    load_assets(window)

        # Update Selected Assets button on Assets Tab
        if event == 'Update Selected Asset':
            selection = vals['Asset_Table'] # Selected asset
            if len(selection) != 1: # ONLY 1
                psg.popup_error('Please select exactly one asset to update.')
            else:
                # Get asset for edit
                aid = selection[0] # [0] == selected asset id
                assets = get_assets()  # Pull all assets
                # Assign each element to var. assets[idx] == asset with matching idx
                aid, tag, old_make, old_model, old_pur, old_warr, old_status, old_loc = assets[aid] 

                # Get users for drop down
                users = get_users() # Get all users
                user_names = [u[1] for u in users] # u[1] == name, for each user
                user_map = {u[1]: u[0] for u in users} # u[0] == user id, map names to ids for each
                
                # Get locaitons for drop down
                locations  = get_locations() # Get all locations
                loc_names = [l[1] for l in locations] # Location names
                loc_map   = {l[1]: l[0] for l in locations} # Map names to id's

                # Populate pop up with current values
                current_vals = [tag, old_make, old_model, old_pur or '', old_warr or '', old_status, old_loc]
                popup = update_asset_popup(current_vals, loc_names)
                
                while True:
                    popup_event, popup_values = popup.read() # Hold asset values, create event var
                    if popup_event in (psg.WIN_CLOSED, 'Cancel'): # Window closed
                        popup.close()
                        break
                    if popup_event == 'Save': # Save button hit
                        # Record new entered values
                        new_make = popup_values['Make'].strip()
                        new_model = popup_values['Model'].strip()
                        new_pur = popup_values['Purchase_Date'].strip() or None
                        new_warr = popup_values['Warranty_Date'].strip() or None
                        new_status = popup_values['Status']
                        new_loc = popup_values['Location']

                        # Validate new entires 
                        if not (new_make and new_model and new_loc):
                            psg.popup_error('Make, Model & Location are required.')
                            continue

                        # Transaction Popup w/ new data (minus old loc)
                        transaction = transaction_popup(
                            user_names,
                            loc_names,
                            default_user=None,
                            default_from=old_loc,
                            default_to=new_loc,
                            default_notes=''
                        )
                        if not transaction:
                            # user cancelled transaction
                            continue
                        
                        # Get id of mapped element from transaction
                        user_id = user_map[transaction['user']]
                        from_loc_id = loc_map[transaction['from_loc']]
                        to_loc_id = loc_map[transaction['to_loc']]
                        notes = transaction['notes']

                        # Update asset w/ new vars
                        update_asset(
                            aid,
                            make=new_make,
                            model=new_model,
                            purchase_date=new_pur,
                            warranty_expiry=new_warr,
                            status=new_status,
                            location_id=to_loc_id
                        )

                        # determine action, return defined code
                        action_code = _determine_action(old_status, new_status)

                        # log transaction w/ action code
                        log_transaction(
                            asset_id=aid,
                            user_id=user_id,
                            action=action_code,
                            notes=transaction['notes'],
                            from_loc=from_loc_id,
                            to_loc=to_loc_id
                        )

                        # Close and refresh
                        popup.close() 
                        load_assets(window)
                        break

        # Check out button on Assets Tab
        if event == 'Check Out':
            selection = vals['Asset_Table'] # GRab selected asset elements
            if not selection:
                psg.popup_error('Please select at least one asset to check out.')
            else:
                # Get current 
                assets = get_assets() 
                status_map = {a[0]: a[6] for a in assets} # map statuses to assets id
                tag_map = {a[0]: a[1] for a in assets} # map ids to asset tags
                location_map = {a[0]: a[7] for a in assets} # map id to location name

                selection_ids = [window.asset_ids[i] for i in selection] # grab ids from selected asset

                # For ids in selected assets check if checked out
                already_out = []
                for aid in selection_ids:
                    if status_map.get(aid) == 'Checked_Out':
                        already_out.append(aid)
                
                # If asset(s) already out, get asset name and throw error
                if already_out:
                    names = []
                    for aid in already_out:
                        names.append(tag_map[aid])
                    psg.popup_error('Cannot check out these assets (already checked out):\n' + ', '.join(names))
                    continue

                # Confirmation pop up
                count = len(selection_ids)
                if psg.popup_yes_no(f'Check out {count} asset{"s" if count>1 else ""}?') != 'Yes':
                    continue
                
                # Populate user drop down, get users, map ids to names
                users = get_users()
                user_names= [u[1] for u in users]
                user_map = {u[1]: u[0] for u in users}

                # Populate locations drop down, get locations, map ids to locations
                loc_rows  = get_locations()
                loc_names = [l[1] for l in loc_rows]
                loc_map = {l[1]: l[0] for l in loc_rows}

                # Use first assets location as from location
                first_id = selection_ids[0]
                current_loc_name = location_map.get(first_id, None)

                # Log transaction info, populate with current vals
                transaction = transaction_popup(
                    user_names,
                    loc_names,
                    default_user=None,
                    default_from=current_loc_name,
                    default_to=None,
                    default_notes=''
                )
                if not transaction:
                    continue
                
                # Get ids of changes w/ userid
                user_id = user_map[transaction['user']]
                from_id = loc_map[transaction['from_loc']]
                to_id = loc_map[transaction['to_loc']]

                # Update asset and log transaction
                for aid in selection_ids: # for each, check out
                    update_asset(aid, status='Checked_Out', location_id=to_id)
                    log_transaction(
                        asset_id=aid,
                        user_id=user_id,
                        action='CHECK_OUT',
                        notes=transaction['notes'],
                        from_loc=from_id,
                        to_loc=to_id
                    )

                # Refresh and throw confirmation
                load_assets(window)
                psg.popup(f'{count} asset{"s" if count>1 else ""} checked out.')

        # Check in button on Assets Tab
        # Copy of Check out with name and list changes
        if event == 'Check In':
            selection = vals['Asset_Table'] # Get selected asset(s) elements
            if not selection: # At least 1 must be selected
                psg.popup_error('Please select at least one asset to check in.')
            else:
                assets = get_assets()
                status_map = {a[0]: a[6] for a in assets} # a[0] == id, a[6] == status
                tag_map = {a[0]: a[1] for a in assets} # a[1] == tag
                location_map = {a[0]: a[7] for a in assets} # a[7] == location name

                selection_ids = [window.asset_ids[i] for i in selection] # Get ids from selection

                already_in = []
                for aid in selection_ids:
                    if status_map.get(aid) == 'Checked_In':
                        already_in.append(aid)

                # for asset(s) already w/ checked in, get names and throw error
                if already_in:
                    names = []
                    for aid in already_in:
                        names.append(tag_map[aid])
                    psg.popup_error('Cannot check in these assets (already checked in):\n' + ', '.join(names))
                    continue
                
                # Get item number, confirmation popup
                count = len(selection_ids)
                if psg.popup_yes_no(f'Check in {count} asset{"s" if count>1 else ""}?') != 'Yes':
                    continue
                
                # Populate user drop down, get users, map ids to names
                users = get_users()
                user_names = [u[1] for u in users]
                user_map = {u[1]: u[0] for u in users}

                # Populate locations drop down, get locations, map ids to locations
                loc_rows = get_locations()
                loc_names = [l[1] for l in loc_rows]
                loc_map = {l[1]: l[0] for l in loc_rows}

                 # Use first assets location as from location
                first_id = selection_ids[0]
                current_loc_name = location_map.get(first_id, None)

                # Log transaction info, populate with current vals
                transaction = transaction_popup(
                    user_names,
                    loc_names,
                    default_user=None,
                    default_from=current_loc_name,
                    default_to=None,
                    default_notes=''
                )
                if not transaction:
                    continue

                # Get ids of changes w/ userid
                user_id = user_map[transaction['user']]
                from_id = loc_map[transaction['from_loc']]
                to_id = loc_map[transaction['to_loc']]

                 # Update asset and log transaction
                for aid in selection_ids: # for each, check out
                    update_asset(aid, status='Checked_In', location_id=to_id)
                    log_transaction(
                        asset_id=aid,
                        user_id=user_id,
                        action='CHECK_IN',
                        notes=transaction['notes'],
                        from_loc=from_id,
                        to_loc=to_id
                    )

                load_assets(window)
                psg.popup(f'{count} asset{"s" if count>1 else ""} checked in.')

        # Add Asset Button on Assets Tab
        if event == 'Add Asset':

        # Get locations for dropdown
            loc_rows = get_locations()
            loc_names = [r[1] for r in loc_rows]
            loc_map   = {r[1]: r[0] for r in loc_rows}  # [id]: [loc name]

            # Add asset popup
            popup = add_asset_popup(loc_names)
            while True:
                popup_event, popup_vals = popup.read()
                # Break when closed
                if popup_event in (psg.WIN_CLOSED, 'Cancel'):
                    popup.close()
                    break
                
                # Saved processsing
                if popup_event == 'Save':
                    # inputted values to vars
                    make = popup_vals['Make'].strip()
                    model = popup_vals['Model'].strip()
                    pur = popup_vals['Purchase_Date'].strip() or None
                    warr = popup_vals['Warranty_Date'].strip() or None
                    status = popup_vals['Status']
                    loc_id = loc_map.get(popup_vals['Location'])

                    # require make model and loc
                    if not make or not model or loc_id is None:
                        psg.popup_error('Make, Model & Location are required.')
                        continue

                    # create asset
                    tag = get_next_asset_tag()
                    insert_asset(
                        tag,
                        make,
                        model,
                        pur,    # purchase_date as 'YYYY-MM-DD' or None
                        warr,   # warranty_expiry as 'YYYY-MM-DD' or None
                        status,
                        loc_id
                    )

                    popup.close()
                    load_assets(window)
                    break     

        # Export Assets Button
        if event == 'Export Assets':
            assets = get_assets()  # (id, tag, make, model, pur, warr, status, loc)

            # need min 1
            if not assets:
                psg.popup_error('No assets to export.')

            else:
                # prompt file 
                path = export_csv_popup('assets.csv')
                if path:
                    with open(path, 'w', newline='') as file:
                        writer = csv.writer(file)
                        # header
                        writer.writerow(['Tag','Make','Model', 'Purchase Date','Warranty Expiry', 'Status','Location'])
                        # data
                        for _, tag, make, model, pur, warr, status, loc in assets:
                            writer.writerow([tag, make, model, pur, warr, status, loc])
                    # throw confirm
                    psg.popup(f'Assets exported to:\n{path}')

        ######## USER EVENTS ############################################
        # Add User Button on Users Tab
        if event == 'Add User':

            # get locations for combo
            loc_rows  = get_locations() 
            loc_names = [r[1] for r in loc_rows]
            loc_map   = {r[1]: r[0] for r in loc_rows} # [id]: [loc name]

            # throw pop up
            popup = add_user_popup(loc_names)

            while True:
                popup_event, popup_vals = popup.read()
                if popup_event in (psg.WIN_CLOSED, 'Cancel'):
                    popup.close()
                    break
                if popup_event == 'Save':
                    full_name = popup_vals['Full_Name'].strip()
                    dept      = popup_vals['Department'].strip()
                    job       = popup_vals['Job_Title'].strip()
                    email     = popup_vals['Email'].strip()
                    username  = popup_vals['UserName'].strip()
                    loc_id    = loc_map.get(popup_vals['Location'])

                    # require make model and loc
                    if not (full_name and username and loc_id):
                        psg.popup_error('Full Name, Username & Location are required.')
                        continue
                    
                    # Create user
                    insert_user(full_name, dept, job, loc_id, email, username)

                    popup.close()
                    load_users(window)
                    break

        # Update Selected User Button on Users Tab
        if event == 'Update Selected User':
            selection = vals['User_Table']

            # Error for < 1 selected
            if len(selection) != 1:
                psg.popup_error('Please select exactly one user to update.')
            else:
                idx = selection[0] # [0] seletec users id(s)
                users = get_users() # (id,full_name,dept,job,loc_name,email,username)

                # assign element to var. 
                user_id, fn, dp, jt, loc_name, em, un = users[idx] # users[idx] == user with matching idx
                current_vals = [user_id, fn, dp, jt, loc_name, em, un]

                # Get locations for drop down
                loc_rows  = get_locations()
                loc_names = [r[1] for r in loc_rows]
                loc_map   = {r[1]: r[0] for r in loc_rows} # loc_id : loc_name

                # ready to edit, pass in locations and selected user data
                popup = edit_user_popup(current_vals, loc_names)

                while True:
                    popup_event, popup_values = popup.read()
                    # handle close
                    if popup_event in (psg.WIN_CLOSED, 'Cancel'):
                        popup.close()
                        break
                    # handle save
                    if popup_event == 'Save':
                        # record new values
                        new_fn = popup_values['Full_Name'].strip()
                        new_dp = popup_values['Department'].strip()
                        new_jt = popup_values['Job_Title'].strip()
                        new_em = popup_values['Email'].strip()
                        new_un = popup_values['UserName'].strip()
                        new_loc_id = loc_map.get(popup_values['Location'])

                        # assert name, user, and loc exsistssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssss
                        if not (new_fn and new_un and new_loc_id):
                            psg.popup_error('Full Name, Username & Location are required.')
                            continue

                        update_user(
                            user_id,
                            full_name=new_fn,
                            department=new_dp,
                            job_title=new_jt,
                            location_id=new_loc_id,
                            email=new_em,
                            username=new_un
                        )

                        popup.close()
                        load_users(window)
                        break

        # Delete Selected Users Button on Users Tab
        if event == 'Delete Selected Users':
            selection = vals['User_Table'] # Selected User
            if not selection: # Throw if no selection
                psg.popup_error('Please select at least one user to delete.') 
            else:
                count = len(selection) # Count for dialog
                response = psg.popup_yes_no(f'Are you sure you want to delete {count} user{"s" if count != 1 else ""}?') # Confirm, no auto closes
                if response == 'Yes':
                    # Collect IDs first
                    selected_ids = [window.user_ids[i] for i in selection]
                    for user_id in selected_ids: # Delete each user, error if failed
                        try:
                            delete_user(user_id)
                        except ValueError as ve:
                            psg.popup_error(str(ve))
                    # Reload
                    load_users(window)
        
        # Export Users to CSV
        if event == 'Export Users':
            users = get_users()  # (id, full_name, dept, job_title, loc, email, username)

            # assert at least 1
            if not users:
                psg.popup_error('No users to export.')
            else:
                path = export_csv_popup('users.csv')
                if path:
                    with open(path, 'w', newline='') as f:
                        writer = csv.writer(f)
                        # Header
                        writer.writerow(['Full Name','Department','Job Title', 'Location','Email','Username'])
                        # data
                        for _, full_name, dept, job_title, loc, email, username in users:
                            writer.writerow([full_name, dept, job_title, loc, email, username])
                    
                    psg.popup(f'Users exported to:\n{path}')

        ######## LOCATION EVENTS #################################0##########
        # Delete Selected Locations Button on Locations Tab
        if event == 'Delete Selected Locations':
            selection = vals['Location_Table']  # Selected Location
            if not selection: # Throw if no selection
                psg.popup_error('Please select at least one location to delete.') 
            else:
                if psg.popup_yes_no('Delete selected locations?')=='Yes': # Confirm, no auto closes
                    for i in selection:
                        try:
                            delete_location(window.loc_ids[i]) # Delete each location, error if failed
                        except ValueError as ve:
                            psg.popup_error(str(ve))
                    # Reload
                    load_locations(window)

        # All Location Button on Locations Tab
        if event == 'Add Location':
            # throw popup
            popup = add_location_popup()

            while True:
                popup_event, popup_vals = popup.read()
                
                # window exited
                if popup_event in (psg.WIN_CLOSED, 'Cancel'):
                    popup.close()
                    break
                
                # save hit
                if popup_event == 'Save':
                    # input loc pop up vals
                    name = popup_vals['Location_Name'].strip()
                    address = popup_vals['Location_Address'].strip()

                    # assert loc name
                    if not name:
                        psg.popup_error("Location name is required.")
                        continue

                    insert_location(name, address)

                    popup.close()
                    load_locations(window)
                    break
        
        # Update Selected Location Button on Locations Tab
        if event == 'Update Selected Location':
            selection = vals['Location_Table']

            # assert 1 is selected
            if len(selection) != 1:
                psg.popup_error('Please select exactly one location to update.')
            else:
                idx = selection[0] # selected loc id
                loc_rows = get_locations()    
                
                # fix IndexError: list index out of range
                if idx < 0 or idx >= len(loc_rows):
                    psg.popup_error('Selection out of range. Please refresh and try again.')
                    continue
                
                # Assign attributes via loc id
                loc_id, cur_name, cur_addr = loc_rows[idx]

                # Throw edit pop up
                popup = edit_location_popup(loc_id, cur_name, cur_addr)

                while True: # while open
                    popup_event, popup_values = popup.read()
                    # Handle close
                    if popup_event in (psg.WIN_CLOSED, 'Cancel'):
                        popup.close()
                        break

                    # Update record
                    if popup_event == 'Save':
                        # new inputs
                        new_name = popup_values['Location_Name'].strip()
                        new_addr = popup_values['Location_Address'].strip()
                        if not new_name: # require name fix entry break
                            psg.popup_error('Location Name cannot be empty.')
                            continue

                        update_location(loc_id, new_name, new_addr)

                        popup.close()
                        load_locations(window)
                        break
                
        ######## WARRANTY EVENTS ################################################
        # Update warranties drop down
        if event == 'Refresh Warranties':
            # get combo days
            days = int(vals['Warranty_Filter'].strip('< days'))
            load_warranties(window, days)

        ######## LOG EVENTS ########################################################
        # Enable log filtering       
        if event ==  'Log_Filter':
            tag = vals['Log_Filter']
            load_logs(window, tag)

        if event == 'Export Logs':
            asset_filter = window['Log_Filter'].get()  # All or implement tag
            logs = get_transactions(asset_filter)     # [timestamp,tag,model,user,action,notes,from,to]
            # assert 1 exsists
            if not logs:
                psg.popup_error('No log entries to export.')
            else:
                path = export_csv_popup('logs.csv')
                if path:
                    with open(path, 'w', newline='') as f:
                        writer = csv.writer(f)
                        # headers
                        writer.writerow(['Timestamp','Tag','Model', 'User','Action','Notes', 'From Location','To Location'])
                        # dump
                        for row in logs:
                            writer.writerow(row)
                    psg.popup(f'Logs exported to:\n{path}')
            
    window.close()

if __name__ == '__main__':
    main()
