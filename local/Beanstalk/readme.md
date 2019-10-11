# Testing environment preparation

1. Set filesystem location to the root directory of your Beanstalk project:

>

    shell> cd ~AWS\local\Beanstalk\request-beanstalk

2. Set **'FLASK_APP'** OS environment variable to value which corresponds with your Flask app file. PowerShell sample listed below (you may want to see your OS documentation, in other cases):

>

    PS> $env:FLASK_APP='application.py'

3. Then, run Flask:

>

    shell> flask run

4. Open ['http://127.0.0.1:5000/'](http://127.0.0.1:5000/) in your web browser.

5. See debug info in your shell.
