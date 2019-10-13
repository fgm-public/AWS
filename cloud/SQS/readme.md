# Required simple queue service (SQS) instanses

* request-harvest (standart queue)

* harvest-analyze (standart queue)

* analyze-mail (standart queue)

**All of these queues must have 'allow' permission to 'all SQS actions' for SQS access related IAM account**

**All of these queues must have 'queue visibility' timeout not less than appropriate lambda timeout**
