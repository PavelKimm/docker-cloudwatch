import time
import argparse
import logging
from boto3 import Session
import docker
from enum import Enum

logging.getLogger().setLevel(logging.INFO)


class DockerContainerStatus(Enum):
    CREATED = 'created'
    RUNNING = 'running'


def get_args():
    """
    Get required arguments from CLI
    """
    parser = argparse.ArgumentParser(
        description='Run a command inside a Docker container and send logs to AWS CloudWatch')

    parser.add_argument('--docker-image', required=True, help='Name of a Docker image')
    parser.add_argument('--bash-command', required=True, help='Bash command (to run inside the Docker image)')
    parser.add_argument(
        '--aws-cloudwatch-group', required=True, dest='cw_group', help='Name of an AWS CloudWatch group')
    parser.add_argument(
        '--aws-cloudwatch-stream', required=True, dest='cw_stream', help='Name of an AWS CloudWatch stream')
    parser.add_argument('--aws-access-key-id', required=True, dest='aws_access_key', help='AWS access key ID')
    parser.add_argument('--aws-secret-access-key', required=True, dest='aws_secret_key', help='AWS secret access key')
    parser.add_argument('--aws-region', required=True, dest='aws_region', help='Name of an AWS region')

    args_ = parser.parse_args()
    return args_

def create_cw_group_if_not_exists(client, group_name):
    """
    Create CloudWatch log group if it doesn't exist
    """
    try:
        client.create_log_group(logGroupName=group_name)
    except client.exceptions.ResourceAlreadyExistsException:
        logging.info('CloudWatch group already exists')

def create_cw_stream_if_not_exists(client, group_name, stream_name):
    """
    Create CloudWatch log stream in specific group if it doesn't exist
    """
    try:
        client.create_log_stream(logGroupName=group_name, logStreamName=stream_name)
    except client.exceptions.ResourceAlreadyExistsException:
        logging.info('CloudWatch stream already exists')

def send_logs_to_aws_cw(client, container, group_name, stream_name):
    """
    Send output of the Docker container to CloudWatch
    """
    try:
        while container.status in [DockerContainerStatus.CREATED.value,
                                   DockerContainerStatus.RUNNING.value]:
            container.reload()
            logs = container.logs()
            if logs:
                log_events = [{'timestamp': int(time.time() * 1000),
                               'message': log.decode('utf-8')} for log in logs.splitlines() if log]
                try:
                    res = client.put_log_events(logGroupName=group_name, logStreamName=stream_name,
                                                logEvents=log_events)
                    if res.get('rejectedLogEventsInfo'):
                        logging.warning('Some log events were rejected by CloudWatch')
                except Exception as e:
                    logging.error('Failed to put log event to CloudWatch: %s' % e)
    except KeyboardInterrupt:
        logging.info('Stopping the container...')
        container.stop()


def main():
    try:
        args = get_args()

        # AWS section
        aws_session = Session(aws_access_key_id=args.aws_access_key,
                              aws_secret_access_key=args.aws_secret_key,
                              region_name=args.aws_region)
        cw_logs_client = aws_session.client('logs')
        create_cw_group_if_not_exists(cw_logs_client, args.cw_group)
        create_cw_stream_if_not_exists(cw_logs_client, args.cw_group, args.cw_stream)

        # Docker section
        docker_client = docker.from_env()
        try:
            container = docker_client.containers.create(args.docker_image, args.bash_command, detach=True)
            container.start()
        except docker.errors.APIError as e:
            logging.error('Failed to create and start a docker container: %s' % e)
            return

        # Send output logs to CloudWatch while container is running
        send_logs_to_aws_cw(cw_logs_client, container, args.cw_group, args.cw_stream)

    finally:
        # Try to remove container after it stops
        try:
            container.remove()
            logging.info('Docker container was removed')
        except (docker.errors.NotFound, NameError):
            logging.info('Container already removed')
        except docker.errors.APIError:
            container.remove(force=True)
            logging.info('Docker container was force removed')


if __name__ == '__main__':
    main()
