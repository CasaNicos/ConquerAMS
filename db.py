import mysql.connector
from mysql.connector import errorcode
from datetime import date, timedelta

########################### MYSQL Config ###############################################################################
DB_CONFIG = {
    'user': 'nico', # Recorded username
    'password': 'nico', # Recorded password
    'host': '127.0.0.1', # LOcalhost
    'database': 'CHW_AMS', # Recorded schema
    'raise_on_warnings': True
}

# Return successful connection to DB, error if not
def get_connection():
    try:
        c = mysql.connector.connect(**DB_CONFIG) # **Unpack dictionary
        return c
    except mysql.connector.Error as err: # Catch mysql errors send output
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Wrong user or password")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Database does not exist")
        else: # Throw others
            print(err)
        raise

########################### Table Initialization ###############################################################################
# Initializes all tables if they don’t already exist
# Run on startup to make sure DB is ready
def initialize_schema():
    connection = get_connection() # Start connection
    cursor = connection.cursor() # Cursor = query excecutor, ready executions
    # Initialize tables
    queries = [
        """
        CREATE TABLE IF NOT EXISTS locations (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            address VARCHAR(512)
        ) ENGINE=InnoDB
        """,
        """
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            full_name VARCHAR(255) NOT NULL,
            department VARCHAR(255),
            job_title VARCHAR(255),
            location_id INT,
            email VARCHAR(255),
            username VARCHAR(100) UNIQUE,
            FOREIGN KEY (location_id) REFERENCES locations(id)
                ON DELETE SET NULL ON UPDATE CASCADE
        ) ENGINE=InnoDB
        """,
        """
        CREATE TABLE IF NOT EXISTS assets (
            id INT AUTO_INCREMENT PRIMARY KEY,
            tag VARCHAR(100) UNIQUE NOT NULL,
            make VARCHAR(255),
            model VARCHAR(255),
            purchase_date DATE,
            warranty_expiry DATE,
            status VARCHAR(50),
            location_id INT,
            FOREIGN KEY (location_id) REFERENCES locations(id)
                ON DELETE SET NULL ON UPDATE CASCADE
        ) ENGINE=InnoDB
        """,
        """
        CREATE TABLE IF NOT EXISTS transactions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            asset_id INT NOT NULL,
            user_id INT NOT NULL,
            action VARCHAR(50) NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            notes TEXT,
            from_location INT,
            to_location INT,
            FOREIGN KEY (asset_id) REFERENCES assets(id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (from_location) REFERENCES locations(id),
            FOREIGN KEY (to_location) REFERENCES locations(id)
        ) ENGINE=InnoDB
        """
    ]
    
    # Run each query above
    for init_query in queries:
        try:
            cursor.execute(init_query)
        except mysql.connector.Error as err: # Catch mysql table exsists error and ignore
            if err.errno == errorcode.ER_TABLE_EXISTS_ERROR:
                continue
            else: # Catch other errors and quit
                cursor.close() # Cursor close first, then connection
                connection.close()
                raise
    
    connection.commit() # Commit changes. Different than work SSMS bc this is transaction based not immediate
    cursor.close()
    connection.close()

########################### CRUD Actions ###############################################################################
########################## ASSETS ##########################
def get_assets():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True) # Dictionary returns a dictionary not tuples
    
    # Select *, join location for locationid
    cursor.execute("""
        SELECT a.id, a.tag,  a.make, a.model,a.purchase_date,a.warranty_expiry,a.status, l.name AS location
        FROM assets a
        LEFT JOIN locations l ON a.location_id = l.id
        ORDER BY a.tag
    """)
    rows = cursor.fetchall() # Gets entries returned by query
    cursor.close()
    connection.close()

    # Return entries as 8 parsed elements
    return [(
        r['id'], r['tag'], r['make'], r['model'],
        r['purchase_date'].isoformat() if r['purchase_date'] else '', # Format for date, else NULL
        r['warranty_expiry'].isoformat() if r['warranty_expiry'] else '',
        r['status'], r['location'] or ''
    ) for r in rows]

# Need each elements passed in IN ORDER
def insert_asset(tag, make, model, purchase_date, warranty_expiry, status, location_id):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute( # Insert query requires elements IN ORDER
        "INSERT INTO assets (tag,make,model,purchase_date,warranty_expiry,status,location_id)" " VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (tag, make, model, purchase_date, warranty_expiry, status, location_id)
    )
    connection.commit()
    cursor.close()
    connection.close()

