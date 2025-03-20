from fix_database import fix_database

if __name__ == "__main__":
    print("Running database fix for academic agent suite...")
    if fix_database():
        print("Database fix completed successfully! The application should now work correctly.")
    else:
        print("Database fix encountered an error. Please check the logs for details.") 