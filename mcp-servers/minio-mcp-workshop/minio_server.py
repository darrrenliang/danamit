import os
import io
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from mcp.server.fastmcp import FastMCP

# Initialize MCP Server
mcp = FastMCP("MinIO-SRE-Toolbox")

# --- Configuration & Security ---
# Comma-separated list of buckets the AI is allowed to access
# Leave empty to allow all buckets (not recommended for production)
ALLOWED_BUCKETS = os.getenv("ALLOWED_BUCKETS", "").split(",")
# Global limit for text previews to prevent Token overflow (1MB)
PREVIEW_LIMIT_BYTES = 1024 * 1024 

def get_s3_client():
    """Returns a boto3 client configured for MinIO."""
    return boto3.client(
        's3',
        endpoint_url=os.getenv("MINIO_ENDPOINT", "http://localhost:9000"),
        aws_access_key_id=os.getenv("MINIO_ACCESS_KEY"),
        aws_secret_access_key=os.getenv("MINIO_SECRET_KEY"),
        config=Config(signature_version='s3v4', s3={'addressing_style': 'path'}),
        region_name='us-east-1'
    )

def validate_bucket_access(bucket: str):
    """Restricts access to unauthorized buckets."""
    if ALLOWED_BUCKETS and ALLOWED_BUCKETS[0] != "" and bucket not in ALLOWED_BUCKETS:
        raise PermissionError(f"Access Denied: Bucket '{bucket}' is not in the allowed list.")

# --- MCP Tools ---

@mcp.tool()
def list_objects(bucket: str, prefix: str = "") -> list:
    """
    Lists objects in a specified bucket.
    Supports prefix filtering for directory-like navigation.
    """
    validate_bucket_access(bucket)
    s3 = get_s3_client()
    
    paginator = s3.get_paginator('list_objects_v2')
    object_metadata = []
    
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        if 'Contents' in page:
            for obj in page['Contents']:
                object_metadata.append({
                    "Key": obj['Key'],
                    "Size_KB": round(obj['Size'] / 1024, 2),
                    "LastModified": str(obj['LastModified'])
                })
    return object_metadata

@mcp.tool()
def get_object_metadata(bucket: str, key: str) -> dict:
    """
    Retrieves metadata for a specific object.
    Use this to check file size before attempting to read.
    """
    validate_bucket_access(bucket)
    s3 = get_s3_client()
    response = s3.head_object(Bucket=bucket, Key=key)
    
    return {
        "Key": key,
        "Size_MB": round(response['ContentLength'] / (1024 * 1024), 2),
        "ContentType": response.get('ContentType'),
        "LastModified": str(response.get('LastModified')),
        "Metadata": response.get('Metadata', {})
    }

@mcp.tool()
def preview_text_object(bucket: str, key: str, size_kb: int = 1024) -> str:
    """
    Reads the beginning of a text file (up to 1MB).
    Ideal for inspecting K8s manifests, config files, or log headers.
    """
    validate_bucket_access(bucket)
    s3 = get_s3_client()
    
    # Enforce a 1MB hard cap to protect the LLM context window
    request_bytes = min(size_kb, 1024) * 1024
    range_header = f"bytes=0-{request_bytes - 1}"
    
    try:
        response = s3.get_object(Bucket=bucket, Key=key, Range=range_header)
        data = response['Body'].read()
        content = data.decode('utf-8', errors='replace')
        
        # Extract total size from Content-Range header (e.g., "bytes 0-1023/5000000")
        total_size = response.get('ContentRange', '').split('/')[-1]
        
        header = f"--- Preview (Read {len(data)/1024:.1f}KB / Total {total_size} bytes) ---\n"
        return header + content
    except ClientError as e:
        return f"Read failed: {str(e)}"

@mcp.tool()
def read_log_tail(bucket: str, key: str, lines: int = 100) -> str:
    """
    Reads the last N lines of a file.
    Efficiently fetches only the end of the file using S3 Range Requests.
    """
    validate_bucket_access(bucket)
    s3 = get_s3_client()
    
    # Get total file size
    meta = s3.head_object(Bucket=bucket, Key=key)
    file_size = meta['ContentLength']
    
    # Fetch the last 128KB which usually contains several hundred lines
    read_offset = max(0, file_size - (128 * 1024))
    response = s3.get_object(Bucket=bucket, Key=key, Range=f"bytes={read_offset}-")
    content = response['Body'].read().decode('utf-8', errors='ignore')
    
    # Return the requested number of lines
    tail_content = "\n".join(content.splitlines()[-lines:])
    return tail_content

@mcp.tool()
def put_object(bucket: str, key: str, content: str, content_type: str = "text/plain"):
    """
    Uploads text content to MinIO.
    Useful for saving AI-generated configs or reports directly to storage.
    """
    validate_bucket_access(bucket)
    s3 = get_s3_client()
    s3.put_object(
        Bucket=bucket, 
        Key=key, 
        Body=content.encode('utf-8'),
        ContentType=content_type
    )
    return f"Successfully uploaded to {bucket}/{key}"

@mcp.tool()
def get_presigned_download_url(bucket: str, key: str, expires_in: int = 3600) -> str:
    """
    Generates a temporary download link for large or binary files.
    The link expires in 1 hour by default.
    """
    validate_bucket_access(bucket)
    s3 = get_s3_client()
    url = s3.generate_presigned_url(
        'get_object', 
        Params={'Bucket': bucket, 'Key': key}, 
        ExpiresIn=expires_in
    )
    return url

if __name__ == "__main__":
    mcp.run()