# Set each element as NONE to fix NULL PARAMETER EXITING issue
def update_asset(id_, tag=None, make=None, model=None, purchase_date=None, warranty_expiry=None, status=None, location_id=None):
    fields = [] # Stores new element assignments with columnname 'make=%s'
    params = [] # Stores new element values 'Dell'
    # Update passed in fields 
    if tag is not None:
        fields.append("tag=%s"); params.append(tag)
    if make is not None:
        fields.append("make=%s"); params.append(make)
    if model is not None:
        fields.append("model=%s"); params.append(model)
    if purchase_date is not None:
        fields.append("purchase_date=%s"); params.append(purchase_date)
    if warranty_expiry is not None:
        fields.append("warranty_expiry=%s"); params.append(warranty_expiry)
    if status is not None:
        fields.append("status=%s"); params.append(status)
    if location_id is not None:
        fields.append("location_id=%s"); params.append(location_id)
    
    # No update  edge case
    if not fields: 
        return
    
    # Build the update query. ADDED COMMA BC SYNTAX ERROR
    update_query = f"UPDATE assets SET {', '.join(fields)} WHERE id=%s"
    params.append(id_) # Add id for where modifier

    connection = get_connection()
    cursor = connection.cursor()
    # Supplies built query then passed in parameters
    cursor.execute(update_query, params)
    connection.commit()
    cursor.close()
    connection.close()

# Delete whole entry via passed in id
def delete_asset(id_):
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("DELETE FROM assets WHERE id=%s", (id_,))
        connection.commit()
    except mysql.connector.IntegrityError as e: 
        if e.errno == errorcode.ER_ROW_IS_REFERENCED_2: # MySQL error when object has entries in transactions
            raise ValueError("Cannot delete asset with log history. Please retire the asset instead.")
        else:
            raise
    finally:
        cursor.close()
        connection.close()

########################## USERS ##########################
# Same as assets
def get_users():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("""
        SELECT u.id, u.full_name, u.department, u.job_title,
               l.name AS location, u.email, u.username
          FROM users u
          LEFT JOIN locations l ON u.location_id = l.id
         ORDER BY u.full_name
    """)
    rows = cursor.fetchall()
    cursor.close()
    connection.close()
    return [(
        r['id'], r['full_name'], r['department'],
        r['job_title'], r['location'] or '',
        r['email'], r['username']
    ) for r in rows]

# Same as assets
def insert_user(full_name, department, job_title, location_id, email, username):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        "INSERT INTO users (full_name,department,job_title,location_id,email,username)"
        " VALUES (%s, %s, %s, %s, %s, %s)",
        (full_name, department, job_title, location_id, email, username)
    )
    connection.commit()
    cursor.close()
    connection.close()

# Same as assets
def update_user(id_, full_name=None, department=None, job_title=None, location_id=None, email=None, username=None):
    fields = []
    params = []
    if full_name is not None:
        fields.append("full_name=%s"); params.append(full_name)
    if department is not None:
        fields.append("department=%s"); params.append(department)
    if job_title is not None:
        fields.append("job_title=%s"); params.append(job_title)
    if location_id is not None:
        fields.append("location_id=%s"); params.append(location_id)
    if email is not None:
        fields.append("email=%s"); params.append(email)
    if username is not None:
        fields.append("username=%s"); params.append(username)
    if not fields:
        return
    
    update_query = f"UPDATE users SET {', '.join(fields)} WHERE id=%s"
    params.append(id_)

    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(update_query, params)
    connection.commit()
    cursor.close()
    connection.close()

# Same as assets
def delete_user(id_):
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("DELETE FROM users WHERE id=%s", (id_,))
        connection.commit()
    except mysql.connector.IntegrityError as e:
        if e.errno == errorcode.ER_ROW_IS_REFERENCED_2: # MySQL error when object has entries in transactions
            raise ValueError("Cannot delete user with log history. Consider updating 'Job Title' or 'Name' to 'RESIGNED'.")
        else:
            raise
    finally:
        cursor.close()

########################## LOCATIONS ##########################
# Same structure as other tables
def get_locations():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT id, name, address FROM locations ORDER BY name")
    rows = cursor.fetchall()

    cursor.close()
    connection.close()

    return [(r['id'], r['name'], r['address'] or '') for r in rows]

# Same structure as other tables
def insert_location(name, address):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("INSERT INTO locations (name,address) VALUES (%s, %s)", (name, address))
    connection.commit()

    cursor.close()
    connection.close()

