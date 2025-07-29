from mysql.connector import pooling

# Database configuration
dbconfig = {
    "host": "localhost",
    "user": "root",
    "password": "0909BH0705VV0102HS",
    "database": "carrykar"
}

# Create the connection pool
connection_pool = pooling.MySQLConnectionPool(pool_name="mypool",
                                              pool_size=10,
                                              **dbconfig)

def get_db_connection():
    """Function to get a connection from the pool."""
    return connection_pool.get_connection()

def close_connection(mydb, mycursor):
    """Function to close the cursor and connection."""
    if mydb.is_connected():
        mycursor.close()
        mydb.close()



# hvkr ncmt qrwd ouia