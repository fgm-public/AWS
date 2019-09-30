
# This function sends a freshly generated report to customer.
# This is LOCAL version, intended fot testing purposes only!

# Mail sender:
import smtplib as smtp
from credentials import email, password, smtp_server

def get_message_from_queue(queue):
    pass

# Define function which will form and send e-mail mesage
def send_email():
    subject = 'The vacancies analysis report you ordered'
    dest_email, email_text = get_message_from_queue(queue)
    message = f'From: {email}\nTo: {dest_email}\nSubject: {subject}\n\n{email_text}'
    server = smtp.SMTP_SSL(smtp_server)
    server.set_debuglevel(1)
    server.ehlo(email)
    server.login(email, password)
    server.auth_plain()
    server.sendmail(email, dest_email, message)
    server.quit()
