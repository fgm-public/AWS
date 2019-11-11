
# Some send mail stuff:
from smtplib         import SMTP_SSL
from email.mime.text import MIMEText
from email.header    import Header
# Application admin email credentials:
from credentials     import mail_creds

class MailSender:
    '''
    ----------------------------------------    
    Class is designed to send email messages
    ----------------------------------------
    Public methods:
        send_email()
    ----------------------------------------
    '''

    # Email address from which the message will be sent 
    source = mail_creds['source']
    # Its password
    password = mail_creds['password']
    # Its SMTP mail server 
    server = mail_creds['smtp_server']

    def __init__(self, destinations, subject, body):
        # Email message body
        self.message = MIMEText(body, 'plain', 'utf-8')
        # Email message subject
        self.message['Subject'] = Header(subject, 'utf-8')
        # Email address from which the message will be sent 
        self.message['From'] = MailSender.source
        # Email address to which the message will be sent
        self.destinations = destinations
        self.message['To'] = ', '.join(destinations)

    def send_email(self):
        '''This method forms and sends e-mail message'''
        # Instantiate mail sender context
        with SMTP_SSL(MailSender.server) as server:
            # Enable debug output
            server.set_debuglevel(1)
            # Some authentication and authorizations
            server.login(MailSender.source, MailSender.password)
            # Send email
            server.sendmail(self.message['From'],
                            self.destinations,
                            self.message.as_string())

# Checks importing issue
if __name__ == "__main__":
    # Send test email
    mail = MailSender( [mail_creds['admin'],],
                      'Тестовое сообщение',
                      'Ответ не требуется' )
    mail.send_email()