# Same structure as other tables
def update_location(id_, name=None, address=None):
    fields = []
    params = []
    if name is not None:
        fields.append("name=%s"); params.append(name)
    if address is not None:
        fields.append("address=%s"); params.append(address)
    if not fields:
        return
    
    update_query = f"UPDATE locations SET {', '.join(fields)} WHERE id=%s"
    params.append(id_)

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(update_query, params)
    connection.commit()

    cursor.close()
    connection.close()

# Same structure as other tables
def delete_location(id_):
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("DELETE FROM locations WHERE id=%s", (id_,))
        connection.commit()
    except mysql.connector.IntegrityError as e:
        if e.errno == errorcode.ER_ROW_IS_REFERENCED_2: # MySQL error when object has entries in transactions
            raise ValueError("Cannot delete location that is linked to users, assets, or transactions. Please label as 'Retired_Location'")
        else:
            raise
    finally:
        cursor.close()
        connection.close()

########################## TRANSACTIONS ##########################-
# Basic insert query no idenitfying params needed
def log_transaction(asset_id, user_id, action, notes='', from_loc=None, to_loc=None):
    connection = get_connection()
    cursor = connection.cursor()

    # Insert passed in elements
    cursor.execute(
        "INSERT INTO transactions "
        "(asset_id,user_id,action,notes,from_location,to_location) VALUES (%s,%s,%s,%s,%s,%s)",
        (asset_id, user_id, action, notes, from_loc, to_loc)
    )

    connection.commit()
    cursor.close()
    connection.close()

# Select * queries for filtered and unfiltered logs
def get_transactions(filter_asset_tag=None):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    # added for filter by asset (-LOG_ASSET_FILTER-) button
    if filter_asset_tag and filter_asset_tag != 'All':
        cursor.execute("""
            SELECT t.timestamp, a.tag, a.model, u.full_name,
                   t.action, t.notes, fl.name AS from_loc, tl.name AS to_loc
              FROM transactions t
              JOIN assets a ON t.asset_id = a.id
              JOIN users u ON t.user_id = u.id
              LEFT JOIN locations fl ON t.from_location = fl.id
              LEFT JOIN locations tl ON t.to_location = tl.id
             WHERE a.tag = %s
             ORDER BY t.timestamp DESC
        """, (filter_asset_tag,))
    else: # Emprty where modifier
        cursor.execute("""
            SELECT t.timestamp, a.tag, a.model, u.full_name,
                   t.action, t.notes, fl.name AS from_loc, tl.name AS to_loc
              FROM transactions t
              JOIN assets a ON t.asset_id = a.id
              JOIN users u ON t.user_id = u.id
              LEFT JOIN locations fl ON t.from_location = fl.id
              LEFT JOIN locations tl ON t.to_location = tl.id
             ORDER BY t.timestamp DESC
        """ )

    # Returned entries
    rows = cursor.fetchall()

    cursor.close()
    connection.close()

    # Parse 
    return [[
        r['timestamp'], r['tag'], r['model'], r['full_name'],
        r['action'], r['notes'], r['from_loc'] or '', r['to_loc'] or ''
    ] for r in rows]

########################## HELPER FUNCTIONS ##########################

# Returns next available asset tag
def get_next_asset_tag():
    connection = get_connection()
    cursor = connection.cursor()

    # Check last id (max(id)) on assets, +1 = next id
    cursor.execute("SELECT COALESCE(MAX(id),0) + 1 FROM assets")
    next_id = cursor.fetchone()[0] # Fets first row, 1 value

    cursor.close()
    connection.close()

    # Alter returned Asset Tag (leading zeros for now)
    return f"A{next_id:04d}" 

# Returns list of assets within warranty window
def get_warranties_within(days=30):
    # Calculate today + window returns formatted
    cutoff = (date.today() + timedelta(days=days)).isoformat() 

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        "SELECT tag, model, warranty_expiry, status "
        "FROM assets WHERE warranty_expiry <= %s "
        "ORDER BY warranty_expiry ASC",
        (cutoff,)
    )
    rows = cursor.fetchall()

    cursor.close()
    connection.close()

    # list
    return [[
        r['tag'], r['model'], r['warranty_expiry'], r['status']
    ] for r in rows]

# Take locationName grab ID
def map_location_name_to_id(name):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT id FROM locations WHERE name = %s", (name,))
    row = cursor.fetchone() # GRab top row

    cursor.close()
    connection.close()

    # if row if populated
    return row[0] if row else None