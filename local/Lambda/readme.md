# Testing environment preparation

You can simply run code from lambda python files in iPython, arbitrary shell or in your preferred IDE.

# Minimum required set of AWS IAM accounts and policies

* Standard 'AWSLambdaSQSQueueExecutionRole' permission must be added to every auto-created lambda role, to provide access to SQS services.

**All of these lambdas must have 'timeout' property not more than appropriate queues 'queue visibility' property**

