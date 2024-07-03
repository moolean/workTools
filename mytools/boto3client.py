import io
import boto3
from botocore.exceptions import NoCredentialsError
from botocore.exceptions import ClientError
from urllib.parse import urlparse

boto3cfg = {
    'endpoint_url': 'http://aoss-internal.ms-sc-01.maoshanwangtechapi-oss.com/',
    'access_key': 'CB7A484694494A748C22282351B3E05C',
    'secret_key': 'C1B454B615104F4FB2F9436CD3667B70',
}

# boto3cfg = {
#     'endpoint_url': 'http://aoss-internal.cn-sh-01.sensecoreapi-oss.cn/',
#     'access_key': 'AE939C3A07AE4E6D93908AA603B9F3A9',
#     'secret_key': 'EA3CA6A34B2747AC8ED79CB1838424E0',
# }

class Boto3Client:
    def __init__(self, endpoint_url=None, access_key=None, secret_key=None):
        if endpoint_url is None:
            endpoint_url = boto3cfg['endpoint_url']
        if access_key is None:
            access_key = boto3cfg['access_key']
        if secret_key is None:
            secret_key = boto3cfg['secret_key']
        self.endpoint_url = endpoint_url
        self.access_key = access_key
        self.secret_key = secret_key

        self.session = boto3.session.Session(aws_access_key_id=access_key, aws_secret_access_key=secret_key)
        self.s3_client = self.session.client('s3', endpoint_url=endpoint_url)
    
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