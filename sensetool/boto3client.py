import io
import os
import boto3
from botocore.exceptions import NoCredentialsError
from botocore.exceptions import ClientError
from urllib.parse import urlparse
from .basic import print_divider
import configparser

class Boto3Client:
    def __init__(self, endpoint_url=None, access_key=None, secret_key=None):
        """
        初始化ceph服务，不输入key则默认使用~/.aoss.cnf
        """

        if endpoint_url and access_key and secret_key:
            self.endpoint_url = endpoint_url
            self.access_key = access_key
            self.secret_key = secret_key
        else:
            # 固定的路径前缀
            fixed_part = "/user/"
            # 获取当前工作目录的路径
            current_directory = os.getcwd()
            # 查找固定部分在当前路径中的位置
            fixed_part_index = current_directory.find(fixed_part)
            if fixed_part_index != -1:
                # 提取固定部分之前的所有内容
                path_before_fixed_part = current_directory[:fixed_part_index]
                # 提取用户名部分（固定部分之后的第一段路径）
                remaining_path = current_directory[fixed_part_index + len(fixed_part):]
                username = remaining_path.split(os.sep)[0]
                # 构建用户根目录的完整路径
                user_root = os.path.join(path_before_fixed_part, fixed_part.strip(os.sep), username)
            else:
                user_root = None

            config = configparser.ConfigParser()
            config.read(os.path.join(user_root,'.aoss.conf'))

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
        prefix = parsed_url.path.lstrip("/")
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
            # print(f'bucket={bucket}, prefix={prefix}')
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

if __name__ == '__main__':
    import sys
    client = Boto3Client()
    data = client.get(sys.argv[1])
    print(f'data size: {len(data)}')