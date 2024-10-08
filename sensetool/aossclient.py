import configparser
import io
import os
import boto3
from botocore.exceptions import NoCredentialsError
from botocore.exceptions import ClientError
from urllib.parse import urlparse
try:
    from aoss_client.client import Client
except:
    pass
from .basic import print_divider

def get_client(*args, boto3=False, **kwargs):
    if not boto3:
        return Client(*args, **kwargs)
    else:
        return AossClient(*args, **kwargs)

class AossClient:
    def __init__(self, endpoint_url=None, access_key=None, secret_key=None):

        if endpoint_url and access_key and secret_key:
            self.endpoint_url = endpoint_url
            self.access_key = access_key
            self.secret_key = secret_key
        else:
            # 获取跟目录路径，统一跟目录为 /mnt/afs/yaotiankuo
            current_directory = os.getcwd().split("/") # ['', 'mnt', 'afs', 'yaotiankuo']
            user_root = "/".join(current_directory[:4])
            # 获取aoss文件，默认aoss.conf在用户跟目录下
            config = configparser.ConfigParser()
            config.read(os.path.join(user_root,'aoss.conf'))

            self.endpoint_url = config['sensetool']['host_base']
            self.access_key = config['sensetool']['access_key']
            self.secret_key = config['sensetool']['secret_key']

        self.session = boto3.session.Session(aws_access_key_id=self.access_key, aws_secret_access_key=self.secret_key)
        self.s3_client = self.session.client('s3', endpoint_url=self.endpoint_url)
        print_divider("初始化client成功")

    def _parse_url(self, file_path):
        assert file_path.startswith('s3://')
        parsed_url = urlparse(file_path)
        bucket = parsed_url.netloc
        prefix = file_path[file_path.find(bucket) + len(bucket):].lstrip("/")
        return bucket, prefix
        

    def get_file_iter(self, file_path):
        bucket, prefix = self._parse_url(file_path)

        try:
            # Use the paginator to handle buckets with many objects
            paginator = self.s3_client.get_paginator('list_objects')
            for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
                for obj in page.get('Contents', []):
                    yield 's3://' + bucket + '/' + obj['Key']
        except NoCredentialsError:
            print("Credentials not available")
        except Exception as e:
            print(f"An error occurred: {e}")

    def get(self, file_path):
        return self.get_file(file_path)
    
    def get_file(self, file_path):
        bucket, prefix = self._parse_url(file_path)
        try:
            # Fetch the file from S3
            response = self.s3_client.get_object(Bucket=bucket, Key=prefix)
            
            # Read the content of the file
            file_content = response['Body'].read()
            return file_content

        except NoCredentialsError:
            print("Credentials are not available")
        except Exception as e:
            print(f"An error occurred: {e}")
    
    def put(self, file_path, data):
        bucket, prefix = self._parse_url(file_path)
        fp = io.BytesIO()
        fp.write(data)
        fp.seek(0)
        response = self.s3_client.upload_fileobj(fp, bucket, prefix)
        return response