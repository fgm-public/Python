
#!/usr/bin/env python3

###############################################################################
#                                                                             #
#     This script runs by OS timer and searches freshly ordered reports.      #
#   If any exists, it starts data harvest and processing. After, it stores    #
#     report to the appropriate directory and sends email notification        #
#       with success message to application admin and report customer.        #
#      Finally, it closes the order issue by change order data status.        #
#                                                                             #
###############################################################################
####   This is SERVER version, intended for deploying to OS environment!   ####
###############################################################################

# MongoDB connection stuff:
from pymongo import MongoClient
# Our send mail class:
from mailsender import MailSender
# Our credentials:
from credentials import mongo, mail_creds

# Email message subjects
problem = 'Laboranalysis application ran into an issue'
success = 'Ваш отчёт готов!'

# This function tries to get an orders from MongoDB
def get_orders_from_mongo():
    # Instantiate MongoDB connection context
    with MongoClient(mongo) as mongodb:
        # Connection to 'orders' collection of 'hh_reports' database
        collection = mongodb.hh_reports['orders']
        # Search for orders
        orders = [order for order in (collection.find({}))]
        if orders:
            for order in orders:
                # If it's vacancy order
                if 'occupation' in order.keys():
                    start_request(order)
                # If it's resume order
                else:
                    start_parse(order)

# This function makes vacancies retrievement and analyze process
def start_request(order):
    # Try to make processing on geted order
    try:
        # Import our vacancy processing class
        from laboranalysis.vacancyhandler import VacancyHandler
        vacancies = VacancyHandler(order.get('occupation'))
        vacancies.analyze()
        vacancies.store_vacancies_to_mongo()
        vacancies.store_results_to_xlsx()
        change_order_status(order)
    # If run into an issue, notificates application admin
    except:
        mail = MailSender( [mail_creds['admin']], 
                            problem,
                            str(order) )
        mail.send_email()
    # If completes successfully,
    # notificates application admin and order customer
    order_customer = order.get('customer')
    mail = MailSender( [mail_creds['admin'], order_customer],
                        success, 
                        order.get('occupation') )
    mail.send_email()

# This function makes resume retrievement and analyze process
def start_parse(order):
    # Try to make processing on geted order
    try:
        # Import our vacancy processing class
        from laboranalysis.resumehandler import ResumeHandler
        resumes = ResumeHandler(order.get('criteria'))
        resumes.analyze()
        resumes.store_resumes_to_mongo()
        resumes.store_results_to_xlsx()
        change_order_status(order)
    # If run into an issue, notificates application admin
    except:
        mail = MailSender( [mail_creds['admin']], 
                            problem, 
                            str(order) )
        mail.send_email()        
    # If completes successfully,
    # notificates application admin and order customer
    order_customer = order.get('customer')
    mail = MailSender( [mail_creds['admin'], order_customer],
                        success, 
                        order.get('criteria') )
    mail.send_email()

# This function changes an order status from staging to complete,
# by moving an order document from 'orders' collection to 'complete' collection
def change_order_status(order):
    # Instantiate MongoDB connection context
    with MongoClient(mongo) as mongodb:
        # Connection to 'complete' collection of 'hh_reports' database
        collection = mongodb.hh_reports['complete']
        # Put completed order
        collection.insert_one(order)
        # Connection to 'orders' collection of 'hh_reports' database
        collection = mongodb.hh_reports['orders']
        # Drop completed order
        collection.delete_one(order)

# Checks importing issue
if __name__ == "__main__":
    # Start work
    get_orders_from_mongo()
    