
# AWS SDK for Python
import boto3

# MongoDB access string
mongo = ('mongodb+srv://'
         'UserName:'
         'X9xX9xX9xX9xX9xX9xX9'
         '@cluster0-r4vye.mongodb.net/test'
         '?retryWrites=true&w=majority'
    )

# AWS S3 storage instance with credentials
s3 = boto3.client('s3',
        region_name='us-east-2',
        aws_access_key_id='X0X0X0X0X0X0X0X0X0X0',
        aws_secret_access_key='X1xX1xX1xX1xX1xX1xX1xX1xX1xX1xX1xX1xX1xX'
    )

# AWS SQS queue access credentials
sqs = boto3.client('sqs',
        region_name='us-east-2',
        aws_access_key_id='X0X0X0X0X0X0X0X0X0X0',
        aws_secret_access_key='X1xX1xX1xX1xX1xX1xX1xX1xX1xX1xX1xX1xX1xX'
    )

# AWS SQS queue instances    
outgoing_queue = 'https://sqs.us-east-2.amazonaws.com/123456789010/myqueue'

incoming_queue = 'https://sqs.us-east-2.amazonaws.com/123456789010/myiqueue'