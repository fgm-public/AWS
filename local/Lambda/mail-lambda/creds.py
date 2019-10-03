
# AWS SDK for Python
import boto3

# E-mail credentials
email = 'mail@.yandex.ru'
password = 'xxx'
smtp_server = 'smtp.yandex.com'

# AWS SQS queue access credentials
sqs = boto3.client('sqs',
        region_name='us-east-2',
        aws_access_key_id='X0X0X0X0X0X0X0X0X0X0',
        aws_secret_access_key='X1xX1xX1xX1xX1xX1xX1xX1xX1xX1xX1xX1xX1xX'
    )

# AWS SQS queue instance    
queue = 'https://sqs.us-east-2.amazonaws.com/123456789010/report.fifo'