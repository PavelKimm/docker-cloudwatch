# Docker + AWS CloudWatch

This script helps to create a Docker container with specific image and send 
its output to AWS CloudWatch.

<br>Firstly, you need to install requirements:

`pip install -r requirements.txt`

<br>Now you can run the program, it has the following arguments:

--docker-image – Name of a Docker image

--bash-command – Bash command (to run inside the Docker image)

--aws-cloudwatch-group – Name of an AWS CloudWatch group

--aws-cloudwatch-stream – Name of an AWS CloudWatch stream

--aws-access-key-id – AWS access key ID

--aws-secret-access-key – AWS secret access key

--aws-region – Name of an AWS region

### Example:
```bash
python docker_script.py
 --docker-image ubuntu
 --bash-command "some command"
 --aws-cloudwatch-group my_group
 --aws-cloudwatch-stream my_stream
 --aws-access-key-id access_key
 --aws-secret-access-key secret_key
 --aws-region eu-north-1
 ```
